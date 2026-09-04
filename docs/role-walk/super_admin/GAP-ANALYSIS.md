# super_admin — Gap Analysis (Phase 2)

Date: 2026-08-27
Docs reviewed: ADR-017 (RBAC model), ADR-016 (db-per-tenant), ADR-026 (tenant wiring),
ADR-029 (read isolation), docs/iam-audit.md (2026-08-12), RBAC matrix spec.
Code reviewed: `backend/api/permissions.py`, `backend/api/rbac.py`, `backend/api/auth.py`,
`backend/api/users.py`, `backend/api/oauth.py`, `frontend/src/navigator.ts`,
`frontend/src/common/Sidebar.tsx`, `backend/api/tenants.py`.

## Findings

| # | Surface | Documented (ADR/audit/spec) | Actual (code) | Severity | Evidence | Notes |
|---|---|---|---|---|---|---|
| G1 | Identity model | ADR-017: `admin` boolean is REMOVED, replaced by role+permissions | `users.admin` boolean still exists and is a parallel super-admin path outside the permission matrix | MEDIUM | `users.py:321` set-only-by-admin, `auth.py` can_access_tenant bypass | iam-audit M-2. No escalation today (3 admin rows: admin, test.super_admin, acme.super_admin; 0 wildcard roles). Recommend converging on SYSTEM_ADMIN permission |
| G2 | Role catalog | ADR-017 default roles include `auditor` (logs:read, files:metadata) | `auditor` role not in `permissions.py` BUILT_IN_ROLES | LOW | `permissions.py` role map | Docs drift — role was aspirational; not in RBAC matrix spec §5. Either add or drop from ADR |
| G3 | Authn (platform owner) | iam-audit H-1: no MFA; H-2: access JWT in localStorage; M-5: token in login body | Still open (H-1, H-2); M-5 still returns token in body | HIGH (H-1/H-2) | `users.py` login body, `session.ts` localStorage | Most impactful for the highest-privilege role (super_admin = full platform + all tenants). H-2 XSS → 1h platform-admin session |
| G4 | Authn | iam-audit M-1: OAuth callback unrate-limited | FIXED — `login_bucket.check(ip)` at top of `oauth_login` + callback | VERIFIED-FIXED | `oauth.py:292-296, 346-350` | 429 after bucket threshold |
| G5 | Tenants API | ADR-016/029: platform owner sees all tenants; per-tenant data-plane scoping | `/api/v2/tenants` 500 (Decimal `storage_used_bytes`) FIXED this session; list is grant-scoped | VERIFIED-FIXED | `response.py` `_default()` Decimal, `tenants.py` | Was 500 → now 200 (walk confirmed) |
| G6 | Tenants write path | ADR-016: create tenant provisions a DB (db_name/db_password) | Tenant create stores registry row; dev DB is shared (`quantumpacs`) — no real per-tenant DB provisioning in dev | MEDIUM | `tenants.py` post, `seed_uat.py` ensure_tenant | Production expects db-per-tenant; dev collapses to shared DB. Walk: verify UI create form + registry fields |
| G7 | Platform data-plane scoping | ADR-029: cross-tenant read isolation — a platform user must not leak tenant A data into tenant B reads | TenantMiddleware scopes requests by X-Tenant-ID; platform role with CROSS_TENANT_READ sees granted tenants | VERIFY-IN-WALK | middleware + tenants.py | Critical correctness property for super_admin — verify in browser + API walk |
| G8 | Sidebar gates | Sidebar item gates should match route gates (reuse verbatim) | Verified matching for all admin items (TENANT_READ etc.) | PASS | Sidebar.tsx | No drift found |

Severity: CRITICAL > HIGH > MEDIUM > LOW > PASS/VERIFIED-FIXED/VERIFY-IN-WALK.

## Open from prior audit (not super_admin-specific but highest blast radius for this role)

- H-1 No MFA, H-2 localStorage access token, M-5 token in login body, M-3 query-string token fallback.
