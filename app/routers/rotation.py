from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.database import get_session
from app.models import Plot, Rotation
from app.schemas.rotation import (
    RotationCreate,
    RotationRead,
    RotationUpdate,
)

router = APIRouter(prefix="/rotations", tags=["rotations"])


def rotation_to_read(rotation: Rotation) -> RotationRead:
    return RotationRead(
        id=rotation.id,
        parcela_id=rotation.parcela_id,
        lote_nome=rotation.lote_nome,
        data_inicio=rotation.data_inicio,
        data_fim=rotation.data_fim,
        notas=rotation.notas,
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
    return [rotation_to_read(r) for r in rotations]


@router.post("/", response_model=RotationRead, status_code=status.HTTP_201_CREATED)
def create_rotation(
    payload: RotationCreate, session: Session = Depends(get_session)
) -> RotationRead:
    lote_nome = payload.lote_nome.strip()
    if not lote_nome:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O nome do lote é obrigatorio",
        )
    if not session.get(Plot, payload.parcela_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A parcela non existe",
        )
    _check_dates(payload.data_inicio, payload.data_fim)

    rotation = Rotation(
        parcela_id=payload.parcela_id,
        lote_nome=lote_nome,
        data_inicio=payload.data_inicio,
        data_fim=payload.data_fim,
        notas=payload.notas,
    )
    session.add(rotation)
    session.commit()
    session.refresh(rotation)
    return rotation_to_read(rotation)


@router.get("/{rotation_id}", response_model=RotationRead)
def get_rotation(
    rotation_id: int, session: Session = Depends(get_session)
) -> RotationRead:
    rotation = session.get(Rotation, rotation_id)
    if not rotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Rotación non atopada"
        )
    return rotation_to_read(rotation)


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

    if "lote_nome" in data:
        lote_nome = (data["lote_nome"] or "").strip()
        if not lote_nome:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="O nome do lote é obrigatorio",
            )
        data["lote_nome"] = lote_nome

    if "parcela_id" in data and not session.get(Plot, data["parcela_id"]):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A parcela non existe",
        )

    new_inicio = data.get("data_inicio", rotation.data_inicio)
    new_fim = data.get("data_fim", rotation.data_fim)
    _check_dates(new_inicio, new_fim)

    for key, value in data.items():
        setattr(rotation, key, value)
    rotation.updated_at = datetime.now(timezone.utc)
    session.add(rotation)
    session.commit()
    session.refresh(rotation)
    return rotation_to_read(rotation)


@router.delete("/{rotation_id}")
def delete_rotation(
    rotation_id: int, session: Session = Depends(get_session)
) -> dict[str, Any]:
    rotation = session.get(Rotation, rotation_id)
    if not rotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Rotación non atopada"
        )
    session.delete(rotation)
    session.commit()
    return {"ok": True}
