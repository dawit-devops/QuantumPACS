# referring_physician — Intended Scope (Phase 1)
Date: 2026-08-29
Sources: navigator.ts, permissions.py (MATRIX_A_REF), Sidebar.tsx, RBAC_matrix_spec.md §5 (Matrix A REF)
Skills invoked: iam-audit, hipaa-compliance

## Role Profile

| Field | Value |
|---|---|
| Role slug | `referring_physician` |
| Workspace | `clinical` (from ROLE_WORKSPACE) |
| Scope class | clinical-scoped (`CLINICAL_SCOPED_ROLES`) |
| Landing route | `/reading` (REPORT_READ passes — reading worklist) |
| Grant set | MATRIX_A_REF (10 grants, read-only) |
| Excluded from | Admin console surfaces, billing, QA, metrics, portal, DICOMweb (no DICOMWEB_READ) |
| Tenant model | test.referring_physician is platform-side (tenant NULL) |
| Credential used | `test.referring_physician` / `Test@123456` (platform-side) |
| Relevant skills | pacs-workflow, dicom-web-query, hipaa-compliance, fhir-developer-skill |

## Reachable Surfaces (sidebar-visible)

| # | Section | UI Function | Route | Gate (permissions) | Intended (one line) |
|---|---|---|---|---|---|
| 1 | — | Files | `/` | VIEWER_ROUTE_PERMISSIONS (STUDY_READ, VIEWER_READ) | Browse/view DICOM files (read-only) |
| 2 | Reading | Reading Worklist | `/reading` | REPORT_READ | Reading worklist — view reports |
| 3 | Reading | Teaching Library | `/teaching` | REPORT_READ | Curated teaching cases |
| 4 | Reading | Critical Results | `/critical` | REPORT_READ | Critical results monitoring |
| 5 | Acquisition | Modality Worklist | `/worklist` | WORKLIST_READ | DICOM modality worklist |
| 6 | Acquisition | Tracking Board | `/tracking` | WORKLIST_READ | Live exam tracking |
| 7 | Acquisition | Schedule Board | `/schedule-board` | WORKLIST_READ, SCHEDULE_READ | Day schedule |
| 8 | Acquisition | Calendar | `/schedule` | SCHEDULE_READ | Resource calendar |
| 9 | Acquisition | Resources | `/schedule/resources` | SCHEDULE_READ | Resource definitions |
| 10 | Coordination | Orders | `/orders` | ORDER_READ | Order list (read-only) |
| 11 | Coordination | Prior Auth | `/prior-auth` | PRIOR_AUTH_READ | Prior auth list |
| 12 | Coordination | Reminders | `/reminders` | PRIOR_AUTH_READ | Reminder config/delivery log |
| 13 | Coordination | Care Plans | `/care-plans` | PATIENT_READ | Care plan board |
| 14 | Coordination | Communications | `/communications` | PATIENT_READ | Patient communication log |

## Not reachable (by design — read-only clinical role, no admin/write surfaces)

| Surface | Route | Reason |
|---|---|---|
| Admin Dashboard / RIS / Staff Schedule / Replicas / Users / Roles / Logs / Routing / HL7 / Interfaces / Maintenance / Backups / Settings | various | adminOnly / no admin perms |
| DICOMweb Server/Store/Browser | /dicomweb* | no DICOMWEB_READ |
| Billing (all) | /billing/* | no BILLING_READ |
| QA | /qa/* | no QA_READ |
| Metrics | /metrics | no METRICS_READ/ANALYTICS_READ |
| Portal | /portal/* | no PORTAL_READ |
| Report Templates | /admin/report-templates | no REPORT_WRITE/REPORT_TEMPLATE_ADMIN |
| Front Desk | /frontdesk/* | R1 (physician walk): frontdesk/portal hidden for clinical roles |

## Key observations (Phase 2 candidates)

1. **Pure read-only**: 10 grants, all reads (CHART/ORDER/PATIENT/PRIOR_AUTH/REPORT/RESULTS/SCHEDULE/STUDY/VIEWER/WORKLIST). No writes at all. Spec Matrix A REF matches exactly (verified in Phase 2).
2. **No DICOMWEB_READ / FILE_READ legacy**: unlike physician (LEGACY_PHYSICIAN adds both), referring_physician has NO legacy union. So Files page is reachable via STUDY_READ/VIEWER_READ (VIEWER_ROUTE_PERMISSIONS is any-of), but DICOMweb console is not.
3. **No EMR write power**: unlike physician (ENCOUNTER_WRITE, NOTE_SIGN, MED_ORDER_WRITE, ORDER_WRITE, CARE_PLAN_WRITE, MAR_READ), referring_physician holds none of these. Pure referrer — views orders/results/reports, initiates referrals.
4. **Front Desk hidden**: R1 fix from physician walk hides frontdesk for clinical roles — applies here too.
5. **Files page**: reachable via STUDY_READ/VIEWER_READ (any-of VIEWER_ROUTE_PERMISSIONS) — read-only file browser.