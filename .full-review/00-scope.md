# Review Scope

## Target

Full backend code review of QuantumPACS PACS system backend.

## Files

- `backend/app.py` — Starlette application entry point
- `backend/config.py` — Configuration management
- `backend/lifecycle.py` — Application lifecycle (DICOM, MLLP startup)
- `backend/log.py` — Logging setup
- `backend/exceptions.py` — Exception handling
- `backend/db/` — Database abstraction layer (tables, queries, migrations)
- `backend/api/` — API routes, auth, validation, rate limiting
- `backend/dcm/` — DICOM server (C-STORE, C-FIND, C-MOVE)
- `backend/es/` — Elasticsearch integration
- `backend/services/` — Business logic services
- `backend/management/` — Management commands
- `backend/migrations/` — Alembic database migrations
- `backend/tests/` — Test suite

## Flags

- Security Focus: no
- Performance Critical: no
- Strict Mode: no
- Framework: Starlette

## Review Phases

1. Code Quality & Architecture
2. Security & Performance
3. Testing & Documentation
4. Best Practices & Standards
5. Consolidated Report
