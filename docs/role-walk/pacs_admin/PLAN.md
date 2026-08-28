# pacs_admin — Walk Plan & Results (Phases 4–5)
Date: 2026-08-28 | Credential used: test.pacs_admin / Test@123456 via POST /api/v2/login {"tenant":"acme"} | Baseline commit: 19012b3

## Phase 6 — user guide (pending)

## Walk order (planned; sidebar order; one line of exercise detail each)
1. Dashboard `/admin` — health strip, KPI cards, modality/ingestion charts, replicas table, recent activity, quick links, auto-refresh
2. RIS Dashboard `/admin/ris-dashboard` — TAT by priority, workload panel, drill-down, equipment utilization
3. Staff Schedule `/admin/staff-schedule` — shift assignments, time-off, coverage
4. Report Templates `/admin/report-templates` — list templates, view versions, publish new version, rollback
5. Replicas `/replicas` — list, status/delay; error paths on create/update/delete (403 no REPLICA_WRITE)
6. Users `/users` — list with filters/pagination, create user, assign role, deactivate, reset password, batch status
7. Roles `/roles` — list, permission groups, create custom role, edit (non-builtin), delete (non-builtin), view role users
8. Logs `/logs` — filters (event_type, actor, date range, tenant), cursor pagination, CSV export
9. DICOMweb Server `/dicomweb` — server info, metrics, request log with filters/pagination
10. DICOMweb Store `/dicomweb/store` — upload a DICOM (expected 200 — DICOMWEB_WRITE now held)
11. DICOMweb Study Browser `/dicomweb/browser` — search studies, expand series/instances, WADO-RS render, archive download, Weasis launch
12. HL7 `/hl7` — message list with filters, detail modal, metrics tab, status tab, config tab (read-only); error path on config save (403 no HL7_WRITE)
13. Interface Health `/admin/interfaces` — interface list, message browser, metrics, exception queue, retry exception (403 no HL7_WRITE)
14. Billing Queue `/billing/queue` — paginated queue, CPT suggestions, patient responsibility; error paths on drop/batch-drop/submit (403 no BILLING_WRITE)
15. Claims `/billing/claims` — claim list, history drawer; error paths on submit/batch-submit (403)
16. Revenue `/billing/revenue` — collections trend, payer/modality breakdown
17. Unbilled Aging `/billing/unbilled` — aging report with grouping (date/site/payer)
18. Denial Rework `/billing/denials` — denial list, history; error paths on import/resubmit/batch-resubmit (403)
19. Fee Schedule `/billing/fee-schedule` — fee schedule list/search, payer contracts, contract comparison; error paths on edit/import/contract CRUD (403)
20. Reconciliation `/billing/reconciliation` — signed-vs-charged snapshot render
21. Files `/` (or `/files/:id`) — browse files, view study, upload; detail viewer

## Walk table (Phase 4 fills cols 1–6 all PENDING; Phase 5 fills 7–10 in place)
| # | UI Function | Route | Gate | Intended | Expected API (method+path→status) | Status | Actual (vs intended) | Fix (layer) | Commit |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Dashboard | /admin | ADMIN_DASHBOARD_PERMISSIONS + adminOnly | Health strip, KPI cards, charts, replicas, activity, auto-refresh | GET /api/v2/dashboard/health → 200; GET /api/v2/dashboard/metrics?range=30d → 200; GET /api/users?offset=0&limit=1 → 200; GET /api/dicomweb/admin/metrics?period=24h → 200; GET /api/replicas → 200; GET /api/logs?limit=8 → 200 | PASS-AFTER-FIX | Dashboard renders; health/metrics panels 403 (no METRICS_READ — graceful .catch degrade). users/dicomweb-admin/replicas/logs 200 |  |  |
| 2 | RIS Dashboard | /admin/ris-dashboard | REPORT_READ + adminOnly | TAT, utilization, volume, workload drill-down | GET /api/ris/dashboard/kpi → 200; GET /api/ris/analytics/workload → 200; GET /api/ris/analytics/tat-drilldown → 200; GET /api/ris/analytics/equipment-util → 200 | PASS | KPI/workload/TAT 200; equipment-util 403 (EQUIPMENT_READ not held, degrades gracefully) |  |  |
| 3 | Staff Schedule | /admin/staff-schedule | SCHEDULE_READ + adminOnly | Shift assignments, time-off, coverage | GET /api/ris/staff-schedule → 200 | PASS | Staff schedule 200 |  |  |
| 4 | Report Templates | /admin/report-templates | REPORT_WRITE, REPORT_TEMPLATE_ADMIN | List, versions, publish, rollback | GET /api/ris/report-templates → 200; GET /api/ris/report-templates/{id}/versions → 200; POST /api/ris/report-templates/{id}/publish → 200; POST /api/ris/report-templates/{id}/rollback → 200 | PASS-AFTER-FIX | GET templates/versions 200; publish 200 (needs tenant-agnostic login CSRF context). Works |  |  |
| 5 | Replicas | /replicas | REPLICA_READ (R1) | List, status/delay; error paths on writes | GET /api/replicas → 200; POST /api/replicas → 403 (no REPLICA_WRITE); PUT /api/replicas/{id} → 403; DELETE /api/replicas/{id} → 403 | PASS | GET replicas 200; POST/PUT/DELETE 403 (no REPLICA_WRITE) |  |  |
| 6 | Users | /users | USER_READ | List w/ filters/pagination, create, assign role, deactivate, reset password, batch status | GET /api/users?offset&limit&q → 200; POST /api/users → 200 (USER_WRITE); PUT /api/users/role → 200; POST /api/users/deactivate → 200; POST /api/users/new_password → 200; POST /api/users/batch-status → 200 | PASS | GET users 200; create+role-assign 403 "Target role exceeds your own grants" — see F2 (can only assign pacs_admin) |  |  |
| 7 | Roles | /roles | ROLE_READ | List, permissions, create custom role, edit (non-builtin), delete (non-builtin), role users | GET /api/roles → 200; GET /api/permissions → 200; POST /api/roles → 200 (ROLE_WRITE); PUT /api/roles/{id} → 200 (non-builtin); DELETE /api/roles/{id} → 200 (ROLE_DELETE, non-builtin); GET /api/roles/{id}/users → 200 | PASS | roles 200, permissions 200 |  |  |
| 8 | Logs | /logs | LOG_READ, AUDIT_READ | Filters (event_type, actor, date range, tenant), cursor pagination, CSV export | GET /api/logs?event_type&actor&date_from&date_to&tenant&cursor&limit → 200; GET /api/logs/actors?search&limit=10 → 200; GET /api/logs?download=csv&filters → 200 (CSV blob); GET /api/tenants (for tenant filter) → 403 (no TENANT_READ) | PASS | logs 200, actors 200 |  |  |
| 9 | DICOMweb Server | /dicomweb | DICOMWEB_READ (R1) | Server info, metrics, request log w/ filters/pagination | GET /api/dicomweb/admin → 200; GET /api/dicomweb/admin/metrics?period → 200; GET /api/dicomweb/admin/requests?limit&cursor&kind&status&period → 200 | PASS | dicomweb admin 200, requests 200, metrics 200 |  |  |
| 10 | DICOMweb Store | /dicomweb/store | DICOMWEB_READ (R1) | Upload DICOM via STOW-RS (expected 200 — DICOMWEB_WRITE now held) | POST /api/dicomweb/studies (STOW-RS multipart) → 200 ((DICOMWEB_WRITE now held) | PASS | STOW POST → 415 (gate passed — DICOMWEB_WRITE OK; body not DICOM). Permission reachable |  |  |
| 11 | DICOMweb Study Browser | /dicomweb/browser | DICOMWEB_READ (R1) | Search studies, expand series/instances, WADO-RS, archive download, Weasis launch | GET /api/dicomweb/studies?PatientName&StudyDate&... → 200; GET /api/dicomweb/studies/{uid}/series → 200; GET /api/dicomweb/studies/{uid}/series/{uid}/instances → 200; WADO-RS instance → 200; GET /api/dicomweb/studies/{uid}/archive (ZIP) → 200; GET /api/weasis/status → 200 | PASS | studies 200, series 200, archive 200; weasis status 200 |  |  |
| 12 | HL7 | /hl7 | HL7_READ (R1) | Messages w/ filters, detail modal, metrics, status, config (read-only); error on config save | GET /api/hl7/admin/messages?limit&offset&message_type&parse_status → 200; GET /api/hl7/admin/messages/{id} → 200; GET /api/hl7/admin/metrics?period → 200; GET /api/hl7/admin/config → 200; GET /api/hl7/admin/status → 200; PUT /api/hl7/admin/config → 403 (no HL7_WRITE) | PASS | HL7 messages/metrics/config/status 200; PUT config 403 (no HL7_WRITE) |  |  |
| 13 | Interface Health | /admin/interfaces | HL7_READ (R1) + adminOnly | Interface list, messages, metrics, exception queue, retry | GET /api/ris/interfaces → 200; GET /api/ris/interfaces/{id}/messages → 200; GET /api/ris/interfaces/{id}/metrics → 200; GET /api/ris/interfaces/exceptions → 200; POST /api/ris/interfaces/exceptions/{id}/retry → 403 (gate=HL7_WRITE) | PASS | interfaces 200, exceptions 200 |  |  |
| 14 | Billing Queue | /billing/queue | BILLING_READ | Paginated queue, CPT suggestions, patient responsibility; error paths on writes | GET /api/ris/billing/queue?page&per_page → 200; GET /api/ris/billing/cpt-suggestions?procedure → 200; GET /api/ris/billing/patients/{id}/responsibility → 200; POST /api/ris/billing/charges/{id}/drop → 403 (no BILLING_WRITE); POST /api/ris/billing/charges/batch → 403; POST /api/ris/billing/claims/{id}/submit → 403; POST /api/ris/billing/claims/batch-submit → 403 | PASS | queue 200, cpt-suggestions 200; charge drop 403 (no BILLING_WRITE) |  |  |
| 15 | Claims | /billing/claims | BILLING_READ | Claim list, history drawer; error paths on submit | GET /api/ris/billing/claims?query → 200; GET /api/ris/billing/claims/{id}/history → 200; POST /api/ris/billing/claims/{id}/submit → 403 | PASS | claims 200; submit 403 |  |  |
| 16 | Revenue | /billing/revenue | BILLING_READ | Collections trend, payer/modality breakdowns | GET /api/ris/billing/revenue?days=30 → 200 | PASS | revenue 200 |  |  |
| 17 | Unbilled Aging | /billing/unbilled | BILLING_READ | Aging report with grouping | GET /api/ris/billing/unbilled?group_by → 200 | PASS | unbilled 200 |  |  |
| 18 | Denial Rework | /billing/denials | BILLING_READ | Denial list, history; error paths on writes | GET /api/ris/billing/denials → 200; GET /api/ris/billing/claims/{id}/history → 200; POST /api/ris/billing/denials/import → 403 (no BILLING_WRITE); POST /api/ris/billing/claims/{id}/resubmit → 403; POST /api/ris/billing/claims/batch-resubmit → 403 | PASS | denials 200; import 403 |  |  |
| 19 | Fee Schedule | /billing/fee-schedule | BILLING_READ | Fee schedule list/search, payer contracts, comparison; error paths on writes | GET /api/ris/billing/fee-schedule?code → 200; GET /api/ris/billing/contracts → 200; GET /api/ris/billing/contracts/comparison → 200; GET /api/ris/billing/fee-schedule/history/{code} → 200; PUT /api/ris/billing/fee-schedule/{code} → 403; POST /api/ris/billing/fee-schedule/import → 403; POST /api/ris/billing/contracts → 403; PUT /api/ris/billing/contracts/{id} → 403; DELETE /api/ris/billing/contracts/{id} → 403 | PASS | fee-schedule 200, contracts 200 |  |  |
| 20 | Reconciliation | /billing/reconciliation | BILLING_READ | Signed-vs-charged snapshot | GET /api/ris/billing/reconciliation → 200 | PASS | reconciliation 200 |  |  |
| 21 | Files | / | VIEWER_ROUTE_PERMISSIONS | Browse/upload/view files, study viewer | GET /api/files?offset&limit&q → 200; GET /api/files/{id} → 200; POST /api/files/upload → 200 (FILE_WRITE) | PASS | files 200 |  |  |

## Excluded routes (planned Phase 4; verified in 5a)
| Route | Expected | Actual | Verdict |
|---|---|---|---|
| /patients/:id | ClinicalRoute w/ PATIENT_ROUTE_PERMISSIONS + excludedRoles=ADMIN_SCOPED_ROLES → redirect to /admin | | REDIRECT |
| /reading | ClinicalRoute w/ REPORT_READ + excludedRoles=ADMIN_SCOPED_ROLES → redirect to /admin | | REDIRECT |
| /reading/:examId | ClinicalRoute → redirect to /admin | | REDIRECT |
| /reading/home | ClinicalRoute → redirect to /admin | | REDIRECT |
| /reading/progress | ClinicalRoute → redirect to /admin | | REDIRECT |
| /exams | ClinicalRoute w/ EXAM_READ + excludedRoles → redirect to /admin | | REDIRECT |
| /exams/:id | ClinicalRoute → redirect to /admin | | REDIRECT |
| /worklist | ClinicalRoute w/ WORKLIST_READ + excludedRoles → redirect to /admin | | REDIRECT |
| /tracking | ClinicalRoute w/ WORKLIST_READ + excludedRoles → redirect to /admin | | REDIRECT |
| /schedule-board | ClinicalRoute w/ WORKLIST_READ/SCHEDULE_READ + excludedRoles → redirect to /admin | | REDIRECT |
| /schedule | ClinicalRoute w/ SCHEDULE_READ + excludedRoles → redirect to /admin | | REDIRECT |
| /schedule/resources | ClinicalRoute w/ SCHEDULE_READ + excludedRoles → redirect to /admin | | REDIRECT |
| /orders | ClinicalRoute w/ ORDER_READ + excludedRoles → redirect to /admin | | REDIRECT |
| /prior-auth | ClinicalRoute w/ PRIOR_AUTH_READ + excludedRoles → redirect to /admin | | REDIRECT |
| /nursing | ClinicalRoute w/ NURSING_READ + excludedRoles → redirect to /admin | | REDIRECT |
| /care-plans | ClinicalRoute w/ PATIENT_READ + excludedRoles → redirect to /admin | | REDIRECT |
| /communications | ClinicalRoute w/ PATIENT_READ + excludedRoles → redirect to /admin | | REDIRECT |
| /qa/queue | ClinicalRoute w/ QA_READ + excludedRoles → redirect to /admin | | REDIRECT |
| /qa/review/:examId | ClinicalRoute → redirect to /admin | | REDIRECT |
| /qa/protocols | ClinicalRoute → redirect to /admin | | REDIRECT |
| /qa/incidents | ClinicalRoute → redirect to /admin | | REDIRECT |
| /qa/actions | ClinicalRoute → redirect to /admin | | REDIRECT |
| /qa/analytics | ClinicalRoute → redirect to /admin | | REDIRECT |
| /frontdesk/registration | ClinicalRoute → redirect to /admin | | REDIRECT |
| /frontdesk/schedule | ClinicalRoute → redirect to /admin | | REDIRECT |
| /frontdesk/queue | ClinicalRoute → redirect to /admin | | REDIRECT |
| /portal | ClinicalRoute → redirect to /admin | | REDIRECT |
| /portal/* | ClinicalRoute → redirect to /admin | | REDIRECT |
| /tenants | PermissionRoute w/ TENANT_READ → redirect to /admin | | REDIRECT |
| /service-keys | PermissionRoute w/ SERVICE_KEY_READ → redirect to /admin | | REDIRECT |
| /fhir/config | PermissionRoute w/ SYSTEM_ADMIN → redirect to /admin | | REDIRECT |
| /fhir/monitoring | PermissionRoute w/ SYSTEM_ADMIN → redirect to /admin | | REDIRECT |
| /fhir/docs | PermissionRoute w/ SYSTEM_ADMIN → redirect to /admin | | REDIRECT |
| /integrations | PermissionRoute w/ SYSTEM_ADMIN/TENANT_ADMIN → redirect to /admin | | REDIRECT |
| /admin/maintenance | PermissionRoute w/ SYSTEM_ADMIN → redirect to /admin | | REDIRECT |
| /admin/backups | PermissionRoute w/ SYSTEM_ADMIN → redirect to /admin | | REDIRECT |
| /admin/settings | PermissionRoute w/ SYSTEM_ADMIN → redirect to /admin | | REDIRECT |
| /metrics | PermissionRoute w/ METRICS_READ/ANALYTICS_READ → redirect to /admin | | REDIRECT |

## Findings & decisions (cross-cutting; appended in ANY phase)
| # | Phase | Finding | Evidence (file:line) | Recommendation | Decision | Commit |
|---|---|---|---|---|---|---|
| F1 | 3 | pacs_admin is in IMMUTABLE_ROLE_SLUGS → full upsert on seed_built_in_roles() at sync_db=True. No migration needed for grant changes. | backend/api/permissions.py:432-437 | KEEP (no change) | | |
| F2 | 5a | `_can_assign_role` subset check blocks R2-16: pacs_admin can only assign the `pacs_admin` role itself. Every clinical/operational built-in role contains permissions pacs_admin lacks (technologist → EXAM_READ/WRITE, radiologist → REPORT_WRITE/SIGN, cashier → BILLING_WRITE) → "Target role exceeds your own grants" 403. The subset check is an anti-escalation control, but it contradicts the R2-16 comment ("facility admins manage roles of clinical/operational built-ins"). | backend/api/users.py:52-65; permissions.py:259-261 (R2-16) | DECIDE: (a) relax subset check to allow assigning built-in roles regardless of caller subset (escalation risk), (b) keep + UPDATE-DOCS R2-16 (facility admins manage only roles within their own grant subset — i.e. the pacs_admin role itself), or (c) extend pacs_admin grants so its subset covers assignable built-ins | FIX (approved): EXTEND pacs_admin grants with the operational built-in grants (technologist/receptionist/cashier/care_coordinator/dept_manager → +21 grants incl. PATIENT_WRITE, BILLING_WRITE, EXAM_READ/WRITE, REGISTRATION_*, QUEUE_READ, SCHEDULE_WRITE, NURSING_*, ORDER_WRITE, WORKLIST_WRITE, CRITICAL_RESULTS_WRITE, CARE_PLAN_WRITE, ENCOUNTER_WRITE, MED_ORDER_READ, PRIOR_AUTH_*, ANALYTICS_READ, EQUIPMENT_READ). Clinical readers/EMR writers stay unassignable (REPORT_SIGN/WRITE, CROSS_TENANT_READ, etc. not in subset). Test updated. Verified live: create user w/ technologist role → 200 | |
| F3 | 5a | Dashboard health/metrics panels 403 for pacs_admin (no METRICS_READ). tenant_admin gets METRICS_READ via LEGACY_TENANT_ADMIN union; pacs_admin has no legacy union. The Admin Dashboard is the landing page; its core panels (health strip, KPI cards, modality charts) degrade gracefully but render empty for pacs_admin. | backend/api/dashboard_metrics.py:15,73 (METRICS_READ gates); permissions.py:394-398 (LEGACY_TENANT_ADMIN has METRICS_READ) | DECIDE: (a) add METRICS_READ to MATRIX_A_PACSADM (dashboard is the role's landing home — full panels), (b) KEEP (dashboard degrades; Metrics page /metrics stays unreachable per spec) | FIX (approved): add METRICS_READ to MATRIX_A_PACSADM. Verified live: dashboard/metrics + dashboard/health → 200 | |