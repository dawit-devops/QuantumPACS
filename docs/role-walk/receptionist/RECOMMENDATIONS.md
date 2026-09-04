# receptionist — Recommendations (Phase 3)
Date: 2026-08-29
Reference: iam-audit (least privilege, role isolation), hipaa-compliance
Skills invoked: iam-audit

| # | Gap | Best-practice principle | Recommended change (layer) | Effort | Priority | User decision |
|---|---|---|---|---|---|---|
| R1 | G1 + G2 — Acquisition + Coordination sections visible to receptionist | Role isolation: a front-office role should not see clinical/coordination surfaces | **REFINE**: hide the Acquisition + Coordination sections for receptionist (role-scoped sidebar filter, same as referring_physician F3). Routes stay deep-linkable. | S | MEDIUM | FIX (approved): hide Acquisition only — Coordination (Orders) stays visible for the registration flow. Sidebar.tsx role filter. |
| R2 | G4 — spec RECEPT row lacks R08 grants | Docs are the contract | **UPDATE-DOCS**: add a note to RBAC_matrix_spec.md Matrix A RECEPT row documenting the R08 front-desk additions (QUEUE_READ, REGISTRATION_READ/WRITE, SCHEDULE_WRITE) | S | LOW | UPDATE-DOCS (approved) |

## Decisions applied
- **R1** (FIX): hide the Acquisition section for receptionist (role-scoped sidebar filter in Sidebar.tsx); Coordination stays visible (Orders used in registration flow). Test added.
- **R2** (UPDATE-DOCS): RBAC_matrix_spec.md Matrix A RECEPT addendum — R08 grants noted.