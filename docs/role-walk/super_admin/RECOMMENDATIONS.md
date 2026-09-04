# super_admin — Best-Practice Recommendations (Phase 3)

Date: 2026-08-27
Skills referenced: iam-audit (Mode 1 — application authorization, Mode 2 — design),
multi-tenant-saas (tenant isolation patterns)

## Recommendations

| # | Gap | Best-practice principle | Recommended change (layer) | Effort | Priority | User decision |
|---|---|---|---|---|---|---|
| G1 | `users.admin` boolean is a parallel super-admin path outside the permission matrix | iam-audit M-2: permission checks centralized, not scattered `if admin` checks. IAM Design: "Admin is not one role." | Backend: remove `users.admin` setter, migrate to `SYSTEM_ADMIN` permission; frontend: remove admin flag UI | Medium | MEDIUM | DEFER (2026-08-27, IAM-hardening sprint) |
| G2 | `auditor` role documented in ADR-017 but missing from `permissions.py` BUILT_IN_ROLES | iam-audit: role definitions written down match code. Docs drift is a finding. | Docs: update ADR-017 to remove `auditor` (aspirational; not in RBAC spec) | Small | LOW | UPDATE-ADR (2026-08-27) — done in `(commit)` |
| G3 | No MFA (H-1), access JWT in localStorage (H-2), token in login body (M-5) | iam-audit: MFA enforced for 100% of users; phishing-resistant MFA for admins. OWASP: never store tokens in localStorage (XSS) | Backend: add TOTP enrollment + verify; frontend: HttpOnly cookie for token; POST body token → auth header | Large | HIGH | DEFER (2026-08-27, dedicated sprint) |
| G4 | OAuth callback unrate-limited | iam-audit: rate limiting on all auth entry points | FIXED — `login_bucket.check(ip)` in `oauth_login` + callback | — | — | VERIFIED-FIXED |
| G5 | Tenants API 500 on Decimal | — | FIXED — `response.py` `_default()` handles Decimal | — | — | VERIFIED-FIXED |
| G6 | Tenant create doesn't provision a real per-tenant DB in dev | multi-tenant-saas: database-per-tenant is the strongest isolation. Dev should self-heal the DB on create. | Backend: `tenants.py` POST should attempt `CREATE DATABASE` + migrate (graceful fallback in dev) | Medium | MEDIUM | DEFER (2026-08-27, tenants walk) |
| G7 | Cross-tenant read isolation | ADR-029: platform user must not leak tenant A data into tenant B reads | VERIFIED during walk: staff-schedule leak → FIXED (D90B911); other data-plane calls scoped | — | — | VERIFIED-FIXED |
| G8 | Sidebar gate parity | Sidebar item gates must match route gates verbatim | VERIFIED: all admin sidebar items match their route gates. No drift. | — | — | PASS |

## Open items requiring user decision

1. **G1**: Converge `users.admin` → `SYSTEM_ADMIN`. This removes a bypass path outside the permission matrix. Impact: backend changes to `users.py`, `auth.py`; frontend removes the admin-flag toggle.
2. **G2**: Update ADR-017 to remove `auditor` (or add the role). The role was aspirational and not in the RBAC spec — simplest fix is to update the ADR.
3. **G3**: MFA + token hardening. Highest blast radius for super_admin (full platform access). Three sub-items: (H-1) TOTP enrollment at login, (H-2) HttpOnly cookie for the access token, (M-5) stop returning the token in the login body. Large effort — needs a dedicated sprint.
4. **G6**: Real per-tenant DB provisioning in dev. The shared dev database means tenant storage/quota stats are identical for acme+default. Production expects database-per-tenant (ADR-016). Dev should self-heal with `CREATE DATABASE IF NOT EXISTS` on tenant create.