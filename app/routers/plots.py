from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Plot
from app.schemas import PlotCreate, PlotRead, PlotUpdate
from app.utils.geo import (
    calculate_area_m2,
    calculate_perimeter_m,
    geojson_to_geometry,
    geometry_to_geojson,
)

router = APIRouter(prefix="/plots", tags=["plots"])


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
    session.commit()
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

    if plot_in.name is not None:
        plot.name = plot_in.name
    if plot_in.color is not None:
        plot.color = plot_in.color
    if plot_in.geometry is not None:
        geometry = geojson_to_geometry(plot_in.geometry)
        plot.geometry = geometry
        plot.area_m2 = calculate_area_m2(geometry)
        plot.perimeter_m = calculate_perimeter_m(geometry)
    if plot_in.cadastral_ref is not None:
        plot.cadastral_ref = plot_in.cadastral_ref
    if plot_in.notes is not None:
        plot.notes = plot_in.notes

    session.add(plot)
    session.commit()
    session.refresh(plot)
    return plot_to_read(plot)


@router.delete("/{plot_id}")
def delete_plot(plot_id: int, session: Session = Depends(get_session)) -> dict[str, Any]:
    plot = session.get(Plot, plot_id)
    if not plot:
        raise HTTPException(status_code=404, detail="Parcela non atopada")
    session.delete(plot)
    session.commit()
    return {"ok": True}
