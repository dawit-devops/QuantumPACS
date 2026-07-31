#!/bin/bash
set -euo pipefail
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"
pg_dump "${DATABASE_URL:-postgresql://quantumpacs:pa55w0rd@localhost:5432/quantumpacs}" \
  --format=custom \
  --file="$BACKUP_DIR/quantumpacs_$TIMESTAMP.dump"
echo "Backup saved: $BACKUP_DIR/quantumpacs_$TIMESTAMP.dump"
