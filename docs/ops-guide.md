# QuantumPACS Operations Guide

> Backup, restore, monitoring, and maintenance procedures.

## Database Backup

QuantumPACS stores all metadata in PostgreSQL 16. The database is the single source of truth for patient, study, series, and file records. DICOM pixel data is stored on the filesystem (local or S3-compatible storage via the Storage plugin).

### Automated Daily Backup

Ship units live in `deploy/systemd/` — copy them into the systemd search path
and adjust `ExecStart` paths for the install location:

```bash
sudo cp deploy/systemd/quantumpacs-backup.service deploy/systemd/quantumpacs-backup.timer \
        deploy/systemd/quantumpacs-failure-notify@.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now quantumpacs-backup.timer
```

- `quantumpacs-backup.service` runs `scripts/backup_db.sh`, which discovers
  the real PostgreSQL host port and password from the running
  `quantumpacs-postgres-1` container (no hardcoded credentials). Override
  `DATABASE_URL` (via `Environment=`) to back up a remote replica, or set
  `BACKUP_DIR`/`RETENTION_DAYS` (default 14 days).
- `quantumpacs-backup.timer` runs daily at 02:30 with `Persistent=true`
  (missed runs fire at boot).
- `quantumpacs-failure-notify@.service` is an `OnFailure=` target for
  service units — the failing unit's journal tail is logged and an optional
  webhook (Slack/Teams) is POSTed. Enable it by adding
  `OnFailure=quantumpacs-failure-notify@%n.service` to a unit, and put
  `QUANTUMPACS_NOTIFY_WEBHOOK=...` in `/etc/quantumpacs/notify.env`.

Manual backup:

```bash
bash scripts/backup_db.sh
```

### Retention Policy

| Retention | Frequency | Location |
|-----------|-----------|----------|
| 7 daily | daily | `/backups/` |
| 4 weekly | weekly (Sun) | `/backups/weekly/` |
| 3 monthly | monthly (1st) | `/backups/monthly/` |

A cleanup cron script:

```bash
#!/bin/bash
find /backups/ -name 'quantumpacs-*.dump' -mtime +7 -delete
find /backups/weekly/ -name 'quantumpacs-*.dump' -mtime +28 -delete
find /backups/monthly/ -name 'quantumpacs-*.dump' -mtime +90 -delete
```

### Full Backup (with DICOM files)

For DR, back up both the database and the DICOM storage directory:

```bash
#!/bin/bash
BACKUP_DIR="/backups/full/$(date +%Y%m%d-%H%M)"
mkdir -p "$BACKUP_DIR"

# Database
pg_dump -h localhost -U quantumpacs -d quantumpacs \
  --format=custom --compress=9 \
  --file="$BACKUP_DIR/database.dump"

# DICOM files (if using local storage)
rsync -a --relative /var/lib/quantumpacs/storage/ "$BACKUP_DIR/storage/"

# Encrypt
gpg --symmetric --cipher-algo AES256 "$BACKUP_DIR/database.dump"
gpg --symmetric --cipher-algo AES256 "$BACKUP_DIR/storage.tar"

# Upload to remote
rclone copy "$BACKUP_DIR" remote:quantumpacs-backups/
```

### Encryption

All off-site backups must be encrypted with GPG symmetric AES-256:

```bash
# Encrypt
gpg --symmetric --cipher-algo AES256 --output backup.dump.gpg backup.dump

# Decrypt
gpg --decrypt --output backup.dump backup.dump.gpg
```

Store the passphrase in a password manager (Bitwarden, 1Password) or hardware HSM. Do NOT store it in the backup script.

## Database Restore

### Prerequisites

1. Stop the QuantumPACS backend: `systemctl --user stop quantumpacs-backend.service`
2. Ensure the target database exists and is empty
3. Have the backup file and decryption key ready

### Restore from custom-format dump

```bash
# Decrypt (if needed)
gpg --decrypt --output /tmp/quantumpacs.dump /backups/quantumpacs-20260723.dump.gpg

# Drop and recreate
sudo -u postgres psql -c "DROP DATABASE IF EXISTS quantumpacs;"
sudo -u postgres psql -c "CREATE DATABASE quantumpacs OWNER quantumpacs;"

# Restore
pg_restore -h localhost -U quantumpacs -d quantumpacs \
  --format=custom --clean --if-exists --no-owner \
  /tmp/quantumpacs.dump

# Apply migrations (Alembic will detect and skip applied ones)
cd /opt/quantumpacs/backend && alembic upgrade head

# Restart
systemctl --user start quantumpacs-backend.service
```

### Restore from plain SQL dump

```bash
psql -h localhost -U quantumpacs -d quantumpacs < /backups/quantumpacs-dump.sql
```

### Verify restore

```bash
# Check row counts
psql -h localhost -U quantumpacs -d quantumpacs -c "
  SELECT 'users' AS tbl, COUNT(*) FROM users
  UNION ALL SELECT 'patients', COUNT(*) FROM patients
  UNION ALL SELECT 'studies', COUNT(*) FROM studies
  UNION ALL SELECT 'series', COUNT(*) FROM series
  UNION ALL SELECT 'files', COUNT(*) FROM files;"

# Check health endpoint
curl -s http://localhost:8080/api/health | python3 -m json.tool
```

## Monitoring

### Health Endpoint

```
GET /api/health
```

Returns:
```json
{"status": "ok", "database": "connected"}
```

- Returns `200` when healthy
- Returns `503` when database is unreachable

### Docker Healthcheck

The Docker image includes a healthcheck that pings `/api/health` every 30s:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/api/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### Logging

All API requests are logged to stdout with method, path, status code, and duration:

```
INFO  2026-07-23 22:46:17 GET /api/files -> 200 (0.042s)
WARN  2026-07-23 22:46:18 POST /api/login -> 400 (0.015s)
```

The `/api/logs` endpoint (admin-only) returns system logs with pagination.

## Migration Strategy

Schema migrations use Alembic. Run before starting the new version:

```bash
cd /opt/quantumpacs/backend
alembic upgrade head
```

Migrations are designed to be backward-compatible within the same major version.
Notable migration sequence:

| Migration | Change | Downtime |
|-----------|--------|----------|
| 001 | Initial schema | Full |
| 002 | PKs, indexes, constraints | None (CONCURRENT) |
| 003 | FK cascades, TIMESTAMPTZ | Brief write lock |
| 004 | BIGINT IDENTITY | Brief write lock |

## Dev/Prod Parity

Dev and prod run the **same** compose stack and the same config branch, so a
green `docker-smoke`/`e2e` CI run is a true pre-production signal.

| Concern | Dev (this machine) | Prod / compose runtime |
|---------|--------------------|------------------------|
| Config branch | `config.local.yaml` (generated by `scripts/setup_dev.sh`) | `QUANTUMPACS_DOCKER=true` env in compose |
| Backend | systemd user unit (`quantumpacs-backend.service`) | compose `backend` service (same image) |
| Frontend | systemd user unit (`quantumpacs-frontend.service`, vite dev server) | compose `frontend` (nginx serves `dist/`, proxies `/api`) |
| Database | Docker `quantumpacs-postgres-1` (host port auto-detected, may be 5433) | compose `postgres` (internal) |
| Secrets | `.env` + env vars → `config.local.yaml` (gitignored) | `.env` → compose env substitution |
| DICOM listener | Same code path (daemon thread in `lifecycle.py`) | Same |

`scripts/dev.sh` is the dev control plane; `docker compose up -d` is the
prod-like runtime. Never start backend/frontend "bare" in a way the parity
checks don't exercise (e.g., missing the `QUANTUMPACS_DOCKER` branch).

## Rollback Procedure

Two independent layers: application and database.

### Application rollback (compose)

Images are tagged per deployment (`quantumpacs-backend:local` dev / registry
tag in prod). Keep the previously-shipped tag available:

```bash
# prod: pin the previous image, keep data volumes
docker compose down
sed -i 's|image: quantumpacs-backend:new|image: quantumpacs-backend:old|' docker-compose.yaml
docker compose up -d
curl -sf http://localhost:8080/api/health   # verify before restoring traffic
```

### Database rollback

Only safe for *schema* regressions; data writes since the bad deploy are lost:

```bash
cd backend && venv/bin/alembic downgrade -1   # revert one migration
```

Check `alembic history` first. If the bad release also ran a destructive
migration, restore from the daily dump instead (see Disaster Recovery).

### Git-level rollback

A bad release is a squash commit on `v3-dev`/`main`:

```bash
git revert <bad-squash-commit>   # new commit that undoes the release
# then ship the revert via the normal PR path
```


## Disaster Recovery

### Failure Scenarios

| Scenario | RTO | RPO | Recovery Steps |
|----------|-----|-----|----------------|
| Database corruption | 1h | 24h | Restore from daily dump |
| Container failure | 5m | 0 | Restart via systemd (auto) |
| Full server loss | 4h | 24h | Provision new server, restore from encrypted backup |
| Accidental file deletion | 1h | 0 | Check `files.deleted` flag (soft-delete), restore from replica |

### DR Runbook

1. Provision new server with Docker + PostgreSQL 16
2. Restore database from latest encrypted backup
3. Restore DICOM files from rsync/rclone backup
4. Start QuantumPACS container
5. Verify `/api/health` returns `200`
6. Update DNS/nginx if needed
