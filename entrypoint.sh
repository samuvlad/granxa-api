#!/usr/bin/env bash
set -e

echo "[entrypoint] Waiting for database..."
python - <<'PY'
import os
import sys
import time
import psycopg2

url = os.environ["DATABASE_URL"].replace("postgresql+psycopg2://", "postgresql://")

for _ in range(60):
    try:
        conn = psycopg2.connect(url)
        conn.close()
        print("[entrypoint] Database is ready")
        sys.exit(0)
    except psycopg2.OperationalError as exc:
        print(f"[entrypoint] Waiting... ({exc})")
        time.sleep(1)

print("[entrypoint] Database not ready after 60s", file=sys.stderr)
sys.exit(1)
PY

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    echo "[entrypoint] Running migrations..."
    alembic upgrade head
else
    echo "[entrypoint] Skipping migrations (RUN_MIGRATIONS!=1)"
fi

echo "[entrypoint] Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
