"""Tests da integración Sheep ↔ Lote ↔ Rotación."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.helpers import (
    make_lote_via_api,
    make_plot_via_api,
    make_rotation_via_api,
    make_sheep_via_api,
)


def test_create_sheep_with_lote(client: TestClient) -> None:
    lote = make_lote_via_api(client, "Lote 1")
    sheep = make_sheep_via_api(client, "ES-TEST-1", lote_id=lote["id"])

    assert sheep["lote_id"] == lote["id"]
    assert sheep["lote"] == {"id": lote["id"], "name": "Lote 1"}
    # Sen rotación activa: parcela_actual_id = None
    assert sheep["parcela_actual_id"] is None


def test_create_sheep_without_lote(client: TestClient) -> None:
    sheep = make_sheep_via_api(client, "ES-TEST-2")
    assert sheep["lote_id"] is None
    assert sheep["lote"] is None
    assert sheep["parcela_actual_id"] is None


def test_parcela_actual_derived_from_active_rotation(client: TestClient) -> None:
    plot = make_plot_via_api(client, "P-Norte")
    lote = make_lote_via_api(client, "Lote Norte")
    make_rotation_via_api(
        client,
        parcela_id=plot["id"],
        lote_id=lote["id"],
        data_inicio="2026-01-01T00:00:00",
    )
    sheep = make_sheep_via_api(client, "ES-TEST-3", lote_id=lote["id"])
    assert sheep["parcela_actual_id"] == plot["id"]

    # Ao recuperar a ovella, a parcela segue a ser a da rotación activa.
    res = client.get(f"/api/sheep/{sheep['id']}")
    assert res.status_code == 200
    assert res.json()["parcela_actual_id"] == plot["id"]


def test_parcela_actual_recomputed_on_rotation_close(client: TestClient) -> None:
    p1 = make_plot_via_api(client, "P1")
    p2 = make_plot_via_api(client, "P2")
    lote = make_lote_via_api(client, "Lote migración")

    rot1 = make_rotation_via_api(
        client,
        parcela_id=p1["id"],
        lote_id=lote["id"],
        data_inicio="2026-01-01T00:00:00",
    )
    sheep = make_sheep_via_api(client, "ES-TEST-4", lote_id=lote["id"])
    assert sheep["parcela_actual_id"] == p1["id"]

    # Pechar a rotación activa.
    res = client.patch(
        f"/api/rotations/{rot1['id']}", json={"data_fim": "2026-02-01T00:00:00"}
    )
    assert res.status_code == 200
    assert res.json()["data_fim"].startswith("2026-02-01T00:00:00")

    # Sen outra rotación activa, a parcela da ovella debe pasar a NULL.
    res = client.get(f"/api/sheep/{sheep['id']}")
    assert res.json()["parcela_actual_id"] is None

    # Crear unha nova rotación activa en P2: a ovella debe recoller a nova.
    make_rotation_via_api(
        client,
        parcela_id=p2["id"],
        lote_id=lote["id"],
        data_inicio="2026-03-01T00:00:00",
    )
    res = client.get(f"/api/sheep/{sheep['id']}")
    assert res.json()["parcela_actual_id"] == p2["id"]


def test_parcela_actual_follows_active_rotation(client: TestClient) -> None:
    p1 = make_plot_via_api(client, "P1")
    p2 = make_plot_via_api(client, "P2")
    lote = make_lote_via_api(client, "Lote")

    # Rotación pechada en P1, logo rotación activa en P2.
    make_rotation_via_api(
        client,
        parcela_id=p1["id"],
        lote_id=lote["id"],
        data_inicio="2026-01-01T00:00:00",
        data_fim="2026-01-31T00:00:00",
    )
    rot2 = make_rotation_via_api(
        client,
        parcela_id=p2["id"],
        lote_id=lote["id"],
        data_inicio="2026-02-01T00:00:00",
    )
    sheep = make_sheep_via_api(client, "ES-TEST-5", lote_id=lote["id"])
    # A activa é p2.
    assert sheep["parcela_actual_id"] == p2["id"]

    # Pechar a activa: non hai outra activa, a parcela pasa a NULL
    # (a rotación anterior en p1 está pechada, non conta).
    res = client.patch(
        f"/api/rotations/{rot2['id']}", json={"data_fim": "2026-02-15T00:00:00"}
    )
    assert res.status_code == 200
    res = client.get(f"/api/sheep/{sheep['id']}")
    assert res.json()["parcela_actual_id"] is None


def test_patch_sheep_to_assign_lote(client: TestClient) -> None:
    plot = make_plot_via_api(client, "P")
    lote = make_lote_via_api(client, "L")
    make_rotation_via_api(
        client,
        parcela_id=plot["id"],
        lote_id=lote["id"],
        data_inicio="2026-01-01T00:00:00",
    )
    sheep = make_sheep_via_api(client, "ES-TEST-6")
    assert sheep["parcela_actual_id"] is None

    res = client.patch(f"/api/sheep/{sheep['id']}", json={"lote_id": lote["id"]})
    assert res.status_code == 200
    assert res.json()["lote_id"] == lote["id"]
    assert res.json()["parcela_actual_id"] == plot["id"]


def test_patch_sheep_change_lote_recomputes_both(
    client: TestClient,
) -> None:
    p1 = make_plot_via_api(client, "P1")
    p2 = make_plot_via_api(client, "P2")
    l1 = make_lote_via_api(client, "L1")
    l2 = make_lote_via_api(client, "L2")
    make_rotation_via_api(
        client,
        parcela_id=p1["id"],
        lote_id=l1["id"],
        data_inicio="2026-01-01T00:00:00",
    )
    make_rotation_via_api(
        client,
        parcela_id=p2["id"],
        lote_id=l2["id"],
        data_inicio="2026-01-01T00:00:00",
    )

    sheep = make_sheep_via_api(client, "ES-TEST-7", lote_id=l1["id"])
    assert sheep["parcela_actual_id"] == p1["id"]

    res = client.patch(f"/api/sheep/{sheep['id']}", json={"lote_id": l2["id"]})
    assert res.status_code == 200
    body = res.json()
    assert body["lote_id"] == l2["id"]
    assert body["parcela_actual_id"] == p2["id"]


def test_parcela_actual_id_input_is_ignored(client: TestClient) -> None:
    """O backend ignora o campo deprecated ``parcela_actual_id``."""
    lote = make_lote_via_api(client, "L")
    plot = make_plot_via_api(client, "P")
    make_rotation_via_api(
        client,
        parcela_id=plot["id"],
        lote_id=lote["id"],
        data_inicio="2026-01-01T00:00:00",
    )
    res = client.post(
        "/api/sheep/",
        json={
            "crotal": "ES-TEST-8",
            "sexo": "femia",
            "data_nacemento": "2023-01-01",
            "lote_id": lote["id"],
            "parcela_actual_id": 9999,  # Debe ignorarse
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["parcela_actual_id"] == plot["id"]


def test_parcela_actual_id_patch_ignored(client: TestClient) -> None:
    lote = make_lote_via_api(client, "L")
    plot = make_plot_via_api(client, "P")
    make_rotation_via_api(
        client,
        parcela_id=plot["id"],
        lote_id=lote["id"],
        data_inicio="2026-01-01T00:00:00",
    )
    sheep = make_sheep_via_api(client, "ES-TEST-9", lote_id=lote["id"])
    res = client.patch(
        f"/api/sheep/{sheep['id']}", json={"parcela_actual_id": 9999}
    )
    assert res.status_code == 200
    assert res.json()["parcela_actual_id"] == plot["id"]


def test_filter_sheep_by_lote_id(client: TestClient) -> None:
    l1 = make_lote_via_api(client, "L1")
    l2 = make_lote_via_api(client, "L2")
    make_sheep_via_api(client, "ES-A", lote_id=l1["id"])
    make_sheep_via_api(client, "ES-B", lote_id=l1["id"])
    make_sheep_via_api(client, "ES-C", lote_id=l2["id"])

    res = client.get(f"/api/sheep/?lote_id={l1['id']}")
    assert res.status_code == 200
    crotales = sorted(s["crotal"] for s in res.json())
    assert crotales == ["ES-A", "ES-B"]

    res = client.get(f"/api/sheep/?lote_id={l2['id']}")
    crotales = [s["crotal"] for s in res.json()]
    assert crotales == ["ES-C"]


def test_list_sheep_of_lote(client: TestClient) -> None:
    l1 = make_lote_via_api(client, "L1")
    make_sheep_via_api(client, "ES-A", lote_id=l1["id"])
    make_sheep_via_api(client, "ES-B", lote_id=l1["id"])

    res = client.get(f"/api/lotes/{l1['id']}/sheep")
    assert res.status_code == 200
    crotales = sorted(s["crotal"] for s in res.json())
    assert crotales == ["ES-A", "ES-B"]


def test_create_sheep_with_invalid_lote_422(client: TestClient) -> None:
    res = client.post(
        "/api/sheep/",
        json={
            "crotal": "ES-BAD",
            "sexo": "femia",
            "data_nacemento": "2023-01-01",
            "lote_id": 9999,
        },
    )
    assert res.status_code == 422
