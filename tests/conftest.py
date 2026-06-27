"""Fixtures de pytest para os tests de integración.

Usa unha base de datos PostgreSQL/PostGIS separada (``granxa_maps_test``)
para non contaminar os datos de desenvolvemento. O esquema créase unha soa
vez por sesión vía Alembic (non SQLModel.metadata.create_all) para probar
exactamente o mesmo esquema que produción: constraints, exclusion
constraints, triggers, columna xerada, etc. Entre tests, trúncanse as
táboas en orde inversa de FK.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Configurar DATABASE_URL ANTES de importar a app para que `app.database.engine`
# se constrúa contra a base de datos de test.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg2://granxa:granxa@localhost:5432/granxa_maps_test",
)
os.environ.setdefault("INIT_DB", "0")
os.environ.setdefault("DB_ECHO", "0")
os.environ.setdefault(
    "JWT_SECRET", "test-jwt-secret-not-secure-but-stable-across-runs"
)

import bcrypt
import jwt
import psycopg2
import pytest
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import make_url, text
from sqlmodel import SQLModel, Session, create_engine
from fastapi.testclient import TestClient

from alembic import command
from alembic.config import Config as AlembicConfig

# Estes imports deben ir DESPOIS de establecer DATABASE_URL.
from app.config import settings  # noqa: E402
from app.database import engine as real_engine, get_session  # noqa: E402
from app.models import Lote, Plot, Rotation, Sheep, User  # noqa: E402,F401
from app.main import app  # noqa: E402


TEST_DB_NAME = settings.database_url.rsplit("/", 1)[-1]
ALEMBIC_INI = str(Path(__file__).resolve().parent.parent / "alembic.ini")

TEST_USERNAME = "test-user"
TEST_PASSWORD = "test-password-123"

# Parsear a DATABASE_URL para obter host/port/user/password (funciona tanto
# no contedor da API como no host de desenvolvemento).
_url = make_url(settings.database_url)
DB_HOST = _url.host or "localhost"
DB_PORT = _url.port or 5432
DB_USER = _url.username or "granxa"
DB_PASSWORD = _url.password or "granxa"


def _admin_conn():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname="postgres",
        user=DB_USER,
        password=DB_PASSWORD,
    )


def _ensure_test_db() -> None:
    conn = _admin_conn()
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB_NAME,))
    if cur.fetchone() is None:
        cur.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    conn.close()

    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=TEST_DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    cur.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    conn.close()


_ensure_test_db()


def _run_alembic_upgrade_head() -> None:
    cfg = AlembicConfig(ALEMBIC_INI)
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session")
def engine():
    test_engine = create_engine(settings.database_url)
    # Limpar calquera estado previo (táboas + alembic_version).
    SQLModel.metadata.drop_all(test_engine)
    with test_engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
        conn.commit()
    # Crear o esquema vía Alembic para probar constraints, triggers, etc.
    _run_alembic_upgrade_head()
    yield test_engine
    test_engine.dispose()


@pytest.fixture(autouse=True)
def _clean_tables(engine):
    """Limpa todas as táboas entre tests, respectando a orde de FKs."""
    with engine.begin() as conn:
        for table in reversed(SQLModel.metadata.sorted_tables):
            conn.execute(table.delete())
    yield


@pytest.fixture
def session(engine) -> Session:
    with Session(engine) as s:
        yield s


@pytest.fixture
def auth_token(engine) -> str:
    """Crea o usuario de test e devolve un JWT válido."""
    with Session(engine) as session:
        user = User(
            username=TEST_USERNAME,
            hashed_password=bcrypt.hashpw(
                TEST_PASSWORD.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8"),
        )
        session.add(user)
        session.commit()

    now = datetime.now(timezone.utc)
    payload = {
        "sub": TEST_USERNAME,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=60)).timestamp()),
    }
    return jwt.encode(
        payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )


@pytest.fixture
def client(engine, auth_token):
    """TestClient con sesión de test e cabeceira ``Authorization`` inxectada."""

    def _get_test_session():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = _get_test_session
    # Non usamos `with TestClient(app)` para evitar que se execute o lifespan
    # (que falaría co motor real). As táboas xa están creadas polo fixture
    # `engine` da sesión.
    test_client = TestClient(app)
    test_client.headers["Authorization"] = f"Bearer {auth_token}"
    yield test_client
    app.dependency_overrides.pop(get_session, None)


@pytest.fixture
def anon_client(engine):
    """TestClient con sesión de test pero sen autenticación (login + 401)."""

    def _get_test_session():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = _get_test_session
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.pop(get_session, None)
