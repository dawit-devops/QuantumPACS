# Changelog

## [2.0.0] - 2026-07-22

### Added
- ADR documentation for all key architectural decisions
- Alembic-based database migrations with version-controlled schema
- Centralized JWT token module (`backend/api/tokens.py`)
- Standardized API response helpers (`backend/api/response.py`)
- Pydantic v2 request validation schemas (`backend/api/schemas/`)
- Structured request body parser with validation errors (`backend/api/validate.py`)
- asyncpg connection pool wrapper (`backend/db/database.py`)
- GitHub Actions CI workflow (lint, test, build)
- Health check endpoint (`/api/health`)
- TypeScript ambient declarations (`frontend/src/types.d.ts`)
- Test setup and Vitest configuration

### Changed
- Migrated backend from ad-hoc ASGI routing to Starlette structured application
- Upgraded PyJWT from 1.x to 2.x with centralized create/verify
- Replaced synchronous SQLite/psycopg2 with asyncpg connection pool
- Upgraded antd from 3.x through 4.x to 5.x
- Migrated frontend build from Create React App to Vite
- Restructured frontend components into feature directories
- Static frontend analysis from graphify-out/ informs architecture decisions

### Fixed
- Disabled CORS credential checks when wildcard origin is used
- Upgraded deprecated/abandoned dependencies (pydicom, pynetdicom, elasticsearch)
- Removed unused legacy auth modules
- Cleaned up commented-out code

### Security
- JWT secret now configurable via `SECRET` environment variable
- Default password replaced with random generation on `db init`
- File change audit trail with user attribution
- Admin-only endpoint gating via permission checks
