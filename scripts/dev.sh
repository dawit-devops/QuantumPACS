#!/bin/bash
set -e

DIR="$(cd "$(dirname "$0")/.." && pwd)"
CMD=${1:-status}

cleanup_port() {
    local port=$1
    local pids
    pids=$(fuser "$port/tcp" 2>/dev/null | awk '{for(i=2;i<=NF;i++) print $i}')
    for pid in $pids; do
        if ps -p "$pid" -o comm= 2>/dev/null | grep -qE 'uvicorn|gunicorn|python'; then
            echo "  cleaning stale process on port $port (PID $pid)"
            kill -9 "$pid" 2>/dev/null || true
        fi
    done
}

verify_config() {
    local CONFIG="$DIR/backend/config.local.yaml"
    if [ ! -f "$CONFIG" ]; then return; fi

    # Fix db_port mismatch — detect actual container port
    local CONTAINER_PORT
    CONTAINER_PORT=$(docker port quantumpacs-postgres-1 5432 2>/dev/null | head -1 | sed 's/.*://')
    if [ -n "$CONTAINER_PORT" ]; then
        local CFG_PORT
        CFG_PORT=$(grep -E '^db_port:' "$CONFIG" 2>/dev/null | awk '{print $2}' | tr -d ' ')
        if [ -n "$CFG_PORT" ] && [ "$CFG_PORT" != "$CONTAINER_PORT" ]; then
            echo "  fixing db_port $CFG_PORT → $CONTAINER_PORT"
            sed -i "s/^db_port: $CFG_PORT/db_port: $CONTAINER_PORT/" "$CONFIG"
        fi
    fi

    # Fix default secret
    local SECRET
    SECRET=$(grep -E '^secret:' "$CONFIG" 2>/dev/null | awk '{print $2}' | tr -d ' ')
    if [ -z "$SECRET" ] || [ "$SECRET" = "default" ] || [ "$SECRET" = "pa55w0rd" ] || \
       [ "$SECRET" = "quantumpacs-default-secret-32-bytes-long!!" ] || \
       [ "$SECRET" = "quantumpacs-dev-secret-replace-in-production-32b" ]; then
        echo "  fixing default secret → custom dev secret"
        if grep -q '^secret:' "$CONFIG" 2>/dev/null; then
            sed -i 's|^secret:.*|secret: quantum-local-dev-secret-replace-in-prod-2026-07-28|' "$CONFIG"
        else
            echo 'secret: quantum-local-dev-secret-replace-in-prod-2026-07-28' >> "$CONFIG"
        fi
    fi
}

case "$CMD" in
  start)
    echo "Starting QuantumPACS dev services..."
    verify_config
    echo "  starting PostgreSQL (Docker)..."
    docker compose up -d 2>&1 || true
    echo "  verifying config..."
    bash "$DIR/scripts/verify_config.sh" 2>&1 | tail -5
    echo "  starting backend..."
    systemctl --user start quantumpacs-backend.service
    echo "  starting frontend..."
    systemctl --user start quantumpacs-frontend.service
    echo "Done."
    ;;
  stop)
    echo "Stopping QuantumPACS dev services..."
    systemctl --user stop quantumpacs-backend.service || true
    systemctl --user stop quantumpacs-frontend.service || true
    cleanup_port 11112
    cleanup_port 8080
    echo "Done."
    ;;
  restart)
    echo "Restarting QuantumPACS dev services..."
    systemctl --user stop quantumpacs-backend.service 2>/dev/null || true
    cleanup_port 11112
    cleanup_port 8080
    verify_config
    systemctl --user start quantumpacs-backend.service
    systemctl --user restart quantumpacs-frontend.service 2>/dev/null || true
    echo "Done."
    ;;
  status)
    echo "=== QuantumPACS Backend ==="
    systemctl --user status quantumpacs-backend.service --no-pager 2>&1 | head -10
    echo ""
    echo "=== QuantumPACS Frontend ==="
    systemctl --user status quantumpacs-frontend.service --no-pager 2>&1 | head -10
    echo ""
    echo "=== Health Check ==="
    echo -n "Backend /api/health: "; curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/health 2>&1 || echo "down"
    echo -n "Backend /api/v2/health: "; curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/v2/health 2>&1 || echo "down"
    echo -n "Frontend (5173): "; curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/ 2>&1 || echo "down"
    echo ""
    ;;
  verify)
    bash "$DIR/scripts/verify_config.sh"
    ;;
  logs)
    journalctl --user -u quantumpacs-backend.service -f --no-pager 2>&1
    ;;
  logs-fe)
    journalctl --user -u quantumpacs-frontend.service -f --no-pager 2>&1
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|verify|logs|logs-fe}"
    exit 1
    ;;
esac
