from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.database import get_session
from app.models import Plot, Rotation
from app.schemas import PlotCreate, PlotRead, PlotUpdate
from app.utils.geo import (
    calculate_area_m2,
    calculate_perimeter_m,
    geojson_to_geometry,
    geometry_to_geojson,
)

router = APIRouter(prefix="/plots", tags=["plots"])


def _handle_integrity_error(exc: IntegrityError) -> None:
    orig = exc.orig
    constraint = getattr(getattr(orig, "diag", None), "constraint_name", None) or ""
    msg = str(getattr(orig, "message", str(getattr(orig, "args", [""])[0]))).lower()
    if constraint == "uq_plots_name" or "uq_plots_name" in msg or "plots_name_key" in msg:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Xa existe unha parcela con ese nome",
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Violación de integridade: " + str(getattr(orig, "args", ["?"])[0]),
    ) from exc



def plot_to_read(plot: Plot) -> PlotRead:
    return PlotRead(
        id=plot.id,
        name=plot.name,
        color=plot.color,
        geometry=geometry_to_geojson(plot.geometry),
        area_m2=plot.area_m2,
        perimeter_m=plot.perimeter_m,
        cadastral_ref=plot.cadastral_ref,
        notes=plot.notes,
        created_at=plot.created_at.isoformat(),
        updated_at=plot.updated_at.isoformat(),
    )


@router.get("/", response_model=list[PlotRead])
def list_plots(session: Session = Depends(get_session)) -> list[PlotRead]:
    plots = session.exec(select(Plot)).all()
    return [plot_to_read(plot) for plot in plots]


@router.post("/", response_model=PlotRead)
def create_plot(plot_in: PlotCreate, session: Session = Depends(get_session)) -> PlotRead:
    geometry = geojson_to_geometry(plot_in.geometry)
    plot = Plot(
        name=plot_in.name,
        color=plot_in.color,
        geometry=geometry,
        area_m2=calculate_area_m2(geometry),
        perimeter_m=calculate_perimeter_m(geometry),
        cadastral_ref=plot_in.cadastral_ref,
        notes=plot_in.notes,
    )
    session.add(plot)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        _handle_integrity_error(exc)
    session.refresh(plot)
    return plot_to_read(plot)


@router.get("/{plot_id}", response_model=PlotRead)
def get_plot(plot_id: int, session: Session = Depends(get_session)) -> PlotRead:
    plot = session.get(Plot, plot_id)
    if not plot:
        raise HTTPException(status_code=404, detail="Parcela non atopada")
    return plot_to_read(plot)


@router.patch("/{plot_id}", response_model=PlotRead)
def update_plot(
    plot_id: int, plot_in: PlotUpdate, session: Session = Depends(get_session)
) -> PlotRead:
    plot = session.get(Plot, plot_id)
    if not plot:
        raise HTTPException(status_code=404, detail="Parcela non atopada")

    data = plot_in.model_dump(exclude_unset=True)

    if "name" in data:
        new_name = (data["name"] or "").strip()
        if not new_name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="O nome da parcela é obrigatorio",
            )
        clash = session.exec(
            select(Plot).where(Plot.name == new_name, Plot.id != plot_id)
        ).first()
        if clash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Xa existe outra parcela con ese nome",
            )
        data["name"] = new_name

    if "geometry" in data and data["geometry"] is not None:
        geometry = geojson_to_geometry(data["geometry"])
        data["area_m2"] = calculate_area_m2(geometry)
        data["perimeter_m"] = calculate_perimeter_m(geometry)

    for key, value in data.items():
        setattr(plot, key, value)
    session.add(plot)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        _handle_integrity_error(exc)
    session.refresh(plot)
    return plot_to_read(plot)


@router.delete("/{plot_id}")
def delete_plot(plot_id: int, session: Session = Depends(get_session)) -> dict[str, Any]:
    plot = session.get(Plot, plot_id)
    if not plot:
        raise HTTPException(status_code=404, detail="Parcela non atopada")

    has_rotations = session.exec(
        select(Rotation.id).where(Rotation.parcela_id == plot_id).limit(1)
    ).first()
    if has_rotations:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Non se pode borrar a parcela: ten rotacións asociadas",
        )

    session.delete(plot)
    session.commit()
    return {"ok": True}
