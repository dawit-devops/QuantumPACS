# receptionist — Intended Scope (Phase 1)
Date: 2026-08-29
Sources: navigator.ts, permissions.py (MATRIX_A_RECEPT), Sidebar.tsx, RBAC_matrix_spec.md §5 (Matrix A RECEPT)
Skills invoked: iam-audit, hipaa-compliance

## Role Profile

| Field | Value |
|---|---|
| Role slug | `receptionist` |
| Workspace | `frontdesk` (from ROLE_WORKSPACE) |
| Scope class | Generic (not admin-scoped, not clinical-scoped) |
| Landing route | `/frontdesk/registration` (REGISTRATION_READ passes) |
| Grant set | MATRIX_A_RECEPT (9 grants: spec RECEPT + R08 additions) |
| Excluded from | Admin surfaces, billing, QA, portal, metrics, DICOMweb |
| Tenant model | `acme.receptionist` is tenant-scoped (seed_uat has receptionist) |
| Credential used | `acme.receptionist` / `Test@123456` (tenant-scoped, acme) |
| Relevant skills | fullstack-guardian, hipaa-compliance |

## Reachable Surfaces (sidebar-visible)

| # | Section | UI Function | Route | Gate (permissions) | Intended (one line) |
|---|---|---|---|---|---|
| 1 | Front Desk | Registration | `/frontdesk/registration` | REGISTRATION_READ | Patient registration (search/create) |
| 2 | Front Desk | Today's Schedule | `/frontdesk/schedule` | SCHEDULE_READ | Visit schedule |
| 3 | Front Desk | Waiting Queue | `/frontdesk/queue` | QUEUE_READ | Privacy-projected waiting queue |
| 4 | Front Desk | Patient Search | (action) | PATIENT_READ | Global patient search |
| 5 | _sidebar leak_ | Acquisition: MWL | `/worklist` | WORKLIST_READ | DICOM modality worklist |
| 6 | _sidebar leak_ | Acquisition: Tracking | `/tracking` | WORKLIST_READ | Live exam tracking |
| 7 | _sidebar leak_ | Acquisition: Schedule Board | `/schedule-board` | WORKLIST_READ, SCHEDULE_READ | Day schedule |
| 8 | _sidebar leak_ | Acquisition: Calendar | `/schedule` | SCHEDULE_READ | Resource calendar |
| 9 | _sidebar leak_ | Acquisition: Resources | `/schedule/resources` | SCHEDULE_READ | Resource definitions |
| 10 | _sidebar leak_ | Coordination: Orders | `/orders` | ORDER_READ | Order list |
| 11 | _sidebar leak_ | Coordination: Care Plans | `/care-plans` | PATIENT_READ | Care plan board |
| 12 | _sidebar leak_ | Coordination: Communications | `/communications` | PATIENT_READ | Patient comm log |

## Not reachable

| Surface | Route | Reason |
|---|---|---|
| Admin Dashboard, Users, Roles, Logs, Replicas, etc. | various | no admin perms |
| DICOMweb | /dicomweb* | no DICOMWEB_READ |
| Billing | /billing/* | no BILLING_READ |
| Reading | /reading, /teaching, /critical | no REPORT_READ |
| QA | /qa/* | no QA_READ |
| Portal | /portal/* | no PORTAL_READ |
| Metrics | /metrics | no METRICS_READ |
| Files | / | no FILE_READ/STUDY_READ |
| Prior Auth | /prior-auth | no PRIOR_AUTH_READ |

## Key observations (Phase 2 candidates)

1. **Sidebar leaks**: receptionist holds WORKLIST_READ, ORDER_READ, PATIENT_READ (needed for frontdesk schedule board + patient search) which unlock the Acquisition and Coordination sections. These are clinical/coordination surfaces not belonging to a front-office role.
2. **Spec vs code**: code = spec Matrix A RECEPT + R08 grants (QUEUE_READ, REGISTRATION_READ/WRITE, SCHEDULE_WRITE) — documented in permissions.py comment.
3. **No FILE_READ**: receptionist doesn't hold any viewer grants, so Files page is not reachable (correct).
4. **Seed_uat has acme.receptionist**: tenant-scoped with demo data.