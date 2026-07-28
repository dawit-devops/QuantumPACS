# QuantumPACS — Agent Instructions

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
- v3 planning documents: `docs/PRD-v3.md`, `docs/IMPLEMENTATION_PLAN-v3.md`, `docs/ROADMAP-v3.md`, plus ADRs 014–021 in `docs/decisions/`
- Inline comments explain *why*, not *what*
- No commented-out code — git history preserves it

### Testing
- **Backend**: pytest with async fixtures in `backend/tests/`
- **Frontend**: Vitest with React Testing Library

## Dev Environment (Permanent Setup)

Services managed via systemd user services — auto-start on boot:

| Service | Type | URL |
|---------|------|-----|
| PostgreSQL | Docker container `quantumpacs-postgres-1`, `restart: unless-stopped` | `localhost:5432` |
| Backend | `quantumpacs-backend.service` (systemd user) | `http://localhost:8080` |
| Frontend | `quantumpacs-frontend.service` (systemd user) | `http://localhost:5173` |

**Commands:**
- `scripts/dev.sh {start|stop|restart|status|logs|logs-fe}` — manage all services
- `systemctl --user start|stop|restart|status quantumpacs-backend.service`
- `systemctl --user start|stop|restart|status quantumpacs-frontend.service`
- `journalctl --user -u quantumpacs-backend.service -f` — tail backend logs
- `journalctl --user -u quantumpacs-frontend.service -f` — tail frontend logs
- `docker compose up -d` — start PostgreSQL via docker-compose
- `docker compose build postgres` — rebuild custom postgres image (after base image update)

**Key fixes applied (Jul 2026):**
- `app.py`: changed from `on_startup` parameter (removed in starlette 1.x) to lifespan pattern, then pinned starlette to `>=0.35.0,<0.36.0` for compatibility
- `es/es.py`: prepends `http://` scheme + `:9200` port to bare hostnames for ES 8.x client compat
- `db_init.py`: replaced `asyncio.get_event_loop()` with `asyncio.run()` for Python 3.14 compat
- `config.local.yaml`: uses dedicated QuantumPACS postgres on port 5432
- `docker-compose.yaml`: removed deprecated `version` key; uses custom `quantumpacs-postgres:16` image built from `docker/postgres/Dockerfile` (strips dcm4chee init scripts from base image)
- `frontend/vite.config.js`: set `host: '0.0.0.0'` for LAN access, port changed to 5173
- Backend runs via `uvicorn app:app --host 0.0.0.0 --port 8080`
- Frontend runs via `vite --host 0.0.0.0 --port 5173`
- Database port config centralized in `config.py` default_config via `db_port` key

## Git Workflow (v3)
- **Branch model**: Phased Git Flow per ADR-022
  - `main` — production v2.x (until v3.0 GA); no direct pushes
  - `v3-dev` — v3 integration; no direct pushes, merge via PR
  - `phase/N-*` — per-phase feature branches off `v3-dev`; delete after merge
  - `release/v3.N` — release candidates from `v3-dev` → `main` + `v3-dev`
  - `fix/*` — hotfixes from `main`, cherry-pick to `v3-dev`
- **Commit style**: Conventional Commits (`feat:`, `fix:`, `chore:`, etc.)
- **Pre-commit gates**: ruff, prettier, tsc, pytest, protected-branch guard (pre-push)
- **CI**: Full suite runs on push to `main`, `v3-dev`, `phase/**`

## Common Gotchas
- `network_mode: host` in docker-compose — services bind directly to host ports
- Elasticsearch 8 needs `xpack.security.enabled=false` for dev (configured in docker-compose), but ES is **not running** in this dev env — search is disabled gracefully
- Database init (`./manage db init`) generates a random password — capture it from output
- Token expiry defaults to 14 days — extend via `create_token(user, expire={'days': 30})`
- CORS allows all origins — tighten before production deployment
- The `notify_event()` PostgreSQL trigger powers real-time replica sync via LISTEN/NOTIFY
- Graphify analysis output in `graphify-out/` — run `/graphify` query for codebase questions
- PostgreSQL runs via `quantumpacs-postgres-1` Docker container on port 5432 (dedicated container built from `docker/postgres/Dockerfile`), but host port may be **5433** if 5432 was already in use — check `docker port quantumpacs-postgres-1 5432`
- Elasticsearch Docker image cannot be pulled (network issues) — search disabled at startup, no impact on basic functionality
- **PWA service worker cache**: `frontend/dist/` build contains `sw.js` that caches stale frontend assets. When visiting the Vite dev server, previously-installed service workers intercept API calls to `/api/*` and fail with "NetworkError". Fix: `rm -rf frontend/dist/` + browser hard refresh (Ctrl+Shift+R) + unregister SW in DevTools → Application → Service Workers. VitePWA `selfDestroying: true` auto-clears stale SWs in dev mode.
- `backend/lifecycle.py` `_run_dicom()` must run in a **daemon thread** — `ae.start_server()` from pynetdicom 3.x blocks the main thread, preventing uvicorn HTTP startup. Use `threading.Thread(target=_run_dicom, daemon=True)`. Run `scripts/verify_config.sh` after any change.
- `backend/api/tracing.py` `traced_connection()` must use `_TracedPool` wrapper — Python 3.14 enforces read-only on `Pool.acquire` attribute (both direct assignment and `object.__setattr__` fail). Wrap pool in a proxy class.
- Backend fails to start if `backend/config.local.yaml` has `db_port: 5432` (wrong) or a default `secret` (rejected by `assert_production_secret()`). Run `scripts/dev.sh start` which auto-fixes both.
