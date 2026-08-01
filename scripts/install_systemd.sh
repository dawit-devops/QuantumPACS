#!/bin/bash
# Install the QuantumPACS systemd user units into ~/.config/systemd/user/.
# The repo copies use %h for the home directory; the frontend unit needs the
# actual node bin dir, which is resolved here (nvm installs live outside %h).
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"
UNIT_DIR="$HOME/.config/systemd/user"
SRC_DIR="$DIR/systemd"

NODE_BIN=""
for cand in "$(command -v node 2>/dev/null || true)" "$HOME/.nvm/versions/node"/*/bin/node; do
    if [ -x "$cand" ]; then
        NODE_BIN="$(dirname "$cand")"
        break
    fi
done
if [ -z "$NODE_BIN" ]; then
    echo "ERROR: node binary not found (nvm or system node)" >&2
    exit 1
fi

BACKEND_PY="$DIR/backend/venv/bin/uvicorn"
if [ ! -x "$BACKEND_PY" ]; then
    echo "WARNING: backend venv not found at $BACKEND_PY (install it first)" >&2
fi

mkdir -p "$UNIT_DIR"

sed 's|%h|'"$HOME"'|g' "$SRC_DIR/quantumpacs-backend.service" > "$UNIT_DIR/quantumpacs-backend.service"
sed -e 's|%h|'"$HOME"'|g' -e "s|__NODE_BIN__|$NODE_BIN|g" -e "s|__NODE__|$NODE_BIN/node|g" \
    "$SRC_DIR/quantumpacs-frontend.service" > "$UNIT_DIR/quantumpacs-frontend.service"

systemctl --user daemon-reload
systemctl --user enable quantumpacs-backend.service quantumpacs-frontend.service 2>/dev/null || true

echo "Installed units:"
echo "  $UNIT_DIR/quantumpacs-backend.service"
echo "  $UNIT_DIR/quantumpacs-frontend.service"
echo "Node bin: $NODE_BIN"
echo "Manage with: systemctl --user start|stop|restart quantumpacs-{backend,frontend}.service"
