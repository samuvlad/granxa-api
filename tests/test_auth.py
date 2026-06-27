"""Tests do control de accesos (login + dependency get_current_user)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.config import settings
from app.services.auth import hash_password
from tests.conftest import TEST_PASSWORD, TEST_USERNAME
from tests.helpers import make_user


def test_login_success(anon_client: TestClient, session: Session) -> None:
    make_user(session, "alice", password="secret123")
    res = anon_client.post(
        "/api/auth/login", json={"username": "alice", "password": "secret123"}
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password(anon_client: TestClient, session: Session) -> None:
    make_user(session, "alice", password="secret123")
    res = anon_client.post(
        "/api/auth/login", json={"username": "alice", "password": "WRONG"}
    )
    assert res.status_code == 401
    assert "incorrectos" in res.json()["detail"].lower()


def test_login_unknown_user(anon_client: TestClient) -> None:
    res = anon_client.post(
        "/api/auth/login", json={"username": "nobody", "password": "x"}
    )
    assert res.status_code == 401


def test_login_inactive_user(anon_client: TestClient, session: Session) -> None:
    make_user(session, "alice", password="secret123", is_active=False)
    res = anon_client.post(
        "/api/auth/login", json={"username": "alice", "password": "secret123"}
    )
    assert res.status_code == 401


def test_login_missing_fields(anon_client: TestClient) -> None:
    res = anon_client.post("/api/auth/login", json={"username": "alice"})
    assert res.status_code == 422
    res = anon_client.post("/api/auth/login", json={"password": "x"})
    assert res.status_code == 422


def test_me_with_token(client: TestClient) -> None:
    res = client.get("/api/auth/me")
    assert res.status_code == 200
    body = res.json()
    assert body["username"] == TEST_USERNAME
    assert body["is_active"] is True
    assert "created_at" in body


def test_me_without_token(anon_client: TestClient) -> None:
    res = anon_client.get("/api/auth/me")
    assert res.status_code == 401


def test_protected_endpoint_without_token(anon_client: TestClient) -> None:
    res = anon_client.get("/api/plots/")
    assert res.status_code == 401


def test_protected_endpoint_with_garbage_token(anon_client: TestClient) -> None:
    anon_client.headers["Authorization"] = "Bearer not-a-valid-jwt"
    res = anon_client.get("/api/plots/")
    assert res.status_code == 401


def test_protected_endpoint_with_wrong_scheme(anon_client: TestClient) -> None:
    anon_client.headers["Authorization"] = f"Basic {TEST_PASSWORD}"
    res = anon_client.get("/api/plots/")
    assert res.status_code == 401


def test_protected_endpoint_with_expired_token(anon_client: TestClient) -> None:
    expired = jwt.encode(
        {
            "sub": "anyone",
            "iat": int(
                (
                    datetime.now(timezone.utc) - timedelta(hours=2)
                ).timestamp()
            ),
            "exp": int(
                (
                    datetime.now(timezone.utc) - timedelta(minutes=1)
                ).timestamp()
            ),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    anon_client.headers["Authorization"] = f"Bearer {expired}"
    res = anon_client.get("/api/plots/")
    assert res.status_code == 401
    assert "caducado" in res.json()["detail"].lower()


def test_protected_endpoint_with_valid_token(client: TestClient) -> None:
    res = client.get("/api/lotes/")
    assert res.status_code == 200
    assert res.json() == []


def test_health_does_not_require_auth(anon_client: TestClient) -> None:
    res = anon_client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_login_with_inactive_token_after_deactivation(
    anon_client: TestClient, session: Session
) -> None:
    """Un token previamente emitido deixa de funcionar se o usuario se desactiva."""
    user = make_user(session, "alice", password="secret123")
    res = anon_client.post(
        "/api/auth/login", json={"username": "alice", "password": "secret123"}
    )
    assert res.status_code == 200
    token = res.json()["access_token"]

    anon_client.headers["Authorization"] = f"Bearer {token}"
    res = anon_client.get("/api/auth/me")
    assert res.status_code == 200

    user.is_active = False
    session.add(user)
    session.commit()

    res = anon_client.get("/api/auth/me")
    assert res.status_code == 401


def test_password_hashing_is_not_plaintext() -> None:
    """O hash gardado non debe ser o contrasinal en claro."""
    h = hash_password("super-secret")
    assert h != "super-secret"
    assert h.startswith("$2")  # bcrypt
