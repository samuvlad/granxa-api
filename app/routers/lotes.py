from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.database import get_session
from app.models import Lote, Rotation, Sheep
from app.schemas.lote import LoteCreate, LoteRead, LoteUpdate
from app.schemas.sheep import SheepRead

router = APIRouter(prefix="/lotes", tags=["lotes"])


def _handle_integrity_error(exc: IntegrityError) -> None:
    orig = exc.orig
    constraint = getattr(getattr(orig, "diag", None), "constraint_name", None) or ""
    msg = str(getattr(orig, "message", str(getattr(orig, "args", [""])[0]))).lower()
    if constraint == "uq_lotes_name" or "uq_lotes_name" in msg or "lotes_name_key" in msg:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Xa existe un lote con ese nome",
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Violación de integridade: " + str(getattr(orig, "args", ["?"])[0]),
    ) from exc


def lote_to_read(lote: Lote) -> LoteRead:
    return LoteRead(
        id=lote.id,
        name=lote.name,
        notas=lote.notas,
        created_at=lote.created_at.isoformat(),
        updated_at=lote.updated_at.isoformat(),
    )


@router.get("/", response_model=list[LoteRead])
def list_lotes(session: Session = Depends(get_session)) -> list[LoteRead]:
    lotes = session.exec(select(Lote).order_by(Lote.name)).all()
    return [lote_to_read(lote) for lote in lotes]


@router.post("/", response_model=LoteRead, status_code=status.HTTP_201_CREATED)
def create_lote(
    payload: LoteCreate, session: Session = Depends(get_session)
) -> LoteRead:
    name = payload.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O nome do lote é obrigatorio",
        )
    existing = session.exec(select(Lote).where(Lote.name == name)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Xa existe un lote con ese nome",
        )

    lote = Lote(name=name, notas=payload.notas)
    session.add(lote)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        _handle_integrity_error(exc)
    session.refresh(lote)
    return lote_to_read(lote)


@router.get("/{lote_id}/sheep", response_model=list[SheepRead])
def list_sheep_of_lote(
    lote_id: int, session: Session = Depends(get_session)
) -> list[SheepRead]:
    from app.routers.sheep import sheep_to_read

    lote = session.get(Lote, lote_id)
    if not lote:
        raise HTTPException(status_code=404, detail="Lote non atopado")

    sheep_list = session.exec(
        select(Sheep).where(Sheep.lote_id == lote_id).order_by(Sheep.id)
    ).all()
    return [sheep_to_read(session, s) for s in sheep_list]


@router.get("/{lote_id}", response_model=LoteRead)
def get_lote(lote_id: int, session: Session = Depends(get_session)) -> LoteRead:
    lote = session.get(Lote, lote_id)
    if not lote:
        raise HTTPException(status_code=404, detail="Lote non atopado")
    return lote_to_read(lote)


@router.patch("/{lote_id}", response_model=LoteRead)
def update_lote(
    lote_id: int,
    payload: LoteUpdate,
    session: Session = Depends(get_session),
) -> LoteRead:
    lote = session.get(Lote, lote_id)
    if not lote:
        raise HTTPException(status_code=404, detail="Lote non atopado")

    data = payload.model_dump(exclude_unset=True)

    if "name" in data:
        new_name = (data["name"] or "").strip()
        if not new_name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="O nome do lote é obrigatorio",
            )
        if new_name != lote.name:
            clash = session.exec(
                select(Lote).where(Lote.name == new_name, Lote.id != lote_id)
            ).first()
            if clash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Xa existe outro lote con ese nome",
                )
            data["name"] = new_name

    for key, value in data.items():
        setattr(lote, key, value)
    session.add(lote)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        _handle_integrity_error(exc)
    session.refresh(lote)
    return lote_to_read(lote)


@router.delete("/{lote_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lote(
    lote_id: int, session: Session = Depends(get_session)
) -> None:
    lote = session.get(Lote, lote_id)
    if not lote:
        raise HTTPException(status_code=404, detail="Lote non atopado")

    has_sheep = session.exec(
        select(Sheep.id).where(Sheep.lote_id == lote_id).limit(1)
    ).first()
    if has_sheep:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Non se pode borrar o lote: ten ovellas asociadas",
        )

    has_rotations = session.exec(
        select(Rotation.id).where(Rotation.lote_id == lote_id).limit(1)
    ).first()
    if has_rotations:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Non se pode borrar o lote: ten rotacións asociadas",
        )

    session.delete(lote)
    session.commit()
    return None
