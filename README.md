# Granxa Maps API

API en FastAPI para xestión de parcelas, lotes e gando con PostgreSQL/PostGIS.

## Quickstart (recomendado — Docker)

Só necesitas Docker. Noutro PC, clona e:

```bash
docker compose up --build
```

Iso levanta:

- PostgreSQL/PostGIS en `localhost:5433`
- API en `http://localhost:8000` (Swagger en `/docs`)

As migracións de Alembic aplícanse automaticamente ao arrancar o contedor
(`alembic upgrade head` no `entrypoint.sh`). O código móntase como volume,
así que os cambios recargan con `--reload` sen necesidade de rebuild.

Atallos con `make`:

```bash
make up        # docker compose up --build
make down      # docker compose down
make logs      # logs en seguimento
make shell     # bash dentro do contedor da API
make migrate   # aplicar migracións
make test      # correr pytest
make clean     # parar e borrar volumes (DB incluída)
```

## Desenvolvemento local sen Docker

Se prefires correr a API no teu Python local:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env

# Noutro terminal, levanta só a DB:
docker compose up -d db

# Migracións + API:
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
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

Todas as rutas da API van baixo o prefix `/api`.

| Recurso   | Prefix           |
|-----------|------------------|
| Parcelas  | `/api/plots/`    |
| Ovellas   | `/api/sheep/`    |
| Rotacións | `/api/rotations/`|
| Lotes     | `/api/lotes/`    |
| Saúde     | `/api/health`    |

## Rede Docker externa

O contedor da API únese á rede externa `granxa-net` para poder
comunicarse con outros servizos do mesmo ecosistema (por exemplo, un
proxy inverso ou servizos complementarios que vivan nesa rede). Antes
de levantar a API por primeira vez, créaa no host:

```bash
docker network create granxa-net
```

Se non existe, `docker compose up` fallará ao iniciar o servizo `api`.

## Changelog

Ver [`CHANGELOG.md`](./CHANGELOG.md).
