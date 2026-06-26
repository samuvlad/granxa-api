from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.database import get_session
from app.models import Lote, Plot, Rotation
from app.schemas.lote import LoteSummary
from app.schemas.rotation import (
    RotationCreate,
    RotationRead,
    RotationUpdate,
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


def _check_dates(data_inicio: Any, data_fim: Any) -> None:
    if data_fim is not None and data_fim < data_inicio:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A data de fin non pode ser anterior á de inicio",
        )


def _handle_integrity_error(exc: IntegrityError) -> None:
    """Converte violacións de constraint da BD en respostas HTTP axeitadas."""
    orig = exc.orig
    msg = str(getattr(orig, "diag", getattr(orig, "message", ""))).lower()
    constraint = getattr(getattr(orig, "diag", None), "constraint_name", None) or ""

    if constraint == "uq_rotations_active_per_lote" or "uq_rotations_active_per_lote" in msg:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Xa existe unha rotación activa para este lote",
        ) from exc
    if constraint == "excl_rotations_lote_overlap" or "excl_rotations_lote_overlap" in msg:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A rotación solápase con outra do mesmo lote",
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Violación de integridade: " + str(getattr(orig, "args", ["?"])[0]),
    ) from exc


@router.get("/", response_model=list[RotationRead])
def list_rotations(session: Session = Depends(get_session)) -> list[RotationRead]:
    stmt = (
        select(Rotation, Lote)
        .outerjoin(Lote, Rotation.lote_id == Lote.id)
        .order_by(Rotation.data_inicio.desc(), Rotation.id.desc())
    )
    rows = session.exec(stmt).all()
    result: list[RotationRead] = []
    for rotation, lote in rows:
        result.append(
            RotationRead(
                id=rotation.id,
                parcela_id=rotation.parcela_id,
                lote_id=rotation.lote_id,
                data_inicio=rotation.data_inicio,
                data_fim=rotation.data_fim,
                notas=rotation.notas,
                lote=LoteSummary(id=lote.id, name=lote.name) if lote else None,
                created_at=rotation.created_at.isoformat(),
                updated_at=rotation.updated_at.isoformat(),
            )
        )
    return result


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
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        _handle_integrity_error(exc)
    session.refresh(rotation)
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

    for key, value in data.items():
        setattr(rotation, key, value)
    session.add(rotation)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        _handle_integrity_error(exc)
    session.refresh(rotation)
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
    session.delete(rotation)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        _handle_integrity_error(exc)
    return {"ok": True}
