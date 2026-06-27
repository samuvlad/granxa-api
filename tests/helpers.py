"""Helpers comúns para os tests de integración."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Lote, Plot, Rotation, Sheep, User
from app.services.auth import hash_password


def make_user(
    session: Session,
    username: str,
    password: str = "test-password-123",
    is_active: bool = True,
) -> User:
    """Crea un usuario directamente na BD (evita pasar polo endpoint de login)."""
    user = User(
        username=username,
        hashed_password=hash_password(password),
        is_active=is_active,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


# GeoJSON dun polígono cadrado simple en Galicia.
SAMPLE_GEOMETRY: dict[str, Any] = {
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
}


def make_plot_via_api(
    client: TestClient,
    name: str,
    geometry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    res = client.post(
        "/api/plots/",
        json={
            "name": name,
            "geometry": geometry or SAMPLE_GEOMETRY,
        },
    )
    assert res.status_code == 200, res.text
    return res.json()


def make_lote_via_api(
    client: TestClient,
    name: str,
    notas: str | None = None,
) -> dict[str, Any]:
    res = client.post("/api/lotes/", json={"name": name, "notas": notas})
    assert res.status_code == 201, res.text
    return res.json()


def make_sheep_via_api(
    client: TestClient,
    crotal: str,
    lote_id: int | None = None,
    *,
    sexo: str = "femia",
    estado: str = "activo",
    nome: str | None = None,
    data_nacemento: str = "2023-01-15",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "crotal": crotal,
        "sexo": sexo,
        "data_nacemento": data_nacemento,
        "estado": estado,
    }
    if nome is not None:
        payload["nome"] = nome
    if lote_id is not None:
        payload["lote_id"] = lote_id
    res = client.post("/api/sheep/", json=payload)
    assert res.status_code == 201, res.text
    return res.json()


def make_rotation_via_api(
    client: TestClient,
    parcela_id: int,
    lote_id: int,
    data_inicio: str,
    data_fim: str | None = None,
) -> dict[str, Any]:
    payload = {
        "parcela_id": parcela_id,
        "lote_id": lote_id,
        "data_inicio": data_inicio,
    }
    if data_fim is not None:
        payload["data_fim"] = data_fim
    res = client.post("/api/rotations/", json=payload)
    assert res.status_code == 201, res.text
    return res.json()
