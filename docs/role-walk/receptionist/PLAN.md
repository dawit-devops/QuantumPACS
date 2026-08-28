# receptionist — Walk Plan & Results (Phases 4–5)
Date: 2026-08-29 | Credential used: acme.receptionist / Test@123456 (tenant-scoped acme) | Baseline commit: d92268c

## Phase 6 — user guide (pending)

## Walk order (planned; sidebar order; one line of exercise detail each)
1. Registration `/frontdesk/registration` — patient search, create patient, register
2. Today's Schedule `/frontdesk/schedule` — day appointments, filters
3. Waiting Queue `/frontdesk/queue` — privacy-projected queue
4. Patient Search (action) — global patient search overlay
5. Orders `/orders` — order list (Coordination, kept per R1)
6. Care Plans `/care-plans` — care plan board (Coordination)
7. Communications `/communications` — patient comm log (Coordination)

## Walk table (Phase 4 fills cols 1–6 all PENDING; Phase 5 fills 7–10 in place)
| # | UI Function | Route | Gate | Intended | Expected API (method+path→status) | Status | Actual (vs intended) | Fix (layer) | Commit |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Registration | /frontdesk/registration | REGISTRATION_READ | Patient search/create/register | GET /api/patients/search?q → 200; POST /api/patients → 200 (PATIENT_WRITE); GET /api/ris/patients/search?q → 200 | PASS | patients/search 200; ris/patients/search 200; POST /api/patients 201 (sex=M; note: schema field is sex not gender — wrong field 500s via patients_sex_check) |  |  |
| 2 | Today's Schedule | /frontdesk/schedule | SCHEDULE_READ | Day appointments | GET /api/ris/appointments?date → 200 | PASS | ris/appointments 200 |  |  |
| 3 | Waiting Queue | /frontdesk/queue | QUEUE_READ | Privacy queue | GET /api/frontdesk/queue → 200 | PASS | /queue 200 (route is /queue not /frontdesk/queue) |  |  |
| 4 | Patient Search | (action) | PATIENT_READ | Global search overlay | GET /api/patients/search?q → 200 | PASS | patients/search 200 |  |  |
| 5 | Orders | /orders | ORDER_READ | Order list | GET /api/ris/orders?offset&limit&q → 200 | PASS | ris/orders 200 |  |  |
| 6 | Care Plans | /care-plans | PATIENT_READ | Care plan board | GET /api/ris/care-plans?offset&limit&q → 200 | PASS | ris/care-plans 200 |  |  |
| 7 | Communications | /communications | PATIENT_READ | Patient comm log | GET /api/ris/communications?patient_id&limit → 200 | PASS | ris/communications 200 |  |  |

## Excluded routes (planned Phase 4; verified in 5a)
| Route | Expected | Actual | Verdict |
|---|---|---|---|
| /admin, /admin/* | adminOnly / PermissionRoute → redirect | | REDIRECT |
| /dicomweb* | PermissionRoute DICOMWEB_READ → redirect | | REDIRECT |
| /billing/* | PermissionRoute BILLING_READ → redirect | | REDIRECT |
| /reading, /teaching, /critical | ClinicalRoute REPORT_READ → redirect | | REDIRECT |
| /qa/* | ClinicalRoute QA_READ → redirect | | REDIRECT |
| /exams | ClinicalRoute EXAM_READ → redirect | | REDIRECT |
| /portal/* | PermissionRoute PORTAL_READ → redirect | | REDIRECT |
| /metrics | PermissionRoute METRICS_READ → redirect | | REDIRECT |
| /worklist, /tracking, /schedule-board, /schedule, /schedule/resources | ClinicalRoute WORKLIST_READ/SCHEDULE_READ — reachable (deep-link, sidebar hidden per R1) | | REACHABLE |

## Findings & decisions (cross-cutting; appended in ANY phase)
| # | Phase | Finding | Evidence (file:line) | Recommendation | Decision | Commit |
|---|---|---|---|---|---|---|
| F1 | 3 | R1: Acquisition section visible to receptionist (WORKLIST_READ/SCHEDULE_READ pass). Coordination (Orders/Care Plans/Comms) also visible (ORDER_READ/PATIENT_READ). | Sidebar.tsx acquisition+coordination items; MATRIX_A_RECEPT | REFINE: hide Acquisition; keep Coordination (Orders used in registration flow) | FIX (approved) | d92268c |

| F2 | 5a | Patient registration POST /api/patients: the CreatePatientRequest schema field is `sex` (M/F/O), not `gender`. Sending `gender` silently defaults to empty string → CheckViolationError `patients_sex_check` → 500 instead of a validation error. The frontend uses `sex` correctly, so this only bites API callers using the wrong field name. | backend/api/schemas/frontdesk.py:11 (sex field); backend/migrations/versions/002_schema_harden.py:58 (patients_sex_check) | KEEP (no change) — the schema is correct; a wrong-field 500 for hand-rolled callers is acceptable, but consider a friendlier validation. | | |