# pacs_admin — Backlog (open items from walk)

Session: role-walk/pacs_admin (branch feature/ris-integration, 2026-08-28).
Fixes applied during the walk (R1/R3/R6 grant changes, F2/F3 operational
grants + METRICS_READ, spec updates) are closed and committed — see
[PLAN.md](PLAN.md) findings table. This file tracks items that were **deferred
or decided KEEP with a future option** during the walk. Triage into sprints
per priority.

| ID | Severity | Area | Item | Source | Status |
|----|----------|------|------|--------|--------|
| BL-001 | Medium | Auth / RBAC (iam-audit) | Replace the legacy `user.admin` boolean path: `_is_platform_admin` (backend/api/tenants.py:35-38) and other admin gates use the parallel `user.admin` column instead of an explicit `SYSTEM_ADMIN`-or-`super_admin` role check. Cross-cutting — same item as tenant_admin BL-001. | G7 (tenant_admin + pacs_admin walks) | Open (tracked, already BL-001) |
| BL-002 | Low | Permissions (least-privilege) | pacs_admin cannot assign radiologist or physician roles to users (`_can_assign_role` subset check blocks every clinical reader/EMR writer role). The F2 fix extended pacs_admin's grants to cover the **operational** built-ins (technologist, receptionist, etc.). Adding clinical reader assignment would require granting REPORT_WRITE/SIGN, CROSS_TENANT_READ, PEER_REVIEW_*, etc. — a significant least-privilege tradeoff. | F2 (Phase 5a, user decision: EXTEND operational only) | Open (decision: keep operational-only; revisit if facility needs to assign radiologists) |
| BL-003 | Low | Docs | Spec Matrix A PACSADM column updated with BILLING_READ ✓, REPORT_TEMPLATE_ADMIN ✓, ROLE_* ✓, and the R1 addendum note. The Matrix A PACSADM row still lacks a column for DICOMWEB_READ/HL7_READ/REPLICA_READ/ROUTING_READ (they are EXT/legacy codes not in the canonical 56-permission table). Consider adding a footnote or a separate ops-permissions table. | R2/R4/R5 (UPDATE-DOCS applied) | Open (decision: docs updated; a separate table for ops perms is future work) |

## Definition of done / triage hints

- **BL-001** (highest priority): replace `user.admin` checks with a role-based helper. Already tracked — target IAM-hardening sprint.
- **BL-002**: no action unless a facility explicitly needs to assign radiologist/physician roles via pacs_admin. If so, the F2 subset-extension approach would need to add REPORT_WRITE, REPORT_SIGN, CROSS_TENANT_READ, PEER_REVIEW_READ/WRITE, etc. to MATRIX_A_PACSADM. Revisit with a product decision.
- **BL-003**: nice-to-have spec improvement. The current addendum note is sufficient.