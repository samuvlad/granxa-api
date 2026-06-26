from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    func,
)
from sqlmodel import Field, SQLModel


class Sheep(SQLModel, table=True):
    __tablename__ = "sheep"
    __table_args__ = (
        CheckConstraint("sexo IN ('macho', 'femia')", name="ck_sheep_sexo"),
        CheckConstraint("estado IN ('activo', 'vendido', 'morto')", name="ck_sheep_estado"),
    )

    id: int | None = Field(default=None, primary_key=True)
    crotal: str = Field(unique=True, index=True, max_length=30)
    nome: str | None = Field(default=None, max_length=120)
    sexo: str = Field(max_length=10)
    data_nacemento: date = Field(sa_column=Column(Date, nullable=False, index=True))
    raca: str = Field(default="Gallega", max_length=80)
    estado: str = Field(default="activo", max_length=20, index=True)

    nai_id: int | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("sheep.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    pai_id: int | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("sheep.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    lote_id: int | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("lotes.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )

    notas: str | None = Field(default=None)
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
