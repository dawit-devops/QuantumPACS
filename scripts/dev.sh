#!/bin/bash
set -e

DIR="$(cd "$(dirname "$0")/.." && pwd)"
CMD=${1:-status}

cleanup_port() {
    local port=$1
    local pids
    pids=$(timeout 5 fuser "$port/tcp" 2>/dev/null | awk '{for(i=2;i<=NF;i++) print $i}')
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
    echo "  starting backend..."
    systemctl --user start quantumpacs-backend.service 2>/dev/null || systemctl --user restart quantumpacs-backend.service
    sleep 2
    echo "  starting frontend..."
    systemctl --user start quantumpacs-frontend.service 2>/dev/null || systemctl --user restart quantumpacs-frontend.service
    echo "  verifying..."
    bash "$DIR/scripts/dev.sh" status
    ;;
  stop)
    echo "Stopping QuantumPACS dev services..."
    systemctl --user stop quantumpacs-backend.service 2>/dev/null || true
    systemctl --user stop quantumpacs-frontend.service 2>/dev/null || true
    cleanup_port 8080
    cleanup_port 11112
    cleanup_port 5173
    echo "  PostgreSQL container left running (docker compose stop to stop)"
    echo "Done."
    ;;
  restart)
    echo "Restarting QuantumPACS dev services..."
    systemctl --user stop quantumpacs-backend.service 2>/dev/null || true
    cleanup_port 8080
    cleanup_port 11112
    verify_config
    docker compose up -d 2>&1 || true
    systemctl --user start quantumpacs-backend.service
    sleep 2
    systemctl --user restart quantumpacs-frontend.service 2>/dev/null || true
    echo ""
    bash "$DIR/scripts/dev.sh" status
    ;;
  status)
    echo "=== QuantumPACS Status ==="
    echo ""
    BE_STATUS=$(systemctl --user is-active quantumpacs-backend.service 2>/dev/null)
    FE_STATUS=$(systemctl --user is-active quantumpacs-frontend.service 2>/dev/null)
    PG_STATUS=$(docker ps --filter name=quantumpacs-postgres-1 --format '{{.Status}}' 2>/dev/null || echo "not running")
    echo "  PostgreSQL : $PG_STATUS"
    echo "  Backend    : $BE_STATUS"
    echo "  Frontend   : $FE_STATUS"
    echo ""
    if [ "$BE_STATUS" = "active" ]; then
      echo "--- Health Endpoints ---"
      HEALTH=$(curl -s http://localhost:8080/api/health 2>/dev/null)
      if [ -n "$HEALTH" ]; then
        echo "  Overall   : $(echo "$HEALTH" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["status"])' 2>/dev/null || echo 'unknown')"
        echo "  DB        : $(echo "$HEALTH" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["components"]["database"]["status"])' 2>/dev/null)"
        echo "  Redis     : $(echo "$HEALTH" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["components"]["redis"]["status"])' 2>/dev/null)"
        echo "  ES        : $(echo "$HEALTH" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["components"]["elasticsearch"]["status"])' 2>/dev/null)"
        echo "  Storage   : $(echo "$HEALTH" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["components"]["storage"]["status"])' 2>/dev/null)"
        echo "  DICOM     : $(echo "$HEALTH" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["components"]["dicom_listener"]["status"])' 2>/dev/null)"
        echo "  Ingestion : $(echo "$HEALTH" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["components"]["ingestion_service"]["status"])' 2>/dev/null)"
      else
        echo "  (health endpoint not responding)"
      fi
    fi
    if [ "$FE_STATUS" = "active" ]; then
      FE_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/ 2>/dev/null)
      echo "  Frontend  : HTTP $FE_CODE"
    fi
    echo ""
    echo "--- Last Log Lines ---"
    echo "  Backend:"
    journalctl --user -u quantumpacs-backend.service --no-pager -n 3 2>/dev/null | sed 's/^/    /'
    echo "  Frontend:"
    journalctl --user -u quantumpacs-frontend.service --no-pager -n 3 2>/dev/null | sed 's/^/    /'
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
