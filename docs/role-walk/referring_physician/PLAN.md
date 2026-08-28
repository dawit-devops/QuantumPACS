# referring_physician — Walk Plan & Results (Phases 4–5)
Date: 2026-08-29 | Credential used: test.referring_physician / Test@123456 (platform-side, tenant NULL) | Baseline commit: b4f9249

## Phase 6 — user guide (pending)

## Walk order (planned; sidebar order; one line of exercise detail each)
1. Reading Worklist `/reading` — list unread exams, filters, pagination
2. Teaching Library `/teaching` — curated teaching cases list
3. Critical Results `/critical` — critical results list
4. Modality Worklist `/worklist` — MWL entries
5. Tracking Board `/tracking` — live exam tracking
6. Schedule Board `/schedule-board` — day schedule
7. Calendar `/schedule` — resource calendar
8. Resources `/schedule/resources` — resource definitions
9. Orders `/orders` — order list (read-only)
10. Prior Auth `/prior-auth` — prior authorization list
11. Reminders `/reminders` — reminder config/delivery log
12. Care Plans `/care-plans` — care plan board
13. Communications `/communications` — patient communication log
14. Files `/` — browse/view DICOM files

## Walk table (Phase 4 fills cols 1–6 all PENDING; Phase 5 fills 7–10 in place)
| # | UI Function | Route | Gate | Intended | Expected API (method+path→status) | Status | Actual (vs intended) | Fix (layer) | Commit |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Reading Worklist | /reading | REPORT_READ | List exams, filters, pagination | GET /api/reports/reading-list?offset&limit&q → 200 | PENDING | | | |
| 2 | Teaching Library | /teaching | REPORT_READ | Teaching cases list | GET /api/teaching-files?offset&limit&q → 200 | PENDING | | | |
| 3 | Critical Results | /critical | REPORT_READ | Critical list | GET /api/notifications/critical → 200 | PENDING | | | |
| 4 | Modality Worklist | /worklist | WORKLIST_READ | MWL entries | GET /api/worklist?limit&offset&q → 200 | PENDING | | | |
| 5 | Tracking Board | /tracking | WORKLIST_READ | Live tracking | GET /api/ris/tracking?limit&offset&q → 200 | PENDING | | | |
| 6 | Schedule Board | /schedule-board | WORKLIST_READ, SCHEDULE_READ | Day schedule | GET /api/worklist?date → 200 | PENDING | | | |
| 7 | Calendar | /schedule | SCHEDULE_READ | Resource calendar | GET /api/ris/appointments?date → 200 | PENDING | | | |
| 8 | Resources | /schedule/resources | SCHEDULE_READ | Resource definitions | GET /api/ris/resources → 200 | PENDING | | | |
| 9 | Orders | /orders | ORDER_READ | Order list | GET /api/ris/orders?offset&limit&q → 200 | PENDING | | | |
| 10 | Prior Auth | /prior-auth | PRIOR_AUTH_READ | Prior auth list | GET /api/ris/prior-auth?offset&limit&q → 200 | PENDING | | | |
| 11 | Reminders | /reminders | PRIOR_AUTH_READ | Reminder config/log | GET /api/ris/reminders/log?limit → 200; GET /api/ris/reminders/config → 200 | PENDING | | | |
| 12 | Care Plans | /care-plans | PATIENT_READ | Care plan board | GET /api/ris/care-plans?offset&limit&q → 200 | PENDING | | | |
| 13 | Communications | /communications | PATIENT_READ | Patient comm log | GET /api/ris/communications?patient_id&limit → 200 | PENDING | | | |
| 14 | Files | / | VIEWER_ROUTE_PERMISSIONS | Browse/view files | GET /api/files?limit&offset&q → 200; POST /api/files/upload → 403 (no FILE_WRITE) | PENDING | | | |

## Excluded routes (planned Phase 4; verified in 5a)
| Route | Expected | Actual | Verdict |
|---|---|---|---|
| /admin | adminOnly → redirect to landing | | REDIRECT |
| /admin/ris-dashboard, /admin/staff-schedule, /admin/interfaces | adminOnly → redirect | | REDIRECT |
| /admin/report-templates | PermissionRoute REPORT_WRITE/REPORT_TEMPLATE_ADMIN → redirect | | REDIRECT |
| /admin/maintenance, /admin/backups, /admin/settings | PermissionRoute SYSTEM_ADMIN → redirect | | REDIRECT |
| /replicas, /users, /tenants, /roles, /logs, /service-keys, /routing | PermissionRoute → redirect | | REDIRECT |
| /fhir/*, /integrations | PermissionRoute SYSTEM_ADMIN → redirect | | REDIRECT |
| /hl7 | PermissionRoute HL7_READ → redirect | | REDIRECT |
| /metrics | PermissionRoute METRICS_READ/ANALYTICS_READ → redirect | | REDIRECT |
| /billing/* | PermissionRoute BILLING_READ → redirect | | REDIRECT |
| /qa/* | ClinicalRoute QA_READ → redirect | | REDIRECT |
| /exams | ClinicalRoute EXAM_READ → redirect | | REDIRECT |
| /frontdesk/* | ClinicalRoute (R1: hidden for clinical roles) → redirect | | REDIRECT |
| /portal/* | PermissionRoute PORTAL_READ → redirect | | REDIRECT |
| /dicomweb* | PermissionRoute DICOMWEB_READ → redirect (no grant) | | REDIRECT |

## Findings & decisions (cross-cutting; appended in ANY phase)
| # | Phase | Finding | Evidence (file:line) | Recommendation | Decision | Commit |
|---|---|---|---|---|---|---|
| F1 | 3 | ADR-017 "files: read" overstates the referring_physician grant (no FILE_READ; Files opens via STUDY_READ/VIEWER_READ) | ADR-017:78; permissions.py MATRIX_A_REF | UPDATE-DOCS | FIX (approved) | b4f9249 |