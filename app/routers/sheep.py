from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.database import get_session
from app.models import Lote, Sheep
from app.schemas.lote import LoteSummary
from app.schemas.sheep import (
    VALID_ESTADO,
    VALID_SEXO,
    SheepCreate,
    SheepRead,
    SheepUpdate,
)
from app.services.lotes import derive_parcela_for_lote, get_active_rotation

router = APIRouter(prefix="/sheep", tags=["sheep"])


def _handle_integrity_error(exc: IntegrityError) -> None:
    orig = exc.orig
    constraint = getattr(getattr(orig, "diag", None), "constraint_name", None) or ""
    msg = str(getattr(orig, "message", str(getattr(orig, "args", [""])[0]))).lower()
    if constraint == "uq_sheep_crotal" or "uq_sheep_crotal" in msg or "sheep_crotal_key" in msg:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Xa existe unha ovella con ese crotal",
        ) from exc
    if constraint == "ck_sheep_sexo" or "ck_sheep_sexo" in msg or "sheep_sexo_check" in msg:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Sexo non válido (macho|femia)",
        ) from exc
    if constraint == "ck_sheep_estado" or "ck_sheep_estado" in msg or "sheep_estado_check" in msg:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Estado non válido (activo|vendido|morto)",
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Violación de integridade: " + str(getattr(orig, "args", ["?"])[0]),
    ) from exc


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

    _check_ancestor_cycle(session, sheep_id, parent_id, kind)


def _check_ancestor_cycle(
    session: Session, sheep_id: int, parent_id: int, kind: str
) -> None:
    """Detecta ciclos na cadea de ascendencia (nai ou pai).

    Sigue recursivamente a cadea do mesmo tipo (nai→nai→... ou pai→pai→...)
    ata 20 niveis. Se se atopa ``sheep_id``, hai un ciclo.
    """
    current = parent_id
    link = "nai_id" if kind == "nai" else "pai_id"
    for _ in range(20):
        if current is None:
            return
        ancestor = session.get(Sheep, current)
        if ancestor is None:
            return
        next_id = getattr(ancestor, link)
        if next_id == sheep_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Ciclo detectado na cadea de {kind}: a ovella {sheep_id} "
                f"sería ascendente de si mesma",
            )
        current = next_id


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
    # Carga todas as ovellas nunha soa query.
    stmt = select(Sheep).order_by(Sheep.id)
    if lote_id is not None:
        stmt = stmt.where(Sheep.lote_id == lote_id)
    sheep_list = session.exec(stmt).all()
    if not sheep_list:
        return []

    # Batch: lotes e rotacións activas para todas as ovellas dunha soa vez.
    lote_ids = {s.lote_id for s in sheep_list if s.lote_id is not None}
    lotes_map: dict[int, LoteSummary] = {}
    parcela_map: dict[int, int | None] = {}
    for lid in lote_ids:
        lote = session.get(Lote, lid)
        if lote is not None:
            lotes_map[lid] = LoteSummary(id=lote.id, name=lote.name)
        rotation = get_active_rotation(session, lid)
        parcela_map[lid] = rotation.parcela_id if rotation else None

    result: list[SheepRead] = []
    for s in sheep_list:
        lote_summary = lotes_map.get(s.lote_id) if s.lote_id is not None else None
        parcela_actual_id = (
            parcela_map.get(s.lote_id) if s.lote_id is not None else None
        )
        result.append(
            SheepRead(
                id=s.id,
                crotal=s.crotal,
                nome=s.nome,
                sexo=s.sexo,
                data_nacemento=s.data_nacemento,
                raca=s.raca,
                estado=s.estado,
                nai_id=s.nai_id,
                pai_id=s.pai_id,
                lote_id=s.lote_id,
                parcela_actual_id=parcela_actual_id,
                lote=lote_summary,
                notas=s.notas,
                created_at=s.created_at.isoformat(),
                updated_at=s.updated_at.isoformat(),
            )
        )
    return result


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
        notas=payload.notas,
    )
    session.add(sheep)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        _handle_integrity_error(exc)
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

    for key, value in data.items():
        setattr(sheep, key, value)
    session.add(sheep)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        _handle_integrity_error(exc)
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
    session.delete(sheep)
    session.commit()
    return {"ok": True}
