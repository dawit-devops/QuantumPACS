#!/bin/bash
# Installs the repo-tracked systemd units (deploy/systemd/) into the user
# systemd dir, and verifies the dev backend/frontend units exist.
# Idempotent; safe to re-run.
set -e

DIR="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$DIR/deploy/systemd"
DEST="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

if [ ! -d "$SRC" ]; then
    echo "error: deploy/systemd/ not found (run from repo root or scripts/)" >&2
    exit 1
fi

mkdir -p "$DEST"

for unit in quantumpacs-backup.service quantumpacs-backup.timer quantumpacs-failure-notify@.service; do
    cp "$SRC/$unit" "$DEST/$unit"
    echo "  installed $unit"
done

# Backend/frontend units are machine-local (their ExecStart points at this
# checkout's venv and ports); do not regenerate them from templates.
for unit in quantumpacs-backend.service quantumpacs-frontend.service; do
    if [ ! -f "$DEST/$unit" ]; then
        echo "  missing $unit — dev services need it (scripts/dev.sh refuses to start without it)" >&2
        exit 1
    fi
    echo "  ok $unit"
done

systemctl --user daemon-reload
echo "Done. Enable with: systemctl --user enable --now quantumpacs-backup.timer"
