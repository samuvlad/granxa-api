from typing import Any

from pydantic import BaseModel


class PlotBase(BaseModel):
    name: str
    color: str = "#3388ff"
    geometry: dict[str, Any]
    area_m2: float | None = None
    perimeter_m: float | None = None
    cadastral_ref: str | None = None
    notes: str | None = None


class PlotCreate(PlotBase):
    pass


class PlotUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    geometry: dict[str, Any] | None = None
    cadastral_ref: str | None = None
    notes: str | None = None


class PlotRead(PlotBase):
    id: int
    created_at: str
    updated_at: str
