#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "== Pull imaxes =="
docker compose -f docker-compose.prod.yml pull

echo "== Levantar servizos =="
docker compose -f docker-compose.prod.yml up -d

echo "== Esperar a que a API estea sa =="
for _ in $(seq 1 30); do
    if curl -fsS http://localhost:8000/api/health >/dev/null 2>&1; then
        echo "API sa."
        break
    fi
    sleep 2
done

docker compose -f docker-compose.prod.yml ps