#!/bin/sh
set -e

# Run pending migrations on every start — fail fast so a broken migration
# stops the container instead of silently serving stale schema. Skippable
# for ephemeral/read-only deployments via SKIP_MIGRATIONS=1. Skipped when
# DB_HOST is unset (no DB_* env -> no psycopg2 fallback URL to use).
if [ "$SKIP_MIGRATIONS" != "1" ] && [ -n "$DB_HOST" ]; then
    python -m alembic upgrade head
fi

exec "$@"
