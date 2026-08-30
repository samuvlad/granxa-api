#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ "$#" -ne 1 ]; then
    echo "Uso: restore.sh <ficheiro.dump>"
    exit 1
fi
BACKUP="$1"
if [ ! -f "$BACKUP" ]; then
    echo "Non existe o ficheiro: $BACKUP"
    exit 1
fi

echo "Vas restaurar $BACKUP sobre a BD granxa_maps (granxa-prod-db)."
read -r -p "Seguro? [y/N] " resp
if [ "$resp" != "y" ] && [ "$resp" != "Y" ]; then
    echo "Cancelado."
    exit 1
fi

docker compose -f docker-compose.prod.yml exec -T db \
    pg_restore -U granxa -d granxa_maps --clean --if-exists < "$BACKUP"

echo "Restauración rematada."