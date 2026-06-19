from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.lote import LoteSummary


class RotationBase(BaseModel):
    parcela_id: int
    lote_id: int
    data_inicio: datetime
    data_fim: datetime | None = None
    notas: str | None = None


class RotationCreate(RotationBase):
    pass


class RotationUpdate(BaseModel):
    parcela_id: int | None = None
    lote_id: int | None = None
    data_inicio: datetime | None = None
    data_fim: datetime | None = None
    notas: str | None = None


class RotationRead(RotationBase):
    id: int
    lote: LoteSummary | None = None
    created_at: str
    updated_at: str
