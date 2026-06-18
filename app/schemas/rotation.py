from datetime import datetime

from pydantic import BaseModel


class RotationBase(BaseModel):
    parcela_id: int
    lote_nome: str
    data_inicio: datetime
    data_fim: datetime | None = None
    notas: str | None = None


class RotationCreate(RotationBase):
    pass


class RotationUpdate(BaseModel):
    parcela_id: int | None = None
    lote_nome: str | None = None
    data_inicio: datetime | None = None
    data_fim: datetime | None = None
    notas: str | None = None


class RotationRead(RotationBase):
    id: int
    created_at: str
    updated_at: str
