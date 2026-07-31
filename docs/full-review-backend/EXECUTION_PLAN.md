# Execution Plan: Backend Review Remediation

**Branch:** `fix/review-remediation` (off `v3-dev`)
**Total:** 9 sprints, ~10-15 engineer-days
**Merges:** After Sprint 4 (first reviewable chunk) or after Sprint 9 (full scope)

---

## Sprint 1: Security Hotfixes (P0 Critical) — ~1-2 days

| # | Issue | File(s) | Fix |
|---|-------|---------|-----|
| 1 | SQL injection — OAuth role slug | `api/oauth.py:144` | Replace f-string with `$1` parameterized query |
| 2 | SQL injection — FHIR `_quote()` | `api/fhir.py` (3 locations) | Replace `PseudoColumn(_quote(...))` with parameterized subqueries |
| 3 | Missing `@requires_permission()` | `api/files.py` (3 endpoints) | Add `@requires_permission(FILE_READ)` decorators |
| 4 | Hardcoded default secrets | `config.py` | Remove default password values; validate on startup; replace `sys.exit(1)` with `ConfigurationError` |
| 5 | Encryption silent plaintext fallback | `api/encryption.py` | Raise `RuntimeError` instead of returning plaintext |
| 6 | Dockerfile vs requirements.txt drift | `Dockerfile`, `requirements.txt` | Align version ranges; use `pip install -r requirements.txt` in Dockerfile |
| 7 | Dependency CVEs | `requirements.txt` | Pin `PyJWT>=2.8.0`, `cryptography>=42.0.0` |

---

## Sprint 2: Performance Criticals (P0) — ~2-3 days

| # | Issue | File(s) | Fix |
|---|-------|---------|-----|
| 1 | Sync `open()` → `aiofiles` | `api/dicomweb.py:250,295` | Replace with `aiofiles.open()` + async read |
| 2 | WADO-RS in-memory OOM | `api/dicomweb.py:286-308` | Use `StreamingResponse` with async generator, yield multipart chunks |
| 3 | `_active_cache` unbounded | `api/auth.py:22` | Add LRU eviction (`OrderedDict`, max 5000, periodic cleanup) |
| 4 | `TokenBucket._attempts` unbounded | `api/ratelimit.py:49` | Add max-size eviction + periodic scavenger |
| 5 | 6 separate Redis connections | `api/redis_client.py` + 4 files | Consolidate to 1 `ConnectionPool`, namespace by key prefix |
| 6 | Missing DB indexes | new migration | `ix_files_sop_instance_uid`, `ix_series_instance_uid`, `ix_studies_study_instance_uid` |
| 7 | Serial health checks | `api/telemetry.py:216-238` | Wrap in `asyncio.gather()` |
| 8 | Per-message Redis in WS | `api/ws.py:141-155` | Use `get_client()` singleton instead of `aioredis.Redis(...)` per call |
| 9 | Fire-and-forget tasks | `services/pg_notify_bridge.py:80,83` | Track tasks with `_pending_tasks` set + done callback |

---

## Sprint 3: P1 Security & Architecture — ~2 days

| # | Issue | File(s) | Fix |
|---|-------|---------|-----|
| 1 | Missing security headers | `app.py` | Add HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy |
| 2 | Timing-safe password compare | `db/users.py:53-60` | Replace `==` with `hmac.compare_digest()` |
| 3 | API key rate limiting | `api/auth.py:133-149` | Add `RedisTokenBucket` check for API key auth |
| 4 | Redis no-auth | `config.py:19` | Validate `redis_password` is set in production |
| 5 | SSRF in webhook tester | `api/webhooks.py:87-106` | Block internal/reserved IP ranges |
| 6 | MLLP CIDR allowlist | `services/ingestion/hl7_server.py:46` | Use `ipaddress.ip_network()` for CIDR matching |
| 7 | No CSRF protection | `app.py` | Add `SameSite=Strict` + `X-CSRF-Token` verification for mutations |
| 8 | IDOR in file access | `api/files.py:211-217` | Add tenant-level authorization check |
| 9 | CORS manual in 4+ locations | `app.py`, `api/auth.py` | Replace with `CORSMiddleware` |
| 10 | `object.__setattr__` workaround | `api/tracing.py:76,104` | Use `__getattr__` proxy pattern |

---

## Sprint 4: CI/CD & Operations Foundation — ~1-2 days

| # | Issue | File(s) | Fix |
|---|-------|---------|-----|
| 1 | No CI pipeline | new `.github/workflows/` | GitHub Actions: lint + test + typecheck + Docker build + vuln scan |
| 2 | `SECURITY_AUDIT.md` stale | `docs/SECURITY_AUDIT.md` | Update findings status; add "Last Verified" header |
| 3 | ADR index incomplete | `docs/decisions/README.md` | Add ADR-014 through ADR-022 |
| 4 | Critical test gaps | `tests/` | Add SQL injection probe tests, token version invalidation test, encryption logging test |
| 5 | conftest fixture consolidation | `tests/conftest.py` | Extract `_FakeAuth`, `_make_app()`, `_mock_conn()` into shared fixtures |

---

## Sprint 5: Architecture & Code Quality — ~2 days

| # | Issue | File(s) | Fix |
|---|-------|---------|-----|
| 1 | Module-level globals → `app.state` | `api/ws.py`, `api/auth.py`, `api/telemetry.py`, `lifecycle.py` | Move globals to `app.state` service registry |
| 2 | `db/__init__.py` import side effects | `db/__init__.py` | Make imports lazy; move pool init to lifespan |
| 3 | Inward dependency (data→infra) | `db/` | Extract interface; inject infra dependencies |
| 4 | `service_layer` bypassed | `api/*.py` | Route DB access through registered services |
| 5 | `sys.exit(1)` in lifespan | `config.py:94` | Raise `ConfigurationError`, catch in lifespan |
| 6 | Startup retry → exponential backoff | `lifecycle.py:138-155` | `asyncio.sleep(0.5 * 2**i)` |
| 7 | `sync.py` `work = True` global | `sync.py:20` | Replace with `asyncio.Event()` |
| 8 | Inconsistent error responses | `api/response.py` + handlers | Standardize on `ok()`, `api_error()`, `not_found()` everywhere |

---

## Sprint 6: Testing Expansion — ~1-2 days

| # | Issue | File(s) | Fix |
|---|-------|---------|-----|
| 1 | Redis fallback test | `tests/test_ratelimit.py` | Mock Redis failure → verify `TokenBucket` fallback |
| 2 | WebSocket pubsub test | `tests/test_ws.py` | Test successful Redis publish path |
| 3 | app.py middleware/CORS test | `tests/test_app.py` | Test middleware stack, CORS preflight, error handlers |
| 4 | Storage adapter tests | `tests/test_storage_b2.py`, etc. | B2, S3, local storage adapter unit tests |
| 5 | Routing engine test | `tests/test_routing.py` | Rule evaluation, matching, destinations |
| 6 | E2E test skeleton | `tests/integration/test_e2e.py` | testcontainers + PostgreSQL, full store→search→retrieve |
| 7 | Shared test fixtures | `tests/conftest.py` | Consolidate `_FakeAuth`, `_make_app()`, `_mock_conn()` |

---

## Sprint 7: Documentation Overhaul — ~1-2 days

| # | Issue | File(s) | Fix |
|---|-------|---------|-----|
| 1 | CHANGELOG.md + UPGRADING.md | new files | keep-a-changelog format; v2→v3 migration guide |
| 2 | README metrics + config table | `README.md` | Fix ADR count (22), test count; document all 55 config keys |
| 3 | Pydantic Field descriptions | `api/schemas/*.py` (16 files) | Add `Field(description=...)` to all fields |
| 4 | Module docstrings (30+ modules) | `dcm/`, `api/dicomweb.py`, `api/fhir.py`, etc. | One-paragraph docstrings per module |
| 5 | DATA_DICTIONARY.md | new file | All 12+ tables, columns, types, indexes, FK refs |
| 6 | Migration docstrings | `migrations/versions/*.py` (33 files) | Add Why/Data migration/Rollback/References sections |
| 7 | OpenAPI spec expansion | `backend/static/openapi.json` | Add FHIR, DICOMweb, HL7, OAuth, worklist, routing endpoints |

---

## Sprint 8: DevOps & Production Readiness — ~2 days

| # | Issue | File(s) | Fix |
|---|-------|---------|-----|
| 1 | Dockerfile multi-stage + non-root | `Dockerfile` | Multi-stage build, distroless runtime, non-root user |
| 2 | `.dockerignore` | new file | Exclude tests, docs, .git, __pycache__ |
| 3 | Gunicorn safe worker config | `api_conf.py` | `workers=1` default, `max_requests=10000`, memory limit awareness |
| 4 | Container vulnerability scanning | `.github/workflows/` | Add `trivy` scan step to CI |
| 5 | DB backup script | `scripts/backup_db.sh` | `pg_dump` with timestamp, off-site guidance |
| 6 | docker-compose.prod.yaml | new file | Caddy + backend + frontend, resource limits, restart policies |
| 7 | Log retention/rotation | `api_conf.py` | JSON access log format, rotation policy |
| 8 | Sentry config hardening | `app.py` | Always init Sentry, `traces_sample_rate` from config |

---

## Sprint 9: Polish & Standards — ~1-2 days

| # | Issue | File(s) | Fix |
|---|-------|---------|-----|
| 1 | Type hints modernization | 10+ files | `Optional[X]` → `X | None`, remove `typing.Optional` imports, add return types |
| 2 | `match/case` refactoring | `api/ws.py`, `api/auth.py` | Replace `if/elif` chains with structural pattern matching |
| 3 | `asyncio.ensure_future()` → `create_task()` | `db/tenants.py:62` | Modern asyncio API |
| 4 | Remove deprecation warning filters | `pyproject.toml:6-7` | Pin `python-multipart` to resolve deprecations |
| 5 | `import time` → module-level | `app.py:46`, `api/tracing.py:114` | Move imports to top of file |
| 6 | `ServiceMiddleware` removal | `api/service_middleware.py` | Remove redundant middleware |
| 7 | Manual v2 route aliasing | `api/routes.py` | Decorator-based version marking |
| 8 | Python 3.14 Dockerfile update | `Dockerfile` | `python:3.14-slim` base image |
