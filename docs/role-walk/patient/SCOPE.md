# patient — Intended Scope (Phase 1)
Date: 2026-08-29
Sources: navigator.ts, permissions.py (MATRIX_C_PATIENT), Sidebar.tsx, RBAC_matrix_spec.md §5 (Matrix C PATIENT)
Skills invoked: hipaa-compliance, frontend-design

## Role Profile

| Field | Value |
|---|---|
| Role slug | `patient` |
| Workspace | `portal` (from ROLE_WORKSPACE) |
| Scope class | Generic (not admin-scoped, not clinical-scoped) |
| Landing route | `/portal` (PORTAL_READ passes) |
| Grant set | MATRIX_C_PATIENT (8 grants, own-data scoped) |
| Excluded from | Admin, clinical, billing, frontdesk surfaces |
| Tenant model | `acme.patient` is tenant-scoped (seed_uat) |
| Credential used | `acme.patient` / `Test@123456` (tenant-scoped, acme) |
| Relevant skills | hipaa-compliance, frontend-design |

## Reachable Surfaces (sidebar-visible)

| # | Section | UI Function | Route | Gate (permissions) | Intended (one line) |
|---|---|---|---|---|---|
| 1 | Portal | My Records | `/portal` | PORTAL_READ | Own patient records |
| 2 | Portal | Appointments | `/portal/appointments` | PORTAL_READ | Own appointments |
| 3 | Portal | Results | `/portal/results` | PORTAL_READ | Own test results |
| 4 | Portal | Follow-ups | `/portal/follow-ups` | PORTAL_READ | Own follow-up tasks |
| 5 | _sidebar leak_ | Acquisition: Schedule Board | `/schedule-board` | SCHEDULE_READ | Day schedule |
| 6 | _sidebar leak_ | Acquisition: Calendar | `/schedule` | SCHEDULE_READ | Resource calendar |
| 7 | _sidebar leak_ | Acquisition: Resources | `/schedule/resources` | SCHEDULE_READ | Resource definitions |
| 8 | _sidebar leak_ | Front Desk: Today's Schedule | `/frontdesk/schedule` | SCHEDULE_READ | Visit schedule |

## Not reachable

| Surface | Route | Reason |
|---|---|---|
| Admin, Billing, QA, Reading, DICOMweb, Metrics, Files | various | no grants |
| Coordination, Acquisition MWL/Tracking | various | no ORDER_READ/WORKLIST_READ |
| Front Desk Registration/Queue/Patient Search | /frontdesk/* | no REGISTRATION_READ/QUEUE_READ/PATIENT_READ |

## Key observations (Phase 2 candidates)

1. **Sidebar leaks**: patient holds SCHEDULE_READ (needed for portal appointments) which unlocks the Acquisition section (Schedule Board, Calendar, Resources) and Front Desk Today's Schedule. These are not patient-facing surfaces.
2. **Own-data scoped**: all grants are self-scoped (PORTAL_READ, FOLLOW_UP_SELF, NOTIFICATIONS_SELF, CHART_READ, RESULTS_READ, MED_ORDER_READ, VIEWER_READ) — the patient sees only their own data.
3. **No FILE_READ**: the F2 Files nav change (gate on FILE_READ) already hides Files for patient.
4. **Seed_uat has acme.patient**: tenant-scoped with demo data.