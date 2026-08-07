#!/bin/bash
# QuantumPACS database backup — main DB plus every active tenant DB.
#
# Precedence for the connection:
#   1. DATABASE_URL if set (full override, e.g. a remote replica)
#   2. The running quantumpacs-postgres-1 container: real host port and the
#      actual POSTGRES_PASSWORD from its environment (never trust a
#      hardcoded default — the port is 5433 on hosts where 5432 was taken)
#   3. Environment fallbacks: POSTGRES_HOST/POSTGRES_PORT/POSTGRES_PASSWORD
#
# Per-tenant backups: every tenant registry row with status 'active' or
# 'provisioning' is dumped with its own connection settings (db_host/db_port/
# db_user/db_password from the row, falling back to the main-DB settings when
# the registry value is empty). Tenant DBs usually share the main host/port.
#
# Retention: backups older than RETENTION_DAYS (default 14) are deleted.
#   --dry-run: print the pg_dump commands without executing them.
set -euo pipefail

DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        *) echo "ERROR: unknown argument: $arg" >&2; exit 2 ;;
    esac
done

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
mkdir -p "$BACKUP_DIR"

if [ -n "${DATABASE_URL:-}" ]; then
    DB_URL="$DATABASE_URL"
    # Main-DB credentials for tenant rows whose registry fields are empty —
    # pulled from the URL itself so tenant dumps use the same credentials.
    DB_URL_USERINFO="${DB_URL#postgresql://}"; DB_URL_USERINFO="${DB_URL_USERINFO%%@*}"
    case "$DB_URL_USERINFO" in
        *:*) MAIN_USER="${DB_URL_USERINFO%%:*}"; MAIN_PASS="${DB_URL_USERINFO#*:}" ;;
        *) MAIN_USER="$DB_URL_USERINFO"; MAIN_PASS="" ;;
    esac
    DB_URL_HOSTPORT="${DB_URL#postgresql://}"; DB_URL_HOSTPORT="${DB_URL_HOSTPORT#*@}"; DB_URL_HOSTPORT="${DB_URL_HOSTPORT%%/*}"
    case "$DB_URL_HOSTPORT" in
        *:*) MAIN_HOST="${DB_URL_HOSTPORT%%:*}"; MAIN_PORT="${DB_URL_HOSTPORT#*:}" ;;
        *) MAIN_HOST="$DB_URL_HOSTPORT"; MAIN_PORT="" ;;
    esac
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

# Main DB dump.
BACKUP_FILE="$BACKUP_DIR/quantumpacs_$TIMESTAMP.dump"
if [ "$DRY_RUN" = "1" ]; then
    echo "DRY-RUN: pg_dump $DB_URL --format=custom --file=$BACKUP_FILE"
else
    pg_dump "$DB_URL" --format=custom --file="$BACKUP_FILE"
    echo "Backup saved: $BACKUP_FILE"
fi

# Per-tenant dumps — the tenants registry lives in the main DB.
# psql is required; when it is missing (or the table does not exist yet) the
# main dump above still succeeds, so this must never be fatal.
# The registry is read with \x1f (unit separator) fields: unlike tabs, a
# non-whitespace IFS does not collapse empty fields (e.g. a tenant that relies
# on the main DB's user/password).
TENANT_ROWS=""
if command -v psql >/dev/null 2>&1; then
    TENANT_ROWS=$(psql "$DB_URL" -AtF$'\x1f' -c \
        "SELECT db_name, COALESCE(db_host, ''), COALESCE(db_port::text, ''), \
                COALESCE(db_user, ''), COALESCE(db_password, '') \
         FROM tenants WHERE status IN ('active', 'provisioning') ORDER BY db_name" \
        2>/dev/null) || TENANT_ROWS=""
else
    echo "WARNING: psql not found — skipping per-tenant backups" >&2
fi

if [ -n "$TENANT_ROWS" ]; then
    while IFS=$'\x1f' read -r tdb thost tport tuser tpass; do
        [ -z "$tdb" ] && continue
        THOST="${thost:-${MAIN_HOST:-${POSTGRES_HOST:-localhost}}}"
        TPORT="${tport:-${MAIN_PORT:-${PORT:-${POSTGRES_PORT:-5432}}}}"
        TUSER="${tuser:-${MAIN_USER:-${POSTGRES_USER:-quantumpacs}}}"
        TPASS="${tpass:-${MAIN_PASS:-${PASSWORD:-${POSTGRES_PASSWORD:-}}}}"
        TENANT_URL="postgresql://${TUSER}:${TPASS}@${THOST}:${TPORT}/${tdb}"
        TENANT_FILE="$BACKUP_DIR/${tdb}_$TIMESTAMP.dump"
        if [ "$DRY_RUN" = "1" ]; then
            echo "DRY-RUN: pg_dump $TENANT_URL --no-password --format=custom --file=$TENANT_FILE"
        else
            pg_dump "$TENANT_URL" --no-password --format=custom --file="$TENANT_FILE"
            echo "Tenant backup saved: $TENANT_FILE"
        fi
    done <<< "$TENANT_ROWS"
fi

# Retention: keep only the latest RETENTION_DAYS of daily dumps (main + tenants).
if [ "$DRY_RUN" = "1" ]; then
    echo "DRY-RUN: find $BACKUP_DIR -name '*.dump' -type f -mtime +$RETENTION_DAYS -delete"
else
    deleted=$(find "$BACKUP_DIR" -name '*.dump' -type f -mtime "+$RETENTION_DAYS" -delete -print | wc -l)
    if [ "$deleted" -gt 0 ]; then
        echo "Retention: removed $deleted backup(s) older than $RETENTION_DAYS days"
    fi
fi
