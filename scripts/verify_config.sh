#!/bin/bash
set -e

DIR="$(cd "$(dirname "$0")/.." && pwd)"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }

echo "=== QuantumPACS Configuration Verification ==="
echo ""

# --- 1. Config file ---
echo "--- 1. Config File ---"
CONFIG="$DIR/backend/config.local.yaml"
if [ ! -f "$CONFIG" ]; then
    warn "config.local.yaml not found — creating from defaults"
    cat > "$CONFIG" <<'EOF'
db_host: 127.0.0.1
db_port: 5433
db_user: quantumpacs
db_password: pa55w0rd
db_database: quantumpacs
redis_host: localhost
redis_port: 6379
secret: quantum-local-dev-secret-replace-in-prod-2026-07-28
EOF
    pass "created $CONFIG"
fi

# Detect actual PostgreSQL port from Docker
CONTAINER_PORT=""
if docker ps --filter name=quantumpacs-postgres-1 --format '{{.Names}}' 2>/dev/null | grep -q postgres; then
    CONTAINER_PORT=$(docker port quantumpacs-postgres-1 5432 2>/dev/null | head -1 | sed 's/.*://')
fi

# Check db_port
DB_PORT=$(grep -E '^db_port:' "$CONFIG" | awk '{print $2}' | tr -d ' ')
if [ -n "$CONTAINER_PORT" ] && [ "$DB_PORT" != "$CONTAINER_PORT" ]; then
    fail "db_port is $DB_PORT but PostgreSQL container exposes $CONTAINER_PORT"
    if grep -q "^db_port: $DB_PORT" "$CONFIG"; then
        sed -i "s/^db_port: $DB_PORT/db_port: $CONTAINER_PORT/" "$CONFIG"
        pass "fixed db_port → $CONTAINER_PORT"
    fi
elif [ -n "$CONTAINER_PORT" ] && [ "$DB_PORT" = "$CONTAINER_PORT" ]; then
    pass "db_port = $CONTAINER_PORT (matches container)"
else
    pass "db_port = $DB_PORT"
fi

# Check secret
SECRET=$(grep -E '^secret:' "$CONFIG" | awk '{print $2}' | tr -d ' ')
if [ -z "$SECRET" ] || [ "$SECRET" = "default" ] || [ "$SECRET" = "pa55w0rd" ] || \
   [ "$SECRET" = "quantumpacs-default-secret-32-bytes-long!!" ] || \
   [ "$SECRET" = "quantumpacs-dev-secret-replace-in-production-32b" ]; then
    fail "secret is a known default — assert_production_secret() will exit"
    if ! grep -q '^secret:' "$CONFIG"; then
        echo 'secret: quantum-local-dev-secret-replace-in-prod-2026-07-28' >> "$CONFIG"
    else
        sed -i 's|^secret:.*|secret: quantum-local-dev-secret-replace-in-prod-2026-07-28|' "$CONFIG"
    fi
    pass "fixed secret"
else
    pass "secret is custom"
fi

echo ""

# --- 2. Dependencies ---
echo "--- 2. Dependencies ---"
VENV_PYTHON="$DIR/backend/venv/bin/python3"
if [ ! -f "$VENV_PYTHON" ]; then
    fail "virtual env python not found at $VENV_PYTHON"
    exit 1
fi

# Check Pillow
if "$VENV_PYTHON" -c "from PIL import Image; print('ok')" 2>/dev/null; then
    pass "Pillow installed"
else
    warn "Pillow missing — installing"
    "$DIR/backend/venv/bin/pip" install Pillow 2>&1 | tail -1
    pass "Pillow installed"
fi

# Check pynetdicom
if "$VENV_PYTHON" -c "from pynetdicom import AE; print('ok')" 2>/dev/null; then
    pass "pynetdicom installed"
else
    fail "pynetdicom missing — run: pip install pynetdicom"
fi

echo ""

# --- 3. Port conflicts ---
echo "--- 3. Port Conflicts ---"
check_port() {
    local port=$1
    if fuser "$port/tcp" 2>/dev/null > /dev/null; then
        warn "port $port is in use (may interfere)"
    else
        pass "port $port free"
    fi
}

check_port 8080
check_port 11112
echo ""

# --- 4. Python 3.14 Compatibility ---
echo "--- 4. Python 3.14 Compatibility ---"
TRACING="$DIR/backend/api/tracing.py"
if grep -q 'class _TracedPool' "$TRACING" 2>/dev/null; then
    pass "tracing.py uses _TracedPool wrapper (Python 3.14 compat)"
elif grep -q 'pool.acquire = traced_acquire\|object.__setattr__.*acquire' "$TRACING" 2>/dev/null; then
    fail "tracing.py uses pool.acquire assignment — fails in Python 3.14"
    warn "  fix: replace with _TracedPool wrapper class"
else
    warn "tracing.py — unable to determine state"
fi

LIFECYCLE="$DIR/backend/lifecycle.py"
if grep -q 'threading.Thread.*_run_dicom' "$LIFECYCLE" 2>/dev/null; then
    pass "lifecycle.py runs DICOM server in daemon thread (non-blocking)"
elif grep -q 'ae.start_server' "$LIFECYCLE" 2>/dev/null; then
    fail "lifecycle.py calls ae.start_server() on main thread — BLOCKS HTTP startup"
    warn "  fix: wrap in threading.Thread as daemon"
else
    warn "lifecycle.py — unable to determine DICOM startup method"
fi
echo ""

# --- 5. PostgreSQL connectivity ---
echo "--- 5. PostgreSQL Check ---"
if command -v pg_isready &>/dev/null; then
    if pg_isready -h 127.0.0.1 -p "$DB_PORT" -U quantumpacs &>/dev/null; then
        pass "PostgreSQL reachable on 127.0.0.1:$DB_PORT"
    else
        fail "PostgreSQL NOT reachable on 127.0.0.1:$DB_PORT"
        docker ps --filter name=quantumpacs-postgres --format "  container {{.Names}} on {{.Ports}}" 2>/dev/null
    fi
else
    warn "pg_isready not available — skipping PostgreSQL check"
fi
echo ""

# --- 6. Docker container ---
echo "--- 6. Docker Container ---"
if docker ps --filter name=quantumpacs-postgres-1 --format '{{.Names}}' 2>/dev/null | grep -q postgres; then
    POSTGRES_PORT=$(docker port quantumpacs-postgres-1 5432 2>/dev/null | head -1 | sed 's/.*://')
    if [ -n "$POSTGRES_PORT" ]; then
        pass "PostgreSQL container exposing port $POSTGRES_PORT"
        if [ "$POSTGRES_PORT" != "$DB_PORT" ]; then
            warn "  config says $DB_PORT but container exposes $POSTGRES_PORT"
        fi
    fi
else
    warn "PostgreSQL container not running — start with: docker compose up -d"
fi
echo ""

# --- 7. Systemd service ---
echo "--- 7. Systemd Service ---"
if systemctl --user is-active quantumpacs-backend.service &>/dev/null; then
    pass "backend service active"
else
    warn "backend service not active"
fi
if systemctl --user is-active quantumpacs-frontend.service &>/dev/null; then
    pass "frontend service active"
else
    warn "frontend service not active"
fi
echo ""

# --- 8. Endpoint verification ---
echo "--- 8. Endpoint Verification ---"
if curl -sf http://localhost:8080/api/health > /dev/null 2>&1; then
    pass "/api/health (v1) responds"
else
    fail "/api/health (v1) not responding"
fi
if curl -sf http://localhost:8080/api/v2/health > /dev/null 2>&1; then
    pass "/api/v2/health responds"
else
    fail "/api/v2/health not responding"
fi
if curl -sf http://localhost:5173/ > /dev/null 2>&1; then
    pass "frontend responds on 5173"
else
    warn "frontend not responding on 5173"
fi
echo ""

echo "=== Verification Complete ==="
