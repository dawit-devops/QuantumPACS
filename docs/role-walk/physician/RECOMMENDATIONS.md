# physician — Recommendations (Phase 3)
Date: 2026-08-28
Reference: iam-audit (least privilege, role isolation), multi-tenant-saas (tenant scoping), hipaa-compliance (PHI access scoping)
Skills invoked: iam-audit, hipaa-compliance

| # | Gap | Best-practice principle | Recommended change (layer) | Effort | Priority | User decision |
|---|---|---|---|---|---|---|
| R1 | G1 — Front Desk visible to physician | Role isolation: a clinical reader should not surface front-office staff surfaces | **REFINE**: hide the Front Desk + My Records sections from clinical-scoped roles in the sidebar (they hold SCHEDULE_READ/PATIENT_READ but those surfaces are not their workspace). Keep the underlying routes deep-linkable. | S | MEDIUM | REFINE (approved) |
| R2 | G2 — DICOMweb reachable | A granted capability should be reachable (or intentionally closed) | **KEEP (no change)** — recorded user decision 2026-08-27 makes DICOMweb intentionally reachable for clinical roles. Note in spec. | S | LOW | KEEP (approved) |
| R3 | G5 — spec drift (FILE_READ, DICOMWEB_READ on PHYS) | Docs are the contract | **UPDATE-DOCS**: add a note to RBAC_matrix_spec.md Matrix B PHYS row that code adds FILE_READ (Files page, viewer roles) + DICOMWEB_READ (intentional legacy reach) beyond the matrix | S | LOW | UPDATE-DOCS (approved) |

## Decisions applied
- **R1** (REFINE): frontend/src/common/Sidebar.tsx section filter — frontdesk + portal hidden for clinical-scoped roles (isClinicalScopedRole). Test added (Sidebar.test.tsx "hides Front Desk and My Records from a physician"). Routes stay deep-linkable.
- **R2** (KEEP): no change — DICOMweb reachable for clinical roles remains (2026-08-27 decision).
- **R3** (UPDATE-DOCS): spec Matrix B PHYS note for FILE_READ + DICOMWEB_READ.