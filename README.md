# Granxa Maps API

API en FastAPI para xestión de parcelas, lotes e gando con PostgreSQL/PostGIS.

## Requisitos

- Python 3.11+
- Docker + Docker Compose

## Levantar a base de datos

```bash
docker compose up -d
```

## Instalación

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

## Migracións (Alembic)

A xestión de esquema faise con Alembic:

```bash
alembic upgrade head   # aplicar todas as migracións pendentes
alembic downgrade -1   # reverter a última
alembic history        # ver o historial
```

En desenvolvemento tamén se pode usar `INIT_DB=1` no `.env` para que o
`lifespan` da app cree as táboas automaticamente con
`SQLModel.metadata.create_all` (útil para tinkering rápido; non usar en
producción).

## Executar

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

A API estará dispoñible en `http://localhost:8000`.

## Documentación

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI: `http://localhost:8000/openapi.json`

## Tests

```bash
pytest
```

Os tests de integración usan unha base de datos PostgreSQL/PostGIS
separada (`granxa_maps_test`) que se crea automaticamente a partir da
configuración `DATABASE_URL` por defecto.

## Endpoints principais

| Recurso   | Prefix       |
|-----------|--------------|
| Parcelas  | `/plots/`    |
| Ovellas   | `/sheep/`    |
| Rotacións | `/rotations/`|
| Lotes     | `/lotes/`    |
| Saúde     | `/health`    |

## Changelog

Ver [`CHANGELOG.md`](./CHANGELOG.md).
