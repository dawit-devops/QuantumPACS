#!/bin/sh
set -e

# Run pending migrations — fail fast: a migration failure must stop the
# container (an unhealthy container is preferable to silently stale schema).
# The single-image deploys may run without DB_* env (DB on the host); the
# ini fallback URL needs psycopg2 which is not installed here, so skip.
if [ "$SKIP_MIGRATIONS" != "1" ] && [ -n "$DB_HOST" ]; then
    alembic upgrade head
fi

# Start Caddy reverse proxy
caddy run --config /etc/caddy/Caddyfile &
CADDY_PID=$!

# Start Starlette/UVicorn via Gunicorn
gunicorn app:app -k uvicorn.workers.UvicornWorker -c api_conf.py &
GUNICORN_PID=$!

# Forward signals and exit when either process dies
trap "kill $CADDY_PID $GUNICORN_PID 2>/dev/null; exit" SIGINT SIGTERM

wait $GUNICORN_PID
EXIT_CODE=$?

kill $CADDY_PID 2>/dev/null
exit $EXIT_CODE
