# IAM Audit Report — QuantumPACS

## Scope: Application IAM layer — authn (password / OAuth-OIDC / service keys), authz (RBAC + cross-tenant grants), token lifecycle, tenant isolation, audit trail
## Date: 2026-08-12
## Mode: Audit (read-only — no policies or grants were changed during this audit)

### Executive Summary

QuantumPACS's identity layer is in strong shape for a production PACS: RS256 JWTs with kid/JWKS, 1h access tokens, 14d refresh tokens confined to HttpOnly `SameSite=Strict` cookies, a Redis + in-process blocklist that fails open for access validation and fails closed for refresh (with a 60s outage cap), per-user `token_version` revocation, single-flight refresh, per-IP rate limits on login/password/refresh, generic 401s (no user enumeration), PBKDF2-SHA256 (600k iterations), PKCE-protected OAuth/OIDC login with single-use state, hashed API keys that may never out-scope their creator, escalation-proof role/key granting (subset checks), per-tenant DB pools behind a TenantMiddleware that fails closed on unknown/blocked tenants, and an audit log covering login success/failure, password changes, and cross-tenant access (dual-written to main + tenant DB).

Top 3 risks:

1. **No MFA** — the only first-factor is a password (or federated IdP login, which is not MFA-enforced). For a PHI workload this is the largest compliance/security gap (HIPAA §164.312(d); NIST 800-63B AAL2).
2. **Access token readable by XSS** — the frontend persists the 1h access JWT in `localStorage`; the backend *also* sets it as an HttpOnly cookie but the app prefers the header path. The blast radius is capped at 1 hour, and the refresh token never touches storage, but a single XSS yields a live session.
3. **OAuth code-exchange path is unrate-limited** — PKCE + single-use state prevent code replay, but the endpoint itself has no throttle, leaving it exposed to enumeration/abuse of the IdP round-trip.

Two bugs found in this audit's sibling walk were **fixed and live-verified** (F-1 tenants API 403 for cross-tenant readers; F-2 `user_tenant_grants.has()` 500). Everything else is dispositioned below.

Recommended next 90 days: deploy MFA (TOTP or IdP-enforced step-up) for all clinical + admin users; move the frontend onto the HttpOnly cookie channel for access tokens (kill the localStorage header path); add the login bucket to the OAuth callback; assign the `hf` tenant a database or delete its registry row.

### Findings / Recommendations

| ID | Severity | Mode | Category | Issue / Recommendation |
|----|----------|------|----------|------------------------|
| H-1 | High | Audit | Authn | No MFA anywhere; password or federated-login only, for a PHI system |
| H-2 | High | Audit | Authn | Access JWT persisted in `localStorage` → XSS-exfiltratable (1h window) |
| M-1 | Medium | Audit | Authn | OAuth code-exchange login (`/api/oauth/login`) not rate-limited |
| M-2 | Medium | Audit | Authz | Legacy `users.admin` boolean is a parallel super-admin path outside RBAC |
| M-3 | Medium | Audit | Authz | Token may be accepted from a URL query param (referrer/log leakage) |
| M-4 | Medium | Audit | Tenant | `hf` tenant registry row exists but its DB is missing → 500 on cross-tenant use |
| M-5 | Medium | Audit | Authn | Login response returns the access token in the JSON body as well as cookie (proxy-log leakage) |
| M-6 | Medium | Audit | Authz | Frontend trusts `localStorage admin/permissions` for UI gates (UX-only; backend re-enforces — document, don't rely on) |
| L-1 | Low | Audit | Authz | Wildcard `'*'` permission accepted by `has_permission` (legacy super-admin); API keys correctly reject it; verify no production tokens carry it |
| L-2 | Low | Audit | Ops | Dev seed accounts use weak passwords (`Test@123456`); e2e admin password committed in repo config |
| L-3 | Low | Audit | Authn | Login throttle is per-IP only (no per-account lockout); botnet-scale stuffing possible — acknowledged tradeoff |
| F-1 | Fixed | Audit | Authz | `/api/v2/tenants` 403 for `CROSS_TENANT_READ` holders — fixed in `tenants.py:50` (grant-scoped listing) |
| F-2 | Fixed | Audit | Tenant | `user_tenant_grants.has()` 500 (`select('1')` pypika bug) — fixed with `fn.Count(1)` |

### Per-finding detail

#### H-1 — No MFA

- **Where**: `backend/api/users.py:56` `Login.post`, `backend/api/oauth.py:288` `oauth_login` — no second factor anywhere in the authn chain.
- **Description**: EMR/PACS access is a single-factor password or one-shot IdP exchange. No TOTP, no FIDO2, no step-up for admin actions.
- **Remediation**: Lowest friction — TOTP (e.g. `pyotp`) with a `totp_secret` column + recovery codes, enforced for admin and clinical roles; or require IdP MFA at the federation boundary. Optionally restrict admin actions behind a re-auth (`REAUTH` challenge like GitHub).
- **Verification**: Attempt login as a test user with a second factor configured but not supplied → must fail; audit event `auth.mfa_required`.

#### H-2 — Access token in localStorage

- **Where**: `frontend/src/api/session.ts:3-17` (`localStorage access_token`), `frontend/src/api/client.ts:153-156` (`X-Auth-Pacs` header), `backend/api/users.py:135-142` (login already sets HttpOnly `token` cookie, path `/api`).
- **Description**: The 1h access JWT is readable by any XSS. Refresh token is correctly HttpOnly-only. Blast radius = 1 hour, and `X-CSRF-Token` + SameSite=Strict blunt CSRF, but XSS → full session theft.
- **Remediation (preferred)**: Use the existing cookie channel — `fetch` with `credentials: "include"`, delete `access_token` from storage; keep the header path only for non-browser clients. Fallback: keep header but add a strict CSP (`script-src 'self'`) so XSS becomes infeasible.
- **Verification**: After login, DevTools → Application → localStorage contains no `access_token`; a scripted `getItem` returns null; API calls still authenticate via cookie.

#### M-1 — OAuth callback unrate-limited

- **Where**: `backend/api/oauth.py:288` `oauth_login` (only `refresh_bucket` at :452-520 guards a later step; the exchange itself is unthrottled).
- **Description**: PKCE + single-use Redis state prevent code replay, but there is no per-IP throttle on the endpoint itself.
- **Remediation**: `allowed, msg = await login_bucket.check(ip)` at the top of `oauth_login`/callback; reuse `login_bucket` seeded values (50/min, lockout 100/5min).
- **Verification**: Fire 60 rapid requests → 429 after the 50th.

#### M-2 — Legacy `admin` flag bypass

- **Where**: `backend/api/auth.py:44/61` (`can_access_tenant`/`can_mutate_tenant` admin bypass), `backend/api/api_keys.py:27`, `backend/api/users.py:247` (only admins may grant it), `backend/api/roles.py:39/97/103`, `backend/api/telemetry.py:153`, `backend/api/utils.py:10`, `backend/api/reading_presets.py:72`.
- **Description**: `users.admin=true` is a platform-super-admin switch outside the role/permission matrix. Set-only-by-admin is enforced, so no escalation path; DB audit shows exactly 2 admin rows (`admin`, `test.super_admin`) — no creep today. Still: it bypasses permission gates by construction, so a future bug that sets the flag (e.g. a user-edit form) is instant total compromise.
- **Remediation**: Converge on `ADMIN`/`SYSTEM_ADMIN` permission; keep the column only as a derived convenience, or gate it behind the same subset rule as roles.
- **Verification**: `select username from users where admin` — expect the 2 known rows; roles audit `where permissions::text like '%"*"%'` — expect 0 (verified 2026-08-12).

#### M-3 — Token in query string

- **Where**: `backend/api/users.py:34` (`_extract_token` falls back to `request.query_params.get('token')`).
- **Description**: If any caller ever puts a JWT in a URL, it leaks via Referer headers and access logs.
- **Remediation**: Drop the query-param fallback; the share-key path has its own dedicated mechanism.
- **Verification**: Grep callers for `?token=` → none; remove the branch and run the auth test suite.

#### M-4 — `hf` tenant missing database

- **Where**: tenants registry (`tenant_slug='hf'`, status active) vs no `hf` DB in dev postgres → `InvalidCatalogNameError` (500) on any `X-Tenant-ID: hf` request.
- **Description**: Cross-tenant/switch flows hit a 500 instead of a clear "tenant unavailable" 5xx/503. Middleware behavior is correct (fail closed); the row/DB mismatch is a lifecycle gap.
- **Remediation**: Provision the DB (tenant lifecycle tooling) or set the row to `decommissioned`; consider mapping missing-DB to 503 in `TenantConnectionPool.get`.
- **Verification**: `X-Tenant-ID: hf` returns 503/404, never 500.

#### M-5 — Token in login response body

- **Where**: `backend/api/users.py:132-133` (`token`/`access_token` fields) alongside the cookie at :135-142.
- **Description**: Body tokens can be captured by proxy/log aggregation layers; the cookie carries the same credential without that exposure.
- **Remediation**: Emit only the cookie for browser clients; return tokens only when explicitly requested (e.g. `?send_token=1` for native clients).
- **Verification**: `POST /api/login` response contains no `token` field; auth still works via cookie.

#### M-6 — Client-side permission gates

- **Where**: `frontend/src/auth/AuthContext.tsx:99`, `PermissionRoute.tsx:33`, `frontend/src/api/session.ts`.
- **Description**: UI shows/hides features from `localStorage admin/permissions`. All server endpoints re-check via `@requires_permission`, so this is UX-only — but a modified client can call anything a role allows regardless of what the UI hides. Correct posture; keep documented so it is never mistaken for enforcement.

#### L-1 — Wildcard `'*'` permission

- **Where**: `backend/api/rbac.py:40` (`'*' in perms → True`); API keys reject it (`api_keys.py:25`).
- **Description**: Any token/role carrying `'*'` is full super-admin by construction. DB scan (2026-08-12): 0 roles carry it, no admin users beyond the 2 known. Tokens could carry it if a legacy fixture mints one.
- **Remediation**: Keep the guard in `_validate_key_permissions`; remove `'*'` support from `has_permission` in a breaking release and migrate to `ADMIN`.

#### L-2 — Seed/weak credentials

- **Where**: all `test.*` users use `Test@123456`; e2e admin password `bdd76e71d63dacba46fd4bd87e637b3f` ships in code/config.
- **Description**: Dev-seeded real accounts with a known password; e2e credential in the repo.
- **Remediation**: Dev-only seed accounts should be disabled outside dev (`status` → `suspended`); rotate the e2e admin via env var only (already supported: `E2E_ADMIN_PASS`).

#### L-3 — Per-IP-only login lockout

- **Where**: `backend/api/ratelimit.py:174-179` — `login_bucket` keyed by IP; no per-account counter (deliberate anti-user-lockout design).
- **Description**: An attacker with a large IP pool can stuff unaudited volumes; per-account locks create DoS-by-lockout. Mitigated by the audit trail (`auth.login_failed` rows) and lockout at 100/5min/IP.
- **Remediation**: Optional: per-account throttling with exponential backoff that never hard-locks (e.g. `+1s, +4s, +16s…`), or CAPTCHA behind 5 failures.

#### F-1 / F-2 — Fixed during this audit (see disposition)

### Strengths verified (no action)

- RS256 with kid/JWKS (`tokens.py`), `iss/aud/iat/typ/jti` claims, revocation via `token_version`.
- Blocklist: fail-open for access, fail-closed for refresh, 60s outage cap, in-process bounded overlay.
- Token storage: refresh = HttpOnly `SameSite=Strict` `Secure` cookie scoped to `/api/auth`; rotation via single-flight client refresh.
- Login hardening: PBKDF2-SHA256 600k, generic 401 + audit `auth.login_failed`, per-IP rate limit + lockout, `needs_rehash` legacy migration path.
- Authorization: single `has_permission`/`@requires_permission` + route-level `guard_endpoint_method`; permissions aliases (AUDIT_READ⇄LOG_READ, ANALYTICS_READ⇄METRICS_READ) without drift; every HTTPEndpoint class carries a permission guard (161 classes, 161+ decorators).
- Escalation-proofing: role assignment requires target ⊆ caller (`_can_assign_role`), same for API-key permissions, `teleradiologist` platform-admin-only modifiable, immutable built-in slugs.
- Tenant isolation: per-tenant DB pools, `can_access_tenant`/`can_mutate_tenant` admission (home tenant, admin, or grant row + CROSS_TENANT_READ), write-scope grants for mutations, 403-on-unknown-claim fail-closed, blocked/invisible statuses, LRU pool lease release.
- Cross-tenant events audited on main + tenant DB before any data-plane work.
- OAuth: PKCE (S256), single-use state + nonce, issuer/audience pinning, group→role mapping, provider secrets stored encrypted via `db/oauth_providers.py` `get_decrypted`.
- API keys: 96-bit raw key returned once, stored hashed with prefix lookup, expiry, per-key permission subset, no wildcard.
- CORS: explicit origin list from config (`cors_origins`, default `http://localhost:5173`), credentials allowed, static `X-CSRF-Token` header + SameSite=Strict.

### Roadmap

**Now (this sprint)**
1. Rate-limit the OAuth login/callback path (M-1) — ~1h.
2. Document M-6/L-1 in the RBAC docs; grep for `?token=` callers (M-3) and remove the query-param fallback.
3. Resolve the `hf` tenant row vs missing DB (M-4): provision the DB or set `decommissioned`.

**Next 90 days**
4. MFA for admin + clinical roles: TOTP column + recovery codes, enforced at login with `auth.mfa_required` audit event (H-1).
5. Frontend cookie-channel migration: drop `localStorage access_token` (H-2); add CSP (`script-src 'self'`) as defense-in-depth.
6. Converge `users.admin` onto the permission matrix (M-2).

**Next year**
7. Per-account throttling w/ backoff (L-3); wildcard removal release (L-1); rotate seed credentials (L-2); remove token from login response body (M-5).

### Disposition

| ID | Disposition | Notes |
|----|-------------|-------|
| F-1 | **Fixed** | `backend/api/tenants.py:50`, live-verified radiologist + admin regression |
| F-2 | **Fixed** | `backend/db/user_tenant_grants.py:27-28` `fn.Count(1)`, live-verified |
| H-1 | Deferred | Roadmap item 4; requires schema change (migration) |
| H-2 | Deferred | Roadmap item 5; requires frontend transport rework |
| M-1 | Deferred | Roadmap item 1; trivial, batch with next commit |
| M-2 | Deferred | Roadmap item 6; behavior-preserving convergence |
| M-3 | Deferred | Roadmap item 2; verify no callers first |
| M-4 | Deferred | Roadmap item 3; ops decision (provision vs decommission) |
| M-5 | Deferred | Roadmap item 7; needs native-client contract review |
| M-6 | Accepted Risk | UX-only gates, backend enforces; documented |
| L-1 | Accepted Risk | Verified 0 instances in DB; tracked for breaking release |
| L-2 | Accepted Risk | Dev-only; rotation via `E2E_ADMIN_PASS` env support |
| L-3 | Accepted Risk | Deliberate anti-lockout tradeoff; audit-trailed |