# technologist — Walk Plan & Results (Phases 4–5)
Date: 2026-08-28 | Credential used: `acme.technologist` / `Test@123456` (seed_uat; login OK → tenant `acme`, 15 perms) | Baseline commit: be34780

## Walk order (planned; sidebar order; one line of exercise detail each)
1. My Exams `/exams` — status tabs (All/Ready/In Progress/Completed/Cancelled), search, 30s auto-refresh, claim/release, next-patient banner
2. Exam Console `/exams/:id` — identity confirm → protocol select/favorite → acquire/retake → QA accept/reject → safety checks → dose panel → critical flag → incident/override → complete
3. Modality Worklist `/worklist` — status/modality filters, KPI strip, search, pagination; view-only for tech (create gated elsewhere)
4. Tracking Board `/tracking` — filters, KPI, row status timeline, resource availability
5. Schedule Board `/schedule-board` — day slots per resource, booking modal visibility (SCHEDULE_READ only → no write)
6. Calendar `/schedule` — day view navigation, resource/modality filters, booking modal (write actions expect denial)
7. Resource Manager `/schedule/resources` — list rooms/modalities/techs; write buttons expect denial
8. Orders `/orders` — order list, filters, detail drawer (view only)
9. Care Plans `/care-plans` — board browse (create/edit buttons expect denial)
10. Communications `/communications` — patient-scoped search (requires patient_id query)
11. Patient Search (overlay) — global search box by name/ID
12. File Browser `/` — DICOM file list, search, upload (FILE_WRITE)
13. Detail Viewer `/files/:id` — Cornerstone3D viewport render, tools

## Walk table (Phase 4 fills cols 1–6 all PENDING; Phase 5 fills 7–10 in place)
| # | UI Function | Route | Gate | Intended | Expected API (method+path→status) | Status | Actual (vs intended) | Fix (layer) | Commit |
|---|---|---|---|---|---|---|---|---|---|
| 1 | My Exams | `/exams` | ClinicalRoute EXAM_READ | R06 assignment list + tabs + claim | GET `/exams?status&assigned&per_page`→200 | PENDING | | | |
| 2 | Exam Console | `/exams/:id` | ClinicalRoute EXAM_READ | Acquire→QA→safety→complete lifecycle | GET `/exams/{id}`→200; POST `/exams/{id}/identity-confirm`→200; POST `/exams/{id}/protocol`→200; POST `/exams/{id}/acquisitions`→201; POST `/exams/{id}/acquisitions/{aid}/accept\|reject`→200; POST `/exams/{id}/safety-checks`→200; POST `/exams/{id}/complete`→200; POST `/exams/{id}/critical-flag`→200; POST `/exams/{id}/incidents`→201; POST `/exams/{id}/overrides`→201 | PENDING | | | |
| 3 | Modality Worklist | `/worklist` | ClinicalRoute WORKLIST_READ | DICOM MWL browse + filters | GET `/worklist?status&page&per_page`→200; GET `/worklist/sync` stats POST `/worklist/sync`→403 (no perm?) | PENDING | | | |
| 4 | Tracking Board | `/tracking` | ClinicalRoute WORKLIST_READ | Live exam status + KPI + timeline | GET `/ris/tracking`→200; GET `/ris/tracking/kpi`→200; GET `/ris/tracking/{id}/timeline`→200; PUT `/ris/tracking/{id}/status`→200 (WORKLIST_WRITE) | PENDING | | | |
| 5 | Schedule Board | `/schedule-board` | ClinicalRoute WORKLIST_READ/SCHEDULE_READ | Day board per resource | GET `/ris/appointments?date=`→200; GET `/ris/resources`→200 | PENDING | | | |
| 6 | Calendar | `/schedule` | ClinicalRoute SCHEDULE_READ | RIS schedule day view + filters | GET `/ris/appointments?date_from&date_to`→200; GET `/ris/resources`→200 | PENDING | | | |
| 7 | Resource Manager | `/schedule/resources` | ClinicalRoute SCHEDULE_READ | View resources | GET `/ris/resources`→200; POST `/ris/resources`→403 (SCHEDULE_WRITE missing) | PENDING | | | |
| 8 | Orders | `/orders` | ClinicalRoute ORDER_READ | Order list view | GET `/ris/orders?per_page`→200 | PENDING | | | |
| 9 | Care Plans | `/care-plans` | ClinicalRoute PATIENT_READ | Browse plans | GET `/ris/care-plans`→200; POST→403 (CARE_PLAN_WRITE missing) | PENDING | | | |
| 10 | Communications | `/communications` | ClinicalRoute PATIENT_READ | Patient-scoped correspondence | GET `/ris/communications?patient_id=`→200; GET without→422 | PENDING | | | |
| 11 | Patient Search | overlay | PATIENT_READ | Quick lookup | GET `/patients?search=`→200 | PENDING | | | |
| 12 | File Browser | `/` | VIEWER_ROUTE_PERMISSIONS | Browse DICOM files | POST `/files/search`→200; GET `/studies`→200 | PENDING | | | |
| 13 | Detail Viewer | `/files/:id` | VIEWER_ROUTE_PERMISSIONS | Cornerstone3D render | GET `/files/{id}`→200; WADO-RS retrieve→200 | PENDING | | | |

## Excluded routes (planned Phase 4; verified in 5a)
| Route | Expected | Actual | Verdict |
|---|---|---|---|
| `/ris/billing/fee-schedule` | 403 (no BILLING_READ) | PENDING | |
| `/ris/billing/claims` | 403 | PENDING | |
| `/qa/*` (queue) | 403/404 (no QA_READ) | PENDING | |
| `/reports` | 403/404 (no REPORT_READ) | PENDING | |
| `/reports/critical` | 403 | PENDING | |
| `/nursing/prep-list` | 403 (no NURSING_READ) | PENDING | |
| `/ris/prior-auth` | 403 (no PRIOR_AUTH_READ) | PENDING | |
| `/tenants` | 403 | PENDING | |
| `/users` | 403 | PENDING | |
| `/reading/*` (REPORT_READ) | 403/404 | PENDING | |

## Findings & decisions (cross-cutting; appended in ANY phase)
| # | Phase | Finding | Evidence (file:line) | Recommendation | Decision | Commit |
|---|---|---|---|---|---|---|
| F1 | 5a | Cross-tenant visibility on shared-DB tenants: `Exams.list_for_technologist` has NO tenant_id WHERE — acme tech sees 541 exams incl. other tenants' rows (tenant_id NULL/default) | backend/db/exams.py:134-194 | Add tenant filter (or document shared-DB tenants get pool-only isolation) | PENDING | |
| F2 | 5a | `Worklist.search` has NO tenant filter — MWL exposes all tenants' scheduled PHI (worklist_entries tenant_id values span dozens of slugs) | backend/db/worklist.py:167-237 | Add tenant filter to search (and verify DICOM C-FIND path) | PENDING | |
| F3 | 5a | `RisAppointments.for_date_range`/`for_day`/`for_resource` have NO tenant filter — appointments API returns rows from perf-*/pa-e2e-*/d2-* tenants to an acme token | backend/db/ris_appointments.py:104-173 | Add tenant filter (a.tenant_id = current slug) | PENDING | |
| F4 | 5a | CSRF middleware allows fallback `csrf_token=1` double-submit for any client — weakens CSRF protection to presence-check only | backend/app.py:157-161 | Remove '1' fallback / require real cookie | PENDING | |
