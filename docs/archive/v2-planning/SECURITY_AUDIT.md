> **Last Verified:** 2026-07-30  
> **Findings Status:** 18 Critical, 29 High, 48 Medium, 19 Low (see `.full-review/05-final-report.md`)  
> **Remediation:** Sprint 1 complete (7 critical security fixes merged), Sprints 2-9 in progress

# QuantumPACS Security Audit

**Date:** 2026-07-23
**Scope:** Starlette backend (`backend/app.py`, `backend/api/auth.py`, `backend/api/routes.py`)
**Methodology:** Static code review against FastAPI/Starlette security best practices

---

## Findings Summary

| ID | Finding | Severity | Status |
|----|---------|----------|--------|
| S-01 | CORS wide-open (`Access-Control-Allow-Origin: *`) | **Critical** | Open |
| S-02 | Custom `X-Auth-Pacs` header instead of standard `Authorization: Bearer` | Low | Open |
| S-03 | No rate limiting on `/api/login` | **High** | Open |
| S-04 | No TrustedHost middleware | Medium | Open |
| S-05 | No HTTPS enforcement at app level (delegated to Caddy) | Low | Accept |
| S-06 | Share link auth bypass exposes viewer without credentials | Medium | Open |
| S-07 | Hardcoded default secrets in config | **High** | Open |
| S-08 | Error responses may leak stack traces | Medium | Open |
| S-09 | No Content Security Policy headers | Medium | Open |
| S-10 | `DELETE /api/files/{id}` has no CSRF protection | Low | Open |

---

## Detailed Findings

### S-01: CORS Wide-Open (Critical)

**Current state:**
```python
# backend/app.py — CustomMiddleware
response.headers['Access-Control-Allow-Origin'] = '*'
response.headers['Access-Control-Allow-Methods'] = '*'
response.headers['Access-Control-Allow-Headers'] = '*'
```

**Risk:** Any website visited by an authenticated user can make cross-origin requests to the API. While the custom `X-Auth-Pacs` header isn't automatically sent by browsers on cross-origin requests (mitigating simple CSRF), credentialed requests with `?token=` in query params could be exploited.

**Additionally:** The `AuthenticationMiddleware.on_error` handler (`api/auth.py:85-86`) returns 401 responses that bypass `CustomMiddleware`, meaning CORS headers are missing on auth error responses. This causes browser console errors for legitimate cross-origin flows (observed in E2E testing on `/api/ws_token`).

**Recommendation:**
1. Replace `*` with a configurable whitelist: `config['cors_origins']` with env var `CORS_ORIGINS`
2. Add CORS headers to the error response in `api/auth.py`:
   ```python
   async def on_auth_error(self, conn, exc):
       resp = unauthorized(str(exc))
       resp.headers['Access-Control-Allow-Origin'] = config.get('cors_origins', '*')
       return resp
   ```
3. For production, set `CORS_ORIGINS=https://pacs.hospital.org`

### S-02: Custom Auth Header (Low)

**Current state:**
```python
# api/auth.py — reads X-Auth-Pacs header
auth_header = request.headers.get('X-Auth-Pacs')
```

**Risk:** Non-standard header may cause issues with API gateways, proxies, and client libraries that expect `Authorization: Bearer <token>`.

**Recommendation:** Support both `Authorization: Bearer` and `X-Auth-Pacs` for backward compatibility. Prefer the standard header in documentation.

### S-03: No Rate Limiting on Login (High)

**Current state:** `/api/login` has no rate limiting. An attacker can attempt unlimited password guesses.

**Risk:** Brute-force password attack. While PBKDF2 with 600k iterations slows attacks (~10 guesses/sec), a distributed attack could still succeed against weak passwords over hours/days.

**Recommendation:**
1. Add token-bucket rate limiting middleware: 5 attempts per IP per minute on `/api/login`
2. Implement account lockout after 10 failed attempts (temporary, 5-minute cooldown)
3. Log all failed login attempts with IP and timestamp

### S-04: No TrustedHost Middleware (Medium)

**Current state:** No `TrustedHostMiddleware` is configured.

**Risk:** Host header injection attacks. An attacker could craft a request with a malicious `Host` header, potentially poisoning cache, password reset links, or bypassing security checks.

**Recommendation:**
```python
from starlette.middleware.trustedhost import TrustedHostMiddleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=config.get('allowed_hosts', ['localhost', '127.0.0.1']))
```

### S-05: HTTPS Enforcement at Caddy Level (Low — Accept)

**Current state:** HTTPS is terminated by Caddy (reverse proxy), not enforced by the Starlette app.

**Risk:** If Caddy is misconfigured or bypassed, traffic to the Starlette app (port 8080) is unencrypted.

**Recommendation:** Document that port 8080 MUST NOT be exposed directly; only port 80 (Caddy) should be public. Add a note in deployment docs. Consider adding `HTTPSRedirectMiddleware` for defense-in-depth.

### S-06: Share Link Auth Bypass (Medium)

**Current state:** The `tempKey` mechanism allows users to view studies without authentication. A valid share key (64-char hex) is stored in localStorage and used as auth credential.

**Risk:** If a share link is intercepted (email, SMS, chat), anyone with the link can view the study until it expires. The key is sent as a URL query parameter, which may be logged by proxies/servers.

**Recommendation:**
1. Document that share links should be sent over secure channels only
2. Add optional PIN code protection for sensitive studies
3. Implement access logging for shared link views
4. Recommend short expiry durations (hours, not days) by default

### S-07: Hardcoded Default Secrets (High)

**Current state:**
```python
# backend/config.py
default_config = {
    'secret': 'default',       # Falls back to db_password
    'superadmin_pass': 'pa55w0rd',
    'db_password': 'pa55w0rd',
}
```

**Risk:** Default credentials are well-known. Deployments that don't override `secret` and `db_password` are trivially compromised.

**Recommendation:**
1. Require `SECRET` env var at startup — fail fast if still default
2. Generate random `superadmin_pass` on first deploy (like `./manage db init` does)
3. Add startup check: if `secret == 'default'`, log a CRITICAL warning and refuse to start in production mode

### S-08: Error Responses May Leak Internals (Medium)

**Current state:** Error handling varies by endpoint. Some errors use `server_error(str(exc))` which may include exception messages with internal paths or SQL queries.

**Recommendation:** Ensure `server_error()` returns a generic message in production. Log the full error server-side only:
```python
def server_error(detail=None):
    log.error(f"Server error: {detail}")
    return JSONResponse({'error': 'Internal server error'}, status_code=500)
```

### S-09: No Content Security Policy (Medium)

**Current state:** No CSP headers are set by the application or Caddy.

**Risk:** XSS attacks could execute arbitrary scripts in the viewer context. Cornerstone3D loads DICOM pixel data which could theoretically be crafted maliciously.

**Recommendation:** Add CSP header in Caddy:
```
header {
    Content-Security-Policy "default-src 'self'; img-src 'self' data: blob:; script-src 'self' 'unsafe-eval'; style-src 'self' 'unsafe-inline'"
}
```

### S-10: DELETE /api/files/{id} No CSRF Protection (Low)

**Current state:** The `DELETE /api/files/{id}` endpoint requires the `X-Auth-Pacs` header. Admin users can delete files.

**Risk:** Since the auth header is custom (not auto-sent by browsers), CSRF is inherently mitigated. However, if the API were accessed with standard `Authorization: Bearer`, CSRF protection would be needed.

**Recommendation:** Accept current state due to custom header protection. If standardizing headers, add CSRF tokens or SameSite cookie checks.

---

## Security Checklist

- [x] All sensitive routes require authentication (verified in `api/routes.py`)
- [x] No sensitive data in URL paths (file IDs are sequential integers — acceptable for internal)
- [x] Passwords hashed with PBKDF2-HMAC-SHA256, 600k iterations
- [x] JWT tokens have expiry (14-day default)
- [x] Deactivated users rejected even with valid JWT (`Users.is_active()` check)
- [x] Path traversal prevented in LocalStorage (`basename(normpath())`)
- [x] SQL injection prevented (parameterized queries via asyncpg + PyPika)
- [x] DICOM files parsed with `stop_before_pixels=True` (no pixel data in memory)

- [ ] CORS origin whitelist configured
- [ ] Rate limiting on login endpoint
- [ ] TrustedHost middleware configured
- [ ] HTTPS enforced (Caddy only — document)
- [ ] CSP headers set
- [ ] Default secrets changed
- [ ] Audit logging for read access (currently write-only)
- [ ] Backup encryption documented

---

## Recommendations Priority

### Immediate (v2.1 — next release)
1. CORS origin whitelist (configurable, default lock to same-origin)
2. Rate limiting on `/api/login` (5 attempts/min per IP, 10 total → 5min lockout)
3. Startup check for default secrets — fail loudly in production
4. Add CORS headers to auth error responses

### Short-term (v2.1 — before production deploy)
5. TrustedHost middleware with configurable allowed hosts
6. CSP headers in Caddy configuration
7. Generic error responses in production mode
8. Read-access audit logging

### Long-term (v2.2)
9. Support `Authorization: Bearer` alongside `X-Auth-Pacs`
10. PIN-protected share links
11. Automated dependency vulnerability scanning in CI (`pip-audit`, `npm audit`)
