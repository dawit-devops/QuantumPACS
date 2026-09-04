# pacs_admin — Recommendations (Phase 3)
Date: 2026-08-28
Reference: iam-audit (least privilege, centralized can(), dead grants, privilege creep), multi-tenant-saas (tenant isolation)
Skills invoked: iam-audit, multi-tenant-saas

| # | Gap | Best-practice principle | Recommended change (layer) | Effort | Priority | User decision |
|---|---|---|---|---|---|---|
| R1 | G1 — PACS-ops surfaces unreachable (role named "PACS admin" cannot open DICOMweb console, HL7, Interface Health, Replicas, Routing) | A role's name and grants must match its actual capability; a granted permission must be exercisable | **REDESIGN**: make pacs_admin a real PACS-ops role — add DICOMWEB_READ, DICOMWEB_WRITE, HL7_READ, REPLICA_READ, ROUTING_READ to MATRIX_A_PACSADM so the role can operate the infrastructure it administers (matches spec's STORAGE_ADMIN/INTERFACE_ADMIN intent + PRD persona) | M | HIGH | FIX (approved) |
| R2 | G2 — BILLING_READ granted but spec Matrix A PACSADM = blank | Docs are the contract | **UPDATE-DOCS**: add BILLING_READ ✓ to spec PACSADM column (billing read intended for facility admins — code stays) | S | MEDIUM | UPDATE-DOCS (approved) |
| R3 | G3 — CRITICAL_RESULTS_WRITE dead grant (no reachable surface for admin-scoped pacs_admin) | Least privilege: a grant must be exercisable; remove dead grants | **TRIM CRITICAL_RESULTS_WRITE** from MATRIX_A_PACSADM (unreachable — exam console is clinical-scoped; spec already omits it). No behavior change | S | LOW | FIX (approved) |
| R4 | G4 — REPORT_TEMPLATE_ADMIN in code, blank in spec | Docs are the contract | **UPDATE-DOCS**: add REPORT_TEMPLATE_ADMIN ✓ to spec Matrix A PACSADM (grant is live + intentional — /admin/report-templates, matches tenant_admin O1/R3) | S | LOW | UPDATE-DOCS (approved) |
| R5 | G5 — ROLE_READ/WRITE/DELETE in code (R2-16), absent from spec | Docs are the contract | **UPDATE-DOCS**: add ROLE_READ/WRITE/DELETE to spec Matrix A PACSADM row with R2-16 note ("facility admins manage roles of clinical/operational built-ins") | S | LOW | UPDATE-DOCS (approved) |
| R6 | G6 — WORKLIST_WRITE dead grant (no reachable surface) | Least privilege: a grant must be exercisable | **TRIM WORKLIST_WRITE** from MATRIX_A_PACSADM (no reachable surface — MWL is clinical-scoped). Keep the read grants (REPORT_READ→RIS Dashboard, SCHEDULE_READ→Staff Schedule) | S | LOW | FIX (approved) |
| R7 | G7 — `_is_platform_admin` legacy `user.admin` | iam-audit M-2: remove parallel super-admin path | **DEFER** — already tracked as BL-001 in tenant_admin backlog (cross-cutting IAM-hardening item) | M | MEDIUM | DEFER (already backlogged) |

## Decisions applied
- **R1** (FIX, HIGH): MATRIX_A_PACSADM += DICOMWEB_READ, DICOMWEB_WRITE, HL7_READ, REPLICA_READ, ROUTING_READ.
- **R2** (UPDATE-DOCS): spec Matrix A PACSADM BILLING_READ → ✓.
- **R3** (FIX): MATRIX_A_PACSADM −= CRITICAL_RESULTS_WRITE.
- **R4** (UPDATE-DOCS): spec Matrix A PACSADM REPORT_TEMPLATE_ADMIN → ✓.
- **R5** (UPDATE-DOCS): spec Matrix A + ROLE_READ/WRITE/DELETE row, PACSADM ✓ (R2-16).
- **R6** (FIX): MATRIX_A_PACSADM −= WORKLIST_WRITE.
- **R7** (DEFER): tracked as BL-001 (tenant_admin backlog).

## Skills invoked
iam-audit (R1 dead/unexercisable grants, R2 least privilege, R3 dead grants, R7 legacy flag), multi-tenant-saas (R1 tenant scoping intact).