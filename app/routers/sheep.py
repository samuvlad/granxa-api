from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.database import get_session
from app.models import Plot, Sheep
from app.schemas.sheep import (
    VALID_ESTADO,
    VALID_SEXO,
    SheepCreate,
    SheepRead,
    SheepUpdate,
)

router = APIRouter(prefix="/sheep", tags=["sheep"])


def sheep_to_read(sheep: Sheep) -> SheepRead:
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
        parcela_actual_id=sheep.parcela_actual_id,
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


def _validate_plot(session: Session, plot_id: int | None) -> None:
    if plot_id is None:
        return
    if not session.get(Plot, plot_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A parcela non existe",
        )


@router.get("/", response_model=list[SheepRead])
def list_sheep(session: Session = Depends(get_session)) -> list[SheepRead]:
    sheep = session.exec(select(Sheep).order_by(Sheep.id)).all()
    return [sheep_to_read(s) for s in sheep]


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
    _validate_plot(session, payload.parcela_actual_id)

    sheep = Sheep(
        crotal=crotal,
        nome=(payload.nome or None),
        sexo=payload.sexo,
        data_nacemento=payload.data_nacemento,
        raca=(payload.raca or "Gallega"),
        estado=payload.estado,
        nai_id=payload.nai_id,
        pai_id=payload.pai_id,
        parcela_actual_id=payload.parcela_actual_id,
        notas=payload.notas,
    )
    session.add(sheep)
    session.commit()
    session.refresh(sheep)
    return sheep_to_read(sheep)


@router.get("/{sheep_id}", response_model=SheepRead)
def get_sheep(sheep_id: int, session: Session = Depends(get_session)) -> SheepRead:
    sheep = session.get(Sheep, sheep_id)
    if not sheep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ovella non atopada"
        )
    return sheep_to_read(sheep)


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
    if "parcela_actual_id" in data:
        _validate_plot(session, data["parcela_actual_id"])

    for key, value in data.items():
        setattr(sheep, key, value)
    sheep.updated_at = datetime.now(timezone.utc)
    session.add(sheep)
    session.commit()
    session.refresh(sheep)
    return sheep_to_read(sheep)


@router.delete("/{sheep_id}")
def delete_sheep(
    sheep_id: int, session: Session = Depends(get_session)
) -> dict[str, Any]:
    sheep = session.get(Sheep, sheep_id)
    if not sheep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ovella non atopada"
        )
    session.delete(sheep)
    session.commit()
    return {"ok": True}
