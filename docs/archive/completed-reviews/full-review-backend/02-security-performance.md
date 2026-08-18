# Phase 2: Security & Performance Review

## Security Findings

| Severity | Count | Key Areas |
|----------|-------|-----------|
| **Critical (P0)** | 6 | Hardcoded secrets, SQL injection (OAuth + FHIR), missing auth on file endpoints, dependency CVEs, encryption silent plaintext fallback |
| **High (P1)** | 8 | Missing security headers, timing attack in password verify, no rate limiting on API keys, unauthenticated Redis, SSRF in webhooks, MLLP IP allowlist broken, no CSRF, IDOR in file access |
| **Medium (P2)** | 9 | Cookie secure flag, OAuth HTTP redirect, WebSocket token in query string, exception info leak, silent exception swallows, API key prefix leak, input validation, OIDC JWKS missing, rate limit key scope |
| **Low (P3)** | 5 | DICOM/MLLP all-interfaces bind, Prometheus metrics, /tmp file permissions, CORS fallback |
| **Total** | **28** | |

### Critical Security Issues
1. **CRIT-01**: Hardcoded default secrets in `config.py` (db_password=`pa55w0rd`, secret, superadmin_pass=`pa55w0rd`)
2. **CRIT-02**: SQL injection via f-string in `api/oauth.py:144` — `f"SELECT id FROM roles WHERE slug = '{role_slug}'"`
3. **CRIT-03**: SQL injection via `_quote()` string escaping in `api/fhir.py` — `PseudoColumn` with interpolated user input
4. **CRIT-04**: Missing `@requires_permission()` on `FilesHandler.get/post` and `FileHandler.get` in `api/files.py`
5. **CRIT-05**: Wide dependency version ranges (`starlette>=1.0.1,<2.0`, `cryptography>=41.0,<50.0`) may include vulnerable versions
6. **CRIT-06**: `encrypt_secret()`/`decrypt_secret()` return plaintext silently when Fernet init fails (`api/encryption.py`)

## Performance Findings

| Severity | Count | Key Areas |
|----------|-------|-----------|
| **Critical** | 6 | Synchronous file I/O blocking event loop, unbounded in-memory caches (auth + ratelimit), WADO-RS builds full response in memory, 6 separate Redis connections, per-request connection churn, global state prevents horizontal scaling |
| **High** | 8 | Missing DB indexes (sop/study/series UIDs), routing rules uncached, per-message Redis connections in WS, fire-and-forget tasks, serial health checks, startup retry no backoff, DICOM event loop saturation, master replica lookup uncached |
| **Medium** | 7 | Dashboard multi-query, C-FIND pagination, tenant pool sizing, SHA-256 recomputation, `_init_locks` leak, legacy metrics overflow, PgNotifyBridge busy-wait |
| **Low** | 3 | ES silent fail, Pool conn timeout, legacy metrics |
| **Total** | **24** | |

### Critical Performance Issues
1. Synchronous `open()`/`read()` in all async handlers: WADO-RS, thumbnails, ZIP download, CSV export
2. WADO-RS study retrieval builds entire multipart response in memory via `b''.join(body_parts)` — potential OOM for large studies
3. `_active_cache` in `api/auth.py` grows monotonically — no eviction
4. `TokenBucket._attempts` defaultdict never prunes dormant IPs
5. 6 separate Redis TCP connections (general, blocklist, auth cache, ratelimit, pubsub, lifecycle)
6. Module-level global state prevents running >1 uvicorn worker

## Critical Issues for Phase 3 Context

- **Security-critical code paths are untested**: OAuth flows, FHIR parameterization, file permission checks, encryption fallback, CSRF
- **Performance benchmarks needed**: WADO-RS streaming, pool sizing under load, cache eviction behavior
- **Global state makes test isolation difficult**: Module-level globals shared across tests, need fixture cleanup
- **No test coverage for**: `api/encryption.py`, `api/oauth.py`, `api/fhir.py`, `db/api_keys.py`, `dcm/server.py`
