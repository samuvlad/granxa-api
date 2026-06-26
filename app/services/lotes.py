"""Servizos de dominio para a xestión de lotes e as súas relacións."""

from __future__ import annotations

from sqlmodel import Session, select

from app.models import Rotation


def get_active_rotation(session: Session, lote_id: int) -> Rotation | None:
    """Devolve a rotación activa (data_fim IS NULL) máis recente dun lote.

    A BD garante (partial unique index ``uq_rotations_active_per_lote``) que
    soamente pode haber unha rotación activa por lote.
    """

    stmt = (
        select(Rotation)
        .where(Rotation.lote_id == lote_id, Rotation.data_fim.is_(None))
        .order_by(Rotation.data_inicio.desc(), Rotation.id.desc())
    )
    return session.exec(stmt).first()


def derive_parcela_for_lote(
    session: Session, lote_id: int | None
) -> int | None:
    """Deriva a parcela actual dun lote a partir da súa rotación activa.

    Devolve ``None`` se o lote non ten rotación activa.
    """

    if lote_id is None:
        return None
    rotation = get_active_rotation(session, lote_id)
    return rotation.parcela_id if rotation is not None else None
