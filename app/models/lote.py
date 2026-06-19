from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column
from sqlmodel import Field, SQLModel


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class Lote(SQLModel, table=True):
    __tablename__ = "lotes"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True, max_length=120)
    notas: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
