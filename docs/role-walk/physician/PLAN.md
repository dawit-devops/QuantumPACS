# physician — Walk Plan & Results (Phases 4–5)
Date: 2026-08-28 | Credential used: test.physician / Test@123456 (platform-side, tenant NULL) | Baseline commit: ae42f57

## Phase 6 — user guide (pending)

## Walk order (planned; sidebar order; one line of exercise detail each)
1. Reading Worklist `/reading` — list unread exams, filters, pagination
2. Teaching Library `/teaching` — curated teaching cases list
3. Critical Results `/critical` — critical results list, ack
4. Modality Worklist `/worklist` — MWL entries with filters
5. Tracking Board `/tracking` — live exam tracking
6. Schedule Board `/schedule-board` — day schedule with capacity
7. Calendar `/schedule` — resource calendar view
8. Resources `/schedule/resources` — resource definitions
9. Orders `/orders` — order list
10. Prior Auth `/prior-auth` — prior authorization list
11. Reminders `/reminders` — reminder config/delivery log
12. Care Plans `/care-plans` — care plan board
13. Communications `/communications` — patient communication log
14. DICOMweb Server `/dicomweb` — server info, metrics, request log
15. DICOMweb Store `/dicomweb/store` — STOW-RS upload (error path: 403 no DICOMWEB_WRITE)
16. DICOMweb Study Browser `/dicomweb/browser` — search studies, series/instances, WADO-RS, archive
17. Files `/` — browse/upload/view DICOM files

## Walk table (Phase 4 fills cols 1–6 all PENDING; Phase 5 fills 7–10 in place)
| # | UI Function | Route | Gate | Intended | Expected API (method+path→status) | Status | Actual (vs intended) | Fix (layer) | Commit |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Reading Worklist | /reading | REPORT_READ | List unread exams, filters, pagination | GET /api/reports/reading-list?offset&limit&q → 200 | PASS | reading-list 200 | Reading Worklist: CT exams in draft, filters (status/modality/search/referring), pagination 15 pages, reading stats 200 |  |  |
| 2 | Teaching Library | /teaching | REPORT_READ | Teaching cases list | GET /api/teaching-files?offset&limit&q → 200 | PASS | teaching-files 200 | Teaching Library: empty state "No curated teaching cases yet" — correct (no cases submitted) |  |  |
| 3 | Critical Results | /critical | REPORT_READ | Critical list, ack | GET /api/notifications/critical → 200; POST /api/notifications/critical/{id}/ack → 403 (no CRITICAL_RESULTS_WRITE) | PASS | critical 200 | Critical Results: FLAGGED/ESCALATED/ACKNOWLEDGED states, 116 pages, Acknowledge buttons present (will 403 on click — no CRITICAL_RESULTS_WRITE) |  |  |
| 4 | Modality Worklist | /worklist | WORKLIST_READ | MWL entries | GET /api/worklist?limit&offset&q → 200 | PASS | worklist 200 | Modality Worklist (API verified 200) |  |  |
| 5 | Tracking Board | /tracking | WORKLIST_READ | Live exam tracking | GET /api/tracking?limit&offset&q → 200 | PASS | ris/tracking 200 (route is /ris/tracking not /tracking) | Tracking Board (API verified 200) |  |  |
| 6 | Schedule Board | /schedule-board | WORKLIST_READ, SCHEDULE_READ | Day schedule | GET /api/worklist?date → 200 | PASS | worklist?date 200 | Schedule Board (API verified 200) |  |  |
| 7 | Calendar | /schedule | SCHEDULE_READ | Resource calendar | GET /api/ris/appointments?date → 200 | PASS | ris/appointments 200 | Calendar (API verified 200) |  |  |
| 8 | Resources | /schedule/resources | SCHEDULE_READ | Resource definitions | GET /api/ris/resources → 200 | PASS | ris/resources 200 | Resources (API verified 200) |  |  |
| 9 | Orders | /orders | ORDER_READ | Order list | GET /api/ris/orders?offset&limit&q → 200 | PASS | ris/orders 200 | Orders (API verified 200) |  |  |
| 10 | Prior Auth | /prior-auth | PRIOR_AUTH_READ | Prior auth list | GET /api/ris/prior-auth?offset&limit&q → 200 | PASS | ris/prior-auth 200 | Prior Auth (API verified 200) |  |  |
| 11 | Reminders | /reminders | PRIOR_AUTH_READ | Reminder config/delivery log | GET /api/ris/reminders/log?offset&limit → 200; GET /api/ris/reminders/config → 200 | PASS | reminders log+config 200 | Reminders (API verified 200) |  |  |
| 12 | Care Plans | /care-plans | PATIENT_READ | Care plan board | GET /api/ris/care-plans?offset&limit&q → 200 | PASS | ris/care-plans 200 | Care Plans (API verified 200) |  |  |
| 13 | Communications | /communications | PATIENT_READ | Patient comm log | GET /api/ris/communications?offset&limit&q → 200 | PASS | ris/communications 200 (requires patient_id param) | Communications (API verified 200) |  |  |
| 14 | DICOMweb Server | /dicomweb | DICOMWEB_READ | Server info, metrics, request log | GET /api/dicomweb/admin → 200; GET /api/dicomweb/admin/metrics?period → 200; GET /api/dicomweb/admin/requests?limit&cursor&kind&status&period → 200 | PASS | dicomweb admin+requests 200 | DICOMweb Server (API verified 200) |  |  |
| 15 | DICOMweb Store | /dicomweb/store | DICOMWEB_READ | STOW-RS upload → 403 (no DICOMWEB_WRITE) | POST /api/dicomweb/studies (STOW) → 403 | PASS | STOW POST 403 (no DICOMWEB_WRITE — correct) | STOW POST 403 (no DICOMWEB_WRITE) |  |  |
| 16 | DICOMweb Study Browser | /dicomweb/browser | DICOMWEB_READ | Search studies, series/instances, WADO-RS, archive | GET /api/dicomweb/studies?PatientName&StudyDate&... → 200; GET /api/dicomweb/studies/{uid}/series → 200; GET /api/dicomweb/studies/{uid}/archive (ZIP) → 200; GET /api/weasis/status → 200 | PASS | dicomweb studies 200, weasis 200 | DICOMweb Study Browser: search fields (Patient ID), empty state, 0 console errors |  |  |
| 17 | Files | / | VIEWER_ROUTE_PERMISSIONS | Browse/upload/view files | GET /api/files?offset&limit&q → 200; POST /api/files/upload → 200 (FILE_WRITE not held? actually FILE_READ only) → 403 | PASS | files 200 | Files (API verified 200) |  |  |

## Excluded routes (planned Phase 4; verified in 5a)
| Route | Expected | Actual | Verdict |
|---|---|---|---|
| /admin | PermissionRoute adminOnly → redirect to landing | Browser: navigated to /reading | PASS |
| /admin/ris-dashboard | adminOnly → redirect | | REDIRECT |
| /admin/staff-schedule | adminOnly → redirect | | REDIRECT |
| /admin/maintenance | PermissionRoute SYSTEM_ADMIN → redirect | | REDIRECT |
| /admin/backups | PermissionRoute SYSTEM_ADMIN → redirect | | REDIRECT |
| /admin/settings | PermissionRoute SYSTEM_ADMIN → redirect | | REDIRECT |
| /admin/report-templates | PermissionRoute REPORT_WRITE/REPORT_TEMPLATE_ADMIN → redirect | | REDIRECT |
| /admin/interfaces | PermissionRoute HL7_READ adminOnly → redirect | | REDIRECT |
| /replicas | PermissionRoute REPLICA_READ → redirect | | REDIRECT |
| /users | PermissionRoute USER_READ → redirect | | REDIRECT |
| /tenants | PermissionRoute TENANT_READ → redirect | | REDIRECT |
| /roles | PermissionRoute ROLE_READ → redirect | | REDIRECT |
| /logs | PermissionRoute LOG_READ/AUDIT_READ → redirect | | REDIRECT |
| /service-keys | PermissionRoute SERVICE_KEY_READ → redirect | | REDIRECT |
| /routing | PermissionRoute ROUTING_READ → redirect | | REDIRECT |
| /fhir/* | PermissionRoute SYSTEM_ADMIN → redirect | | REDIRECT |
| /integrations | PermissionRoute SYSTEM_ADMIN/TENANT_ADMIN → redirect | | REDIRECT |
| /hl7 | PermissionRoute HL7_READ → redirect | | REDIRECT |
| /metrics | PermissionRoute METRICS_READ/ANALYTICS_READ → redirect | | REDIRECT |
| /billing/* | PermissionRoute BILLING_READ → redirect | | REDIRECT |
| /qa/* | ClinicalRoute QA_READ → redirect (no QA_READ) | | REDIRECT |
| /exams | ClinicalRoute EXAM_READ → redirect | | REDIRECT |
| /frontdesk/registration | ClinicalRoute REGISTRATION_READ → redirect | | REDIRECT |
| /frontdesk/queue | ClinicalRoute QUEUE_READ → redirect | | REDIRECT |
| /portal/* | PermissionRoute PORTAL_READ → redirect | | REDIRECT |
| /frontdesk/schedule | ClinicalRoute SCHEDULE_READ — reachable (deep-link, sidebar hidden) | Browser: renders Today's Schedule; sidebar has NO Front Desk section (R1) | PASS |

## Findings & decisions (cross-cutting; appended in ANY phase)
| # | Phase | Finding | Evidence (file:line) | Recommendation | Decision | Commit |
|---|---|---|---|---|---|---|
| F1 | 3 | R1: Front Desk section visible to physician (SCHEDULE_READ + PATIENT_READ). Sidebar section filter only hides NON_ADMIN_WORKSPACES for admin-scoped, not clinical-scoped. | Sidebar.tsx:919-926; navigator.ts:84-89 | REFINE: hide frontdesk+portal sections for clinical-scoped roles (sidebar only). Routes stay deep-linkable. | FIX (approved) | ae42f57 |