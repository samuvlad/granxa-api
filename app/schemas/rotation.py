from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, field_validator

from app.schemas.lote import LoteSummary


def _to_utc(value: datetime) -> datetime:
    """Normaliza un datetime a UTC; se é tz-naive asúmese UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class RotationBase(BaseModel):
    parcela_id: int
    lote_id: int
    data_inicio: datetime
    data_fim: datetime | None = None
    notas: str | None = None

    @field_validator("data_inicio", "data_fim", mode="after")
    @classmethod
    def _normalize_dt(cls, v: datetime | None) -> datetime | None:
        return _to_utc(v) if v is not None else None


class RotationCreate(RotationBase):
    pass


class RotationUpdate(BaseModel):
    parcela_id: int | None = None
    lote_id: int | None = None
    data_inicio: datetime | None = None
    data_fim: datetime | None = None
    notas: str | None = None

    @field_validator("data_inicio", "data_fim", mode="after")
    @classmethod
    def _normalize_dt(cls, v: datetime | None) -> datetime | None:
        return _to_utc(v) if v is not None else None


class RotationRead(BaseModel):
    id: int
    parcela_id: int
    lote_id: int
    data_inicio: datetime
    data_fim: datetime | None = None
    notas: str | None = None
    lote: LoteSummary | None = None
    created_at: str
    updated_at: str
