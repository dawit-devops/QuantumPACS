# radiologist — Walk Ledger (Phase 5)

Date: 2026-08-27

| # | UI Function | Route | Permissions | Intended | Actual | Status | Refinement (layer) | Commit |
|---|---|---|---|---|---|---|---|---|
| 1 | Reading Worklist | `/reading` | REPORT_READ | List exams awaiting report | `GET /reports/reading-list` 200 (empty seed) | PASS | — | — |
| 2 | Reading Stats | `/reading` | REPORT_READ | Personal stats | `GET /reports/reading-stats` 200 after fix (was 500: int→str days) | REFINE→PASS | db/reports.py str(int(days)) | `c3ea5e5` |
| 3 | Reading Console | `/reading/:examId` | REPORT_READ | Viewer + report lifecycle | pending browser walk | — | — | — |
| 4 | Teaching Library | `/teaching` | REPORT_READ | Browse/add teaching files | `GET /teaching-files` 200 | PASS | — | — |
| 5 | Peer Review | `/peer-review` | PEER_REVIEW_READ | Inbox, accept/decline, submit | `GET /peer-reviews` 200, `GET /peer-reviews/reviewers` 200 | PASS | — | — |
| 6 | Critical Results | `/critical` | REPORT_READ | Acknowledge flags | `GET /notifications/critical` 200 | PASS | — | — |
| 7 | Report Templates | `/admin/report-templates` | REPORT_WRITE | Library CRUD | `GET /ris/report-templates` 200 | PASS | — | — |
| 8 | Files | `/` | VIEWER | File browser | `GET /files` 200 | PASS | — | — |
| 9 | Exams | `/exams` | EXAM_READ | View exams | `GET /exams` 200 | PASS | — | — |
| 10 | Worklist | `/worklist` | WORKLIST_READ | Modality worklist | `GET /worklist` 200 | PASS | — | — |
| 11 | Tracking | `/tracking` | WORKLIST_READ | Tracking board | `GET /ris/tracking` + `/ris/tracking/kpi` 200 | PASS | — | — |
| 12 | Schedule | `/schedule-board` | WORKLIST_READ/SCHEDULE_READ | Day board | `GET /ris/appointments?date=` 200 | PASS | — | — |
| 13 | Orders | `/orders` | ORDER_READ | Order list | `GET /orders` 200 | PASS | — | — |
| 14 | Prior Auth | `/prior-auth` | PRIOR_AUTH_READ | PA panel | `GET /ris/prior-auth` 200 | PASS | — | — |
| 15 | Reminders | `/reminders` | PRIOR_AUTH_READ | Reminder config/log | `GET /ris/reminders/config` 200 | PASS | — | — |
| 16 | Care Plans | `/care-plans` | PATIENT_READ | Care plans | `GET /ris/care-plans` 200 | PASS | — | — |
| 17 | Communications | `/communications` | PATIENT_READ | Messaging | `GET /ris/communications?patient_id=` requires param (400 w/o) | PASS | — | — |
| 18 | Account | `/account` | — | Profile/prefs | `GET /account/profile|preferences` 200 | PASS | — | — |

## Excluded (verified)
- QA `/qa/queue` → 403, Metrics `/metrics` → 403, Billing `/ris/billing/queue` → 403, admin config/backups/logs/roles/users → 403. Correct.

## Security findings (pending user decision)
1. **Tenants registry leaks DB credentials**: `GET /tenants` returns 200 for radiologist (via CROSS_TENANT_READ, intentional for tenant switcher) but the response includes `db_name/db_host/db_port/db_user` — sensitive infra info to any clinical role. (tenants.py:65-106)
2. **DICOMweb admin API open to radiologist**: `GET /dicomweb/admin` → 200 because radiologist holds legacy DICOMWEB_READ; UI hides the console (adminOnly) but the API is reachable. UI/API scope mismatch. (dicomweb_admin.py gate)

## Phase 5b browser walk results (2026-08-27)

| # | Surface | Route | Result | Notes |
|---|---|---|---|---|
| 1 | Reading Worklist | `/reading` | PASS | CT exams listed, filters, pagination, Continue/Take; auto-refresh |
| 2 | Reading Console | `/reading/:examId` | PASS | Report opened + `report.opened` + `report.images_opened` audit fired; templates loaded (`/reports/templates?modality=CT`); findings/impression textareas; Sign/Preliminary/Critical/Teaching buttons; "No imaging available" (exam has no DICOM) |
| 3 | Peer Review | `/peer-review` | PASS | Empty state correct ("No peer reviews assigned to you yet") |
| 4 | Critical Results | `/critical` | PASS | Empty state correct |
| 5 | Report Templates | `/admin/report-templates` | PASS | Admin section scoped to ONLY Report Templates for radiologist; template list renders; Edit/History buttons |
| 6 | My Exams (Technologist Worklist) | `/exams` | PASS | View-only acquisition surface renders |
| 7 | Orders (Coordination) | `/orders` | PASS | 3 open orders; view-only |
| 8 | Files | `/` | PASS | File browser renders |
| 9 | Admin console exclusion | `/admin` | PASS | Redirects to `/reading` (adminOnly gate) |

Zero console errors across all walked pages.

## Design decisions made by user
1. R2: ENFORCE REPORT_TEMPLATE_ADMIN on template create/publish/rollback (1ff0e7a)
2. R3: ADD PHI read audit (report.opened / images_opened / priors_opened / peer_review.opened) (1ff0e7a)
3. R5: FIX dev `hf` DB (create + migrate) so teleradiologist cross-tenant doesn't 500 (69e45e0)
4. Tenants DB-credential leak → STRIP for non-platform roles (66085fe)
5. DICOMweb admin API → REVERSED: grant radiologist access (remove admin-scoped gate), align sidebar + route to plain DICOMWEB_READ (0f1ff97)
6. R1 (ADR update), R7 (auditor docs) → DEFER
7. **Reading worklist → patient image linkage**: seed a worklist exam linked to the E2E-RAD-CT-1 study (accession + MRN match, no final report) so the demo shows Cornerstone3D rendering actual pixels
8. **Weasis button in ReadingConsole**: add a "Weasis" launch button (gated on weasisEnabled && DICOMWEB_READ && selectedStudy.study_instance_uid) mirroring Detail.tsx — the radiologist can launch the study in the Weasis web viewer from the reading console
