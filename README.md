# Granxa Maps API

API en FastAPI para xestión de parcelas e gando con PostgreSQL/PostGIS.

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

## Executar

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

A API estará dispoñible en `http://localhost:8000`.

## Documentación

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI: `http://localhost:8000/openapi.json`
