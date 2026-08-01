# QuantumPACS Operations Guide

> Backup, restore, monitoring, and maintenance procedures.

## Database Backup

QuantumPACS stores all metadata in PostgreSQL 16. The database is the single source of truth for patient, study, series, and file records. DICOM pixel data is stored on the filesystem (local or S3-compatible storage via the Storage plugin).

### Automated Daily Backup

A systemd timer is recommended:

```ini
# /etc/systemd/system/quantumpacs-backup.service
[Unit]
Description=QuantumPACS daily database backup

[Service]
Type=oneshot
ExecStart=/usr/bin/pg_dump -h localhost -U quantumpacs -d quantumpacs \
  --format=custom --compress=9 \
  --file=/backups/quantumpacs-$(date +%%Y%%m%%d-%%H%%M).dump
Environment=PGPASSWORD=your_db_password
```

```ini
# /etc/systemd/system/quantumpacs-backup.timer
[Unit]
Description=Run QuantumPACS backup daily at 3am

[Timer]
OnCalendar=03:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable: `systemctl enable --now quantumpacs-backup.timer`

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

The Docker images include healthchecks:

```yaml
healthcheck:
  # Backend (slim image has no curl — uses stdlib urllib)
  test: ["CMD", "python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=3).status == 200 else 1)"]
  interval: 30s
  timeout: 5s
  retries: 3

  # Frontend (nginx alpine)
  test: ["CMD", "wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8080/"]
  interval: 30s
  timeout: 5s
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

## Rollback Procedure

Downgrade strategy when a release must be reverted (D-M13):

### 1. Database

```bash
# Only if the new version contains migrations the old version cannot read.
# Plain DROP for index migrations; migrations using CONCURRENTLY are
# non-transactional and must be reverted with their downgrade().
cd /opt/quantumpacs/backend
alembic downgrade -1

# Verify: alembic current
```

If the DB cannot be downgraded safely (destructive changes), restore from the
latest backup instead — see "Disaster Recovery" below.

### 2. Application

```bash
# systemd deployment
git checkout <previous-tag>
scripts/install_systemd.sh
systemctl --user restart quantumpacs-backend.service quantumpacs-frontend.service

# container deployment (images are tagged with the commit sha; `latest` is
# also pushed for main/v3-dev)
docker compose --profile app up -d \
  --force-recreate --no-deps backend frontend \
  && docker image pull quantumpacs-backend:<previous-sha>
```

### 3. Verify

```bash
curl -sf http://localhost:8080/api/health | python3 -m json.tool
curl -sf http://localhost:5173/ > /dev/null && echo "frontend up"
```

### 4. Communications

- Post a rollback notice in the team channel with the previous tag/sha.
- Log the reason in the incident tracker; backfilled into `docs/` after the fact.

## Environment Parity

Dev / CI / production should differ only in credentials and scale (D-M12):

| Aspect | Dev (systemd) | CI (GitHub Actions) | Prod (docker compose) |
|--------|---------------|----------------------|-----------------------|
| Node | `.nvmrc` (22.12.0) via nvm | `node-version-file: frontend/.nvmrc` | `node:22.12.0-alpine` image |
| Backend | `uvicorn` in venv | `uvicorn` + alembic upgrade + seed | `quantumpacs-backend` image |
| Config | `config.local.yaml` (gitignored) | env vars in workflow | env vars via `.env` |
| DB | Docker postgres:16 | postgres:16 service | postgres:16 service |
| Migration | `manage db migrate` | `alembic upgrade head` in e2e job | `alembic upgrade head` on deploy |

The single source of truth for the Node version is `frontend/.nvmrc`; the
frontend Dockerfile pins the same exact version. CI installs a pinned
playwright chromium so e2e runs match local results.

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
6. Update DNS/Caddy if needed
