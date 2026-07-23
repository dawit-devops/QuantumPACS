# OpenPACS

[![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Starlette](https://img.shields.io/badge/Starlette-000?logo=starlette)](https://www.starlette.io/)
[![React](https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=black)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![Ant Design](https://img.shields.io/badge/Ant%20Design-0170FE?logo=ant-design&logoColor=white)](https://ant.design/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Elasticsearch](https://img.shields.io/badge/Elasticsearch-005571?logo=elasticsearch&logoColor=white)](https://www.elastic.co/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Claude Code](https://img.shields.io/badge/Built%20with-Claude%20Code-DA7857?logo=anthropic)](https://claude.ai/code)
[![Claude Skills](https://img.shields.io/badge/Uses-Claude%20Skills-DA7857?logo=anthropic)](https://github.com/dmccreary/claude-skills)

Open-source Picture Archiving and Communication System (PACS) for medical image management. Built for production radiology workflows — DICOM ingestion, multi-planar reconstruction viewer, multi-site replication, and full-text search over studies and metadata.

## Overview

OpenPACS is a modern, web-based PACS that replaces traditional vendor-locked imaging systems with an open architecture. It handles the full imaging lifecycle — from DICOM modality ingestion through storage, viewing, reporting, and multi-site replication.

The backend runs on Starlette with async PostgreSQL access via asyncpg, JWT-authenticated REST APIs, and a pluggable storage abstraction that supports local filesystem, S3-compatible object stores, and Backblaze B2. The frontend is a single-page application built with React 18, Ant Design 5, and Cornerstone3D for zero-footprint DICOM viewing in the browser.

DICOM modalities send studies to the built-in DICOM listener (pynetdicom), which routes them through configurable storage backends, indexes metadata into PostgreSQL and Elasticsearch, and notifies connected viewers in real time via WebSocket.

## Site Metrics

| Metric | Count |
|--------|-------|
| Backend Python Modules | 61 |
| Frontend Components | 38 |
| Architecture Decision Records | 8 |
| Test Files | 14 |
| Code Lines (Backend) | 3,525 |
| Code Lines (Frontend) | 3,105 |
| DICOM Libraries | pydicom, pynetdicom, cornerstone3d |

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose (for PostgreSQL and other services)

### Quick Start (Docker)

```bash
git clone https://github.com/wooque/openpacs.git
cd openpacs
docker compose up -d
```

If Elasticsearch fails to start with permission errors:
```bash
chmod -R 1000 ./es
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
# or
npm run build        # production build to build/
```

Serve `build/` via Nginx/Caddy, or copy to `backend/static/` with `OPENPACS_DOCKER=true`.

## Repository Structure

```
openpacs/
├── backend/                      # Python Starlette API server
│   ├── api/                      # HTTP endpoints, auth, validation, schemas
│   │   └── schemas/              # Pydantic v2 request/response models
│   ├── db/                       # Database access layer
│   ├── dcm/                      # DICOM listener and processing
│   ├── es/                       # Elasticsearch indexing and search
│   ├── migrations/               # Alembic database migrations
│   │   └── versions/             # Version-controlled migration scripts
│   ├── storage/                  # Pluggable storage backends
│   ├── tests/                    # pytest test suite
│   ├── app.py                    # Starlette application entry point
│   ├── config.py                 # YAML + environment configuration
│   └── manage                    # Database management CLI
├── frontend/                     # React SPA
│   └── src/
│       ├── account/              # Account settings
│       ├── common/               # Shared components and utilities
│       ├── detail/               # Study detail and viewer
│       ├── files/                # File management
│       ├── login/                # Authentication
│       ├── logs/                 # System logs
│       ├── notfound/             # 404 page
│       ├── patient/              # Patient browsing
│       ├── replicas/             # Replica management
│       ├── test/                 # Test setup
│       └── users/                # User administration
├── docs/
│   └── decisions/                # Architecture Decision Records (ADRs)
├── docker/                       # Docker build files
│   └── postgres/                 # Custom PostgreSQL image
├── es/                           # Elasticsearch configuration
├── storage/                      # Local storage mounts
├── docker-compose.yaml           # Service orchestration
├── Dockerfile                    # Backend container image
└── Caddyfile                     # Reverse proxy configuration
```

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

- **Backend**: Python 3.11, Starlette, asyncpg, Alembic, Pydantic v2, PyJWT, pydicom, pynetdicom
- **Frontend**: React 18, TypeScript, Vite, Ant Design 5, Cornerstone3D, dicom-parser
- **Database**: PostgreSQL 16, Elasticsearch 8
- **Infrastructure**: Docker, Caddy, GitHub Actions

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
| `docker compose up -d` | Start all services (PostgreSQL, etc.) |
| `npm run dev` | Start frontend dev server |
| `npm run build` | Production frontend build |
| `npm test` | Run frontend tests |
| `npm run lint` | Lint frontend code |
| `npm run typecheck` | TypeScript type checking |
| `pytest` | Run backend tests (from `backend/`) |
| `flake8` | Lint backend code (from `backend/`) |

## Reporting Issues

Found a bug, typo, or have a suggestion? Please report it on [GitHub Issues](https://github.com/wooque/openpacs/issues).

When reporting issues, include:
- Description of the problem or suggestion
- Steps to reproduce (for bugs)
- Expected vs actual behavior
- Browser/environment details (for viewer issues)

## Contributing

1. Open an issue to discuss changes before implementing
2. Write tests for new endpoints and DICOM processing logic
3. Run `pytest` and `npm test` before opening a PR
4. Update ADRs for architectural decisions
5. Follow existing code conventions — match the patterns you find

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2019 Vuk Mirovic.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the conditions in the full license.

## Acknowledgements

This project builds on several open-source projects:

- **[Starlette](https://www.starlette.io/)** — Lightweight ASGI framework for the Python backend
- **[Cornerstone3D](https://www.cornerstonejs.org/)** — Medical image visualization in the browser
- **[pydicom](https://pydicom.github.io/)** — DICOM file parsing for Python
- **[pynetdicom](https://pydicom.github.io/pynetdicom/stable/)** — DICOM networking protocol
- **[Ant Design](https://ant.design/)** — React UI component library
- **[asyncpg](https://magicstack.github.io/asyncpg/)** — High-performance PostgreSQL driver
- **[Alembic](https://alembic.sqlalchemy.org/)** — Database migration management
- **[Vite](https://vitejs.dev/)** — Frontend build tooling

## Contact

**Vuk Mirovic** — Copyright holder and maintainer

Questions or collaboration opportunities? Open an issue on [GitHub](https://github.com/wooque/openpacs).
