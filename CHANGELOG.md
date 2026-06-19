# Changelog — API

## v0.2.0 — Asignación de ovellas a lotes

### Resumo

Engadimos a entidade `Lote` como recurso de primeira clase. As ovellas
poden asignarse a un lote e a súa `parcela_actual` derivase automaticamente
da rotación activa do lote.

### Migración de base de datos

```bash
alembic upgrade head
```

A migration:

- Crea a táboa `lotes` (id, name único, notas, timestamps).
- Engade `sheep.lote_id` (FK nullable a `lotes.id`, `ON DELETE SET NULL`).
- Engade `rotations.lote_id` (FK NOT NULL a `lotes.id`, `ON DELETE CASCADE`).
- Migra os `lote_nome` distintos existentes a `lotes`.
- Asigna cada ovella con `parcela_actual_id` ao lote da rotación activa
  máis recente desa parcela. As ovellas sen coincidencia quedan con
  `lote_id = NULL` (rexistradas no log da migración).
- Recalcula `sheep.parcela_actual_id` a partir da rotación activa do lote.
- Elimina a columna `rotations.lote_nome`.

**Importante**: antes de despregar, executar `alembic upgrade head`. O
`init_db()` antigo (que creaba táboas con `SQLModel.metadata.create_all`)
está desactivado por defecto; pódese reactivar con `INIT_DB=1` no `.env`
en desenvolvemento.

### Modelo de datos

#### Nova táboa `lotes`

| Campo       | Tipo            | Notas                       |
|-------------|-----------------|-----------------------------|
| id          | int PK          | autoincrement               |
| name        | str UNIQUE      | máx. 120 caracteres         |
| notas       | str NULL        |                             |
| created_at  | timestamp       |                             |
| updated_at  | timestamp       |                             |

#### Cambios en `sheep`

- Engadido `lote_id` (FK nullable a `lotes.id`).
- `parcela_actual_id` mantense por compatibilidade pero xa NON se acepta
  como input. O backend ignórao (rexístrase warning no log) e dérivao
  da rotación activa do lote.

#### Cambios en `rotations`

- `lote_nome: str` → `lote_id: int` (FK NOT NULL a `lotes.id`).

### Endpoints novos

| Método | Ruta                       | Descrición                              |
|--------|----------------------------|------------------------------------------|
| GET    | `/lotes/`                  | Lista os lotes (ordenados por `name`).   |
| POST   | `/lotes/`                  | Crea un lote. Body: `{ name, notas? }`.  |
| GET    | `/lotes/{id}`              | Detalle dun lote.                        |
| PATCH  | `/lotes/{id}`              | Actualiza `name` e/ou `notas`.           |
| DELETE | `/lotes/{id}`              | 204. 409 se ten ovellas ou rotacións.    |
| GET    | `/lotes/{id}/sheep`        | Ovellas do lote (con `parcela_actual_id` derivada). |
| GET    | `/sheep/?lote_id={id}`     | Filtro de ovellas por lote.              |

### Endpoints modificados

- `POST /sheep/`, `PATCH /sheep/{id}`:
  - Aceptan `lote_id` (opcional).
  - **Ignoran** `parcela_actual_id` (warning no log).
- `POST /rotations/`, `PATCH /rotations/{id}`:
  - `lote_nome` substituído por `lote_id` (FK obrigatoria).
  - Ao crear unha rotación activa, recalcula `parcela_actual_id` das
    ovellas do lote.
  - Ao pechar unha rotación, recalcula:
    - se hai outra rotación activa do mesmo lote → usar a súa parcela;
    - se non → `parcela_actual_id = NULL`.

### Cambios nos responses

- `GET /sheep/` e `GET /sheep/{id}`:
  - Inclúe `lote_id` (int|null).
  - Inclúe `lote: { id, name } | null` embebido.
  - `parcela_actual_id` segue presente pero agora é **derivado** (non
    editable).
- `GET /rotations/` e `GET /rotations/{id}`:
  - Inclúe `lote: { id, name }` embebido.
  - `lote_nome` xa non está presente.

### Compatibilidade

- **Breaking**: `lote_nome` deixa de existir. Os clientes que o envían
  non obteñen erro (Pydantic ignora campos extra), pero o valor non se
  persiste en ningures.
- **Soft breaking**: `parcela_actual_id` en `POST/PATCH /sheep/` é
  ignorado. Os clientes que o seguen enviando obterán o valor
  *derivado* no response.
- Recoméndase activar un feature flag no frontend durante o rollout
  (`USE_LOTES_V2=true`) e desactivalo se se detectan regresións.

### Regra de negocio: `parcela_actual_id`

A columna `sheep.parcela_actual_id` segue existindo pero xa non é
editábel. O backend:

1. Ao crear unha ovella con `lote_id`, calcula a parcela activa
   inmediatamente.
2. Ao crear/actualizar/cerrar/eliminar unha rotación, recalcula a
   parcela activa para todas as ovellas do lote afectado.
3. Ao cambiar o `lote_id` dunha ovella, recalcula ambos os dous lotes
   (anterior e novo).

A "rotación activa" dun lote é a máis recente con `data_fim IS NULL`
(ordeado por `data_inicio DESC, id DESC`).

### Exemplo: crear un lote, asignar unha ovella, rotar

```http
POST /lotes/
{ "name": "Lote 1 — Ovejas adultas" }
→ 201 { "id": 1, "name": "...", ... }

POST /sheep/
{ "crotal": "ES001", "sexo": "femia", "data_nacemento": "2023-01-01",
  "lote_id": 1 }
→ 201 { "lote_id": 1, "parcela_actual_id": null, ... }

POST /rotations/
{ "parcela_id": 5, "lote_id": 1, "data_inicio": "2026-06-01T00:00:00" }
→ 201 { "lote": { "id": 1, "name": "..." }, ... }
# A ovella do lote 1 pasa automaticamente a parcela_actual_id = 5

GET /sheep/?lote_id=1
→ 200 [{ "lote_id": 1, "parcela_actual_id": 5, ... }]
```

### Notas para o equipo de frontend

- O picker de parcelas na pantalla de ovellas xa non é editable. Só se
  mostra (read-only) en base ao `parcela_actual_id` derivado.
- Engadir UI para xestión de lotes: lista, creación, edición, borrado.
  Usar `GET /lotes/`, `POST /lotes/`, `PATCH /lotes/{id}`,
  `DELETE /lotes/{id}`.
- Engadir un selector de lote no formulario de edición de ovellas e no
  detalle de rotacións.
- Telas a actualizar:
  - `SheepList` / `SheepForm`: mostrar `lote` embebido + `parcela_actual_id`
    derivado.
  - `RotationForm`: substituír input libre de `lote_nome` por selector
    de lotes.
  - Novo: `LotesList` / `LoteForm`.
