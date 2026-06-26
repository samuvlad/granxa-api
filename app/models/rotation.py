from datetime import datetime
from typing import Any

from sqlalchemy import (
    Column,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint, TSTZRANGE
from sqlmodel import Field, SQLModel


class Rotation(SQLModel, table=True):
    __tablename__ = "rotations"
    __table_args__ = (
        # Soamente unha rotación activa (data_fim IS NULL) por lote.
        Index(
            "uq_rotations_active_per_lote",
            "lote_id",
            unique=True,
            postgresql_where="data_fim IS NULL",
        ),
        # Index optimizado para get_active_rotation(lote_id).
        Index(
            "ix_rotations_active_lookup",
            "lote_id",
            "data_inicio",
            "id",
            postgresql_where="data_fim IS NULL",
        ),
        # Non pode haber rotacións solapadas do mesmo lote. A columna
        # xerada `duracion` materializa o rango tstzrange(data_inicio,
        # data_fim|infinity) e o exclusion constraint fail o check.
        ExcludeConstraint(
            ("lote_id", "="),
            ("duracion", "&&"),
            name="excl_rotations_lote_overlap",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    parcela_id: int = Field(
        sa_column=Column(
            ForeignKey("plots.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
    lote_id: int = Field(
        sa_column=Column(
            ForeignKey("lotes.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    data_inicio: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True)
    )
    data_fim: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    notas: str | None = Field(default=None)

    # Columna xerada: rango temporal. PostgreSQL rexeita escrituras
    # directas nela, así que non a expomos no modelo para escritura
    # (default=None non afecta porque é GENERATED ALWAYS). Declarámola
    # só para que SQLAlchemy non tente INSERTala.
    duracion: Any = Field(
        sa_column=Column(
            "duracion",
            TSTZRANGE(),
            Computed(
                "tstzrange(data_inicio, COALESCE(data_fim, 'infinity'), '[)')",
                persisted=True,
            ),
            nullable=False,
        ),
    )

    created_at: datetime = Field(
        sa_column=Column(
            "created_at",
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            "updated_at",
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        )
    )
