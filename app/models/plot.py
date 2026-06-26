from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import Column, DateTime, Index, func
from sqlmodel import Field, SQLModel


class Plot(SQLModel, table=True):
    __tablename__ = "plots"
    __table_args__ = (
        Index(
            "ix_plots_geometry",
            "geometry",
            postgresql_using="gist",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=120, unique=True, index=True)
    color: str = Field(default="#3388ff", max_length=16)
    geometry: Any = Field(
        sa_column=Column(Geometry("POLYGON", srid=4326), nullable=False)
    )
    area_m2: float | None = Field(default=None)
    perimeter_m: float | None = Field(default=None)
    cadastral_ref: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None)
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
