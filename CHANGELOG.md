# Changelog

All notable changes to QuantumPACS are documented here.

## [Unreleased]

### Added
- Three-layer design token system (`tokens.css` — primitive, semantic, component)
- Ant Design theme config (`theme.ts`) aligned with brand colors (#0077B6 primary, #6366F1 secondary)
- Component specs for 6 UI components with states, variants, ASCII layouts
- Brand presentation slide deck (`docs/presentation/brand-deck.html`)
- Token audit report (`docs/token-audit.md`) — 11 hardcoded hex values found and fixed
- CORS headers on auth error handler (fixes E2E ws_token bug)
- Rate limiting (`api/ratelimit.py`): 5 attempts/min per IP, lockout at 10 for 5 min, wired into Login
- TrustedHostMiddleware with configurable `allowed_hosts`
- Startup CRITICAL warning when default secrets detected in config
- CSP + security headers in Caddyfile (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`)
- Bearer token authorization support alongside legacy `X-Auth-Pacs`
- 3 Alembic migrations: 002 (PKs, UNIQUE, FK indexes, CHECK), 003 (ON DELETE CASCADE, TIMESTAMPTZ), 004 (BIGINT IDENTITY)
- `paginated()` response helper with `{data, meta, links}` envelope
- `api_error()` structured error response helper
- Deprecation headers (`X-API-Deprecated`, `X-API-Sunset`, `X-API-Replacement`) on legacy endpoints
- Read-access audit logging for file views and downloads
- GitHub Actions CI: backend (pytest + PostgreSQL), frontend (tsc + vitest + build), security (pip-audit + npm audit)
- 5 Playwright E2E test scenarios (CORS, rate limiter, token auth, sidebar, 404)
- Health endpoint with PostgreSQL `SELECT 1` check (200/503)
- Ops guide (`docs/ops-guide.md`): backup/restore/DR/monitoring/migration
- Production Dockerfile improvements: `tini` init, `PYTHONUNBUFFERED=1`, Python 3.12-slim, Node 22-alpine, `docker-entrypoint.sh` with migration auto-run

### Fixed
- Frontend `tokens.css` and `index.css` never imported — added imports in `index.tsx`
- N+1 query in `Replica.get_all()` — single batch query with JOIN
- `Series.do_update` bug (was self-assigning `number` instead of `description`)
- `notify_event()` PostgreSQL trigger — NULL-safe `COALESCE` wrapping
- Broken `path_params` → `query_params` in user/log pagination endpoints
- 10 TypeScript errors across CornerstoneElement, history, SearchBar, Sidebar, users
- Missing `PRIMARY KEY` on `replica_files` table
- Missing `UNIQUE` constraint on `users.username`
- Missing FK indexes on 8 foreign key columns
- 10 `TIMESTAMP` → `TIMESTAMPTZ` columns
- 10 `SERIAL` → `BIGINT GENERATED ALWAYS AS IDENTITY` PKs
- Dockerfile: `QUANTUM_DOCKER` → `QUANTUMPACS_DOCKER` (env var consistency)

### Changed
- `GET /api/users` now paginated with `{data, meta, links}` envelope
- `GET /api/logs` now paginated with `{data, meta, links}` envelope
- Static files served from `frontend/dist/` (was `frontend/build/`)
- Node image 26-alpine → 22-alpine (LTS) in Dockerfile
- Python image 3.11-slim → 3.12-slim in Dockerfile
- `CMD` shell pattern → `tini` + `docker-entrypoint.sh` for proper signal handling

### Documentation
- 5 new ADRs: 009 (Design System), 010 (Rate Limiting), 011 (DB Schema Harden), 012 (CI Pipeline), 013 (Ops Guide)
- README: updated tech stack versions, config vars, security table, testing counts, repo structure, architecture diagram
- PRD (`docs/PRD.md`): comprehensive product requirements
- Security audit (`docs/SECURITY_AUDIT.md`): 9 findings implemented
- REST API review (`docs/REST_API_REVIEW.md`): 6 findings implemented
- DB schema review (`docs/DB_SCHEMA_REVIEW.md`): 4 migrations with 30+ changes
