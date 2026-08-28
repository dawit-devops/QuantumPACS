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
| 1 | My Exams | `/exams` | ClinicalRoute EXAM_READ | R06 assignment list + tabs + claim | GET `/exams?status&assigned&per_page`→200 | PASS | Renders; My/Pool tabs, status tabs w/ counts, modality+search filters, pagination, claim/open buttons; 30s auto-refresh. Tab counts show ALL 541 completed incl. other tenants' rows (F1 visible live: "A1 RealDb Patient", "Tenant^Patient" rows). Note: status tabs show totals but My-Exams tab body empty (no exams assigned to acme.technologist; pool shows the 541). One console 403: GET `/api/v2/tenants` (sidebar tenant probe) — cosmetic, tenant name already known client-side. | | |
| 2 | Exam Console | `/exams/:id` | ClinicalRoute EXAM_READ | Acquire→QA→safety→complete lifecycle | GET `/exams/{id}`→200; POST identity-confirm/protocol/acquisitions/accept|reject/safety-checks/complete/critical-flag→200; POST incidents/overrides→201 | PASS (read-only paths) | Completed exam renders all 5 workflow steps: identity table, protocol select/favorite + body-part/indication filters (T-06 favorites, T-06 indication), QA queue w/ W/L sliders + ionizing-alert (T-14), dose ledger panel, safety checks w/ prior screenings (T-04-adjacent), nursing read-only tabs (vitals/checklist/consent/notes — 4× GET 200). Write actions disabled since exam completed — lifecycle gates correct. Console errors: only the `/tenants` 403 + transient ws_token ERR_CONNECTION_REFUSED (dev backend restart). | | |
| 3 | Modality Worklist | `/worklist` | ClinicalRoute WORKLIST_READ | DICOM MWL browse + filters | GET `/worklist?status&page&per_page`→200; POST `/worklist`→403 w/o CSRF/2xx w/ | PASS | Table/Calendar toggle, All/Scheduled/Performed/Cancelled tabs w/ counts, station-AE filter, date range, search, pagination — all render; GET `/worklist*` + `/worklist/station-aes` 200. Create Entry + MWL Pending buttons visible (WORKLIST_WRITE granted). Cross-tenant PHI visible (F2 live: Tenant^Patient rows from other slugs). | | |
| 4 | Tracking Board | `/tracking` | ClinicalRoute WORKLIST_READ | Live exam status + KPI + timeline | GET `/ris/tracking`→200; GET `/ris/tracking/kpi`→200; PUT `/ris/tracking/{id}/status`→422 validation | PASS | Kanban (Scheduled 19 / Arrived / In Progress / Completed 1) + Table toggle, KPI strip (Today 0, Overdue 318, STAT 0), modality/status/priority/room/date filters. Card click → Exam Details dialog (patient, accession, procedure, priority URGENT, room) — 200s. Overdue=318 driven by cross-tenant stale rows (F2/F3 visible). No timeline GET fired on card click (timeline only used in Table view). | | |
| 5 | Schedule Board | `/schedule-board` | ClinicalRoute WORKLIST_READ/SCHEDULE_READ | Day board per resource | GET `/worklist?date_from&date_to&per_page=200`→200 | PASS | Day nav (prev/today/next) works; "No worklist entries for 2026-08-28" empty state + modality column grid render; Total/Scheduled/Performed/Cancelled counters. Board reads worklist (MWL), not ris_appointments — no bookings exist for today. Transient ws_token 5xxs during a backend restart (not a surface bug). | | |
| 6 | Calendar | `/schedule` | ClinicalRoute SCHEDULE_READ | RIS schedule day view + filters | GET `/ris/appointments?date_from&date_to`→200; GET `/ris/resources`→200 | PASS | Day/Week/Month/Gantt/Heatmap segmented, resource-type+modality filters, 8 Acme resources × 07:00–18:30 30-min slots rendered from per-resource availability calls (200). Free-cell click + header click do nothing for this role — canWrite=false (SCHEDULE_WRITE) hides Book/Batch/Waitlist buttons; cell becomes inert gridcell (CalendarGrid.tsx:151). Correct gate behavior. One transient "Failed to fetch" on first load (network blip) recovered on reload. | | |
| 7 | Resource Manager | `/schedule/resources` | ClinicalRoute SCHEDULE_READ | View resources | GET `/ris/resources`→200 | PASS | 8 Acme resource cards (type, modality, location, status, created) with type/modality filters. No Create/Save buttons rendered (SCHEDULE_WRITE-gated in ResourceManager.tsx) — correct. | | |
| 8 | Orders | `/orders` | ClinicalRoute ORDER_READ | Order list view | GET `/orders`→200 | REFINE | List renders w/ status alert (3 open · 3 waiting >24h), status/modality filters, search. BUT row click navigates `/patients/{patient_id}` (MRN string) → GET `/patients/{id}` 500: `api/utils.get_id` does `int(id)` and blows up on non-numeric MRN (backend/api/utils.py:6, frontend Orders.tsx:227). `patient_db_id` is always null (patients table has no row for the order's MRN) so the `?? r.patient_id` fallback always fires. Also Schedule button visible — routes to schedule-board (fine). → Finding F5 (frontend+backend fix). | F5 (frontend fix: stop navigating on bad id; backend: 404 not 500) | |
| 9 | Care Plans | `/care-plans` | ClinicalRoute PATIENT_READ | Browse plans | GET `/ris/care-plans`→200 | REFINE | Page crashes: ErrorBoundary "Something went wrong". GET returns `tasks` as a JSON **string** (asyncpg jsonb→str default; api/care_plans.py:31 returns rows raw), frontend `taskProgress` calls `tasks.filter` → TypeError (CarePlans.tsx:104-108). 5 acme plans never render. → Finding F6 (backend serialize tasks; frontend defensive parse). | F6 (backend fix) | |
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
| F1 | 5a | Cross-tenant visibility on shared-DB tenants: `Exams.list_for_technologist` has NO tenant_id WHERE — acme tech sees 541 exams incl. other tenants' rows (tenant_id NULL/default) | backend/db/exams.py:134-194 | Add tenant filter (or document shared-DB tenants get pool-only isolation) | **RECORDED 2026-08-28** — decide after browser walk; priority HIGH | |
| F2 | 5a | `Worklist.search` has NO tenant filter — MWL exposes all tenants' scheduled PHI (worklist_entries tenant_id values span dozens of slugs) | backend/db/worklist.py:167-237 | Add tenant filter to search (and verify DICOM C-FIND path) | **RECORDED 2026-08-28** — decide after browser walk; priority HIGH | |
| F3 | 5a | `RisAppointments.for_date_range`/`for_day`/`for_resource` have NO tenant filter — appointments API returns rows from perf-*/pa-e2e-*/d2-* tenants to an acme token | backend/db/ris_appointments.py:104-173 | Add tenant filter (a.tenant_id = current slug) | **RECORDED 2026-08-28** — decide after browser walk; priority HIGH | |
| F4 | 5a | CSRF middleware allows fallback `csrf_token=1` double-submit for any client — weakens CSRF protection to presence-check only | backend/app.py:157-161 | Remove '1' fallback / require real cookie | **DEFERRED 2026-08-28** — MEDIUM hardening item; verify frontend sets real cookie first | |
| F5 | 5b | Orders row click → `/patients/{MRN}` → 500. `get_id()` does `int()` on a non-numeric MRN; `patient_db_id` null for visit-order patients (no patients row) | frontend/src/coordinator/Orders.tsx:227; backend/api/utils.py:6; backend/api/orders.py (patient_db_id unpopulated) | Backend: PatientHandler return 404 for non-numeric id (or Orders coalesce to a valid patient key). Frontend: only navigate when `patient_db_id` present, else no-op/tooltip. | **RECORDED 2026-08-28** — decision gate pending | |
| F6 | 5b | Care Plans page crashes — `tasks` JSONB returned as string by API (asyncpg default), frontend calls `.filter` on it | backend/api/care_plans.py:31 (raw `dict(r)` passthrough); frontend/src/coordinator/CarePlans.tsx:104-108 | Backend: `json.loads` tasks when str before returning (match db/nursing.py:113 pattern); frontend: guard `Array.isArray`. | **RECORDED 2026-08-28** — decision gate pending | |
