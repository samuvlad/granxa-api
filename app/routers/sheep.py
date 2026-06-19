import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.database import get_session
from app.models import Lote, Plot, Sheep
from app.schemas.lote import LoteSummary
from app.schemas.sheep import (
    VALID_ESTADO,
    VALID_SEXO,
    SheepCreate,
    SheepRead,
    SheepUpdate,
)
from app.services.lotes import derive_parcela_for_lote, recompute_parcela_actual_for_lote


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sheep", tags=["sheep"])


def _lote_summary(session: Session, lote_id: int | None) -> LoteSummary | None:
    if lote_id is None:
        return None
    lote = session.get(Lote, lote_id)
    if not lote:
        return None
    return LoteSummary(id=lote.id, name=lote.name)


def sheep_to_read(session: Session, sheep: Sheep) -> SheepRead:
    parcela_actual_id = derive_parcela_for_lote(session, sheep.lote_id)
    return SheepRead(
        id=sheep.id,
        crotal=sheep.crotal,
        nome=sheep.nome,
        sexo=sheep.sexo,
        data_nacemento=sheep.data_nacemento,
        raca=sheep.raca,
        estado=sheep.estado,
        nai_id=sheep.nai_id,
        pai_id=sheep.pai_id,
        lote_id=sheep.lote_id,
        parcela_actual_id=parcela_actual_id,
        lote=_lote_summary(session, sheep.lote_id),
        notas=sheep.notas,
        created_at=sheep.created_at.isoformat(),
        updated_at=sheep.updated_at.isoformat(),
    )


def _validate_parent(
    session: Session, sheep_id: int, parent_id: int | None, kind: str
) -> None:
    if parent_id is None:
        return
    if parent_id == sheep_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unha ovella non pode ser {kind} de si mesma",
        )
    parent = session.get(Sheep, parent_id)
    if not parent:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{kind.capitalize()} non atopada",
        )
    expected_sexo = "femia" if kind == "nai" else "macho"
    if parent.sexo != expected_sexo:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"O {kind} debe ser unha ovella de sexo {expected_sexo}",
        )


def _validate_lote(session: Session, lote_id: int | None) -> None:
    if lote_id is None:
        return
    if not session.get(Lote, lote_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O lote non existe",
        )


@router.get("/", response_model=list[SheepRead])
def list_sheep(
    lote_id: int | None = Query(default=None, description="Filtrar por lote"),
    session: Session = Depends(get_session),
) -> list[SheepRead]:
    stmt = select(Sheep).order_by(Sheep.id)
    if lote_id is not None:
        stmt = stmt.where(Sheep.lote_id == lote_id)
    sheep_list = session.exec(stmt).all()
    return [sheep_to_read(session, s) for s in sheep_list]


@router.post("/", response_model=SheepRead, status_code=status.HTTP_201_CREATED)
def create_sheep(
    payload: SheepCreate, session: Session = Depends(get_session)
) -> SheepRead:
    crotal = payload.crotal.strip()
    if not crotal:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O crotal é obrigatorio",
        )
    if payload.sexo not in VALID_SEXO:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Sexo non válido (macho|femia)",
        )
    if payload.estado not in VALID_ESTADO:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Estado non válido (activo|vendido|morto)",
        )

    existing = session.exec(select(Sheep).where(Sheep.crotal == crotal)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Xa existe unha ovella con ese crotal",
        )

    _validate_parent(session, 0, payload.nai_id, "nai")
    _validate_parent(session, 0, payload.pai_id, "pai")
    _validate_lote(session, payload.lote_id)

    if "parcela_actual_id" in payload.model_fields_set and payload.parcela_actual_id is not None:
        logger.warning(
            "Ignorando parcela_actual_id=%s en POST /sheep/: dérivase do lote",
            payload.parcela_actual_id,
        )

    parcela_actual_id = derive_parcela_for_lote(session, payload.lote_id)

    sheep = Sheep(
        crotal=crotal,
        nome=(payload.nome or None),
        sexo=payload.sexo,
        data_nacemento=payload.data_nacemento,
        raca=(payload.raca or "Gallega"),
        estado=payload.estado,
        nai_id=payload.nai_id,
        pai_id=payload.pai_id,
        lote_id=payload.lote_id,
        parcela_actual_id=parcela_actual_id,
        notas=payload.notas,
    )
    session.add(sheep)
    session.commit()
    session.refresh(sheep)
    return sheep_to_read(session, sheep)


@router.get("/{sheep_id}", response_model=SheepRead)
def get_sheep(sheep_id: int, session: Session = Depends(get_session)) -> SheepRead:
    sheep = session.get(Sheep, sheep_id)
    if not sheep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ovella non atopada"
        )
    return sheep_to_read(session, sheep)


@router.patch("/{sheep_id}", response_model=SheepRead)
def update_sheep(
    sheep_id: int, payload: SheepUpdate, session: Session = Depends(get_session)
) -> SheepRead:
    sheep = session.get(Sheep, sheep_id)
    if not sheep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ovella non atopada"
        )

    data = payload.model_dump(exclude_unset=True)

    if "parcela_actual_id" in data:
        logger.warning(
            "Ignorando parcela_actual_id=%s en PATCH /sheep/%d: dérivase do lote",
            data.pop("parcela_actual_id"),
            sheep_id,
        )

    if "sexo" in data and data["sexo"] not in VALID_SEXO:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Sexo non válido (macho|femia)",
        )
    if "estado" in data and data["estado"] not in VALID_ESTADO:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Estado non válido (activo|vendido|morto)",
        )

    if "crotal" in data:
        crotal = (data["crotal"] or "").strip()
        if not crotal:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="O crotal é obrigatorio",
            )
        existing = session.exec(
            select(Sheep).where(Sheep.crotal == crotal, Sheep.id != sheep_id)
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Xa existe unha ovella con ese crotal",
            )
        data["crotal"] = crotal

    if "nai_id" in data:
        _validate_parent(session, sheep_id, data["nai_id"], "nai")
    if "pai_id" in data:
        _validate_parent(session, sheep_id, data["pai_id"], "pai")
    if "lote_id" in data:
        _validate_lote(session, data["lote_id"])

    previous_lote_id = sheep.lote_id
    new_lote_id = data.get("lote_id", previous_lote_id)

    for key, value in data.items():
        setattr(sheep, key, value)
    sheep.updated_at = datetime.now(timezone.utc)

    lote_changed = previous_lote_id != sheep.lote_id
    if lote_changed:
        if previous_lote_id is not None:
            recompute_parcela_actual_for_lote(session, previous_lote_id)
        if sheep.lote_id is not None:
            sheep.parcela_actual_id = derive_parcela_for_lote(session, sheep.lote_id)
        else:
            sheep.parcela_actual_id = None

    session.add(sheep)
    session.commit()
    session.refresh(sheep)
    return sheep_to_read(session, sheep)


@router.delete("/{sheep_id}")
def delete_sheep(
    sheep_id: int, session: Session = Depends(get_session)
) -> dict[str, Any]:
    sheep = session.get(Sheep, sheep_id)
    if not sheep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ovella non atopada"
        )
    lote_id = sheep.lote_id
    session.delete(sheep)
    session.commit()
    return {"ok": True}
