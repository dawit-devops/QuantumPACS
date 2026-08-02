#!/bin/bash
# QuantumPACS database backup.
#
# Precedence for the connection:
#   1. DATABASE_URL if set (full override, e.g. a remote replica)
#   2. The running quantumpacs-postgres-1 container: real host port and the
#      actual POSTGRES_PASSWORD from its environment (never trust a
#      hardcoded default — the port is 5433 on hosts where 5432 was taken)
#   3. Environment fallbacks: POSTGRES_HOST/POSTGRES_PORT/POSTGRES_PASSWORD
#
# Retention: backups older than RETENTION_DAYS (default 14) are deleted.
set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
mkdir -p "$BACKUP_DIR"

if [ -n "${DATABASE_URL:-}" ]; then
    DB_URL="$DATABASE_URL"
else
    PORT="5432"
    PASSWORD="${POSTGRES_PASSWORD:-}"
    if docker ps --filter name=quantumpacs-postgres-1 --format '{{.Names}}' 2>/dev/null | grep -q postgres; then
        DETECTED_PORT=$(docker port quantumpacs-postgres-1 5432 2>/dev/null | head -1 | sed 's/.*://')
        [ -n "$DETECTED_PORT" ] && PORT="$DETECTED_PORT"
        CONTAINER_PW=$(docker exec quantumpacs-postgres-1 printenv POSTGRES_PASSWORD 2>/dev/null | tr -d ' \n')
        [ -n "$CONTAINER_PW" ] && PASSWORD="$CONTAINER_PW"
    fi
    PORT="${POSTGRES_PORT:-$PORT}"
    PASSWORD="${PASSWORD:-${POSTGRES_PASSWORD:-}}"
    if [ -z "$PASSWORD" ]; then
        echo "ERROR: cannot determine DB password — set POSTGRES_PASSWORD or DATABASE_URL" >&2
        exit 1
    fi
    DB_URL="postgresql://${POSTGRES_USER:-quantumpacs}:${PASSWORD}@${POSTGRES_HOST:-localhost}:${PORT}/${POSTGRES_DB:-quantumpacs}"
fi

BACKUP_FILE="$BACKUP_DIR/quantumpacs_$TIMESTAMP.dump"
pg_dump "$DB_URL" --format=custom --file="$BACKUP_FILE"
echo "Backup saved: $BACKUP_FILE"

# Retention: keep only the latest RETENTION_DAYS of daily dumps.
deleted=$(find "$BACKUP_DIR" -name 'quantumpacs_*.dump' -type f -mtime "+$RETENTION_DAYS" -delete -print | wc -l)
if [ "$deleted" -gt 0 ]; then
    echo "Retention: removed $deleted backup(s) older than $RETENTION_DAYS days"
fi
