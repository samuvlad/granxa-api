"""Tests de integridade relacional e constraints a nivel BD.

Cubren os cambios do reset v0.4.0:
- Restrición de borrado de parcela con rotacións.
- unicidade de Plot.name.
- CHECK de sexo/estado a nivel BD (insert directo).
- updated_at bump vía trigger DB en PATCH de plots/lotes.
- PATCH con ``notes: null`` realmente o setea a NULL.
- Detección de ciclos na cadea de ascendencia.
"""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient
from sqlmodel import Session, text

from tests.helpers import (
    make_lote_via_api,
    make_plot_via_api,
    make_rotation_via_api,
    make_sheep_via_api,
)


# ---------------------------------------------------------------------------
# DELETE /plots/{id} restrinxido se ten rotacións
# ---------------------------------------------------------------------------


def test_delete_plot_with_rotations_409(client: TestClient) -> None:
    plot = make_plot_via_api(client, "Con rotacións")
    lote = make_lote_via_api(client, "L")
    make_rotation_via_api(
        client,
        parcela_id=plot["id"],
        lote_id=lote["id"],
        data_inicio="2026-01-01T00:00:00",
        data_fim="2026-02-01T00:00:00",
    )
    res = client.delete(f"/api/plots/{plot['id']}")
    assert res.status_code == 409
    assert "rotacións" in res.json()["detail"]


def test_delete_plot_without_rotations_ok(client: TestClient) -> None:
    plot = make_plot_via_api(client, "Sen rotacións")
    res = client.delete(f"/api/plots/{plot['id']}")
    assert res.status_code == 200
    res = client.get(f"/api/plots/{plot['id']}")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# Plot.name UNIQUE
# ---------------------------------------------------------------------------


def test_create_plot_duplicate_name_409(client: TestClient) -> None:
    make_plot_via_api(client, "Parcela única")
    res = client.post(
        "/api/plots/",
        json={
            "name": "Parcela única",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-8.55, 42.55],
                        [-8.54, 42.55],
                        [-8.54, 42.56],
                        [-8.55, 42.56],
                        [-8.55, 42.55],
                    ]
                ],
            },
        },
    )
    assert res.status_code == 409


def test_update_plot_duplicate_name_409(client: TestClient) -> None:
    a = make_plot_via_api(client, "A")
    b = make_plot_via_api(client, "B")
    res = client.patch(f"/api/plots/{b['id']}", json={"name": "A"})
    assert res.status_code == 409


# ---------------------------------------------------------------------------
# CHECK constraints en sheep.sexo / sheep.estado (a nivel BD)
# ---------------------------------------------------------------------------


def test_invalid_sexo_rejected_by_db(session: Session) -> None:
    from app.models import Sheep

    bad = Sheep(
        crotal="BAD-SEXO",
        sexo="unicornio",
        data_nacemento=date(2023, 1, 1),
    )
    session.add(bad)
    try:
        session.commit()
        assert False, "esperábase que a BD rexeitase sexo inválido"
    except Exception:
        session.rollback()


def test_invalid_estado_rejected_by_db(session: Session) -> None:
    from app.models import Sheep

    bad = Sheep(
        crotal="BAD-ESTADO",
        sexo="femia",
        estado="perdido",
        data_nacemento=date(2023, 1, 1),
    )
    session.add(bad)
    try:
        session.commit()
        assert False, "esperábase que a BD rexeitase estado inválido"
    except Exception:
        session.rollback()


# ---------------------------------------------------------------------------
# updated_at bump vía trigger DB
# ---------------------------------------------------------------------------


def test_plot_updated_at_bumped_by_trigger(client: TestClient, session: Session) -> None:
    from app.models import Plot

    plot = make_plot_via_api(client, "Plot trigger")
    before = session.get(Plot, plot["id"]).updated_at

    res = client.patch(f"/api/plots/{plot['id']}", json={"color": "#ff0000"})
    assert res.status_code == 200

    # Recargar desde a sesión nova para ver o valor do trigger.
    session.expire_all()
    after = session.get(Plot, plot["id"]).updated_at
    assert after > before


def test_lote_updated_at_bumped_by_trigger(client: TestClient, session: Session) -> None:
    from app.models import Lote

    lote = make_lote_via_api(client, "Lote trigger")
    before = session.get(Lote, lote["id"]).updated_at

    res = client.patch(f"/api/lotes/{lote['id']}", json={"notas": "cambiado"})
    assert res.status_code == 200

    session.expire_all()
    after = session.get(Lote, lote["id"]).updated_at
    assert after > before


# ---------------------------------------------------------------------------
# PATCH con ``notes: null`` setea a NULL (semántica exclude_unset)
# ---------------------------------------------------------------------------


def test_patch_plot_notes_to_null(client: TestClient) -> None:
    plot = make_plot_via_api(client, "Plot null notes")
    res = client.patch(
        f"/api/plots/{plot['id']}", json={"notes": "algo de nota"}
    )
    assert res.status_code == 200
    assert res.json()["notes"] == "algo de nota"

    res = client.patch(f"/api/plots/{plot['id']}", json={"notes": None})
    assert res.status_code == 200
    assert res.json()["notes"] is None


# ---------------------------------------------------------------------------
# Detección de ciclos na cadea de ascendencia
# ---------------------------------------------------------------------------


def test_parent_cycle_rejected(client: TestClient) -> None:
    nai = make_sheep_via_api(client, "ES-NAI", sexo="femia")
    # Crear filla con nai_id = nai
    filla = make_sheep_via_api(client, "ES-FILLA", sexo="femia")
    res = client.patch(f"/api/sheep/{filla['id']}", json={"nai_id": nai["id"]})
    assert res.status_code == 200

    # Agora intentar que a nai teña como nai á filla → ciclo.
    res = client.patch(f"/api/sheep/{nai['id']}", json={"nai_id": filla["id"]})
    assert res.status_code == 422
    assert "ciclo" in res.json()["detail"].lower()
