# radiologist — Intended Scope (Phase 1)

Date: 2026-08-27
Sources: `frontend/src/navigator.ts`, `backend/api/permissions.py`, `frontend/src/common/Sidebar.tsx`

## Role Profile

| Field | Value |
|---|---|
| Role slug | `radiologist` |
| Workspace | `reading` (ROLE_WORKSPACE: `radiologist: "reading"`) |
| Scope class | clinical-scoped (`CLINICAL_SCOPED_ROLES` includes `radiologist`) |
| Landing route | `/reading` (LANDING_STEPS first `workspace: "reading"` step, gate `REPORT_READ`) |
| Grant set | 23 permissions — `RADIOLOGIST_PERMISSIONS = sorted(LEGACY_RADIOLOGIST \| MATRIX_A_RAD_TEL)`; identical to `teleradiologist` (spec §5) |
| Excluded from | Admin console (all `adminOnly` items + admin permission-gated items), QA (`QA_READ` absent), Billing (`BILLING_READ` absent), Portal (`PORTAL_READ` absent), Metrics (`METRICS_READ` absent), Nursing Prep (`NURSING_READ` absent), Front Desk registration/queue (`REGISTRATION_READ`/`QUEUE_READ` absent), DICOMweb console (`adminOnly` despite holding `DICOMWEB_READ` — legacy) |
| Tenant model | tenant-bound clinical data-plane; holds `CROSS_TENANT_READ` (teleradiology/telemedicine) |
| Seeded login | `acme.radiologist` / `Test@123456` |

## Permission set (23)

`PATIENT_READ`, `ORDER_READ`, `SCHEDULE_READ`, `PRIOR_AUTH_READ`, `WORKLIST_READ`,
`WORKLIST_WRITE`, `REPORT_READ`, `REPORT_WRITE`, `REPORT_SIGN`,
`CRITICAL_RESULTS_WRITE`, `REPORT_TEMPLATE_ADMIN`, `VIEWER_READ`, `STUDY_READ`,
`STUDY_EXPORT`, `CHART_READ`, `RESULTS_READ`, `MED_ORDER_READ`, `CROSS_TENANT_READ`,
`FILE_READ`, `EXAM_READ`, `PEER_REVIEW_READ`, `PEER_REVIEW_WRITE`, `DICOMWEB_READ`.

## Reachable Surfaces (sidebar order)

| # | Section | UI Function | Route | Gate (permissions) | Intended (one line) |
|---|---|---|---|---|---|
| 1 | Reading | Reading Worklist | `/reading` | `REPORT_READ` | Primary landing — list of exams awaiting report, filter/search, open into viewer |
| 2 | Reading | Reading Console | `/reading/:examId` | `REPORT_READ` | Core viewer + reporting: stack viewport, W/L, annotations, measurement, dictation, draft/sign |
| 3 | Reading | Teaching Library | `/teaching` | `REPORT_READ` | Curated teaching-file library (add/remove cases) |
| 4 | Reading | Peer Review | `/peer-review` | `PEER_REVIEW_READ` | Peer-review inbox: assigned reviews, accept/decline, submit score |
| 5 | Reading | Critical Results | `/critical` | `REPORT_READ` | List critical-result flags; acknowledge/deliver |
| 6 | Acquisition | My Exams | `/exams` | `EXAM_READ` | Read-only exam list (technologist console is theirs, but rad can view) |
| 7 | Acquisition | Modality Worklist | `/worklist` | `WORKLIST_READ` | Scheduled-procedure worklist (view) |
| 8 | Acquisition | Tracking Board | `/tracking` | `WORKLIST_READ` | Exam lifecycle tracking board (view) |
| 9 | Acquisition | Schedule | `/schedule-board` | `WORKLIST_READ`\|`SCHEDULE_READ` | Day schedule board (view) |
| 10 | Acquisition | Calendar | `/schedule` | `SCHEDULE_READ` | Resource/appointment calendar (view) |
| 11 | Acquisition | Resources | `/schedule/resources` | `SCHEDULE_READ` | Resource manager (view) |
| 12 | Coordination | Orders | `/orders` | `ORDER_READ` | Order list + detail (read-only) |
| 13 | Coordination | Prior Auth | `/prior-auth` | `PRIOR_AUTH_READ` | Prior-authorization panel (view) |
| 14 | Coordination | Reminders | `/reminders` | `PRIOR_AUTH_READ` | Reminder config/log (view) |
| 15 | Coordination | Care Plans | `/care-plans` | `PATIENT_READ` | Care plans (view) |
| 16 | Coordination | Communications | `/communications` | `PATIENT_READ` | Secure messaging (view) |
| 17 | Admin | Report Templates | `/admin/report-templates` | `REPORT_WRITE` | Template library (read/edit — NOT adminOnly) |
| 18 | Front Desk | Today's Schedule | `/frontdesk/schedule` | `SCHEDULE_READ` | Today's appointments (view, has SCHEDULE_READ) |
| 19 | Files | Files | `/` | `VIEWER_ROUTE_PERMISSIONS` | File/study browser (always-visible entry) |
| 20 | Files | Study/Detail | `/files/:id` | `VIEWER_ROUTE_PERMISSIONS` | Detail viewer + annotations |
| 21 | Patient | Patient | `/patients/:id` | `PATIENT_ROUTE_PERMISSIONS` | Patient chart (view) |
| 22 | Account | Account | `/account` | — | Profile, password, session |
| 23 | Notifications | Notifications bell | — | — | In-app feed |

## Not reachable (by design)

- Admin console (all `adminOnly` items): Dashboard, RIS Dashboard, Staff Schedule, Interface Health, DICOMweb console — excluded by `adminOnly` even with `DICOMWEB_READ`.
- Admin permission-gated: Replicas, Users, Tenants, Roles, Logs, Service Keys, Routing, HL7, FHIR, Integrations, Maintenance, Backups, Settings.
- QA (`/qa/*`), Billing (`/billing/*`), Portal (`/portal*`), Metrics (`/metrics`), Nursing Prep (`/nursing`), Front Desk Registration/Waiting Queue.
- Reading: Resident Home + My Progress (`roles: ["resident"]`).

## Notes for the walk

- The core radiologist workflow is **Reading Worklist → Reading Console → draft/sign report** — the primary surfaces to exercise deeply (viewer, tools, annotations, report lifecycle, sign).
- `REPORT_TEMPLATE_ADMIN` + `REPORT_WRITE` make Report Templates reachable (open to clinical roles too).
- `CROSS_TENANT_READ` means the role may read cross-tenant for teleradiology — verify it stays scoped on data-plane reads (same isolation concern as super_admin but opposite direction).
- Critical Results + Peer Review are radiologist-specific responsibilities (write actions).
