#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

BACKUP_DIR="${BACKUP_DIR:-/opt/granxa/backups}"
DB_NAME="${DB_NAME:-granxa_maps}"
STAMP="$(date +%Y%m%d-%H%M)"

mkdir -p "$BACKUP_DIR"

echo "[$(date -Is)] Iniciando backup de $DB_NAME..."
docker compose -f docker-compose.prod.yml exec -T db \
    pg_dump -U granxa -Fc "$DB_NAME" > "$BACKUP_DIR/granxa_$STAMP.dump"

# Rotación: conservar 48 backups horarios + 14 diarios (00:00).
# Borrar os horarios con máis de 48 h que non sexan o diario (00:00).
find "$BACKUP_DIR" -name 'granxa_*.dump' -mmin +2880 ! -name 'granxa_*_0000.dump' -delete
# Borrar todo o que teña máis de 14 días.
find "$BACKUP_DIR" -name 'granxa_*.dump' -mtime +14 -delete

echo "[$(date -Is)] Backup feito: $BACKUP_DIR/granxa_$STAMP.dump"