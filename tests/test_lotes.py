"""Tests do CRUD de /lotes/."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.helpers import (
    make_lote_via_api,
    make_plot_via_api,
    make_rotation_via_api,
    make_sheep_via_api,
)


def test_list_lotes_empty(client: TestClient) -> None:
    res = client.get("/lotes/")
    assert res.status_code == 200
    assert res.json() == []


def test_create_and_get_lote(client: TestClient) -> None:
    lote = make_lote_via_api(client, "Lote 1 — Test", notas="notas iniciais")
    assert lote["id"] > 0
    assert lote["name"] == "Lote 1 — Test"
    assert lote["notas"] == "notas iniciais"
    assert "created_at" in lote

    res = client.get(f"/lotes/{lote['id']}")
    assert res.status_code == 200
    assert res.json()["name"] == "Lote 1 — Test"


def test_create_lote_strips_name(client: TestClient) -> None:
    res = client.post("/lotes/", json={"name": "  "})
    assert res.status_code == 422


def test_create_lote_duplicate_name_409(client: TestClient) -> None:
    make_lote_via_api(client, "Lote duplicado")
    res = client.post("/lotes/", json={"name": "Lote duplicado"})
    assert res.status_code == 409


def test_update_lote(client: TestClient) -> None:
    lote = make_lote_via_api(client, "Lote orixinal")
    res = client.patch(
        f"/lotes/{lote['id']}",
        json={"name": "Lote renomeado", "notas": "novas"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "Lote renomeado"
    assert body["notas"] == "novas"


def test_update_lote_duplicate_name_409(client: TestClient) -> None:
    a = make_lote_via_api(client, "A")
    b = make_lote_via_api(client, "B")
    res = client.patch(f"/lotes/{b['id']}", json={"name": "A"})
    assert res.status_code == 409


def test_delete_lote_ok(client: TestClient) -> None:
    lote = make_lote_via_api(client, "Lote baleiro")
    res = client.delete(f"/lotes/{lote['id']}")
    assert res.status_code == 204
    res = client.get(f"/lotes/{lote['id']}")
    assert res.status_code == 404


def test_delete_lote_with_sheep_409(client: TestClient) -> None:
    lote = make_lote_via_api(client, "Lote con ovellas")
    make_sheep_via_api(client, "ES-TEST-1", lote_id=lote["id"])
    res = client.delete(f"/lotes/{lote['id']}")
    assert res.status_code == 409
    assert "ovellas" in res.json()["detail"]


def test_delete_lote_with_rotations_409(client: TestClient) -> None:
    plot = make_plot_via_api(client, "P-1")
    lote = make_lote_via_api(client, "Lote con rotacións")
    make_rotation_via_api(
        client,
        parcela_id=plot["id"],
        lote_id=lote["id"],
        data_inicio="2026-01-01T00:00:00",
        data_fim="2026-02-01T00:00:00",
    )
    res = client.delete(f"/lotes/{lote['id']}")
    assert res.status_code == 409
    assert "rotacións" in res.json()["detail"]


def test_list_lotes_ordered_by_name(client: TestClient) -> None:
    make_lote_via_api(client, "B-lote")
    make_lote_via_api(client, "A-lote")
    make_lote_via_api(client, "C-lote")
    res = client.get("/lotes/")
    assert res.status_code == 200
    names = [l["name"] for l in res.json()]
    assert names == ["A-lote", "B-lote", "C-lote"]
