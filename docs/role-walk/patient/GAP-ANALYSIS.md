# patient — Gap Analysis (Phase 2)
Date: 2026-08-29
Sources: RBAC_matrix_spec.md §5 (Matrix C PATIENT), permissions.py MATRIX_C_PATIENT, navigator.ts, Sidebar.tsx
Skills invoked: hipaa-compliance, iam-audit

## Gaps

| # | Surface | Documented (ADR/spec) | Actual (code) | Severity | Evidence (file:line) | Notes |
|---|---|---|---|---|---|---|
| G1 | Acquisition section visible (Schedule Board / Calendar / Resources) | Spec Matrix C PATIENT: SCHEDULE_READ (own) — for the portal's own appointments. Acquisition section is a technologist/scheduler surface | Sidebar shows Acquisition section for patient (SCHEDULE_READ passes Schedule Board/Calendar/Resources). These are clinical scheduling surfaces, not patient portal | MEDIUM | Sidebar.tsx: acquisition items (SCHEDULE_READ gates); MATRIX_C_PATIENT has SCHEDULE_READ | Same pattern as referring_physician F3 / receptionist R1 — SCHEDULE_READ needed for own appointments but leaks the Acquisition section |
| G2 | Front Desk "Today's Schedule" visible | Spec Matrix C PATIENT: no frontdesk grants | Sidebar shows Front Desk section with Today's Schedule (SCHEDULE_READ passes). Front Desk is for receptionist staff | MEDIUM | Sidebar.tsx: fd-visits (SCHEDULE_READ); MATRIX_C_PATIENT has SCHEDULE_READ | Front Desk section should not be visible to a patient |
| G3 | Code vs spec: FOLLOW_UP_SELF, NOTIFICATIONS_SELF | Spec Matrix C PATIENT: PORTAL_READ, CHART_READ (own), RESULTS_READ (released), MED_ORDER_READ (own), SCHEDULE_READ (own), VIEWER_READ (share) | Code adds FOLLOW_UP_SELF + NOTIFICATIONS_SELF | PASS | permissions.py:389-393 | Documented inline (self-scoped follow-up + notifications) — deliberate |
| G4 | No FILE_READ | Spec: patient has no file grants | Code matches — Files nav already hidden (F2 referring_physician fix gates on FILE_READ) | PASS | PermissionsRoute VIEWER_ROUTE_PERMISSIONS; F2 (75107be) | Files hidden for patient — correct |

## Summary
- G1/G2: sidebar leaks (Acquisition + Front Desk visible via SCHEDULE_READ).
- G3: no gap (deliberate self-scoped grants).
- G4: no gap (Files hidden).