from pydantic import BaseModel, Field


class LoteBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    notas: str | None = None


class LoteCreate(LoteBase):
    pass


class LoteUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    notas: str | None = None


class LoteRead(LoteBase):
    id: int
    created_at: str
    updated_at: str


class LoteSummary(BaseModel):
    """Versión reducida do lote para incluír embebida noutros recursos."""

    id: int
    name: str
