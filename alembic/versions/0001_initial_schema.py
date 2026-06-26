"""initial schema: plots, lotes, sheep, rotations

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-26 00:00:00.000000

Esquema relacional san desde o principio. Inclúe:
- PostGIS + btree_gist.
- Timestamps timestamptz con DEFAULT now() + trigger updated_at.
- Constraints de integridade: UNIQUE en nomes, CHECK en sexo/estado.
- Rotacións: columna xerada duracion (tstzrange) + exclusion de solapamento
  + partial unique index para unha soa rotación activa por lote.
- Sen columna sheep.parcela_actual_id (dérivase on read da rotación activa).
- FK rotations.parcela_id con RESTRICT (preserva histórico de rotacións).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry


# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Función PL/pgSQL que actualiza updated_at en cada UPDATE.
# Defínese unha soa vez e os triggers das catro táboas a invocan.
# ---------------------------------------------------------------------------
SET_UPDATED_AT_SQL = """
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""


def _create_updated_at_trigger(table: str) -> None:
    op.execute(
        f"""
        CREATE TRIGGER trg_{table}_updated_at
        BEFORE UPDATE ON {table}
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at()
        """
    )


def upgrade() -> None:
    # Extensións necesarias.
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    # Función compartida set_updated_at().
    op.execute(SET_UPDATED_AT_SQL)

    # ------------------------------------------------------------------
    # plots
    # ------------------------------------------------------------------
    op.create_table(
        "plots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("color", sa.String(length=16), nullable=False, server_default="#3388ff"),
        sa.Column("geometry", Geometry("POLYGON", srid=4326), nullable=False),
        sa.Column("area_m2", sa.Float(), nullable=True),
        sa.Column("perimeter_m", sa.Float(), nullable=True),
        sa.Column("cadastral_ref", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_plots"),
        sa.UniqueConstraint("name", name="uq_plots_name"),
    )
    op.create_index(op.f("ix_plots_id"), "plots", ["id"], unique=False)
    op.create_index("ix_plots_name", "plots", ["name"], unique=False)
    op.execute(
        "CREATE INDEX ix_plots_geometry ON plots USING gist (geometry)"
    )
    _create_updated_at_trigger("plots")

    # ------------------------------------------------------------------
    # lotes
    # ------------------------------------------------------------------
    op.create_table(
        "lotes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("notas", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_lotes"),
        sa.UniqueConstraint("name", name="uq_lotes_name"),
    )
    op.create_index(op.f("ix_lotes_id"), "lotes", ["id"], unique=False)
    op.create_index("ix_lotes_name", "lotes", ["name"], unique=True)
    _create_updated_at_trigger("lotes")

    # ------------------------------------------------------------------
    # sheep
    #
    # Sin parcela_actual_id: a parcela actual dunha ovella derívase on read
    # a partir da rotación activa do seu lote (ver app/services/lotes.py).
    # ------------------------------------------------------------------
    op.create_table(
        "sheep",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("crotal", sa.String(length=30), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=True),
        sa.Column("sexo", sa.String(length=10), nullable=False),
        sa.Column("data_nacemento", sa.Date(), nullable=False),
        sa.Column(
            "raca",
            sa.String(length=80),
            nullable=False,
            server_default="Gallega",
        ),
        sa.Column(
            "estado",
            sa.String(length=20),
            nullable=False,
            server_default="activo",
        ),
        sa.Column("nai_id", sa.Integer(), nullable=True),
        sa.Column("pai_id", sa.Integer(), nullable=True),
        sa.Column("lote_id", sa.Integer(), nullable=True),
        sa.Column("notas", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sheep"),
        sa.UniqueConstraint("crotal", name="uq_sheep_crotal"),
        sa.CheckConstraint("sexo IN ('macho', 'femia')", name="ck_sheep_sexo"),
        sa.CheckConstraint(
            "estado IN ('activo', 'vendido', 'morto')", name="ck_sheep_estado"
        ),
        sa.ForeignKeyConstraint(
            ["nai_id"], ["sheep.id"], name="fk_sheep_nai_id_sheep", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["pai_id"], ["sheep.id"], name="fk_sheep_pai_id_sheep", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["lote_id"], ["lotes.id"], name="fk_sheep_lote_id_lotes", ondelete="SET NULL"
        ),
    )
    op.create_index(op.f("ix_sheep_id"), "sheep", ["id"], unique=False)
    op.create_index(op.f("ix_sheep_crotal"), "sheep", ["crotal"], unique=True)
    op.create_index(
        op.f("ix_sheep_data_nacemento"), "sheep", ["data_nacemento"], unique=False
    )
    op.create_index(op.f("ix_sheep_estado"), "sheep", ["estado"], unique=False)
    op.create_index(op.f("ix_sheep_lote_id"), "sheep", ["lote_id"], unique=False)
    _create_updated_at_trigger("sheep")

    # ------------------------------------------------------------------
    # rotations
    #
    # - parcela_id con RESTRICT: borrar unha parcela con rotacións é un erro
    #   de negocio (perderíase histórico). O router devolve 409.
    # - lote_id con CASCADE: ao borrar un lote, vaise o seu histórico de
    #   rotacións (o borrado de lote xa está restrinxido se ten rotacións).
    # - duracion: columna xerada tstzrange(data_inicio, data_fim|infinity).
    # - exclusion: non pode haber dúas rotacións do mesmo lote con rangos
    #   solapados.
    # - partial unique index: soamente unha rotación activa (data_fim IS NULL)
    #   por lote.
    # ------------------------------------------------------------------
    op.create_table(
        "rotations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("parcela_id", sa.Integer(), nullable=False),
        sa.Column("lote_id", sa.Integer(), nullable=False),
        sa.Column("data_inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_fim", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notas", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "duracion",
            sa.dialects.postgresql.TSTZRANGE(),
            # '[)' => intervalo pechado en inicio, aberto en fin.
            # Se data_fim é NULL, usamos 'infinity' para representar "aberta".
            sa.Computed(
                "tstzrange(data_inicio, COALESCE(data_fim, 'infinity'), '[)')",
                persisted=True,
            ),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_rotations"),
        sa.ForeignKeyConstraint(
            ["parcela_id"],
            ["plots.id"],
            name="fk_rotations_parcela_id_plots",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["lote_id"],
            ["lotes.id"],
            name="fk_rotations_lote_id_lotes",
            ondelete="CASCADE",
        ),
    )
    op.create_index(op.f("ix_rotations_id"), "rotations", ["id"], unique=False)
    op.create_index(
        op.f("ix_rotations_parcela_id"), "rotations", ["parcela_id"], unique=False
    )
    op.create_index(
        op.f("ix_rotations_lote_id"), "rotations", ["lote_id"], unique=False
    )
    op.create_index(
        op.f("ix_rotations_data_inicio"), "rotations", ["data_inicio"], unique=False
    )
    # Partial unique: unha soa rotación activa por lote.
    op.create_index(
        "uq_rotations_active_per_lote",
        "rotations",
        ["lote_id"],
        unique=True,
        postgresql_where=sa.text("data_fim IS NULL"),
    )
    # Index optimizado para get_active_rotation(lote_id).
    op.execute(
        """
        CREATE INDEX ix_rotations_active_lookup
        ON rotations (lote_id, data_inicio DESC, id DESC)
        WHERE data_fim IS NULL
        """
    )
    # Exclusion: non pode haber rotacións solapadas do mesmo lote.
    op.execute(
        """
        ALTER TABLE rotations
        ADD CONSTRAINT excl_rotations_lote_overlap
        EXCLUDE USING gist (lote_id WITH =, duracion WITH &&)
        """
    )
    _create_updated_at_trigger("rotations")


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_rotations_updated_at ON rotations")
    op.execute("ALTER TABLE rotations DROP CONSTRAINT IF EXISTS excl_rotations_lote_overlap")
    op.execute("DROP INDEX IF EXISTS ix_rotations_active_lookup")
    op.drop_index("uq_rotations_active_per_lote", table_name="rotations")
    op.drop_index(op.f("ix_rotations_data_inicio"), table_name="rotations")
    op.drop_index(op.f("ix_rotations_lote_id"), table_name="rotations")
    op.drop_index(op.f("ix_rotations_parcela_id"), table_name="rotations")
    op.drop_index(op.f("ix_rotations_id"), table_name="rotations")
    op.drop_table("rotations")

    op.execute("DROP TRIGGER trg_sheep_updated_at ON sheep")
    op.drop_index(op.f("ix_sheep_lote_id"), table_name="sheep")
    op.drop_index(op.f("ix_sheep_estado"), table_name="sheep")
    op.drop_index(op.f("ix_sheep_data_nacemento"), table_name="sheep")
    op.drop_index(op.f("ix_sheep_crotal"), table_name="sheep")
    op.drop_index(op.f("ix_sheep_id"), table_name="sheep")
    op.drop_table("sheep")

    op.execute("DROP TRIGGER trg_lotes_updated_at ON lotes")
    op.drop_index("ix_lotes_name", table_name="lotes")
    op.drop_index(op.f("ix_lotes_id"), table_name="lotes")
    op.drop_table("lotes")

    op.execute("DROP TRIGGER trg_plots_updated_at ON plots")
    op.execute("DROP INDEX IF EXISTS ix_plots_geometry")
    op.drop_index("ix_plots_name", table_name="plots")
    op.drop_index(op.f("ix_plots_id"), table_name="plots")
    op.drop_table("plots")

    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")
