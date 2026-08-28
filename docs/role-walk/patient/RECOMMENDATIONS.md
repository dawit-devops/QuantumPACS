# patient — Recommendations (Phase 3)
Date: 2026-08-29
Reference: hipaa-compliance (own-data access), iam-audit (role isolation)
Skills invoked: hipaa-compliance, iam-audit

| # | Gap | Best-practice principle | Recommended change (layer) | Effort | Priority | User decision |
|---|---|---|---|---|---|---|
| R1 | G1 + G2 — Acquisition + Front Desk sections visible to patient | Role isolation: a patient should only see their own portal surfaces | **REFINE**: hide the Acquisition + Front Desk sections for patient (role-scoped sidebar filter, same pattern as referring_physician F3 / receptionist R1). Routes stay deep-linkable. | S | MEDIUM | FIX (approved) |
| R2 | G3 — spec Matrix C PATIENT lacks FOLLOW_UP_SELF/NOTIFICATIONS_SELF | Docs are the contract | **UPDATE-DOCS**: add a note to RBAC_matrix_spec.md Matrix C PATIENT row documenting the self-scoped grants (FOLLOW_UP_SELF, NOTIFICATIONS_SELF) | S | LOW | UPDATE-DOCS (approved) |

## Decisions applied
- **R1** (FIX): hide Acquisition + Front Desk sections for patient (role-scoped sidebar filter in Sidebar.tsx).
- **R2** (UPDATE-DOCS): RBAC_matrix_spec.md Matrix C PATIENT addendum — FOLLOW_UP_SELF + NOTIFICATIONS_SELF noted.