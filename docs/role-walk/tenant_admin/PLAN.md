# tenant_admin — Walk Plan & Results (Phases 4–5)
Date: 2026-08-28 | Credential used: test.tenant_admin / Test@123456 via POST /api/v2/login {"tenant":"acme"} | Baseline commit: 2306d0c

## Walk order (planned; sidebar order; one line of exercise detail each)
1. Report Templates `/admin/report-templates` — list templates, view versions, publish new version, rollback
2. Dashboard `/admin` — health strip, KPI cards, modality/ingestion charts, replicas table, recent activity, quick links, auto-refresh
3. RIS Dashboard `/admin/ris-dashboard` — TAT by priority, workload panel, drill-down, equipment utilization
4. Replicas `/replicas` — list, status/delay; error paths on create/update/delete (403)
5. Users `/users` — list with filters/pagination, create user, assign role, deactivate, reset password, batch status
6. Tenants `/tenants` — list, health probes, usage panel; error paths on create/delete (403 platform-only)
7. Roles `/roles` — list, permission groups, create custom role, edit (non-builtin), delete (non-builtin), view role users
8. Logs `/logs` — filters (event_type, actor, date range, tenant), cursor pagination, CSV export
9. Service Keys `/service-keys` — list, create (show raw key), delete
10. Routing `/routing` — list rules with pagination; error paths on create/update/delete (403 no ROUTING_WRITE)
11. HL7 `/hl7` — message list with filters, detail modal, metrics tab, status tab, config tab (read-only); error path on config save (403 no HL7_WRITE)
12. Interface Health `/admin/interfaces` — interface list, message browser, metrics, exception queue, retry exception
13. DICOMweb Server `/dicomweb` — server info, metrics, request log with filters/pagination
14. DICOMweb Store `/dicomweb/store` — upload a DICOM → expected 403 (no DICOMWEB_WRITE)
15. DICOMweb Study Browser `/dicomweb/browser` — search studies, expand series/instances, WADO-RS render, archive download, Weasis launch
16. Billing Queue `/billing/queue` — paginated queue, CPT suggestions, patient responsibility; error paths on drop/batch-drop/submit (403 no BILLING_WRITE)
17. Claims `/billing/claims` — claim list, history drawer; error paths on submit/batch-submit (403)
18. Revenue `/billing/revenue` — collections trend, payer/modality breakdown
19. Unbilled Aging `/billing/unbilled` — aging report with grouping (date/site/payer)
20. Denial Rework `/billing/denials` — denial list, history; error paths on import/resubmit/batch-resubmit (403)
21. Fee Schedule `/billing/fee-schedule` — fee schedule list/search, payer contracts, contract comparison; error paths on edit/import/contract CRUD (403)
22. Reconciliation `/billing/reconciliation` — signed-vs-charged snapshot render
23. Metrics `/metrics` — totals cards, ingestion chart, modality distribution, system health

## Walk table (Phase 4 fills cols 1–6 all PENDING; Phase 5 fills 7–10 in place)
| # | UI Function | Route | Gate | Intended | Expected API (method+path→status) | Status | Actual (vs intended) | Fix (layer) | Commit |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Report Templates | /admin/report-templates | REPORT_WRITE, REPORT_TEMPLATE_ADMIN | List, versions, publish, rollback | GET /api/ris/report-templates → 200; GET /api/ris/report-templates/{id}/versions → 200; POST /api/ris/report-templates/{id}/publish → 200; POST /api/ris/report-templates/{id}/rollback → 200 |PASS| | | |
| 2 | Dashboard | /admin | ADMIN_DASHBOARD_PERMISSIONS + adminOnly | Health strip, KPI cards, charts, replicas, recent activity, quick links, auto-refresh | GET /api/v2/dashboard/health → 200; GET /api/v2/dashboard/metrics?range=30d → 200; GET /api/users?offset=0&limit=1 → 200; GET /api/dicomweb/admin/metrics?period=24h → 200; GET /api/replicas → 200; GET /api/logs?limit=8 → 200 |PASS| | | |
| 3 | RIS Dashboard | /admin/ris-dashboard | REPORT_READ + adminOnly | TAT, utilization, volume, workload drill-down | GET /api/ris/dashboard/kpi → 200; GET /api/ris/analytics/workload → 200; GET /api/ris/analytics/tat-drilldown → 200; GET /api/ris/analytics/equipment-util → 200 |PASS-AFTER-FIX| Workload tab 500'd (F5: `e.scheduled_date`/`a.room` don't exist); fixed. Equipment tab degrades gracefully (EQUIPMENT_READ not granted) | backend (ris_dashboard.py) | |
| 4 | Replicas | /replicas | REPLICA_READ | List, status/delay; error paths on writes | GET /api/replicas → 200; POST /api/replicas → 403 (no REPLICA_WRITE); PUT /api/replicas/{id} → 403; DELETE /api/replicas/{id} → 403 |PASS-AFTER-FIX| Page crashed (F6: `id.slice` on numeric id); fixed. Renders 1 replica (Master, ACTIVE) | frontend (Replicas.tsx) | |
| 5 | Users | /users | USER_READ | List w/ filters/pagination, create, assign role, deactivate, reset password, batch status | GET /api/users?offset&limit&q → 200; POST /api/users → 200 (USER_WRITE); PUT /api/users/role → 200; POST /api/users/deactivate → 200; POST /api/users/new_password → 200; POST /api/users/batch-status → 200 |PASS| | | |
| 6 | Tenants | /tenants | TENANT_READ | List, health, usage panel; error paths on create/delete | GET /api/tenants → 200 (no db_* fields); GET /api/tenants/health → 200; GET /api/tenants/{id}/usage → 200 (METERING_READ); POST /api/tenants → 403 (platform-only); DELETE /api/tenants/{id} → 403 (no TENANT_WRITE) |PASS| | | |
| 7 | Roles | /roles | ROLE_READ | List, permissions, create custom role, edit (non-builtin), delete (non-builtin), role users | GET /api/roles → 200; GET /api/permissions → 200; POST /api/roles → 200 (ROLE_WRITE); PUT /api/roles/{id} → 200 (non-builtin); DELETE /api/roles/{id} → 200 (ROLE_DELETE, non-builtin); GET /api/roles/{id}/users → 200 |PASS| | | |
| 8 | Logs | /logs | LOG_READ, AUDIT_READ | Filters (event_type, actor, date range, tenant), cursor pagination, CSV export | GET /api/logs?event_type&actor&date_from&date_to&tenant&cursor&limit → 200; GET /api/logs/actors?search&limit=10 → 200; GET /api/logs?download=csv&filters → 200 (CSV blob); GET /api/tenants (for tenant filter) → 200 |PASS| | | |
| 9 | Service Keys | /service-keys | SERVICE_KEY_READ | List, create (show raw key once), delete | GET /api/api-keys → 200; POST /api/api-keys → 200 (SERVICE_KEY_WRITE); DELETE /api/api-keys/{id} → 200 (SERVICE_KEY_DELETE) |PASS-AFTER-FIX| | | |
| 10 | Routing | /routing | ROUTING_READ | List rules w/ pagination; error paths on writes | GET /api/routing?page&per_page → 200; POST /api/routing → 403 (no ROUTING_WRITE); PUT /api/routing/{id} → 403; DELETE /api/routing/{id} → 403 |PASS| | | |
| 11 | HL7 | /hl7 | HL7_READ | Messages w/ filters, detail modal, metrics, status, config (read-only); error on config save | GET /api/hl7/admin/messages?limit&offset&message_type&parse_status → 200; GET /api/hl7/admin/messages/{id} → 200; GET /api/hl7/admin/metrics?period → 200; GET /api/hl7/admin/config → 200; GET /api/hl7/admin/status → 200; PUT /api/hl7/admin/config → 403 (no HL7_WRITE) |PASS| | | |
| 12 | Interface Health | /admin/interfaces | HL7_READ + adminOnly | Interface list, messages, metrics, exception queue, retry | GET /api/ris/interfaces → 200; GET /api/ris/interfaces/{id}/messages → 200; GET /api/ris/interfaces/{id}/metrics → 200; GET /api/ris/interfaces/exceptions → 200; POST /api/ris/interfaces/exceptions/{id}/retry → 403 (gate=HL7_WRITE, INTERFACE_ADMIN is monitor-only) |PASS| | | |
| 13 | DICOMweb Server | /dicomweb | DICOMWEB_READ | Server info, metrics, request log w/ filters/pagination | GET /api/dicomweb/admin → 200; GET /api/dicomweb/admin/metrics?period → 200; GET /api/dicomweb/admin/requests?limit&cursor&kind&status&period → 200 |PASS| | | |
| 14 | DICOMweb Store | /dicomweb/store | DICOMWEB_READ | Upload DICOM → error path | POST /api/dicomweb/studies (STOW-RS multipart) → 403 (no DICOMWEB_WRITE) |PASS| | | |
| 15 | DICOMweb Study Browser | /dicomweb/browser | DICOMWEB_READ | Search studies, expand series/instances, WADO-RS, archive download, Weasis launch | GET /api/dicomweb/studies?PatientName&StudyDate&... → 200; GET /api/dicomweb/studies/{uid}/series → 200; GET /api/dicomweb/studies/{uid}/series/{uid}/instances → 200; WADO-RS instance → 200; GET /api/dicomweb/studies/{uid}/archive (ZIP) → 200; GET /api/weasis/status → 200 |PASS| | | |
| 16 | Billing Queue | /billing/queue | BILLING_READ | Paginated queue, CPT suggestions, patient responsibility; error paths on writes | GET /api/ris/billing/queue?page&per_page → 200; GET /api/ris/billing/cpt-suggestions?procedure → 200; GET /api/ris/billing/patients/{id}/responsibility → 200; POST /api/ris/billing/charges/{id}/drop → 403 (no BILLING_WRITE); POST /api/ris/billing/charges/batch → 403; POST /api/ris/billing/claims/{id}/submit → 403; POST /api/ris/billing/claims/batch-submit → 403 |PASS| | | |
| 17 | Claims | /billing/claims | BILLING_READ | Claim list, history drawer; error paths on submit | GET /api/ris/billing/claims?query → 200; GET /api/ris/billing/claims/{id}/history → 200; POST /api/ris/billing/claims/{id}/submit → 403 |PASS| | | |
| 18 | Revenue | /billing/revenue | BILLING_READ | Collections trend, payer/modality breakdowns | GET /api/ris/billing/revenue?days=30 → 200 |PASS-AFTER-FIX| | | |
| 19 | Unbilled Aging | /billing/unbilled | BILLING_READ | Aging report with grouping | GET /api/ris/billing/unbilled?group_by → 200 |PASS| | | |
| 20 | Denial Rework | /billing/denials | BILLING_READ | Denial list, history; error paths on writes | GET /api/ris/billing/denials → 200; GET /api/ris/billing/claims/{id}/history → 200; POST /api/ris/billing/denials/import → 403 (no BILLING_WRITE); POST /api/ris/billing/claims/{id}/resubmit → 403; POST /api/ris/billing/claims/batch-resubmit → 403 |PASS| | | |
| 21 | Fee Schedule | /billing/fee-schedule | BILLING_READ | Fee schedule list/search, payer contracts, comparison; error paths on writes | GET /api/ris/billing/fee-schedule?code → 200; GET /api/ris/billing/contracts → 200; GET /api/ris/billing/contracts/comparison → 200; GET /api/ris/billing/fee-schedule/history/{code} → 200; PUT /api/ris/billing/fee-schedule/{code} → 403; POST /api/ris/billing/fee-schedule/import → 403; POST /api/ris/billing/contracts → 403; PUT /api/ris/billing/contracts/{id} → 403; DELETE /api/ris/billing/contracts/{id} → 403 |PASS| | | |
| 22 | Reconciliation | /billing/reconciliation | BILLING_READ | Signed-vs-charged snapshot | GET /api/ris/billing/reconciliation → 200 |PASS| | | |
| 23 | Metrics | /metrics | METRICS_READ, ANALYTICS_READ | Totals cards, ingestion chart, modality distribution, system health | GET /api/v2/dashboard/metrics?range=30d → 200; GET /api/v2/dashboard/health → 200 |PASS| | | |

## Excluded routes (planned Phase 4; verified in 5a)
> Note: curl hits on these SPA routes return 500 in dev because the backend's static fallback
> (`./static/index.html`) does not exist here — the frontend is served by Vite on :5173.
> The redirect/block verdicts are verified in the Phase 5b browser walk, not by curl.

| Route | Expected | Actual | Verdict |
|---|---|---|---|---|
| /patients/:id | ClinicalRoute w/ PATIENT_ROUTE_PERMISSIONS + excludedRoles=ADMIN_SCOPED_ROLES → redirect to /admin | | REDIRECT (browser SPA navigates to /admin) |
| /reading | ClinicalRoute w/ REPORT_READ + excludedRoles=ADMIN_SCOPED_ROLES → redirect to /admin | Browser: navigated to /admin | PASS |
| /reading/:examId | ClinicalRoute w/ REPORT_READ + excludedRoles=ADMIN_SCOPED_ROLES → redirect to /admin | | REDIRECT |
| /reading/home | ClinicalRoute w/ REPORT_READ + excludedRoles=ADMIN_SCOPED_ROLES → redirect to /admin | | REDIRECT |
| /reading/progress | ClinicalRoute w/ REPORT_READ + excludedRoles=ADMIN_SCOPED_ROLES → redirect to /admin | | REDIRECT |
| /teaching | ClinicalRoute w/ REPORT_READ + excludedRoles=ADMIN_SCOPED_ROLES → redirect to /admin | | REDIRECT |
| /peer-review | ClinicalRoute w/ PEER_REVIEW_READ + excludedRoles=ADMIN_SCOPED_ROLES → redirect to /admin | | REDIRECT |
| /critical | ClinicalRoute w/ REPORT_READ + excludedRoles=ADMIN_SCOPED_ROLES → redirect to /admin | | REDIRECT |
| /exams | ClinicalRoute w/ EXAM_READ + excludedRoles=ADMIN_SCOPED_ROLES → redirect to /admin | | REDIRECT |
| /exams/:id | ClinicalRoute w/ EXAM_READ + excludedRoles=ADMIN_SCOPED_ROLES → redirect to /admin | | REDIRECT |
| /worklist | ClinicalRoute w/ WORKLIST_READ + excludedRoles=ADMIN_SCOPED_ROLES → redirect to /admin | Browser: navigated to /admin | PASS |
| /tracking | ClinicalRoute w/ WORKLIST_READ + excludedRoles=ADMIN_SCOPED_ROLES → redirect to /admin | | REDIRECT |
| /schedule-board | ClinicalRoute w/ WORKLIST_READ/SCHEDULE_READ + excludedRoles → redirect to /admin | | REDIRECT |
| /schedule | ClinicalRoute w/ SCHEDULE_READ + excludedRoles → redirect to /admin | | REDIRECT |
| /schedule/resources | ClinicalRoute w/ SCHEDULE_READ + excludedRoles → redirect to /admin | | REDIRECT |
| /orders | ClinicalRoute w/ ORDER_READ + excludedRoles → redirect to /admin | | REDIRECT |
| /prior-auth | ClinicalRoute w/ PRIOR_AUTH_READ + excludedRoles → redirect to /admin | | REDIRECT |
| /nursing | ClinicalRoute w/ NURSING_READ + excludedRoles → redirect to /admin | | REDIRECT |
| /care-plans | ClinicalRoute w/ PATIENT_READ + excludedRoles → redirect to /admin | | REDIRECT |
| /communications | ClinicalRoute w/ PATIENT_READ + excludedRoles → redirect to /admin | | REDIRECT |
| /qa/queue | ClinicalRoute w/ QA_READ + excludedRoles → redirect to /admin | Browser: navigated to /admin | PASS |
| /qa/review/:examId | ClinicalRoute w/ QA_READ + excludedRoles → redirect to /admin | | REDIRECT |
| /qa/protocols | ClinicalRoute w/ QA_READ + excludedRoles → redirect to /admin | | REDIRECT |
| /qa/incidents | ClinicalRoute w/ QA_READ + excludedRoles → redirect to /admin | | REDIRECT |
| /qa/actions | ClinicalRoute w/ QA_READ + excludedRoles → redirect to /admin | | REDIRECT |
| /qa/analytics | ClinicalRoute w/ QA_READ + excludedRoles → redirect to /admin | | REDIRECT |
| /frontdesk/registration | ClinicalRoute w/ REGISTRATION_READ + excludedRoles → redirect to /admin | | REDIRECT |
| /frontdesk/schedule | ClinicalRoute w/ SCHEDULE_READ + excludedRoles → redirect to /admin | | REDIRECT |
| /frontdesk/queue | ClinicalRoute w/ QUEUE_READ + excludedRoles → redirect to /admin | | REDIRECT |
| /portal | ClinicalRoute w/ PORTAL_READ + excludedRoles → redirect to /admin | | REDIRECT |
| /portal/* | ClinicalRoute w/ PORTAL_READ + excludedRoles → redirect to /admin | | REDIRECT |
| /admin/staff-schedule | AdminConsoleRoute w/ SCHEDULE_READ + excludedRoles (CLINICAL_SCOPED_ROLES) → redirect to /admin | | REDIRECT |
| /admin/maintenance | PermissionRoute w/ SYSTEM_ADMIN → redirect to /admin | Browser: navigated to /admin | PASS |
| /admin/backups | PermissionRoute w/ SYSTEM_ADMIN → redirect to /admin | | REDIRECT |
| /admin/settings | PermissionRoute w/ SYSTEM_ADMIN → redirect to /admin | | REDIRECT |
| /fhir/config | PermissionRoute w/ SYSTEM_ADMIN → redirect to /admin | | REDIRECT |
| /fhir/monitoring | PermissionRoute w/ SYSTEM_ADMIN → redirect to /admin | | REDIRECT |
| /fhir/docs | PermissionRoute w/ SYSTEM_ADMIN → redirect to /admin | | REDIRECT |
| /integrations | PermissionRoute w/ SYSTEM_ADMIN | REOPENED: gate widened to [SYSTEM_ADMIN, TENANT_ADMIN] (O1) — Webhooks tab hidden for non-SYSTEM_ADMIN | FIXED (O1) |
| /files/:id | PermissionRoute w/ VIEWER_ROUTE_PERMISSIONS (no excludedRoles) → reachable, renders with reduced features for admin-scoped | PASS (browser) | REACHABLE |
| / | PermissionRoute w/ VIEWER_ROUTE_PERMISSIONS (no excludedRoles) → reachable, renders with reduced features for admin-scoped | | |

## Findings & decisions (cross-cutting; appended in ANY phase)
| # | Phase | Finding | Evidence (file:line) | Recommendation | Decision | Commit |
|---|---|---|---|---|---|---|
| F1 | 4 | Files surface (`/` and `/files/:id`) is gated on PermissionRoute with no excludedRoles for admin-scoped roles — tenant_admin can reach it. The Detail viewer renders in reduced-feature mode (hides annotations, reading presets, report actions). The plan premise considered Files "clinically excluded" but code confirms reachable for tenant_admin. | frontend/src/index.tsx:846-861 | KEEP: accurate — enum in Excluded routes table with expected "reachable" verdict; Phase 5 will verify the reduced-feature mode. | | |
| F2 | 5a | Revenue endpoint 500s for all BILLING_READ holders: `by_payer` query references `ris_claims.charge_amount` but the column is `paid_amount`. | backend/api/billing.py:1212 | FIX: use `SUM(paid_amount)` (by_modality/aging correctly use `ris_charges.charge_amount`). | FIX (approved) | (pending) |
| F4 | 5a | PLAN row 12 retry expectation was wrong: the exception-retry endpoint gates `HL7_WRITE`, not INTERFACE_ADMIN. Matches the prior routing-gate decision (Sidebar comment: INTERFACE_ADMIN dropped, backend rejects). tenant_admin holding INTERFACE_ADMIN can monitor but not replay. Corrected plan — no code change. | backend/api/hl7_admin.py (RisInterfaceExceptionRetryHandler), frontend/src/common/Sidebar.tsx routing gate comment | KEEP (consistent with prior decision) | |
| F3 | 5a | API-key creation 500s for every role: `api_keys.created_by` column is UUID but `users.id` is SERIAL integer → `DatatypeMismatchError`. | backend/db/api_keys.py:73; migration 016_api_keys.py:42 | FIX: migration 114 alters `created_by` to BIGINT (table empty, no data cast). | FIX (approved) | (pending) |
| O1 | 5a | ORPHANED surface: tenant_admin holds TENANT_ADMIN and backend `/api/v2/oauth/providers*` returns 200 (verified via curl), but the only UI that calls it (Integrations page) was gated SYSTEM_ADMIN at both the route (`frontend/src/index.tsx:833`) and nav item (`frontend/src/common/Sidebar.tsx:587`) — a granted, tenant-scoped capability (OIDC provider CRUD + test-connection, ADM-16) with no reachable surface. Webhooks backend endpoints are SYSTEM_ADMIN-gated, so widening must not expose them. | backend/api/oauth_providers.py (TENANT_ADMIN gate); frontend/src/integrations/Integrations.tsx:77; frontend/src/api/integrations.ts:23-43 | FIX: route + nav gate widened to [SYSTEM_ADMIN, TENANT_ADMIN]; Webhooks tab rendered conditionally on SYSTEM_ADMIN (default tab = oauth for tenant_admin). Browser-verified: /integrations loads for tenant_admin, only OAuth Providers tab shows, webhooks API still 403. | FIX (approved) | (pending) |
| O2 | 5a | DEAD grants: `STORAGE_ADMIN` and `CDS_ADMIN` are in tenant_admin's (and pacs_admin's) grant set but no route gates on either — only permissions.py references them. Nothing in the backend is unlocked by them. | backend/api/permissions.py (enum + grant sets); grep across backend/api/*.py shows no gate sites | TRIM from MATRIX_C_TENANT_ADMIN (least-privilege). | KEEP (recorded; user chose to keep grants as-is) | — |
| F5 | 5b | RIS Dashboard Workload tab 500s: `by_modality` query references `e.scheduled_date` (does not exist on `exams`) and `by_room` query references `a.room` (does not exist on `ris_appointments`; resource name is in `ris_resources.name` via `resource_id`). Also status values `'scheduled'/'arrived'` don't match the exams CHECK constraint (`'ready'/'in_progress'`). | backend/api/ris_dashboard.py:53-64 (by_modality), 66-82 (by_room); backend/migrations/versions/033_exams.py:46-74 (exams schema), 069_ris_appointments.py:38-68 (ris_appointments schema) | FIX: `e.scheduled_date` → `e.created_at::date`, `e.status IN ('scheduled','arrived')` → `IN ('ready','in_progress')`, `a.room` → `JOIN ris_resources rr ON rr.id = a.resource_id` + `rr.name AS room`. | FIX (approved) | (pending) |
| F6 | 5b | Replicas page crashes with `TypeError: id.slice is not a function` — the API returns `id` as integer (`1`), not string, but the ID column render calls `id.slice(0, 8)`. Replicas is unreachable for every role. | frontend/src/replicas/Replicas.tsx:191; curl confirms `"id": 1` (integer) | FIX: `String(id).slice(0, 8)` | FIX (approved) | (pending) |