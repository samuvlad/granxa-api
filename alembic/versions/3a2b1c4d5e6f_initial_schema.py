"""initial schema: plots, sheep, rotations (pre-lotes)

Revision ID: 3a2b1c4d5e6f
Revises:
Create Date: 2026-06-01 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry


# revision identifiers, used by Alembic.
revision: str = "3a2b1c4d5e6f"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Necesario para a columna `plots.geometry`.
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # 1) Táboa `plots` (con xeometría PostGIS).
    op.create_table(
        "plots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("color", sa.String(), nullable=False, server_default="#3388ff"),
        sa.Column("geometry", Geometry("POLYGON", srid=4326), nullable=False),
        sa.Column("area_m2", sa.Float(), nullable=True),
        sa.Column("perimeter_m", sa.Float(), nullable=True),
        sa.Column("cadastral_ref", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plots_id"), "plots", ["id"], unique=False)

    # 2) Táboa `sheep` (sen `lote_id`).
    #    As auto-FKs (`nai_id`, `pai_id`) créanse DESPOIS de existir a
    #    táboa porque apuntan a `sheep.id` (auto-referencia).
    op.create_table(
        "sheep",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("crotal", sa.String(length=30), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=True),
        sa.Column("sexo", sa.String(length=10), nullable=False),
        sa.Column("data_nacemento", sa.Date(), nullable=False),
        sa.Column("raca", sa.String(length=80), nullable=False, server_default="Gallega"),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="activo"),
        sa.Column("nai_id", sa.Integer(), nullable=True),
        sa.Column("pai_id", sa.Integer(), nullable=True),
        sa.Column("parcela_actual_id", sa.Integer(), nullable=True),
        sa.Column("notas", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("crotal", name="uq_sheep_crotal"),
        sa.ForeignKeyConstraint(
            ["parcela_actual_id"],
            ["plots.id"],
            name="fk_sheep_parcela_actual_id_plots",
            ondelete="SET NULL",
        ),
    )
    op.create_index(op.f("ix_sheep_id"), "sheep", ["id"], unique=False)
    op.create_index(op.f("ix_sheep_crotal"), "sheep", ["crotal"], unique=True)
    op.create_index(
        op.f("ix_sheep_data_nacemento"), "sheep", ["data_nacemento"], unique=False
    )
    op.create_index(op.f("ix_sheep_estado"), "sheep", ["estado"], unique=False)
    op.create_foreign_key(
        "fk_sheep_nai_id_sheep",
        "sheep",
        "sheep",
        ["nai_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_sheep_pai_id_sheep",
        "sheep",
        "sheep",
        ["pai_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 3) Táboa `rotations` (versión antiga con `lote_nome`, sen `lote_id`).
    op.create_table(
        "rotations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("parcela_id", sa.Integer(), nullable=False),
        sa.Column("lote_nome", sa.String(length=120), nullable=False),
        sa.Column("data_inicio", sa.DateTime(), nullable=False),
        sa.Column("data_fim", sa.DateTime(), nullable=True),
        sa.Column("notas", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["parcela_id"],
            ["plots.id"],
            name="fk_rotations_parcela_id_plots",
            ondelete="CASCADE",
        ),
    )
    op.create_index(op.f("ix_rotations_id"), "rotations", ["id"], unique=False)
    op.create_index(
        op.f("ix_rotations_parcela_id"), "rotations", ["parcela_id"], unique=False
    )
    op.create_index(
        op.f("ix_rotations_data_inicio"), "rotations", ["data_inicio"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_rotations_data_inicio"), table_name="rotations")
    op.drop_index(op.f("ix_rotations_parcela_id"), table_name="rotations")
    op.drop_index(op.f("ix_rotations_id"), table_name="rotations")
    op.drop_table("rotations")

    op.drop_constraint("fk_sheep_pai_id_sheep", "sheep", type_="foreignkey")
    op.drop_constraint("fk_sheep_nai_id_sheep", "sheep", type_="foreignkey")
    op.drop_constraint("fk_sheep_parcela_actual_id_plots", "sheep", type_="foreignkey")
    op.drop_index(op.f("ix_sheep_estado"), table_name="sheep")
    op.drop_index(op.f("ix_sheep_data_nacemento"), table_name="sheep")
    op.drop_index(op.f("ix_sheep_crotal"), table_name="sheep")
    op.drop_index(op.f("ix_sheep_id"), table_name="sheep")
    op.drop_table("sheep")

    op.drop_index(op.f("ix_plots_id"), table_name="plots")
    op.drop_table("plots")
