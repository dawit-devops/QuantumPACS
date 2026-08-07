# QuantumPACS

[![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Starlette](https://img.shields.io/badge/Starlette-000?logo=starlette)](https://www.starlette.io/)
[![React](https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=black)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![Ant Design](https://img.shields.io/badge/Ant%20Design-0170FE?logo=ant-design&logoColor=white)](https://ant.design/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Backend CI](https://github.com/dawit-devops/QuantumPACS/actions/workflows/backend.yml/badge.svg)](https://github.com/dawit-devops/QuantumPACS/actions/workflows/backend.yml)
[![Frontend CI](https://github.com/dawit-devops/QuantumPACS/actions/workflows/frontend.yml/badge.svg)](https://github.com/dawit-devops/QuantumPACS/actions/workflows/frontend.yml)

Open-source Picture Archiving and Communication System (PACS) for medical image management. Production-grade DICOM ingestion, zero-footprint Cornerstone3D viewer, multi-site replication, and real-time collaboration.

## Overview

QuantumPACS replaces traditional vendor-locked imaging systems with an open, modern architecture. It handles the full imaging lifecycle — from DICOM modality ingestion through storage, viewing, reporting, and multi-site replication.

**Backend:** Starlette with asyncpg, JWT-authenticated REST APIs, Alembic migrations, and pluggable storage (filesystem, S3, B2).  
**Frontend:** React SPA with Ant Design 6, Cornerstone3D 5 for zero-footprint DICOM viewing in the browser.  
**Database:** PostgreSQL 16 with 10-table schema, LISTEN/NOTIFY replication triggers.

## Site Metrics

| Metric | Count |
|--------|-------|
| Backend Python Modules | 61 |
| Frontend Components | 38 |
 | Architecture Decision Records | 22 |
 | Backend Tests | 103 (pytest) |
 | Frontend Tests | 246 (Vitest) |
 | E2E Tests | 45 across 11 specs (Playwright) |
 | DB Migrations | 31 (Alembic) |

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker and Docker Compose (for PostgreSQL)

### Quick Start (Docker)

```bash
git clone https://github.com/dawit-devops/QuantumPACS.git
cd quantumpacs
cp .env.example .env      # optional: override POSTGRES_PASSWORD / SECRET
docker compose up -d      # full stack: postgres, redis, elasticsearch, backend, frontend
docker compose ps         # wait until backend is healthy
```

- Frontend: <http://localhost:5173> (nginx, proxies `/api` to the backend)
- Backend API: <http://localhost:8080> — health: `curl http://localhost:8080/api/health`
- Credentials: the initial superadmin login is `admin` with the password from
  `SUPERADMIN_PASS` (default `pa55w0rd` — override in any non-dev deployment).
  The **database** password is separate: `manage db init` generates a random
  one (capture it from the output); with Docker it comes from
  `POSTGRES_PASSWORD` in `.env`.

### Development Workflow (recommended)

The permanent dev environment runs as systemd user services backed by a
PostgreSQL Docker container:

```bash
bash scripts/dev.sh start     # starts backend (:8080) + frontend (:5173)
bash scripts/dev.sh status
bash scripts/dev.sh logs      # tail backend logs
bash scripts/dev.sh logs-fe   # tail frontend logs
bash scripts/setup_dev.sh     # first-time setup: config, venv, ports, schema
```

### Manual Setup

#### Backend

```bash
cd backend
python -m venv venv        # creates venv at backend/venv/ (canonical location)
source venv/bin/activate
pip install -r requirements.txt
./manage db init          # creates database, outputs random password
export DB_PASS=<password> # or set in config.local.yaml
./start.sh                # starts DICOM listener, sync, HTTP server
```

> The virtual environment is at `backend/venv/`. This is the sole canonical venv used by the systemd service, pre-commit hooks, and `manage` script. Run tests with `cd backend && python -m pytest tests/` (with venv activated).

#### Frontend

```bash
cd frontend
npm install
npm run dev          # development server with HMR (http://localhost:5173)
npm run build        # production build to dist/
```

Serve `dist/` via the nginx image (`frontend/Dockerfile`), or copy to `backend/static/` with `QUANTUMPACS_DOCKER=true`.

## Repository Structure

```
quantumpacs/
├── backend/                      # Python Starlette API server
│   ├── api/                      # HTTP endpoints, auth, validation, schemas
│   │   └── schemas/              # Pydantic v2 request/response models
│   ├── db/                       # Database access layer (asyncpg + PyPika)
│   ├── dcm/                      # DICOM listener and processing
│   ├── es/                       # Elasticsearch indexing (optional)
│   ├── migrations/               # Alembic migrations (001-031)
│   │   └── versions/             # Version-controlled migration scripts
│   ├── storage/                  # Pluggable storage backends
│   ├── tests/                    # 103 pytest tests
│   ├── app.py                    # Starlette app with middleware
│   ├── config.py                 # YAML + environment config
│   └── manage                    # Database management CLI
├── frontend/                     # React SPA (Vite + AntD 6 + Cornerstone3D 5)
│   ├── e2e/                      # Playwright E2E tests
│   └── src/
│       ├── common/               # Design tokens, theme, logo, sidebar
│       ├── detail/               # Cornerstone3D DICOM viewer
│       ├── files/                # File management + search
│       ├── login/                # Authentication
│   ├── src/test/                 # 246 Vitest tests
│       └── ...
├── docs/
│   ├── decisions/                # 22 Architecture Decision Records (ADRs)
│   ├── component-specs.md        # UI component state/variant specs
│   ├── design-tokens.json        # Three-layer token system
│   ├── ops-guide.md              # Backup/restore/monitoring/DR
│   ├── presentation/             # Brand slide deck
│   ├── token-audit.md            # Hardcoded color audit
│   ├── PRD.md                    # Product Requirements Document
│   ├── REST_API_REVIEW.md        # REST API design audit
│   ├── DB_SCHEMA_REVIEW.md       # Database schema audit
│   └── SECURITY_AUDIT.md         # Security audit
├── docker/                       # Docker build files
│   └── postgres/                 # Custom PostgreSQL 16 image
├── docker-compose.yaml           # Service orchestration (postgres/redis/es/backend/frontend)
├── deploy/systemd/               # Backup timer + failure-notify units
├── nginx.conf                    # Frontend proxy + security headers (in frontend/)
└── .github/workflows/            # CI pipelines (lint, tests, build, docker-smoke)
```

## Architecture

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│  Browser      │────▶│  nginx (frontend│────▶│  PostgreSQL   │
│  (React SPA   │     │   image: proxy  │     │  + LISTEN/    │
│   + Viewer)   │◀────│   + CSP) :5173 │◀────│  NOTIFY      │
└──────────────┘     └────────┬─────────┘     └──────────────┘
                              │
                     ┌────────▼─────────┐
                     │  Starlette API    │
                     │  (Uvicorn/Gun)    │
                     │                   │
                     │  ┌─ JWT Auth     │
                     │  │  (Bearer +     │
                     │  │   X-Auth-Pacs) │
                     │  ├─ Rate Limit    │
                     │  │  (5/min login) │
                     │  ├─ DICOM Router  │
                     │  ├─ File Manager  │
                     │  └─ Replicator    │
                     └────────┬─────────┘
                              │
                     ┌────────▼─────────┐
                     │   Storage Layer   │
                     │  (FS / S3 / B2)   │
                     └──────────────────┘
```

Architecture decisions: 22 ADRs in [docs/decisions/](docs/decisions/).

### Multi-Tenancy

- **DB-per-tenant isolation** (ADR-016): each tenant gets its own PostgreSQL
  database (created + alembic-migrated at provisioning); a registry DB holds
  tenant metadata (slug, status, DB connection, storage quota).
- **Routing** (ADR-026): the tenant middleware resolves the tenant from the JWT
  `tenant` claim or the `X-Tenant-ID` header (super-admin override) and sets a
  request-scoped contextvar, so every `get_conn()` call inside a routed request
  transparently hits the tenant DB. `default` tenant seeds the platform DB.
- **Status lifecycle**: provisioning / active / suspended / quarantined /
  decommissioned — the middleware returns 403 (suspended/quarantined) or 404
  (decommissioned) for non-active tenants.
- **Quota & metering**: uploads are gated by the tenant's storage quota
  (`QUOTA_EXCEEDED`, 90% breach notification); `tenant_usage_daily` records
  per-tenant API calls, storage, and active users — the foundation for future
  billing (out of scope).
- **Backup & health**: each tenant DB is backed up independently via
  `scripts/backup_db.sh`; `GET /api/v2/tenants/health` probes all tenant DBs.
- Auth stays on the registry DB (`users.tenant = slug`); tenant DBs are clinical
  data stores only. Ingestion/sync currently run platform-scoped — per-tenant
  ingest routing is a documented follow-up (ADR-026).

## Configuration

Settings loaded from `config.local.yaml` + environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET` | auto-derived | JWT signing secret (warns if default) |
| `SUPERADMIN_PASS` | `pa55w0rd` | Initial admin password |
| `DB_HOST` | `127.0.0.1` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_DATABASE` | `quantumpacs` | PostgreSQL database |
| `DB_USER` | `quantumpacs` | PostgreSQL user |
| `DB_PASSWORD` | `pa55w0rd` | PostgreSQL password |
| `ES_HOST` | `localhost` | Elasticsearch host |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed CORS origins (lock for production) |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | TrustedHost middleware |
| `REDIS_HOST` | `localhost` | Redis host for rate limiting and cache |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_PASSWORD` | `` | Redis password |
| `DB_POOL_SIZE` | `8` | asyncpg connection pool size |
| `SENTRY_DSN` | `` | Sentry DSN for error tracking |
| `OAUTH_ISSUER` | `` | OAuth/OpenID issuer URL |
| `OAUTH_CLIENT_ID` | `` | OAuth client ID |
| `OAUTH_CLIENT_SECRET` | `` | OAuth client secret |
| `OAUTH_REDIRECT_URI` | `` | OAuth callback redirect URI |
| `OAUTH_JWKS_URI` | `` | JWKS URI for OAuth token verification |
| `OAUTH_TOKEN_URL` | `` | OAuth token endpoint URL |
| `OAUTH_DEFAULT_ROLE` | `radiologist` | Default role for OAuth-provisioned users |
| `OAUTH_SCOPE` | `openid email profile` | OAuth scopes |
| `OAUTH_SECRET_ENCRYPTION_KEY` | `` | Key for encrypting stored OAuth client secrets |
| `DICOM_AE_TITLE` | `QUANTUMPACS` | DICOM Application Entity title |
| `DICOM_CSTORE_PORT` | `11112` | DICOM C-STORE SCP port |
| `DICOM_MWL_PORT` | `11113` | DICOM Modality Worklist SCP port |
| `DICOM_CMOVE_PORT` | `11114` | DICOM C-MOVE SCP port |
| `HL7_MLLP_PORT` | `12579` | HL7 MLLP listener port |
| `HL7_MLLP_TLS_CERT` | `` | HL7 MLLP TLS certificate path |
| `HL7_MLLP_TLS_KEY` | `` | HL7 MLLP TLS key path |
| `HL7_MLLP_ALLOWED_IPS` | `` | Comma-separated IPs allowed for HL7 |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `` | OpenTelemetry OTLP exporter endpoint |
| `OTEL_SERVICE_NAME` | `quantumpacs-backend` | OpenTelemetry service name |
| `OTEL_DEPLOYMENT_ENVIRONMENT` | `development` | OpenTelemetry deployment environment |
| `OTEL_SAMPLER` | `always_on` | OpenTelemetry sampler type |
| `OTEL_BSP_SCHEDULE_DELAY` | `5000` | OpenTelemetry batch span processor delay (ms) |
| `OTEL_BSP_MAX_QUEUE_SIZE` | `2048` | OpenTelemetry batch span processor queue size |
| `OTEL_BSP_MAX_EXPORT_BATCH_SIZE` | `512` | OpenTelemetry batch span processor batch size |
| `PROMETHEUS_ENABLED` | `true` | Enable Prometheus metrics endpoint |
| `MAX_UPLOAD_SIZE_MB` | `500` | Maximum upload file size (MB) |
| `B2_CORS_ORIGINS` | `http://localhost:5173` | Backblaze B2 allowed CORS origins |
| `INGESTION_STREAM` | `events:ingestion` | Redis stream name for ingestion events |
| `INGESTION_GROUP` | `ingestion-service` | Redis consumer group for ingestion |
| `INGESTION_CONSUMER` | `worker-1` | Redis consumer name for ingestion |
| `INGESTION_POLL_COUNT` | `10` | Redis stream poll count per batch |
| `INGESTION_POLL_BLOCK_MS` | `5000` | Redis stream poll block timeout (ms) |
| `INGESTION_MAX_RETRIES` | `3` | Max retries for failed ingestion |
| `QUANTUMPACS_DOCKER` | — | Enable Docker mode (serves static files) |

## Security

Security audit completed ([docs/SECURITY_AUDIT.md](docs/SECURITY_AUDIT.md)):

| Control | Status |
|---------|--------|
| JWT authentication (14-day expiry) | ✅ |
| PBKDF2-HMAC-SHA256 password hashing (600k iterations) | ✅ |
| Rate limiting on login (5/min per IP) | ✅ |
| CORS origin whitelist (configurable) | ✅ |
| TrustedHost middleware | ✅ |
| CSP + security headers (Caddy) | ✅ |
| Default secret startup warning | ✅ |
| Read-access audit logging | ✅ |
| Parameterized queries (no SQL injection) | ✅ |
| Bearer + X-Auth-Pacs token support | ✅ |
| Soft-delete + deactivated user rejection | ✅ |

## Tech Stack

- **Backend:** Python 3.12+, Starlette 0.35+, asyncpg, PyPika, Alembic, Pydantic v2, PyJWT, pydicom, pynetdicom
- **Frontend:** React 19, TypeScript, Vite, Ant Design 6, Cornerstone3D 5, dicom-parser
- **Database:** PostgreSQL 16, Elasticsearch 9 (optional)
- **Infrastructure:** Docker compose, nginx (frontend image), GitHub Actions CI

## Testing

| Suite | Command | Count |
|-------|---------|-------|
| Backend unit | `cd backend && python -m pytest` | 103 tests |
| Frontend unit | `cd frontend && npx vitest run` | 246 tests |
| E2E (Playwright) | `cd frontend && npx playwright test` | 45 tests (11 specs) |
| TypeScript | `cd frontend && npx tsc --noEmit` | 0 errors |

## Commands

| Command | Description |
|---------|-------------|
| `./manage db init` | Initialize database + superadmin user |
| `./manage db create` | Create schema |
| `./manage db drop` | Drop database |
| `./manage db shell` | Open database shell |
| `./manage db import` | Import DICOM files |
| `./start.sh` | Start all backend processes |
| `alembic upgrade head` | Apply pending migrations |
| `docker compose up -d` | Start all services |
| `npm run dev` | Frontend dev server (HMR) |
| `npm run build` | Production build |
| `npm test` | Vitest |
| `cd frontend && npx playwright test` | E2E tests |

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2019 Vuk Mirovic.
