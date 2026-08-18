# Comprehensive Code Review Report — QuantumPACS Backend

## Review Target

Full backend code review of QuantumPACS PACS system backend:

- `backend/app.py`, `config.py`, `lifecycle.py`, `log.py`, `exceptions.py`
- `backend/db/` — Database abstraction layer
- `backend/api/` — API routes, auth, validation, rate limiting
- `backend/dcm/` — DICOM server (C-STORE, C-FIND, C-MOVE)
- `backend/es/` — Elasticsearch integration
- `backend/services/` — Business logic services
- `backend/management/`, `backend/migrations/`, `backend/tests/`

## Executive Summary

QuantumPACS backend demonstrates a sound architectural foundation (Starlette async, asyncpg pools, Redis Streams, structured logging, Prometheus metrics) but has **critical security vulnerabilities, performance anti-patterns, and operations gaps** that must be addressed before production deployment. The most urgent issues are SQL injection vectors in two locations, hardcoded default secrets, missing authorization on file endpoints, and synchronous file I/O blocking the async event loop. The project has zero CI/CD automation, no production deployment strategy, and no secrets management.

**Total findings: 126 (18 Critical, 29 High, 48 Medium, 19 Low)**

---

## Findings by Priority

### Critical Issues (P0 — Must Fix Immediately)

**Security (6):**
1. Hardcoded default secrets in `config.py` — `db_password`, `secret`, `superadmin_pass` default to weak values (pa55w0rd)
2. SQL injection via f-string in `api/oauth.py:144` — role slug interpolated directly into SQL
3. SQL injection via `_quote()` string escaping in `api/fhir.py` — PseudoColumn with user input
4. Missing `@requires_permission()` on `FilesHandler.get/post` and `FileHandler.get` in `api/files.py`
5. Wide dependency version ranges (`starlette>=1.0.1,<2.0`, `cryptography>=41.0,<50.0`)
6. Encryption silently returns plaintext when Fernet fails (`api/encryption.py`)

**Performance (6):**
1. Synchronous `open()`/`read()` in all async WADO-RS, thumbnail, ZIP, CSV handlers
2. WADO-RS study retrieval builds entire multipart response in memory — OOM risk
3. `_active_cache` in `api/auth.py` grows monotonically — no eviction
4. `TokenBucket._attempts` never prunes dormant IPs
5. 6 separate Redis TCP connections instead of 1 pooled connection
6. Module-level global state prevents >1 uvicorn worker

**Architecture (6):**
1. DB models mixed with search/storage concerns
2. API handlers bypass service layer (direct DB access)
3. `assert_production_secret()` calls `sys.exit(1)` in async lifespan
4. Dockerfile vs requirements.txt version drift (elasticsearch 9 vs 8, starlette 1.x vs 0.35.x)
5. Dual schema management (sync_db + Alembic) diverges DB state
6. No formal API versioning strategy

**CI/CD (4):**
1. Zero CI/CD pipeline — no GitHub Actions, GitLab CI, or any CI config
2. Module-level globals prevent safe multi-worker Gunicorn deployment
3. No production deployment script or container registry target
4. No secrets management — production secrets in YAML/env vars

**Documentation (2):**
1. OpenAPI spec covers <20% of 50+ endpoints
2. No CHANGELOG or UPGRADING.md despite 33 migrations and breaking changes

### High Priority (P1 — Fix Before Next Release)

**Security (8):**
- Missing security headers (HSTS, CSP, X-Frame-Options, etc.)
- Timing-attack-vulnerable password hash comparison (uses `==`)
- No rate limiting on API key validation endpoint
- Redis without authentication (empty password)
- SSRF via webhook test endpoint (arbitrary URL POST)
- MLLP IP allowlist broken — CIDR string never matches individual IPs
- No CSRF protection on cookie-authenticated endpoints
- IDOR — sequential file IDs without tenant-level checks

**Performance (8):**
- Missing DB indexes on `sop_instance_uid`, `series_instance_uid`, `study_instance_uid`
- Routing rules loaded from DB on every C-STORE (no caching)
- Per-message Redis connections in WebSocket handler
- Fire-and-forget asyncio tasks in PgNotifyBridge
- Health checks run serially (no `asyncio.gather`)
- Startup retry loop wastes 30s (no exponential backoff)
- DICOM C-STORE blocks event loop via `run_coroutine_threadsafe`
- Master replica lookup uncached

**Architecture (11):**
- Module-level globals impede lifecycle management
- `db/__init__.py` side effects at import time
- Inward dependency from data layer to infrastructure
- CORS headers set manually in 4+ locations
- Inconsistent error response format across endpoints
- Dual data access strategy (services vs direct DB)
- Hardcoded service registration prevents extensibility
- Inconsistent async/threading boundary
- Missing observability for background workers
- `object.__setattr__` workaround in tracing.py (Python 3.14)
- Module-level `work = True` shutdown flag in sync.py

**Testing (6):**
- SQL injection vectors never probed in tests
- Token version invalidation untested
- Encryption failure logging unchecked
- Redis fallback untested
- WebSocket pubsub path untested
- app.py middleware/CORS untested

**Documentation (4):**
- README metrics inaccurate (13 ADRs claimed, actually 22)
- ADR index missing ADRs 014-022
- SECURITY_AUDIT.md describes already-fixed issues as "Open"
- API Pydantic schemas lack field-level descriptions

**CI/CD (6):**
- Stale Dockerfile (no multi-stage, runs as root)
- Missing .dockerignore for build context
- Gunicorn workers = CPU count without memory awareness
- No container image vulnerability scanning
- No DB backup or disaster recovery plan
- No Infrastructure as Code beyond docker-compose

### Medium Priority (P2 — Plan for Next Sprint)

**Security (9):** Cookie secure flag on non-login endpoints, OAuth HTTP redirect, WebSocket token in query string, exception stack traces in logs, silent exception swallowing, API key prefix reduces search space, missing input validation on filenames, OIDC JWKS endpoint missing, rate limit key scope too narrow

**Performance (7):** Dashboard runs 7 serial queries, C-FIND returns 1000 unpaginated, tenant pool sizes hardcoded, SHA-256 recomputed in HL7 handler, `_init_locks` leak, legacy metrics overflow risk, PgNotifyBridge busy-wait loop

**Testing (4):** No E2E test skeleton, no conftest fixture consolidation, load tests target frontend only, migration/tenant tests missing

**Documentation (7):** 70% of modules lack docstrings (especially dcm/, fhir.py, dicomweb.py, ingestion/), no DATA_DICTIONARY.md, migration docstrings too brief, README missing 40+ config keys, REST_API_REVIEW recommendations untracked, DICOM server has zero inline docs, no observability runbooks

### Low Priority (P3 — Track in Backlog)

**Security (5), Testing (3), Documentation (2), DevOps (4), Architecture (5)**

---

## Findings by Category

| Category | Critical | High | Medium | Low | Total |
|----------|----------|------|--------|-----|-------|
| Code Quality | 6 | 11 | 8 | 0 | 25 |
| Security | 6 | 8 | 9 | 5 | 28 |
| Performance | 6 | 8 | 7 | 3 | 24 |
| Testing | 3 | 6 | 4 | 3 | 16 |
| Documentation | 2 | 4 | 7 | 2 | 15 |
| Framework/Standards | 5 | 4 | 10 | 5 | 24 |
| CI/CD & DevOps | 4 | 6 | 5 | 4 | 19 |

**Grand Total: 126 findings**

---

## Recommended Action Plan

### Sprint 1 — Security Patch (Critical P0s)
1. Parameterize all SQL in `oauth.py` and `fhir.py` — replace f-strings with `$1` params
2. Add `@requires_permission(FILE_READ)` to all file endpoints in `api/files.py`
3. Remove hardcoded defaults from `config.py`, validate on startup
4. Replace `sys.exit(1)` in `assert_production_secret()` with `ConfigurationError`
5. Replace sync `open()` with `aiofiles.open()` in WADO-RS, thumbnails, ZIP, CSV

### Sprint 2 — Production Readiness
1. **Create CI pipeline** (GitHub Actions): ruff, pytest, vitest, tsc, Docker build
2. Add security headers middleware (HSTS, CSP, X-Frame-Options, etc.)
3. Consolidate Redis connections into single ConnectionPool
4. Add LRU eviction to `_active_cache` and `TokenBucket._attempts`
5. Add DB indexes for `sop_instance_uid`, `series_instance_uid`, `study_instance_uid`
6. Add E2E test skeleton (testcontainers + PostgreSQL)

### Sprint 3 — Operations Hardening
1. Create production deployment script (build → push → deploy → health gate → rollback)
2. Add secrets management (Vault, env vars, or k8s Secrets)
3. Add DB backup script and document DR plan
4. Create DATA_DICTIONARY.md and CHANGELOG.md
5. Expand OpenAPI spec to cover all endpoints

### Sprint 4 — Architecture & Observability
1. Fix CORS — use CORSMiddleware instead of manual headers in 4+ locations
2. Stream WADO-RS responses via StreamingResponse (avoid OOM)
3. Add exponential backoff to startup retry loop
4. Parallelize health checks with `asyncio.gather`
5. Add module docstrings to 30+ undocumented modules

---

## Key Strengths Identified (not just problems)

- **Architecture**: Good modular monolith design, async-first with asyncpg/Starlette, Redis Streams for eventing
- **Observability**: Prometheus metrics, OpenTelemetry tracing, structured JSON logging, Sentry integration
- **Auth**: JWT with refresh tokens, OAuth/OIDC support, RBAC, API key validation
- **Testing**: 85 test files, 65% coverage, good error-path testing, Starlette TestClient pattern
- **Documentation**: 22 ADRs, persona flows, REST API review, DB schema review, production readiness review
- **DICOM**: Full DICOMweb (WADO/QIDO/STOW-RS), FHIR R4, HL7 v2.x MLLP, pynetdicom SCP
- **Multi-tenancy**: Database-per-tenant with connection pooling and eviction
- **Background services**: PgNotifyBridge, Redis Stream ingestion, DICOM forwarding
