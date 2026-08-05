# Feature: Authentication & Authorization

## Requirements (EARS Format)

While a user is unauthenticated, when they visit any protected route, the system shall redirect them to `/login`.
While a user is on the login page, when they submit valid credentials, the system shall authenticate them and redirect to the home page.
While a user is authenticated, when their access token expires, the system shall silently refresh it using the refresh token.
While a user is authenticated, when their refresh token also expires, the system shall redirect them to `/login`.
While a user has a valid share key in the URL, when they access the associated study, the system shall render the viewer in read-only mode.
While a user submits incorrect credentials repeatedly, the system shall rate-limit and display a lockout countdown.
While a user is on the login page with SSO providers configured, when they click a provider button, the system shall redirect to that identity provider.

## Architecture

### [Backend] — Existing (no changes needed)

The backend auth system is complete. Verified by reading the implementation:

| Component | Status | File |
|-----------|--------|------|
| Login endpoint (`POST /api/login`) | ✅ | `api/users.py:Login` |
| Token pair creation (access 1h + refresh 14d) | ✅ | `api/tokens.py:create_token_pair` |
| Token refresh with rotation (`POST /api/auth/refresh`) | ✅ | `api/users.py:RefreshToken` |
| Token blocklist via Redis (jti-keyed) | ✅ | `api/tokens.py:block_token / is_blocked` |
| Logout (`POST /api/auth/logout`) | ✅ | `api/users.py:Logout` |
| Auth middleware (API Key → Bearer → cookie → share key) | ✅ | `api/auth.py:TokenAuth` |
| Rate limiting (5/60s per IP, 10 → 5min lockout) | ✅ | `api/ratelimit.py` |
| OAuth/SSO with PKCE + JWKS | ✅ | `api/oauth.py` |
| Token version for forced logout on role change | ✅ | `db/users.py:get_token_version` |
| Share-key auth via `share_files` table | ✅ | `api/auth.py` fallback |
| Multi-tenant via `X-Tenant-ID` or JWT claim | ✅ | `api/tenant_middleware.py` |
| RBAC with `@requires_permission()` | ✅ | `api/rbac.py` |

**Login response shape** (confirmed):
```json
{
  "id": "uuid",
  "admin": false,
  "role": "radiologist",
  "permissions": ["FILE_READ", "PATIENT_READ", ...],
  "token": "<jwt>",
  "access_token": "<jwt>",
  "refresh_token": "<jwt>"
}
```
Also sets `Set-Cookie: token=<jwt>; HttpOnly; Secure; SameSite=Strict; Path=/api`.

**Refresh response shape**:
```json
{
  "access_token": "<jwt>",
  "refresh_token": "<jwt>",
  "expires_in": 3600,
  "token_type": "Bearer"
}
```

### [Frontend] — Changes needed

The frontend has the core auth infrastructure but has gaps in session management UX:

| Component | Status | File |
|-----------|--------|------|
| AuthContext (user state, signIn/signOut, hasPermission) | ✅ | `auth/AuthContext.tsx` |
| ProtectedRoute (redirect to /login) | ✅ | `auth/ProtectedRoute.tsx` |
| Login page (username/password + SSO) | ✅ | `login/Login.tsx` |
| Token storage + auto-refresh on 401 | ✅ | `helpers.ts:request()` |
| Share-key URL param handling | ✅ | `index.tsx` reads `?key=` |

**Gaps to fill:**

1. **Proactive token refresh** — Currently only refreshes on 401. Should schedule refresh before expiry (e.g., 5min before).
2. **Lockout UX** — Server returns 429 with `RATE_LIMITED`, but the login page treats it as a generic form error. Should show a countdown timer.
3. **Share-key UX** — Expired/invalid keys show no friendly message. Need an error page or inline message.
4. **Logout** — Should call `POST /api/auth/logout` to block the token server-side (currently just clears localStorage).
5. **Login page tenant context** — If multi-tenant, consider showing the tenant name after login.

### [Security]

| Check | Status | Detail |
|-------|--------|--------|
| Auth required on protected endpoints | ✅ | `@requires_permission()` decorator + middleware |
| Authz checks (ownership/role) | ✅ | `TokenAuth.authenticate()` checks user active + token_version |
| Input validation | ✅ | Pydantic schemas on all auth endpoints |
| Sensitive data excluded from responses | ✅ | Login response has no password/token leakage |
| Rate limiting on login | ✅ | Redis token bucket (5/60s per IP) |
| Security event logging | ✅ | `login_attempts` table + audit logging |
| CSRF protection | ✅ | `SameSite=Strict` + `HttpOnly` cookie |
| XSS protection | ✅ | No user input rendered in auth flows |
| Brute force mitigation | ✅ | Exponential backoff rate limiter |
| Output encoding | ✅ | JSON responses, no HTML rendering |

## Implementation Plan

### Phase 1: Frontend Session Management (3 changes)

- [x] **1a**: Add proactive token refresh timer in AuthContext
- [x] **1b**: Update Login page to handle 429 rate-limit with countdown
- [x] **1c**: Update logout to call `POST /api/auth/logout`

### Phase 2: Share-Key Error UX (1 change)

- [x] **2a**: Add share-key error handling in index.tsx or a dedicated component

### Phase 3: Verify & Cleanup

- [x] **3a**: Run `tsc --noEmit` and `vite build`
- [x] **3b**: Update the discussion doc with answers found in backend code
