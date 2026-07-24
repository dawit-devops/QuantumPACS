#!/bin/sh
set -e

# Run pending migrations
if [ "$SKIP_MIGRATIONS" != "1" ]; then
    alembic upgrade head 2>/dev/null || echo "No migrations to apply or alembic not configured"
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
