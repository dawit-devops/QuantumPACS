#!/bin/bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$DIR/venv"

"$VENV/bin/python" db_init.py
"$VENV/bin/python" dcm_server.py &
"$VENV/bin/python" sync.py &
"$VENV/bin/gunicorn" app:app -k uvicorn.workers.UvicornWorker -c api_conf.py