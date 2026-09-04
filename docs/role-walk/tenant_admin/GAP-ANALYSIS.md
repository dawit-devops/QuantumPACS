# tenant_admin — Gap Analysis (Phase 2)
Date: 2026-08-28
Sources: ADR-017, iam-audit, permissions.py, api/tenants.py

## Gaps

| # | Surface | Documented (ADR/spec) | Actual (code) | Severity | Evidence (file:line) | Notes |
|---|---|---|---|---|---|---|
| G1 | Tenant-scoped authority | ADR-017 §Role table: "All resources within tenant: all actions" | No REPORT_WRITE, SCHEDULE_READ, EXAM_READ, etc. — cannot do "all actions" within tenant | LOW | permissions.py:349-363 | Docs drift: Matrix C intentionally limits tenant_admin (no clinical writes, no SYSTEM_ADMIN). The ADR description is aspirational, not literal. |
| G2 | Tenant provisioning | ADR-017: tenant_admin cannot provision tenants | POST /tenants gated on _is_platform_admin (user.admin) → tenant_admin (admin=false) blocked | PASS | api/tenants.py:141-146 | Correctly scoped: only platform-level user (super_admin) can provision. |
| G3 | Tenant create/update scoping | ADR-016: tenant_bound admin cannot access other tenants | PUT /tenants/{id} checks _owns_tenant(user, slug) | PASS | api/tenants.py:187-191 | Scoped correctly. |
| G4 | `_is_platform_admin` relies on `user.admin` boolean | iam-audit M-2: legacy `users.admin` is a parallel super-admin path outside RBAC | `_is_platform_admin` checks `user.admin` flag, not role | MEDIUM | api/tenants.py:35-38, iam-audit.md | Legacy bypass: `user.admin` is a boolean column, not an RBAC permission. tenant_admin has admin=false so it's correctly scoped, but the pattern is fragile. |
| G5 | Tenant list DB credential leak | iam-audit F-1 + radiologist walk fix | `_is_platform_admin` check strips db_* fields for non-platform users | PASS | api/tenants.py:135 | Fixed in 66085fe. tenant_admin (admin=false) does not see db_* fields. |
| G6 | No REPORT_TEMPLATE_ADMIN route | tenant_admin has REPORT_TEMPLATE_ADMIN but sidebar gates on REPORT_WRITE | Sidebar hides Report Templates (/admin/report-templates gates on REPORT_WRITE, not REPORT_TEMPLATE_ADMIN) | LOW | Sidebar.tsx:460 | sidebar gate mismatch: REPORT_TEMPLATE_ADMIN is the correct permission for template management, but the sidebar item checks REPORT_WRITE. Route gate may also mismatch. |

## Skills invoked
iam-audit (G4 — legacy admin flag), multi-tenant-saas (G3 — tenant scoping).