# QuantumPACS — Admin Guide

Day-to-day operations for hospital IT administrators managing a QuantumPACS deployment.

## User Management

### Creating Users
```bash
# Via API (admin token required)
curl -X POST http://localhost:8080/api/users \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"username": "dr.smith", "admin": false}'

# Response includes one-time password
{"password": "a1b2c3d4e5f6"}
```

### Deactivating Users
```bash
curl -X POST http://localhost:8080/api/users/deactivate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"id": 3}'
```

### Resetting Passwords
```bash
curl -X POST http://localhost:8080/api/users/new_password \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"id": 3}'
# Returns new one-time password
```

## Storage Management

### Adding a Replica
```bash
curl -X POST http://localhost:8080/api/replicas \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"type": "s3", "location": "s3://pacs-bucket", "key": "...", "secret": "..."}'
```

Supported types: `local` (filesystem), `s3` (S3-compatible), `b2` (Backblaze B2).

### Setting Master Replica
```bash
curl -X POST http://localhost:8080/api/replicas/1 \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"master": true}'
```

## Backup & Restore

Follow the procedures in [ops-guide.md](ops-guide.md).

Quick backup:
```bash
pg_dump -h localhost -U quantumpacs quantumpacs > backup-$(date +%Y%m%d).sql
gpg --encrypt --recipient admin@hospital.org backup-*.sql
```

## Monitoring

### Health Check
```bash
curl http://localhost:8080/api/health
# {"status":"ok","database":"connected"}
```

Returns `200` if both the HTTP server and PostgreSQL are reachable.
Returns `503` if the database is unreachable (the API still responds).

### Logs
```bash
# System logs (paginated)
curl http://localhost:8080/api/logs?page=1&per_page=20 \
  -H "Authorization: Bearer <token>"
```

### Audit Trail
File access events (reads, downloads, annotation changes) are logged to `file_changes`:

```sql
SELECT * FROM file_changes WHERE file_id = 42 ORDER BY created DESC;
```

## Database Migrations

```bash
# Apply pending migrations
./manage db migrate

# Check current migration
./manage db current

# View migration history
./manage db history

# Rollback last migration
./manage db rollback
```

Migrations are stored in `backend/migrations/versions/`.

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET` | auto-derived | JWT signing secret |
| `SUPERADMIN_PASS` | `pa55w0rd` | Initial admin password |
| `DB_HOST` | `127.0.0.1` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_POOL_SIZE` | `8` | asyncpg connection pool size |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | TrustedHost filter |
| `SENTRY_DSN` | (empty) | Sentry error reporting DSN |

## Rate Limiting

Login attempts are rate-limited per IP address:
- 5 attempts per 60-second window before soft block
- 10 total failures triggers a 5-minute hard lockout
- Attempts are logged in the `login_attempts` table for audit

## Security Headers

The Caddy reverse proxy sets:
- `Content-Security-Policy` — restricts script/style/connect sources
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`

## Troubleshooting

### Database connection fails
```bash
systemctl --user status quantumpacs-backend.service
journalctl --user -u quantumpacs-backend.service -n 50
```

Check PostgreSQL is running:
```bash
docker compose ps
pg_isready -h localhost -U quantumpacs
```

### Elasticsearch unavailable
Search gracefully falls back to returning empty results. No action needed — the system operates without ES.

### DICOM listener not accepting connections
```bash
netstat -tlnp | grep 11112
```
Ensure port 11112 is not blocked by a firewall and no other process is bound to it.
