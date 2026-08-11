#!/bin/bash
# ============================================================
# QuantumPACS Development Environment Setup
# ============================================================
# Run BEFORE dev.sh start — ensures correct configuration.
# Usage: bash scripts/setup_dev.sh [--force-recreate-db]
# ============================================================
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; NC='\033[0m'
pass() { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }

ENV_FILE="$DIR/backend/config.local.yaml"
VENV_PYTHON="$DIR/backend/venv/bin/python3"
VENV_PIP="$DIR/backend/venv/bin/pip"

echo ""
echo -e "${BOLD}=== QuantumPACS Dev Environment Setup ===${NC}"
echo ""

# --- Step 1: Docker PostgreSQL ---
echo -e "${BOLD}[1/8] Docker PostgreSQL${NC}"
if ! docker ps --filter name=quantumpacs-postgres-1 --format '{{.Names}}' 2>/dev/null | grep -q postgres; then
    warn "PostgreSQL container not running — starting"
    docker compose -f "$DIR/docker-compose.yaml" up -d postgres 2>&1 | tail -1
fi

# Wait for healthy
for i in $(seq 1 30); do
    if docker inspect quantumpacs-postgres-1 --format '{{.State.Health.Status}}' 2>/dev/null | grep -q healthy; then
        pass "PostgreSQL healthy"
        break
    fi
    if [ "$i" -eq 30 ]; then
        fail "PostgreSQL failed to become healthy"
        docker logs quantumpacs-postgres-1 --tail 5
        exit 1
    fi
    sleep 1
done

# Detect actual host port
CONTAINER_PORT=$(docker port quantumpacs-postgres-1 5432 2>/dev/null | head -1 | sed 's/.*://')
[ -n "$CONTAINER_PORT" ] && pass "Host port: $CONTAINER_PORT" || { fail "Cannot detect PostgreSQL port"; exit 1; }
echo ""

# --- Step 2: Redis ---
echo -e "${BOLD}[2/8] Redis${NC}"
if redis-cli -h localhost -p 6379 ping 2>/dev/null | grep -q PONG; then
    pass "Redis responding"
else
    # Try Docker Redis
    if docker ps --filter name=quantumpacs-redis --format '{{.Names}}' 2>/dev/null | grep -q redis; then
        pass "Redis running in Docker"
    else
        warn "Redis not running — starting container"
        if docker run -d --name quantumpacs-redis --restart unless-stopped -p 6379:6379 redis:8-alpine >/dev/null 2>&1; then
            pass "Redis container started"
        else
            fail "Could not start Redis container (image pull likely blocked)"
            warn "Start manually once network allows: docker run -d --name quantumpacs-redis --restart unless-stopped -p 6379:6379 redis:8-alpine"
        fi
    fi
fi
echo ""

# --- Step 3: Python Dependencies ---
echo -e "${BOLD}[3/8] Python Dependencies${NC}"
if [ ! -f "$VENV_PYTHON" ]; then
    fail "Virtual env not found at $VENV_PYTHON"
    warn "Create it: python3 -m venv $DIR/backend/venv"
    exit 1
fi
pass "Virtual env found"

# Install from requirements-dev.txt (runtime + dev/test overlay)
"$VENV_PIP" install -r "$DIR/backend/requirements-dev.txt" -q 2>&1 | tail -1 || true

# Verify key packages
for pkg in "pydicom" "PIL" "pynetdicom" "asyncpg" "starlette" "uvicorn"; do
    if "$VENV_PYTHON" -c "import $pkg" 2>/dev/null; then
        true
    else
        warn "$pkg not importable — installing"
        "$VENV_PIP" install "$pkg" -q 2>&1 | tail -1
    fi
done
pass "All dependencies installed"
echo ""

# --- Step 4: Config File ---
echo -e "${BOLD}[4/8] Configuration${NC}"
if [ ! -f "$ENV_FILE" ]; then
    warn "config.local.yaml not found — creating"
    cat > "$ENV_FILE" <<EOF
db_host: 127.0.0.1
db_port: $CONTAINER_PORT
db_user: quantumpacs
db_password: ${POSTGRES_PASSWORD:-pa55w0rd}
db_database: quantumpacs
redis_host: localhost
redis_port: 6379
secret: quantum-local-dev-secret-replace-in-prod-2026-07-28
EOF
    pass "config.local.yaml created"
fi

# Fix db_port
CFG_PORT=$(grep -E '^db_port:' "$ENV_FILE" 2>/dev/null | awk '{print $2}' | tr -d ' ')
if [ -n "$CFG_PORT" ] && [ "$CFG_PORT" != "$CONTAINER_PORT" ]; then
    warn "db_port $CFG_PORT → $CONTAINER_PORT"
    sed -i "s/^db_port: $CFG_PORT/db_port: $CONTAINER_PORT/" "$ENV_FILE"
fi
pass "db_port = $CONTAINER_PORT"

# Fix secret
SECRET=$(grep -E '^secret:' "$ENV_FILE" 2>/dev/null | awk '{print $2}' | tr -d ' ')
if [ -z "$SECRET" ] || [[ " default pa55w0rd quantumpacs-default-secret-32-bytes-long!! quantumpacs-dev-secret-replace-in-production-32b " =~ " $SECRET " ]]; then
    warn "default secret detected — replacing"
    if grep -q '^secret:' "$ENV_FILE" 2>/dev/null; then
        sed -i 's|^secret:.*|secret: quantum-local-dev-secret-replace-in-prod-2026-07-28|' "$ENV_FILE"
    else
        echo 'secret: quantum-local-dev-secret-replace-in-prod-2026-07-28' >> "$ENV_FILE"
    fi
fi
pass "secret configured"
echo ""

# --- Step 5: Python 3.14 Compatibility Fixes ---
echo -e "${BOLD}[5/8] Python 3.14 Compatibility${NC}"

# tracing.py — _TracedPool wrapper
TRACING="$DIR/backend/api/tracing.py"
if grep -q 'class _TracedPool' "$TRACING" 2>/dev/null; then
    pass "tracing.py: _TracedPool wrapper OK"
elif grep -q 'pool.acquire\|object.__setattr__.*acquire' "$TRACING" 2>/dev/null; then
    fail "tracing.py: uses pool.acquire assignment (read-only in Python 3.14)"
    warn "Fix: git checkout phase/6-frontend-v3 -- backend/api/tracing.py"
    exit 1
fi

# lifecycle.py — DICOM daemon thread
LIFECYCLE="$DIR/backend/lifecycle.py"
if grep -q 'threading.Thread.*_run_dicom' "$LIFECYCLE" 2>/dev/null; then
    pass "lifecycle.py: DICOM in daemon thread OK"
elif grep -q 'ae.start_server' "$LIFECYCLE" 2>/dev/null; then
    fail "lifecycle.py: ae.start_server() on main thread (blocks HTTP)"
    warn "Fix: git checkout phase/6-frontend-v3 -- backend/lifecycle.py"
    exit 1
fi
echo ""

# --- Step 6: Port Cleanup ---
echo -e "${BOLD}[6/8] Port Cleanup${NC}"
for port in 8080 11112; do
    if fuser "$port/tcp" 2>/dev/null > /dev/null; then
        warn "port $port in use — killing"
        fuser -k -9 "$port/tcp" 2>/dev/null || true
        sleep 1
    fi
    pass "port $port free"
done
echo ""

# --- Step 7: Database Schema ---
echo -e "${BOLD}[7/8] Database Schema${NC}"
TABLE_COUNT=$(docker exec quantumpacs-postgres-1 psql -U quantumpacs -d quantumpacs -t -A -c "SELECT count(*) FROM pg_catalog.pg_tables WHERE schemaname='public'" 2>/dev/null | tr -d ' ')
if [ -n "$TABLE_COUNT" ] && [ "$TABLE_COUNT" -gt 0 ]; then
    pass "$TABLE_COUNT tables present"
else
    warn "No tables found — run: python3 backend/manage.py db init"
fi
echo ""

# --- Step 8: Start Backend ---
echo -e "${BOLD}[8/8] Starting Services${NC}"
echo "  Starting backend via systemd..."
systemctl --user start quantumpacs-backend.service 2>/dev/null &
SYSCTL_PID=$!

# Wait for endpoint (up to 45s for ES retries)
BACKEND_READY=false
for i in $(seq 1 45); do
    if curl -sf http://localhost:8080/api/health > /dev/null 2>&1; then
        BACKEND_READY=true
        break
    fi
    sleep 1
done

if [ "$BACKEND_READY" = true ]; then
    STATUS=$(curl -s http://localhost:8080/api/health | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
    pass "Backend running (status: $STATUS)"
    echo "  └─ /api/health   → $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/api/health)"
    echo "  └─ /api/v2/health → $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/api/v2/health)"
else
    fail "Backend failed to start — check: journalctl --user -u quantumpacs-backend.service -n 30 --no-pager"
    exit 1
fi

# Start frontend if not active
if ! systemctl --user is-active quantumpacs-frontend.service &>/dev/null; then
    systemctl --user start quantumpacs-frontend.service 2>/dev/null || true
fi
FRONTEND_CODE=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:5173/ 2>&1 || echo "down")
pass "Frontend (HTTP $FRONTEND_CODE)"
echo ""

# ============================================================
echo -e "${BOLD}=== Setup Complete ===${NC}"
echo ""
echo "  Backend:  http://localhost:8080 (status: $STATUS)"
echo "  Frontend: http://localhost:5173 (HTTP $FRONTEND_CODE)"
echo "  DB:       postgresql://quantumpacs:${POSTGRES_PASSWORD:-pa55w0rd}@127.0.0.1:$CONTAINER_PORT/quantumpacs"
echo "  Redis:    localhost:6379"
echo ""
echo "  Health endpoints:"
echo "    curl http://localhost:8080/api/health     (v1)"
echo "    curl http://localhost:8080/api/v2/health   (v2)"
echo ""
echo "  Quick commands:"
echo "    bash scripts/dev.sh status"
echo "    bash scripts/dev.sh logs"
echo "    bash scripts/verify_config.sh"
echo ""
