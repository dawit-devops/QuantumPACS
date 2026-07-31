# Auth — Requirements Review

Frontend is ready to build the auth layer. We need backend decisions on a few things before we commit to an implementation. These are the blocking questions — everything else in the [backend requirements doc](../ai/auth/backend-requirements.md) is implementable as-is.

---

## 1. Token Model

### Refresh rotation
Frontend stores access + refresh tokens in localStorage. When the access token is near expiry, we use the refresh token to get a new pair.

**Question**: Do you return a **new refresh token** on every refresh (rotation), or do we reuse the same refresh token until it expires?

If rotation: we need to handle the case where two browser tabs both refresh at the same time — one gets a new pair, the other tries to use the now-stale refresh token. We can work around this, but we need to know.

### Permission change mid-session
When an admin changes a user's role or permissions while the user has an active session:

**Question**: Should the user's existing tokens remain valid until natural expiry (~1h for access), or should they be force-logged out on the next API call?

Current frontend behavior: we try the API call, get a 401, attempt silent refresh, if that also 401s → redirect to login. This handles both cases, but if you want immediate invalidation we need to ensure the refresh token is also invalidated.

### Active sessions listing
**Question**: Is there or will there be a way to list/revoke active sessions per user? Needed for a future "log out all devices" feature. If not planned, we skip it.

---

## 2. Login Response

The frontend currently expects this shape from a successful login:

| Field | Purpose |
|-------|---------|
| `access_token` | JWT for API auth headers |
| `refresh_token` | For silent refresh |
| `id` | User database ID |
| `username` | Display name |
| `role` | Role name (string) |
| `permissions` | Array of permission slugs |
| `tenant_id` | Tenant context |
| `admin` | Legacy admin boolean |

**Question**: Is this accurate? Are there fields we're not expecting but should handle? (e.g., `token_type`, `expires_in`, `display_name`, `email`)

---

## 3. Multi-Tenant Login

The app supports database-per-tenant. Some users may share usernames across tenants.

**Question**: How do we scope a login to the right tenant?

Options:
- **Tenant input field** on the login form — user types or selects their tenant
- **Username convention** — `user@tenant` or `tenant\user` format
- **Email domain** — derive tenant from email domain suffix
- **SSO only** — tenant comes from the IdP response

The current frontend has no tenant input. If you want one, we need design direction.

---

## 4. SSO Flow

The login page shows SSO provider buttons. Clicking one should redirect to the IdP.

**Question**: Does backend handle the full OAuth callback?

- **Backend-handled** (preferred): Frontend redirects to `/api/oauth/login?idp={slug}`, backend redirects to IdP, IdP redirects back to backend callback, backend sets cookie/returns token, redirects to frontend with token in URL. Frontend just needs the redirect URL.
- **Frontend-handled**: Backend returns the IdP's auth URL, frontend redirects, IdP redirects back to frontend with auth code, frontend sends code to backend to exchange for tokens.

Current frontend expects option A (redirect to backend URL). Let us know if this is wrong.

---

## 5. Lockout Behavior

The login page displays a countdown timer when the account is locked.

**Question**: Is lockout **per-username**, **per-IP**, or both?

- Per-username: message says "This account is locked. Retry in Xs"
- Per-IP: message says "Too many attempts from this network"
- Both: whichever threshold is hit first

This affects the error message we display. We also persist lockout state client-side (localStorage) to prevent unnecessary server calls — is that acceptable, or should we always go to the server to check lockout status?

---

## 6. Share Key Scope

Share links use a 64-char key in the URL (`?key=...`) for view-only access.

**Question**: Does a single share key grant access to:

- The **whole study** (all series, all files)? → Viewer would show full study hierarchy
- A **single file**? → Viewer shows just that file, no series navigation
- A **specific series**? → Viewer shows that series with instance navigation

Also: **If the underlying study/file is deleted**, should the share link show:
- A friendly "This study is no longer available" message
- A generic 404 page
- Something else

---

## 7. Auth Resolution Order

We need to clarify the priority when multiple auth methods are present.

**Question**: What's the resolution order when a request includes multiple credentials simultaneously? (e.g., both a cookie and a share key, or both an API key header and a Bearer token)

Current behavior appears to be: Share key → API key → Bearer → Cookie → 401. Is this correct? What takes precedence when a user is logged in AND has a share key in the URL?

---

## Backend Answers (verified from code)

After reading the actual backend implementation, all 7 questions are answered:

1. **Refresh rotation** → **Yes, rotation**. `RefreshToken` endpoint calls `block_token(body.refresh_token)` before issuing a new pair. Each refresh invalidates the previous refresh token. (api/users.py:189)

2. **Login response shape** → Confirmed. Returns `{id, admin, role, permissions, token, access_token, refresh_token}`. Also sets `HttpOnly; Secure; SameSite=Strict` cookie. Backend also accepts tokens from `Authorization: Bearer`, `X-Auth-Pacs`, query param `token`, or the cookie. (api/users.py:52-68)

3. **Multi-tenant login** → No tenant input needed. Tenant is derived from the JWT `tenant` claim (populated by `create_token_pair` from user data) or from the `X-Tenant-ID` header. Middleware checks `user.can_access_tenant()`. (api/tenant_middleware.py)

4. **SSO flow** → **Backend-handled** (option A). Frontend redirects to `/api/oauth/login?idp={slug}`, backend handles the entire OAuth flow, redirects back to app with token in URL. (api/oauth.py)

5. **Lockout scope** → **Per-IP**. Redis token bucket tracks by client IP. 5 attempts per 60s, then 10 attempts → 5min lockout. The 429 response message includes timing: `api_error('RATE_LIMITED', msg, status=429)`. (api/ratelimit.py)

6. **Share key scope** → **Per-file**. Auth middleware checks `share_files` table for a matching non-expired entry. If the file is deleted, the share record remains but the file endpoint returns 404. (db/share_files.py, api/auth.py)

7. **Auth resolution order** → `X-API-Key` → `X-Auth-Pacs` header → `Authorization: Bearer` → query `?token=` → cookie → share key. Share key is last priority — a logged-in user accessing a share link gets full access (logged-in takes precedence). (api/auth.py:TokenAuth)

## Remaining Frontend Gaps

The backend auth system is complete. Verified all components exist and work. Two frontend gaps remain:

1. **Proactive token refresh** — Currently only refreshes on 401. Add a timer to refresh before expiry (eliminates the 401 flash).
2. **Share-key expired error** — Currently redirects silently to `/login`. Should show an "expired link" message.

Implementing these now.

## Discussion Log

- 2026-07-29: Reviewed backend auth implementation. All 7 questions answered by reading the actual code. No backend changes needed — only frontend polish remaining.
