from datetime import datetime
from typing import Optional

from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, SQLModel

from app.models.plot import now_utc


class Rotation(SQLModel, table=True):
    __tablename__ = "rotations"

    id: int | None = Field(default=None, primary_key=True)
    parcela_id: int = Field(
        sa_column=Column(
            ForeignKey("plots.id", ondelete="CASCADE"),
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
    data_inicio: datetime = Field(nullable=False, index=True)
    data_fim: datetime | None = Field(default=None, nullable=True)
    notas: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
