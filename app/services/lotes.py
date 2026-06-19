"""Servizos de dominio para a xestión de lotes e as súas relacións."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session, select

from app.models import Lote, Rotation, Sheep


logger = logging.getLogger(__name__)


def get_active_rotation(session: Session, lote_id: int) -> Rotation | None:
    """Devolve a rotación activa (data_fim IS NULL) máis recente dun lote.

    Se hai varias rotacións activas (non debería, pero o modelo non o impide),
    devólvese a de data_inicio máis recente.
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


def recompute_parcela_actual_for_lote(
    session: Session, lote_id: int
) -> int | None:
    """Recalcula e persiste ``parcela_actual_id`` das ovellas dun lote.

    A nova parcela é a da rotación activa do lote. Se non hai ningunha,
    ``parcela_actual_id`` pasa a ``NULL``.

    Devolve o novo valor (ou ``None``).
    """

    new_parcela = derive_parcela_for_lote(session, lote_id)

    sheep_list = session.exec(select(Sheep).where(Sheep.lote_id == lote_id)).all()
    now = datetime.now(timezone.utc)
    for s in sheep_list:
        if s.parcela_actual_id != new_parcela:
            s.parcela_actual_id = new_parcela
            s.updated_at = now
            session.add(s)

    if sheep_list:
        logger.info(
            "Recalculada parcela_actual_id para %d ovellas do lote %s: %s",
            len(sheep_list),
            lote_id,
            new_parcela,
        )

    return new_parcela
