from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Column, Date, ForeignKey
from sqlmodel import Field, SQLModel


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class Sheep(SQLModel, table=True):
    __tablename__ = "sheep"

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
    parcela_actual_id: int | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("plots.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    notas: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
