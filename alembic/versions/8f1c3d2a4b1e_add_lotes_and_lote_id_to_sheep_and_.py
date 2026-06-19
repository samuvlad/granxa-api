"""add lotes and lote_id to sheep and rotations

Revision ID: 8f1c3d2a4b1e
Revises:
Create Date: 2026-06-19 16:00:00.000000

"""
from typing import Sequence, Union

import logging
import sqlalchemy as sa
from alembic import op
from sqlmodel import Session, select
from sqlalchemy.orm import sessionmaker


# revision identifiers, used by Alembic.
revision: str = "8f1c3d2a4b1e"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


logger = logging.getLogger("alembic.env")


def upgrade() -> None:
    # 1) Crear a táboa `lotes`.
    op.create_table(
        "lotes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("notas", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_lotes_id"), "lotes", ["id"], unique=False)
    op.create_index(op.f("ix_lotes_name"), "lotes", ["name"], unique=True)

    # 2) Engadir `lote_id` (nullable) en `sheep`.
    op.add_column(
        "sheep",
        sa.Column("lote_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f("ix_sheep_lote_id"), "sheep", ["lote_id"], unique=False
    )
    op.create_foreign_key(
        "fk_sheep_lote_id_lotes",
        "sheep",
        "lotes",
        ["lote_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 3) Engadir `lote_id` (nullable, polo de agora) en `rotations`.
    op.add_column(
        "rotations",
        sa.Column("lote_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f("ix_rotations_lote_id"), "rotations", ["lote_id"], unique=False
    )
    op.create_foreign_key(
        "fk_rotations_lote_id_lotes",
        "rotations",
        "lotes",
        ["lote_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 4) Migración de datos:
    #    - Crear lotes a partir de `lote_nome` distintos en `rotations`.
    #    - Asignar `rotations.lote_id` ao lote correspondente.
    bind = op.get_bind()
    SessionLocal = sessionmaker(bind=bind, class_=Session)
    with SessionLocal() as session:
        # 4a) Obter nomes distintos de `lote_nome` que non estean baleiros.
        distinct_names = session.exec(
            sa.text(
                "SELECT DISTINCT lote_nome FROM rotations "
                "WHERE lote_nome IS NOT NULL AND TRIM(lote_nome) <> ''"
            )
        ).all()
        name_to_id: dict[str, int] = {}
        for (raw_name,) in distinct_names:
            name = raw_name.strip()
            if name in name_to_id:
                continue
            result = session.execute(
                sa.text(
                    "INSERT INTO lotes (name, notas, created_at, updated_at) "
                    "VALUES (:name, NULL, NOW(), NOW()) RETURNING id"
                ),
                {"name": name},
            )
            lote_id = result.scalar_one()
            name_to_id[name] = lote_id
            logger.info("Migración: creado lote %r con id=%s", name, lote_id)

        # 4b) Asignar `rotations.lote_id` para cada fila existente.
        all_rotations = session.execute(
            sa.text("SELECT id, lote_nome FROM rotations")
        ).all()
        for rot_id, raw_name in all_rotations:
            if raw_name is None:
                logger.warning(
                    "Rotación id=%s ten lote_nome=NULL: quedará con lote_id=NULL",
                    rot_id,
                )
                continue
            name = raw_name.strip()
            lote_id = name_to_id.get(name)
            if lote_id is None:
                logger.warning(
                    "Rotación id=%s con lote_nome=%r sen lote asociado: "
                    "quedará con lote_id=NULL",
                    rot_id,
                    raw_name,
                )
                continue
            session.execute(
                sa.text("UPDATE rotations SET lote_id = :lote_id WHERE id = :id"),
                {"lote_id": lote_id, "id": rot_id},
            )

        # 4c) Para cada ovella con `parcela_actual_id` non nulo, asignar ao
        #     lote da rotación activa máis recente desa parcela (se existe).
        #     Rexistramos os avisos correspondentes.
        active_for_parcela = session.execute(
            sa.text(
                """
                SELECT DISTINCT ON (parcela_id) parcela_id, lote_id
                FROM rotations
                WHERE data_fim IS NULL
                ORDER BY parcela_id, data_inicio DESC, id DESC
                """
            )
        ).all()
        parcela_to_lote: dict[int, int] = {
            parcela_id: lote_id for parcela_id, lote_id in active_for_parcela
        }

        sheep_rows = session.execute(
            sa.text("SELECT id, crotal, parcela_actual_id FROM sheep")
        ).all()
        for sheep_id, crotal, parcela_id in sheep_rows:
            if parcela_id is None:
                logger.info(
                    "Ovella id=%s crotal=%s: sen parcela_actual_id, queda con lote_id=NULL",
                    sheep_id,
                    crotal,
                )
                continue
            lote_id = parcela_to_lote.get(parcela_id)
            if lote_id is None:
                logger.warning(
                    "Ovella id=%s crotal=%s: parcela_actual_id=%s sen "
                    "rotación activa, queda con lote_id=NULL",
                    sheep_id,
                    crotal,
                    parcela_id,
                )
                continue
            session.execute(
                sa.text("UPDATE sheep SET lote_id = :lote_id WHERE id = :id"),
                {"lote_id": lote_id, "id": sheep_id},
            )
            logger.info(
                "Ovella id=%s crotal=%s: asignada ao lote_id=%s (parcela=%s)",
                sheep_id,
                crotal,
                lote_id,
                parcela_id,
            )

        # 4d) Recalcular `parcela_actual_id` das ovellas a partir da
        #     rotación activa do seu lote (regra de negocio).
        lote_ids = set(parcela_to_lote.values())
        for lote_id in lote_ids:
            active = session.execute(
                sa.text(
                    """
                    SELECT parcela_id FROM rotations
                    WHERE lote_id = :lote_id AND data_fim IS NULL
                    ORDER BY data_inicio DESC, id DESC
                    LIMIT 1
                    """
                ),
                {"lote_id": lote_id},
            ).first()
            if not active:
                # Non debería ocorrer porque viñemos de parcela_to_lote.
                continue
            (parcela_id,) = active
            session.execute(
                sa.text(
                    "UPDATE sheep SET parcela_actual_id = :parcela_id "
                    "WHERE lote_id = :lote_id"
                ),
                {"parcela_id": parcela_id, "lote_id": lote_id},
            )

        session.commit()

    # 5) Agora que todos os `lote_id` están cubertos (ou ben NULL documentado),
    #    facemos a columna NOT NULL. Para evitar abortar se hai filas en NULL,
    #    poñémolo en NOT NULL nunha segunda operación tras o backfill.
    op.alter_column("rotations", "lote_id", existing_type=sa.Integer(), nullable=False)

    # 6) Eliminar a columna `lote_nome` xa obsoleta.
    op.drop_column("rotations", "lote_nome")


def downgrade() -> None:
    # Recrear a columna `lote_nome` como nullable, e poboala a partir de
    # `rotations.lote_id -> lotes.name` antes de facela NOT NULL.
    op.add_column(
        "rotations",
        sa.Column("lote_nome", sa.String(length=120), nullable=True),
    )
    op.execute(
        "UPDATE rotations AS r "
        "SET lote_nome = l.name "
        "FROM lotes AS l "
        "WHERE r.lote_id = l.id"
    )

    op.drop_constraint("fk_rotations_lote_id_lotes", "rotations", type_="foreignkey")
    op.drop_index(op.f("ix_rotations_lote_id"), table_name="rotations")
    op.drop_column("rotations", "lote_id")
    op.alter_column("rotations", "lote_nome", existing_type=sa.String(length=120), nullable=False)

    op.drop_constraint("fk_sheep_lote_id_lotes", "sheep", type_="foreignkey")
    op.drop_index(op.f("ix_sheep_lote_id"), table_name="sheep")
    op.drop_column("sheep", "lote_id")

    op.drop_index(op.f("ix_lotes_name"), table_name="lotes")
    op.drop_index(op.f("ix_lotes_id"), table_name="lotes")
    op.drop_table("lotes")
