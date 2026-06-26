# AGENTS.md — granxa-maps-api

Servizo FastAPI para xestionar parcelas, lotes, ovellas e rotacións sobre PostgreSQL/PostGIS. ORM SQLModel, migracións con Alembic, GeoAlchemy2/PostGIS para a xeometría.

Entrada: `app/main.py`. Configuración: `app/config.py` (Pydantic Settings, le `.env`).

## Comandos

Camiño recomendado: Docker.

```bash
docker network create granxa-net      # unha soa vez, ver "Rede Docker" abaixo
docker compose up --build             # DB en :5433, API en :8000, Swagger en /docs
make up / make logs / make shell / make down / make clean
make migrate                          # alembic upgrade head dentro do contedor da API
make test                             # pytest dentro do contedor da API
```

Desenvolvemento local con Python: `python3 -m venv venv && source venv/bin/activate && pip install -e ".[dev]"`, logo `docker compose up -d db`, `alembic upgrade head`, `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`.

O `Dockerfile` instala os paquetes de sistema `libgdal-dev libgeos-dev libproj-dev` por mor de `geoalchemy2`/`shapely`/`pyproj`. Un `pip install` a pelo nun host sen esas libs fallará ao compilar.

`entrypoint.sh` execútase en cada arranque do contedor: agarda ata 60s por Postgres → (se `RUN_MIGRATIONS=1`) `alembic upgrade head` → `uvicorn … --reload`. Por defecto `RUN_MIGRATIONS=1`; en produción con múltiples réplicas, desactívao e executa as migracións nun init container/job.

## Notas de alto valor

### 1. Todos os endpoints van baixo `/api`

Os routers móntanse con `prefix="/api"` en `app/main.py` (`plots`, `sheep`, `rotations`, `lotes` e o de saúde). Cando engadas un test ou modifiques unha ruta, lembra que o path debe incluír `/api/...` — se non, `pytest` devolverá 404. Axuda: `tests/helpers.py` centraliza as chamadas comúns (`make_plot_via_api`, `make_lote_via_api`, `make_sheep_via_api`, `make_rotation_via_api`).

### 2. `granxa-net` é unha rede Docker externa

`docker-compose.yml` declara `granxa-net` como `external: true`. O servizo `api` non arrancará se a rede non existe no host. Créaa unha soa vez:

```bash
docker network create granxa-net
```

O contedor da API únese a esta rede para falar con outros servizos do ecosistema granxa (proxy inverso, etc.).

### 3. Particularidades do conftest de tests (`tests/conftest.py`)

- Establece `DATABASE_URL=postgresql+psycopg2://granxa:granxa@localhost:5432/granxa_maps_test` **antes** de importar `app.*` para que `app.database.engine` se constrúa contra a base de datos de test. Non reordenes os imports. Os parámetros de conexión (host/port/user/password) obtéñense parseando `DATABASE_URL`, así funciona tanto no contedor da API (`db:5432`) como no host (`localhost:5433`).
- Crea automaticamente `granxa_maps_test` e activa as extensións `postgis` e `btree_gist` como usuario `granxa:granxa`.
- O esquema créase **unha vez por sesión vía `alembic upgrade head`** (non `SQLModel.metadata.create_all`) para probar exactamente o mesmo que produción: constraints, exclusion constraints, columna xerada `duracion`, triggers `updated_at`, etc. Entre tests, trúncanse as táboas en orde inversa de FK (autouse `_clean_tables`).
- Usa `TestClient(app)` **sen** `with` para saltarse o `lifespan` (que tocaría o motor real). Non o cambies.
- Sobreescribe `get_session` para usar o motor de test.

Executar un test concreto: `docker compose exec api pytest tests/test_lotes.py -k delete_lote`.

### 4. `Sheep.parcela_actual_id` non se persiste

Non hai columna `sheep.parcela_actual_id` na BD. A parcela actual dunha ovella **dérivase on read** da rotación activa do seu `lote_id` (`app/services/lotes.py:derive_parcela_for_lote`, invocada desde `sheep_to_read` e na listaxe con batch). O campo só aparece no response (`SheepRead.parcela_actual_id`); se un cliente o envía no payload, Pydantic descártao en silencio (xa non está no schema de entrada).

### 5. Regra de dominio: rotación activa (enforce na BD)

A "rotación activa" dun lote = a fila con `data_fim IS NULL`. A BD **garante** que só pode haber unha por lote mediante o partial unique index `uq_rotations_active_per_lote`. Ademais, o exclusion constraint `excl_rotations_lote_overlap` (sobre a columna xerada `duracion tstzrange`) rexeita rotacións solapadas do mesmo lote. As violacións destas constraints cáptanse nos routers como `IntegrityError` → 409 (`app/routers/rotation.py:_handle_integrity_error`).

Non hai `recompute_parcela_actual_for_lote` (a columna xa non existe); a derivación faise só ao ler.

### 6. As novas táboas de SQLModel hai que exportalas

`alembic/env.py` importa `from app.models import Lote, Plot, Rotation, Sheep` para rexistrar as táboas. Calquera modelo novo debe reexportarse en `app/models/__init__.py`; se non, Alembic non xerará nin aplicará a súa migración.

## Variables de contorno

Pydantic Settings le desde `.env`. Os nomes dos campos van en minúsculas no modelo, pero por defecto as variables de contorno van en maiúsculas. `.env` está en `.gitignore`; copia desde `.env.example`.

| Variable         | Por defecto                                                                 | Notas |
|------------------|-----------------------------------------------------------------------------|-------|
| `DATABASE_URL`   | `postgresql+psycopg2://granxa:granxa@localhost:5432/granxa_maps`             | Usada por `app.database.engine`, `alembic/env.py` e o conftest de tests. |
| `API_HOST`       | `0.0.0.0`                                                                   | Só de referencia — `entrypoint.sh` leva `--host 0.0.0.0 --port 8000` fixos. |
| `API_PORT`       | `8000`                                                                      | Idem. |
| `INIT_DB`        | `0` (`False`)                                                               | Se vale `1`, o `lifespan` de FastAPI chama `SQLModel.metadata.create_all` ao arrancar. Só para tinkering en desenvolvemento — evita Alembic. |
| `DB_ECHO`        | `0` (`False`)                                                               | Activa o log de SQL de SQLAlchemy (`app/database.py`). |
| `RUN_MIGRATIONS` | `1` (`True`)                                                                | Se vale `1`, o `entrypoint.sh` executa `alembic upgrade head` ao arrancar. En prod con múltiples réplicas, desactívao e migra nun init container/job. |

## Outras cousas que paga a pena saber

- **A lista de CORS está hardcoded** en `app/main.py` (`localhost:3000`, `192.168.1.11:3000`). Engade alí os novos orixes; non hai variable de contorno para isto.
- **Xeometría de parcela** é PostGIS `POLYGON` SRID 4326 a través de GeoAlchemy2. `area_m2` e `perimeter_m` calcúlanse en UTM ao insertar/actualizar (`app/utils/geo.py`) e gárdanse — non se calculan ao ler.
- **Non hai ferramentas de lint nin typecheck configuradas.** Non hai config de ruff/mypy/pyright, non hai pre-commit, non hai workflow de CI (`.github/` non existe). `pytest` é a única verificación. Non corras un `make lint` — non existe.
- **O borrado de lote está restrinxido**: `DELETE /api/lotes/{id}` devolve 409 se o lote ten ovellas ou rotacións (`app/routers/lotes.py`).
- **O borrado de parcela está restrinxido**: `DELETE /api/plots/{id}` devolve 409 se a parcela ten rotacións (`app/routers/plots.py`). Ademais a FK `rotations.parcela_id` é `ON DELETE RESTRICT`, así que un borrado fóra da API tampouco pode destruír histórico de rotacións.
- **Integridade relacional na BD**: timestamps son `timestamptz` con `DEFAULT now()` e un trigger `BEFORE UPDATE` (`set_updated_at()`) actualiza `updated_at` automaticamente en todas as táboas — non se toca manualmente nos routers. `sheep.sexo`/`sheep.estado` teñen `CHECK` constraints; `plots.name` e `lotes.name` son `UNIQUE`. As violacións destas constraints cáptanse como `IntegrityError` → 409/422 nos routers.
- **Migracións**: `alembic/versions/` contén unha soa revisión inicial (`0001_initial`) escrita a man. As novas revisións deben encadear desde a cabeza actual. Corre `alembic history` para ver a cadea.
- **Layout**: `app/{config,database,main}.py`, `app/{models,routers,schemas,services,utils}/`, `alembic/`, `tests/`. `app/services/` polo de agora só contén `lotes.py`; a lóxica de dominio que non atangue a un único recurso vive aí.
- **Helpers**: `tests/helpers.py` expón factorías `make_*_via_api` que crean entidades a través da API. Prefireas antes que escribir payloads inline.
