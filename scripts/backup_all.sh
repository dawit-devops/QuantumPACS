#!/bin/bash
# Wrapper around backup_db.sh — the script now backs up the main database AND
# every active tenant database, so there is a single entry point for full
# platform backups. All flags (e.g. --dry-run) are forwarded.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$DIR/backup_db.sh" "$@"
