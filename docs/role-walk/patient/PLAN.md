# patient — Walk Plan & Results (Phases 4–5)
Date: 2026-08-29 | Credential used: acme.patient / Test@123456 (tenant-scoped acme) | Baseline commit: 716b84b

## Phase 6 — user guide (pending)

## Walk order (planned; sidebar order; one line of exercise detail each)
1. My Records `/portal` — own patient records view
2. Appointments `/portal/appointments` — own appointments
3. Results `/portal/results` — own test results
4. Follow-ups `/portal/follow-ups` — own follow-up tasks

## Walk table (Phase 4 fills cols 1–6 all PENDING; Phase 5 fills 7–10 in place)
| # | UI Function | Route | Gate | Intended | Expected API (method+path→status) | Status | Actual (vs intended) | Fix (layer) | Commit |
|---|---|---|---|---|---|---|---|---|---|
| 1 | My Records | /portal | PORTAL_READ | Own patient records | GET /api/portal/records → 200 (or similar self-scoped) | PENDING | | | |
| 2 | Appointments | /portal/appointments | PORTAL_READ | Own appointments | GET /api/portal/appointments → 200 | PENDING | | | |
| 3 | Results | /portal/results | PORTAL_READ | Own test results | GET /api/portal/results → 200 | PENDING | | | |
| 4 | Follow-ups | /portal/follow-ups | PORTAL_READ | Own follow-up tasks | GET /api/portal/follow-ups → 200 | PENDING | | | |

## Excluded routes (planned Phase 4; verified in 5a)
| Route | Expected | Actual | Verdict |
|---|---|---|---|
| /admin, /admin/* | adminOnly / PermissionRoute → redirect | | REDIRECT |
| /dicomweb* | PermissionRoute DICOMWEB_READ → redirect | | REDIRECT |
| /billing/* | PermissionRoute BILLING_READ → redirect | | REDIRECT |
| /reading, /teaching, /critical | ClinicalRoute REPORT_READ → redirect | | REDIRECT |
| /qa/* | ClinicalRoute QA_READ → redirect | | REDIRECT |
| /exams | ClinicalRoute EXAM_READ → redirect | | REDIRECT |
| /metrics | PermissionRoute METRICS_READ → redirect | | REDIRECT |
| /frontdesk/* | ClinicalRoute (hidden for patient per R1) → redirect | | REDIRECT |
| /worklist, /tracking, /schedule-board, /schedule, /schedule/resources | ClinicalRoute WORKLIST_READ/SCHEDULE_READ — reachable (deep-link, sidebar hidden per R1) | | REACHABLE |

## Findings & decisions (cross-cutting; appended in ANY phase)
| # | Phase | Finding | Evidence (file:line) | Recommendation | Decision | Commit |
|---|---|---|---|---|---|---|
| F1 | 3 | R1: Acquisition + Front Desk sections visible to patient via SCHEDULE_READ | Sidebar.tsx acquisition+frontdesk items; MATRIX_C_PATIENT has SCHEDULE_READ | REFINE: hide both sections | FIX (approved) | 716b84b |