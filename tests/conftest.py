"""Fixtures de pytest para os tests de integración.

Usa unha base de datos PostgreSQL/PostGIS separada (``granxa_maps_test``)
para non contaminar os datos de desenvolvemento. As táboas créanse unha
soa vez por sesión e, antes de cada test, vólvense ao estado baleiro.
"""

from __future__ import annotations

import os

# Configurar DATABASE_URL ANTES de importar a app para que `app.database.engine`
# se construía contra a base de datos de test.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg2://granxa:granxa@localhost:5432/granxa_maps_test",
)
os.environ.setdefault("INIT_DB", "0")

import psycopg2
import pytest
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import text
from sqlmodel import SQLModel, Session, create_engine
from fastapi.testclient import TestClient

# Estes imports deben ir DESPOIS de establecer DATABASE_URL.
from app.config import settings  # noqa: E402
from app.database import engine as real_engine, get_session  # noqa: E402
from app.models import Lote, Plot, Rotation, Sheep  # noqa: E402,F401
from app.main import app  # noqa: E402


TEST_DB_NAME = settings.database_url.rsplit("/", 1)[-1]


def _admin_conn():
    return psycopg2.connect(
        host="localhost",
        dbname="postgres",
        user="granxa",
        password="granxa",
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
        host="localhost",
        dbname=TEST_DB_NAME,
        user="granxa",
        password="granxa",
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    conn.close()


_ensure_test_db()


@pytest.fixture(scope="session")
def engine():
    test_engine = create_engine(settings.database_url)
    SQLModel.metadata.drop_all(test_engine)
    SQLModel.metadata.create_all(test_engine)
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
def client(engine):
    """TestClient coa sesión da base de datos de test inxectada."""

    def _get_test_session():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = _get_test_session
    # Non usamos `with TestClient(app)` para evitar que se execute o lifespan
    # (que falaría co motor real). As táboas xa están creadas polo fixture
    # `engine` da sesión.
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.pop(get_session, None)
