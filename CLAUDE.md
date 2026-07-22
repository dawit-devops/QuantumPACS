# OpenPACS — Agent Instructions

## Project Overview

Production PACS (Picture Archiving and Communication System) for medical image management. Backend in Python (Starlette), frontend in React (Vite + Ant Design + Cornerstone3D).

## Key Conventions

### Backend
- **Framework**: Starlette with async endpoints and Uvicorn/Gunicorn
- **Database**: asyncpg connection pool via `db/database.py` `Database` class — use `get_database().acquire()` for connections
- **Migrations**: Alembic in `backend/migrations/` — always create a new migration for schema changes
- **Auth**: JWT via `api/tokens.py` (`create_token` / `verify_token`) — all endpoints authenticated by default
- **Response format**: Use helpers from `api/response.py` (`ok()`, `created()`, `not_found()`, etc.)
- **Request validation**: `api/validate.py` `parse_body()` with Pydantic v2 schemas from `api/schemas/`
- **Config**: `backend/config.py` loads from YAML + env vars — add new keys to `default_config`
- **Logging**: `log = get_logger(__name__)` from `backend/log.py`

### Frontend
- **Build**: Vite with manual chunk splitting for react, antd, cornerstone
- **UI**: Ant Design v5 components
- **DICOM viewer**: Cornerstone3D with cornerstone-wado-image-loader
- **State**: Component-local state + React context (no Redux)
- **Types**: Ambient declarations in `src/types.d.ts` for cornerstone, hammerjs, dicom-parser
- **CSS**: CSS Modules for component styles

### Documentation
- Architectural decisions go in `docs/decisions/ADR-NNN-title.md` — follow existing ADR format
- README covers quick start, commands, architecture overview
- Inline comments explain *why*, not *what*
- No commented-out code — git history preserves it

### Testing
- **Backend**: pytest with async fixtures in `backend/tests/`
- **Frontend**: Vitest with React Testing Library

## Common Gotchas
- `network_mode: host` in docker-compose — services bind directly to host ports
- Elasticsearch 8 needs `xpack.security.enabled=false` for dev (configured in docker-compose)
- Database init (`./manage db init`) generates a random password — capture it from output
- Token expiry defaults to 14 days — extend via `create_token(user, expire={'days': 30})`
- CORS allows all origins — tighten before production deployment
- The `notify_event()` PostgreSQL trigger powers real-time replica sync via LISTEN/NOTIFY
- Graphify analysis output in `graphify-out/` — run `/graphify` query for codebase questions
