from typing import Any

from pydantic import BaseModel, Field


class PlotBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    color: str = "#3388ff"
    geometry: dict[str, Any]
    area_m2: float | None = None
    perimeter_m: float | None = None
    cadastral_ref: str | None = None
    notes: str | None = None


class PlotCreate(PlotBase):
    pass


class PlotUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    color: str | None = None
    geometry: dict[str, Any] | None = None
    cadastral_ref: str | None = None
    notes: str | None = None


class PlotRead(PlotBase):
    id: int
    created_at: str
    updated_at: str
