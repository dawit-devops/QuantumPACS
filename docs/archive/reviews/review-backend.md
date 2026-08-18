# Backend Codebase Review — QuantumPACS

- **Reviewer role**: Backend specialist (Python / Starlette / asyncpg / JWT)
- **Skill applied**: `python-backend` (async-first, security by default, fail-fast)
- **Scope**: `backend/` — app wiring, middleware, auth backend, token lifecycle, rate limiting, WS
- **Date**: 2026-08-03
- **Verdict**: Solid production posture. Middleware ordering, secret assertion, tracing, and auth hardening are deliberate and documented. Findings are mostly hardening/compliance items; one migration issue (see DB review) will block `alembic upgrade head`.

---

## 1. Strengths

| Area | Observation |
|---|---|
| App wiring | `lifespan` pattern (Starlette 1.x compatible), service registry, explicit state objects, daemon-thread DICOM server (`lifecycle.py`). |
| Secret handling | `assert_production_secret()` aborts startup on default secret (`app.py:140-143`, `config.py:93`). |
| Auth backend | Token revocation blocklist, cached active-state with bounded `OrderedDict` (5000), token-version invalidation, share-link scope restriction to `/api/files/{id}*` and `/api/ws_token` (`api/auth.py:222`). |
| Security headers | HSTS, CSP `default-src 'self'`, `X-Frame-Options: DENY`, nosniff, referrer policy (`app.py:48-57`). |
| Error paths | CORS headers mirrored on middleware-level error responses — a real browser-blocking bug class this project explicitly fixed (`api/response.py:56-82`). |
| Rate limiting | Redis sliding-window with per-process in-memory fallback for login and API keys; `record_db` audit trail (`api/ratelimit.py`). |
| Observability | Request-ID, tracing pool wrapper (documented Python 3.14 `Pool.acquire` readonly fix), per-route metrics, structured request logging (`app.py:88-95`). |

---

## 2. Findings

### B1 (Medium) — WebSocket handshake path skips blocklist/active/token-version checks
`api/auth.py:251-262`: for `scheme == 'ws'`, the query token is verified and immediately reduced to `{'id', 'admin'}` — `is_blocked`, `_get_cached_active`, and `token_version` are not consulted (they are for HTTP requests at `:233-250`).
- **Scenario**: A revoked or deactivated user's already-open socket stays registered in `ws.py` user/client maps until it closes; the frontend's `ws_token` is 1-minute so new connections can't be minted post-revocation, limiting the window.
- **Recommendation**: Run the same `is_blocked`/active/version checks in the WS branch (they share `verify_token` output), or rely on `WSToken` issuance (which *does* go through the full HTTP auth) and document that the WS branch intentionally trusts the 1-min token.

### B2 (Medium) — CSRF check excludes `PATCH`
`app.py:114`: `if request.method in ('POST', 'PUT', 'DELETE')` — PATCH requests bypass the CSRF sentinel.
- **Scenario**: Currently no PATCH routes exist (verified by search), so this is latent. The first PATCH endpoint added later would silently skip CSRF protection.
- **Recommendation**: Add `PATCH` to the tuple with a comment, or invert: apply to everything not in `_PUBLIC_PATHS` regardless of method.

### B3 (Medium) — CSRF token is a static sentinel (`'1'`)
`app.py:116`: `X-CSRF-Token != '1'` — the value is a constant, so this is a same-origin check, not a per-session token. It works because the refresh-token cookie is `SameSite=Strict` (`app.py:122`), but it adds no defense against same-site subdomain XSS or cookie-less CSRF carriers.
- **Scenario**: Any XSS on the same site can trivially set the header; the guard's value is only "attacker can't read the header from a *different origin*" — which CORS already enforces.
- **Recommendation**: Acceptable for this deployment; document it as an origin check. If the app ever runs on `localhost` + non-https production proxies, add a real per-session CSRF cookie.

### B4 (Medium) — Token revocation/blocklist silently degrades when Redis is down
`api/tokens.py:69-76` (`is_blocked` returns `False` on any error) and `auth.py:233`: with Redis unavailable, revoked JWTs keep working and the in-memory blocklist path does not exist (blocklist is Redis-only).
- **Scenario**: Redis outage during a security incident — revocation stops working entirely, which matters for HIPAA session-termination expectations.
- **Recommendation**: Fail closed for `is_blocked` when Redis was previously available (log + deny), or fall back to a DB-backed blocklist.

### B5 (Low) — In-memory rate-limit fallback is per-process
`api/ratelimit.py:113-114`: without Redis, each worker process has its own `TokenBucket`. N workers = N× the attempt budget per IP.
- **Scenario**: Multi-worker deployment without Redis → login brute-force budget multiplied by worker count.
- **Recommendation**: Document the constraint; consider a DB-backed fallback (a `login_attempts` table already exists for audit).

### B6 (Low) — Auth cache TTL window for deactivation/token-version changes
`api/auth.py:78-90` caches active state for 60 s. A deactivated user keeps a valid session for up to 60 s (plus token TTL if cache persists). Deliberate tradeoff, but worth an explicit ops note for compliance audits.

### B7 (Low) — `create_token` still allows 14-day single-token mode
`api/tokens.py:26-50`: the default `expire={'days': 14}` is used by any caller that passes no expiry. The v2 login path correctly uses `create_token_pair` (1h access + 14d refresh, `api/users.py:66,244`). Audit remaining `create_token` callers to ensure no browser-facing path issues 14-day tokens.

---

## 3. Recommendations (priority order)

1. **B4** — fail-closed revocation (or DB fallback) before relying on Redis for compliance.
2. **B1/B2** — close the WS auth gap and add `PATCH` to the CSRF guard (both cheap, both latent-gap closers).
3. **B7** — grep `create_token(` callers; migrate any long-lived issuance to the pair flow.
4. Document **B5/B6** in the ops guide so deployments without Redis know the real limits.

*Reviewed with skill: `python-backend` — async/security/database pattern references consulted.*
