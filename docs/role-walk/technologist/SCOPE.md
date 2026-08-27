# technologist — Intended Scope (Phase 1)
Date: 2026-08-28
Sources: navigator.ts, permissions.py, Sidebar.tsx (commits 0f1ff97)

## Role Profile

| Field | Value |
|---|---|
| Role slug | `technologist` |
| Workspace | `acquisition` (from ROLE_WORKSPACE) |
| Scope class | clinical-scoped (CLINICAL_SCOPED_ROLES) |
| Landing route | `/exams` (first acquisition LANDING_STEP; /exams gate EXAM_READ) |
| Grant set | `TECHNOLOGIST_PERMISSIONS = LEGACY_TECHNOLOGIST \| MATRIX_A_TECH` |
| Excluded from | admin console, Reading/QA workspaces, Billing, admin-scoped roles' surfaces |
| Tenant model | tenant-bound clinical data-plane |
| Seeded login | `acme.technologist` / `Test@123456` |
| Relevant skills | pacs-workflow, dicom-web-query, pydicom, hipaa-compliance, user-feature-review |

### Grant set (permissions.py:376-403)
```
LEGACY_TECHNOLOGIST = {EXAM_READ, EXAM_WRITE, DICOMWEB_READ}
MATRIX_A_TECH = {
  PATIENT_READ, ORDER_READ, SCHEDULE_READ,
  WORKLIST_READ, WORKLIST_WRITE, CRITICAL_RESULTS_WRITE,
  VIEWER_READ, STUDY_READ, FILE_READ, FILE_WRITE,
  CHART_READ, RESULTS_READ, EXAM_READ, EXAM_WRITE,
}
```
Note: no REPORT_READ, no QA_READ, no PEER_REVIEW_READ, no NURSING_READ,
no BILLING_READ, no PRIOR_AUTH_READ, no REPORT_WRITE/SIGN.

## Reachable Surfaces

| # | Section | UI Function | Route | Gate (permissions) | Intended (one line) |
|---|---|---|---|---|---|
| 1 | Acquisition | My Exams (technologist worklist) | `/exams` | ClinicalRoute EXAM_READ | R06 assignment list of exams the technologist performs |
| 2 | Acquisition | Exam Console | `/exams/:id` | ClinicalRoute EXAM_READ | Acquire → QA → safety → complete the exam (primary surface) |
| 3 | Acquisition | Modality Worklist (DICOM MWL) | `/worklist` | ClinicalRoute WORKLIST_READ | DICOM worklist of scheduled procedures |
| 4 | Acquisition | Tracking Board | `/tracking` | ClinicalRoute WORKLIST_READ | Live status of all exams (S6-13) |
| 5 | Acquisition | Schedule Board | `/schedule-board` | ClinicalRoute WORKLIST_READ/SCHEDULE_READ | Day board, capacity booking |
| 6 | Acquisition | Calendar | `/schedule` | ClinicalRoute SCHEDULE_READ | RIS-native schedule over resources |
| 7 | Acquisition | Resource Manager | `/schedule/resources` | ClinicalRoute SCHEDULE_READ | Rooms/modalities/techs resources |
| 8 | Coordination | Orders | `/orders` | ClinicalRoute ORDER_READ | Order list (view) |
| 9 | Coordination | Care Plans | `/care-plans` | ClinicalRoute PATIENT_READ | Per-patient care plans (view) |
| 10 | Coordination | Communications | `/communications` | ClinicalRoute PATIENT_READ | Correspondence trail (view) |
| 11 | Coordination | Patient Search | (overlay) | PATIENT_READ | Quick patient lookup |
| 12 | Files | File Browser | `/` | PermissionRoute VIEWER_ROUTE_PERMISSIONS (FILE_READ/STUDY_READ/VIEWER_READ) | Browse DICOM files |
| 13 | Files | Detail Viewer | `/files/:id` | PermissionRoute VIEWER_ROUTE_PERMISSIONS | Cornerstone3D viewer |

## Not reachable (by design)
- Reading workspace (`/reading`, `/teaching`, `/peer-review`, `/critical`) — REPORT_READ / PEER_REVIEW_READ not granted
- QA workspace (`/qa/*`) — QA_READ not granted
- Billing (`/billing/*`) — BILLING_READ not granted
- Admin console (`/admin/*`, `/dicomweb`) — admin-scoped roles excluded (CLINICAL_SCOPED_ROLES)
- Nursing Prep (`/nursing`) — NURSING_READ not granted
- Prior Auth / Reminders — PRIOR_AUTH_READ not granted

## Skills invoked
Phase 1 loaded: pacs-workflow, dicom-web-query, hipaa-compliance (per the
ROLE & FEATURE SKILL MAP). pydicom + user-feature-review queued for
Phase 5 surfaces that touch DICOM pixels or are walked live.
