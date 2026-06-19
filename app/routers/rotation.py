from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.database import get_session
from app.models import Lote, Plot, Rotation
from app.schemas.lote import LoteSummary
from app.schemas.rotation import (
    RotationCreate,
    RotationRead,
    RotationUpdate,
)
from app.services.lotes import (
    recompute_parcela_actual_for_lote,
)

router = APIRouter(prefix="/rotations", tags=["rotations"])


def _lote_summary(session: Session, lote_id: int) -> LoteSummary | None:
    lote = session.get(Lote, lote_id)
    if not lote:
        return None
    return LoteSummary(id=lote.id, name=lote.name)


def rotation_to_read(session: Session, rotation: Rotation) -> RotationRead:
    return RotationRead(
        id=rotation.id,
        parcela_id=rotation.parcela_id,
        lote_id=rotation.lote_id,
        data_inicio=rotation.data_inicio,
        data_fim=rotation.data_fim,
        notas=rotation.notas,
        lote=_lote_summary(session, rotation.lote_id),
        created_at=rotation.created_at.isoformat(),
        updated_at=rotation.updated_at.isoformat(),
    )


def _check_dates(data_inicio: datetime, data_fim: datetime | None) -> None:
    if data_fim is not None and data_fim < data_inicio:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A data de fin non pode ser anterior á de inicio",
        )


@router.get("/", response_model=list[RotationRead])
def list_rotations(session: Session = Depends(get_session)) -> list[RotationRead]:
    rotations = session.exec(
        select(Rotation).order_by(Rotation.data_inicio.desc(), Rotation.id.desc())
    ).all()
    return [rotation_to_read(session, r) for r in rotations]


@router.post("/", response_model=RotationRead, status_code=status.HTTP_201_CREATED)
def create_rotation(
    payload: RotationCreate, session: Session = Depends(get_session)
) -> RotationRead:
    if not session.get(Plot, payload.parcela_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A parcela non existe",
        )
    if not session.get(Lote, payload.lote_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O lote non existe",
        )
    _check_dates(payload.data_inicio, payload.data_fim)

    rotation = Rotation(
        parcela_id=payload.parcela_id,
        lote_id=payload.lote_id,
        data_inicio=payload.data_inicio,
        data_fim=payload.data_fim,
        notas=payload.notas,
    )
    session.add(rotation)
    session.commit()
    session.refresh(rotation)

    if rotation.data_fim is None:
        recompute_parcela_actual_for_lote(session, rotation.lote_id)
        session.commit()

    return rotation_to_read(session, rotation)


@router.get("/{rotation_id}", response_model=RotationRead)
def get_rotation(
    rotation_id: int, session: Session = Depends(get_session)
) -> RotationRead:
    rotation = session.get(Rotation, rotation_id)
    if not rotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Rotación non atopada"
        )
    return rotation_to_read(session, rotation)


@router.patch("/{rotation_id}", response_model=RotationRead)
def update_rotation(
    rotation_id: int, payload: RotationUpdate, session: Session = Depends(get_session)
) -> RotationRead:
    rotation = session.get(Rotation, rotation_id)
    if not rotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Rotación non atopada"
        )

    data = payload.model_dump(exclude_unset=True)

    new_lote_id = data.get("lote_id", rotation.lote_id)
    new_parcela_id = data.get("parcela_id", rotation.parcela_id)
    new_inicio = data.get("data_inicio", rotation.data_inicio)
    new_fim = data.get("data_fim", rotation.data_fim)

    if "lote_id" in data and not session.get(Lote, data["lote_id"]):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O lote non existe",
        )
    if "parcela_id" in data and not session.get(Plot, data["parcela_id"]):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A parcela non existe",
        )

    _check_dates(new_inicio, new_fim)

    previous_lote_id = rotation.lote_id
    previous_fim = rotation.data_fim

    for key, value in data.items():
        setattr(rotation, key, value)
    rotation.updated_at = datetime.now(timezone.utc)
    session.add(rotation)
    session.commit()
    session.refresh(rotation)

    became_active = previous_fim is not None and rotation.data_fim is None
    became_closed = previous_fim is None and rotation.data_fim is not None
    lote_changed = previous_lote_id != rotation.lote_id

    if became_active or became_closed or lote_changed:
        if lote_changed:
            recompute_parcela_actual_for_lote(session, previous_lote_id)
        recompute_parcela_actual_for_lote(session, rotation.lote_id)
        session.commit()

    return rotation_to_read(session, rotation)


@router.delete("/{rotation_id}")
def delete_rotation(
    rotation_id: int, session: Session = Depends(get_session)
) -> dict[str, Any]:
    rotation = session.get(Rotation, rotation_id)
    if not rotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Rotación non atopada"
        )
    lote_id = rotation.lote_id
    was_active = rotation.data_fim is None
    session.delete(rotation)
    session.commit()
    if was_active:
        recompute_parcela_actual_for_lote(session, lote_id)
        session.commit()
    return {"ok": True}
