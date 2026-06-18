from datetime import datetime, timezone
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import Column, event
from sqlmodel import Field, SQLModel


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class Plot(SQLModel, table=True):
    __tablename__ = "plots"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    color: str = Field(default="#3388ff")
    geometry: Any = Field(
        sa_column=Column(Geometry("POLYGON", srid=4326), nullable=False)
    )
    area_m2: float | None = Field(default=None)
    perimeter_m: float | None = Field(default=None)
    cadastral_ref: str | None = Field(default=None)
    notes: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
