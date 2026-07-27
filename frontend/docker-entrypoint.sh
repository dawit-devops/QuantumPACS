#!/bin/sh
set -e

export BACKEND_HOST="${BACKEND_HOST:-localhost:8080}"

envsubst '${BACKEND_HOST}' < /etc/nginx/nginx.conf > /tmp/nginx.conf
cat /tmp/nginx.conf > /etc/nginx/nginx.conf
rm /tmp/nginx.conf

exec "$@"