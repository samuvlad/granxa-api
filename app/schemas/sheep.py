from datetime import date

from pydantic import BaseModel, Field

from app.schemas.lote import LoteSummary


VALID_SEXO = {"macho", "femia"}
VALID_ESTADO = {"activo", "vendido", "morto"}


class SheepBase(BaseModel):
    crotal: str
    nome: str | None = None
    sexo: str
    data_nacemento: date
    raca: str = "Gallega"
    estado: str = "activo"
    nai_id: int | None = None
    pai_id: int | None = None
    lote_id: int | None = None
    notas: str | None = None


class SheepCreate(SheepBase):
    pass


class SheepUpdate(BaseModel):
    crotal: str | None = None
    nome: str | None = None
    sexo: str | None = None
    data_nacemento: date | None = None
    raca: str | None = None
    estado: str | None = None
    nai_id: int | None = None
    pai_id: int | None = None
    lote_id: int | None = None
    notas: str | None = None


class SheepRead(SheepBase):
    id: int
    parcela_actual_id: int | None = None
    lote: LoteSummary | None = None
    created_at: str
    updated_at: str
