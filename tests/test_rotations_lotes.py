"""Tests do recurso /rotations/ con lote_id."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.helpers import (
    make_lote_via_api,
    make_plot_via_api,
    make_rotation_via_api,
    make_sheep_via_api,
)


def test_create_rotation_with_lote_id(client: TestClient) -> None:
    plot = make_plot_via_api(client, "P")
    lote = make_lote_via_api(client, "L")
    rot = make_rotation_via_api(
        client,
        parcela_id=plot["id"],
        lote_id=lote["id"],
        data_inicio="2026-01-01T00:00:00",
    )
    assert rot["lote_id"] == lote["id"]
    assert rot["parcela_id"] == plot["id"]
    assert rot["lote"] == {"id": lote["id"], "name": "L"}


def test_rotation_recomputes_parcela_on_create(client: TestClient) -> None:
    plot = make_plot_via_api(client, "P")
    lote = make_lote_via_api(client, "L")
    sheep = make_sheep_via_api(client, "ES-X", lote_id=lote["id"])
    assert sheep["parcela_actual_id"] is None

    make_rotation_via_api(
        client,
        parcela_id=plot["id"],
        lote_id=lote["id"],
        data_inicio="2026-01-01T00:00:00",
    )

    res = client.get(f"/sheep/{sheep['id']}")
    assert res.json()["parcela_actual_id"] == plot["id"]


def test_two_active_rotations_same_lote_allowed(client: TestClient) -> None:
    """O modelo permite varias rotacións activas; a 'activa' é a máis recente."""
    p1 = make_plot_via_api(client, "P1")
    p2 = make_plot_via_api(client, "P2")
    lote = make_lote_via_api(client, "L")
    rot1 = make_rotation_via_api(
        client,
        parcela_id=p1["id"],
        lote_id=lote["id"],
        data_inicio="2026-01-01T00:00:00",
    )
    rot2 = make_rotation_via_api(
        client,
        parcela_id=p2["id"],
        lote_id=lote["id"],
        data_inicio="2026-02-01T00:00:00",
    )
    assert rot1["data_fim"] is None
    assert rot2["data_fim"] is None


def test_close_active_rotation_picks_next(client: TestClient) -> None:
    p1 = make_plot_via_api(client, "P1")
    p2 = make_plot_via_api(client, "P2")
    lote = make_lote_via_api(client, "L")

    rot1 = make_rotation_via_api(
        client,
        parcela_id=p1["id"],
        lote_id=lote["id"],
        data_inicio="2026-01-01T00:00:00",
    )
    make_rotation_via_api(
        client,
        parcela_id=p2["id"],
        lote_id=lote["id"],
        data_inicio="2026-02-01T00:00:00",
    )
    sheep = make_sheep_via_api(client, "ES-Y", lote_id=lote["id"])
    assert sheep["parcela_actual_id"] == p2["id"]

    # Pechar a activa (p2). A ovella pasa a p1.
    res = client.patch(
        f"/rotations/{rot1['id'] + 1}", json={"data_fim": "2026-02-15T00:00:00"}
    )
    assert res.status_code == 200
    res = client.get(f"/sheep/{sheep['id']}")
    assert res.json()["parcela_actual_id"] == p1["id"]


def test_lote_nome_not_accepted_anymore(client: TestClient) -> None:
    """O campo antigo ``lote_nome`` non forma parte do schema."""
    p1 = make_plot_via_api(client, "P1")
    lote = make_lote_via_api(client, "L")
    res = client.post(
        "/rotations/",
        json={
            "parcela_id": p1["id"],
            "lote_id": lote["id"],
            "lote_nome": "Lote vello",
            "data_inicio": "2026-01-01T00:00:00",
        },
    )
    # Pydantic ignora silenciosamente campos extra (configura por defecto).
    assert res.status_code == 201
    body = res.json()
    assert "lote_nome" not in body
    assert body["lote_id"] == lote["id"]


def test_update_rotation_to_change_lote(client: TestClient) -> None:
    p1 = make_plot_via_api(client, "P1")
    p2 = make_plot_via_api(client, "P2")
    l1 = make_lote_via_api(client, "L1")
    l2 = make_lote_via_api(client, "L2")

    rot = make_rotation_via_api(
        client,
        parcela_id=p1["id"],
        lote_id=l1["id"],
        data_inicio="2026-01-01T00:00:00",
    )

    res = client.patch(
        f"/rotations/{rot['id']}",
        json={"lote_id": l2["id"], "parcela_id": p2["id"]},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["lote_id"] == l2["id"]
    assert body["parcela_id"] == p2["id"]
    assert body["lote"]["name"] == "L2"


def test_delete_active_rotation_clears_parcela(client: TestClient) -> None:
    p1 = make_plot_via_api(client, "P1")
    lote = make_lote_via_api(client, "L")
    rot = make_rotation_via_api(
        client,
        parcela_id=p1["id"],
        lote_id=lote["id"],
        data_inicio="2026-01-01T00:00:00",
    )
    sheep = make_sheep_via_api(client, "ES-Z", lote_id=lote["id"])
    assert sheep["parcela_actual_id"] == p1["id"]

    res = client.delete(f"/rotations/{rot['id']}")
    assert res.status_code == 200
    res = client.get(f"/sheep/{sheep['id']}")
    assert res.json()["parcela_actual_id"] is None


def test_dates_validation(client: TestClient) -> None:
    p1 = make_plot_via_api(client, "P1")
    lote = make_lote_via_api(client, "L")
    res = client.post(
        "/rotations/",
        json={
            "parcela_id": p1["id"],
            "lote_id": lote["id"],
            "data_inicio": "2026-02-01T00:00:00",
            "data_fim": "2026-01-01T00:00:00",
        },
    )
    assert res.status_code == 422
