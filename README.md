# OpenPACS

Open-source Picture Archiving and Communication System for medical image management. DICOM ingestion, study browsing, multi-planar reconstruction viewer, multi-site replication, and full-text search — built for production radiology workflows.

## Quick Start

```bash
# Clone and start all services
git clone https://github.com/wooque/openpacs
docker compose up -d
```

If Elasticsearch fails to start with permission errors:
```bash
chmod -R 1000 ./es
docker compose up -d
```

Open `http://localhost` — default credentials: `admin` / `pa55w0rd`

## Manual Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
./manage db init          # creates DB, outputs random password
export DB_PASS=<password> # or set in config.local.yaml
./start.sh                # starts DICOM listener, sync, HTTP server
```

### Frontend

```bash
npm install
npm run build             # outputs to build/
```

Serve `build/` via Nginx/Caddy, or copy to `backend/static/` and set `OPENPACS_DOCKER=true`.

## Commands

| Command | Description |
|---------|-------------|
| `./manage db init` | Initialize database and create superadmin user |
| `./manage db create` | Create database schema |
| `./manage db drop` | Drop database |
| `./manage db reset` | Drop and recreate database |
| `./manage db shell` | Open database shell |
| `./manage db import` | Import DICOM files |
| `./start.sh` | Start all backend processes |
| `npm run dev` | Start frontend dev server |
| `npm run build` | Production frontend build |
| `npm test` | Run frontend tests |
| `npm run lint` | Lint frontend code |
| `npm run typecheck` | TypeScript type checking |
| `pytest` | Run backend tests (from `backend/`) |
| `flake8` | Lint backend code (from `backend/`) |
| `docker compose up -d` | Start all services |

## Architecture

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│  Browser      │────▶│  Caddy (reverse  │────▶│  PostgreSQL   │
│  (React SPA   │     │   proxy)         │     │  + Elastic    │
│   + Viewer)   │◀────│                  │◀────│  Search       │
└──────────────┘     └────────┬─────────┘     └──────────────┘
                              │
                     ┌────────▼─────────┐
                     │  Starlette API    │
                     │  (Uvicorn/Gun)    │
                     │                   │
                     │  ┌─ JWT Auth     │
                     │  ├─ DICOM Router │
                     │  ├─ File Manager │
                     │  └─ Replicator   │
                     └────────┬─────────┘
                              │
                     ┌────────▼─────────┐
                     │   Filesystem      │
                     │   (DICOM store)   │
                     └──────────────────┘
```

Key design decisions documented in [docs/decisions/](docs/decisions/):
- **ADR-001**: Strangler Fig incremental modernization
- **ADR-002**: Starlette backend framework
- **ADR-003**: JWT token authentication
- **ADR-004**: PostgreSQL + asyncpg + Alembic
- **ADR-005**: REST API with Pydantic validation
- **ADR-006**: React + Vite + Ant Design + Cornerstone3D
- **ADR-007**: Multi-tier storage (FS + DB + ES)
- **ADR-008**: Security architecture

## Configuration

Settings loaded from `config.local.yaml` (if present) and overridden by environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET` | `db_password` | JWT signing secret |
| `SUPERADMIN_PASS` | `pa55w0rd` | Initial admin password |
| `DB_HOST` | `127.0.0.1` | PostgreSQL host |
| `DB_DATABASE` | `openpacs` | PostgreSQL database name |
| `DB_USER` | `openpacs` | PostgreSQL user |
| `DB_PASS` | `pa55w0rd` | PostgreSQL password |
| `ES_HOST` | `localhost` | Elasticsearch host |
| `OPENPACS_DOCKER` | — | Enable Docker mode (backend serves static) |

## Tech Stack

- **Backend**: Python 3.11, Starlette, asyncpg, Alembic, Pydantic v2, PyJWT
- **Frontend**: React 18, TypeScript, Vite, Ant Design 5, Cornerstone3D
- **Database**: PostgreSQL 16, Elasticsearch 8
- **Infrastructure**: Docker, Caddy, GitHub Actions

## Contributing

1. Open an issue to discuss changes before implementing
2. Write tests for new endpoints and DICOM processing logic
3. Run `pytest` and `npm test` before opening a PR
4. Update ADRs for architectural decisions
5. Follow existing code conventions — match the patterns you find

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2019 Vuk Mirovic.
