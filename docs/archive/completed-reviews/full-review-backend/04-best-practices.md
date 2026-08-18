# Phase 4: Best Practices & Standards

## Framework & Language Findings

| Severity | Count | Key Areas |
|----------|-------|-----------|
| **Critical** | 5 | Dockerfile vs requirements.txt version drift, sync file I/O in async WADO handlers, `sys.exit(1)` in lifespan, default secrets shipped in source |
| **High** | 4 | CORS set in 4+ locations, `object.__setattr__` workaround (Python 3.14), 5+ separate Redis connections, module-level `work = True` shutdown flag |
| **Medium** | 10 | Mixed `Optional[X]` vs `X | None` types, deprecation warnings hidden, missing return type annotations, Dockerfile Python 3.11 vs dev 3.14, `asyncio.ensure_future()`, broad `except Exception`, `import time` in request handlers, `cpu_count()` workers too aggressive, service layer bypassed |
| **Low** | 5 | Redundant ServiceMiddleware, manual v2 route aliasing, no `match/case`, hardcoded `venv/` path |
| **Total** | **24** | |

### Critical Issues
1. **Dockerfile vs requirements.txt drift**: Different version ranges for elasticsearch (9 vs 8), starlette (1.x vs 0.35.x), and others — Dockerfile installs separately from pip requirements
2. **Sync `open()` in async WADO handlers** (`api/dicomweb.py:250,295`) — blocks event loop on every file read
3. **`sys.exit(1)` in lifespan** (`config.py:94`) — `assert_production_secret()` calls `sys.exit()` inside async context
4. **Default secrets shipped in source** (`config.py:7-8`) — hardcoded `pa55w0rd` defaults
5. **Service layer bypassed** — all endpoints directly instantiate table objects instead of using registered services

## CI/CD & DevOps Findings

| Severity | Count | Key Areas |
|----------|-------|-----------|
| **Critical** | 4 | No CI/CD pipeline at all, module-level globals prevent multi-worker Gunicorn, no production deployment script, no secret management |
| **High** | 6 | Stale Dockerfile (no multi-stage, root user), missing .dockerignore, gunicorn workers=CPU count, no vulnerability scanning, no DB backup/DR plan, no IaC beyond docker-compose |
| **Medium** | 5 | Pre-commit hook uses `venv/bin/python` hardcoded, Caddy bundled in backend container, OTel fallback to console, duplicate docker-compose files, Sentry gated on DSN truthiness |
| **Low** | 4 | No Makefile, no Playwright config, no log retention/rotation, health endpoint leaks component error details |
| **Total** | **19** | |

### Critical Issues
1. **Zero CI/CD automation** — no `.github/`, `.gitlab-ci.yml`, or any CI config. Builds, tests, deploys are entirely manual.
2. **Module-level globals prevent scaling** — Gunicorn workers >1 breaks DICOM SCP, MLLP, Redis consumers, PG notify bridge (port conflicts, duplicate processing)
3. **No production deployment script** — no container registry target, no rollback plan, no health gate
4. **No secrets management** — production secrets in YAML/env vars, no Vault/k8s Secrets integration
