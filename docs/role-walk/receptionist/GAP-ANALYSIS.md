# receptionist — Gap Analysis (Phase 2)
Date: 2026-08-29
Sources: RBAC_matrix_spec.md §5 (Matrix A RECEPT), permissions.py MATRIX_A_RECEPT, navigator.ts, Sidebar.tsx
Skills invoked: iam-audit (least privilege)

## Gaps

| # | Surface | Documented (ADR/spec) | Actual (code) | Severity | Evidence (file:line) | Notes |
|---|---|---|---|---|---|---|
| G1 | Acquisition section visible (MWL / Tracking / Schedule / Calendar / Resources) | Spec Matrix A RECEPT: WORKLIST_READ, SCHEDULE_READ — needed for the schedule board day data. The Acquisition section is a technologist/clinical surface | Sidebar shows Acquisition section for receptionist (WORKLIST_READ/SCHEDULE_READ pass). The MWL / Tracking / Schedule / Calendar / Resources items are all visible — clinical surfaces for a front-office role | MEDIUM | Sidebar.tsx: acquisition section items (WORKLIST_READ, SCHEDULE_READ gates); MATRIX_A_RECEPT includes WORKLIST_READ, SCHEDULE_READ | Same pattern as referring_physician F3 — WORKLIST_READ/SCHEDULE_READ needed for landing + schedule board, but the Acquisition section is not the receptionist's workspace |
| G2 | Coordination section visible (Orders / Care Plans / Communications) | Spec Matrix A RECEPT: ORDER_READ (needed for registration flow). PATIENT_READ (needed for patient search). Coordination section is a care-coordinator/physician surface | Sidebar shows Coordination section for receptionist (ORDER_READ/PATIENT_READ pass). Orders, Care Plans, Communications items all visible | MEDIUM | Sidebar.tsx: coordination section items (ORDER_READ, PATIENT_READ gates) | Same pattern — ORDER_READ/PATIENT_READ are needed for frontdesk operations but the Coordination section is not the receptionist's workspace |
| G3 | Code vs spec: R08 additions | Spec Matrix A RECEPT: PATIENT_READ, PATIENT_WRITE, ORDER_READ, SCHEDULE_READ, WORKLIST_READ | Code MATRIX_A_RECEPT adds: QUEUE_READ, REGISTRATION_READ, REGISTRATION_WRITE, SCHEDULE_WRITE (R08 front-desk grants) | PASS | permissions.py:231-237 | Documented in inline comment — R08 grants are deliberate extensions |
| G4 | Spec drift: spec lacks R08 grants | Spec Matrix A RECEPT row only has 5 perms | Code has 9 perms (R08 additions) | LOW | RBAC_matrix_spec.md Matrix A RECEPT row | Docs should note the R08 additions |

## Summary
- G1/G2: sidebar leaks — same pattern as referring_physician F3 (clinical/coordination sections visible via shared grants).
- G3: no gap (intentional R08 additions).
- G4: minor spec drift — RECEPT row should note the R08 grants.