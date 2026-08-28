# tenant_admin — Recommendations (Phase 3)
Date: 2026-08-28
Reference: iam-audit (least privilege, centralized can(), legacy flag), multi-tenant-saas (tenant isolation)

| # | Gap | Best-practice principle | Recommended change (layer) | Effort | Priority | User decision |
|---|---|---|---|---|---|---|
| R1 | G1 docs drift (ADR "all actions") | Docs are the contract | UPDATE-DOCS: ADR-017 tenant_admin row → "tenant-scoped admin: users/roles/service keys, billing read, interfaces, storage, templates, read-only clinical" (Matrix C has no clinical writes / SYSTEM_ADMIN) | S | LOW | UPDATE-DOCS (approved) |
| R2 | G4 `_is_platform_admin` uses `user.admin` boolean | iam-audit: remove parallel super-admin path; use RBAC role check | REDESIGN (defer): replace `user.admin` with an explicit `SYSTEM_ADMIN`-or-`super_admin` role check in tenants.py + other admin gates | M | MEDIUM | DEFER (approved — tracked as open item) |
| R3 | G6 REPORT_TEMPLATE_ADMIN unreachable | Centralized can(); a granted permission must be exercisable | FIX: frontend sidebar + route gate for `/admin/report-templates` accept `["REPORT_WRITE", "REPORT_TEMPLATE_ADMIN"]` (mirror the backend gate) | S | MEDIUM | FIX (approved — applied) |
| R4 | G2/G3 tenant provisioning + scoping | Multi-tenant isolation | KEEP (no change): verified PASS — only platform admin provisions; _owns_tenant scopes reads/updates | — | — | KEEP |
| R5 | G5 credential leak | Least privilege | KEEP (no change): verified FIXED (66085fe) | — | — | KEEP |

## Skills invoked
iam-audit (R2 — legacy admin flag; R3 — centralized can()), multi-tenant-saas (R4 — tenant isolation).