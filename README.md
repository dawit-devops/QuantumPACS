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
[![Backend CI](https://github.com/wooque/quantumpacs/actions/workflows/backend.yml/badge.svg)](https://github.com/wooque/quantumpacs/actions/workflows/backend.yml)
[![Frontend CI](https://github.com/wooque/quantumpacs/actions/workflows/frontend.yml/badge.svg)](https://github.com/wooque/quantumpacs/actions/workflows/frontend.yml)

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
| Architecture Decision Records | 13 |
| Backend Tests | 103 (pytest) |
| Frontend Tests | 33 (Vitest) |
| E2E Tests | 8 (Playwright) |
| DB Migrations | 4 (Alembic) |

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker and Docker Compose (for PostgreSQL)

### Quick Start (Docker)

```bash
git clone https://github.com/wooque/quantumpacs.git
cd quantumpacs
docker compose up -d
```

Open `http://localhost` — default credentials: `admin` / `pa55w0rd`

### Manual Setup

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
./manage db init          # creates database, outputs random password
export DB_PASS=<password> # or set in config.local.yaml
./start.sh                # starts DICOM listener, sync, HTTP server
```

#### Frontend

```bash
cd frontend
npm install
npm run dev          # development server with HMR (http://localhost:5173)
npm run build        # production build to dist/
```

Serve `dist/` via Caddy/Nginx, or copy to `backend/static/` with `QUANTUMPACS_DOCKER=true`.

## Repository Structure

```
quantumpacs/
├── backend/                      # Python Starlette API server
│   ├── api/                      # HTTP endpoints, auth, validation, schemas
│   │   └── schemas/              # Pydantic v2 request/response models
│   ├── db/                       # Database access layer (asyncpg + PyPika)
│   ├── dcm/                      # DICOM listener and processing
│   ├── es/                       # Elasticsearch indexing (optional)
│   ├── migrations/               # Alembic migrations (001-004)
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
│       ├── test/                 # 33 Vitest tests
│       └── ...
├── docs/
│   ├── decisions/                # 13 Architecture Decision Records (ADRs)
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
├── docker-compose.yaml           # Service orchestration
├── Dockerfile                    # Multi-stage production image
├── Caddyfile                     # Caddy reverse proxy + security headers
└── .github/workflows/            # CI pipelines (backend, frontend, security)
```

## Architecture

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│  Browser      │────▶│  Caddy (reverse  │────▶│  PostgreSQL   │
│  (React SPA   │     │   proxy + CSP)   │     │  + LISTEN/    │
│   + Viewer)   │◀────│   :80 → :8080   │◀────│  NOTIFY      │
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

Architecture decisions: 13 ADRs in [docs/decisions/](docs/decisions/).

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
| `DB_PASS` | `pa55w0rd` | PostgreSQL password |
| `ES_HOST` | `localhost` | Elasticsearch host |
| `CORS_ORIGINS` | `*` | Allowed CORS origins (lock for production) |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | TrustedHost middleware |
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
- **Database:** PostgreSQL 16, Elasticsearch 8 (optional)
- **Infrastructure:** Docker multi-stage, Caddy, GitHub Actions CI

## Testing

| Suite | Command | Count |
|-------|---------|-------|
| Backend unit | `cd backend && python -m pytest` | 103 tests |
| Frontend unit | `cd frontend && npx vitest run` | 33 tests |
| E2E (Playwright) | `cd frontend && npx playwright test` | 8 tests |
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
