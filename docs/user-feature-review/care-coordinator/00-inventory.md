# 00 — Inventory: care_coordinator (Phase 1)

Date: 2026-08-14 · Role: `test.care_coordinator` / `Test@123456` · Branch: `phase/user-feature-review-care-coordinator` (working tree)

## Role definition (canonical, Matrix B — EMR coordination row)

13 grants — **no drift** (the technologist review's P0-1 fix held; DB row == `BUILT_IN_ROLES`):

```
CARE_PLAN_WRITE, CHART_READ, ENCOUNTER_WRITE, MED_ORDER_READ,
ORDER_READ, ORDER_WRITE, PATIENT_READ, PRIOR_AUTH_READ,
REPORT_READ, RESULTS_READ, SCHEDULE_READ, STUDY_READ, VIEWER_READ
```

### Grant → surface audit

| Grant | Backend gate exists? | UI surface? | Notes |
|---|---|---|---|
| CHART_READ | partial | patient page | chart/encounter timeline not rendered beyond demographics |
| PATIENT_READ | yes | Patient page `/patients/:id` | ✅ works (verified with patient 13) |
| STUDY_READ / VIEWER_READ | yes | study list / viewer | viewer reachable from patient page |
| REPORT_READ / RESULTS_READ | yes | Reading Worklist | renders; 0 rows (all exams final) |
| SCHEDULE_READ | yes | Schedule Board route | **dead end** — board data needs WORKLIST_READ |
| ORDER_READ | yes | none | order list UI absent |
| **ORDER_WRITE** | yes | **none** | **no UI** |
| **CARE_PLAN_WRITE** | yes | **none** | **no UI** |
| **ENCOUNTER_WRITE** | yes | **none** | **no UI** |
| **MED_ORDER_READ** | yes | **none** | **no UI** |
| **PRIOR_AUTH_READ** | yes | **none** | **no UI** |

The five defining grants (`CARE_PLAN_WRITE`, `ORDER_WRITE`, `ENCOUNTER_WRITE`,
`MED_ORDER_READ`, `PRIOR_AUTH_READ`) appear **only as permission labels in
`src/api/roles.ts`** — no component gates on any of them anywhere in `src/`.

## Reachable surfaces (live walkthrough)

Landing: `/reading` (Reading Worklist — the radiologist workspace).

| # | Surface | Route | Status | Evidence |
|---|---|---|---|---|
| 1 | Reading Worklist (landing) | `/reading` | renders, 0 rows | `01-10-reading-worklist.png` |
| 2 | Patient page | `/patients/13` | ✅ demographics + studies + series | `05-14-patient-real.png` |
| 3 | Files page | `/` | **dead end** — `Missing permission: FILE_READ` | `06-15-files-state.png` |
| 4 | Schedule Board | `/schedule-board` | **dead end** — `Failed to load schedule · WORKLIST_READ` | `07-16-schedule-board.png` |
| 5 | Account | `/account` | renders | `04-13-account.png` |
| 6 | Notifications bell | global | renders | — |

### Denial probes (all bounce to `/reading` ✅)
`/exams`, `/worklist`, `/qa/queue`, `/admin`, `/metrics`, `/frontdesk/registration`,
`/frontdesk/queue`, `/portal`, `/roles`, `/users`, `/tenants`, `/logs`, `/replicas`,
`/dicomweb` — all redirect to `/reading`.

Sidebar shows only: Files, Account, Reading (+ bell/dark-mode). No Schedule item
(sidebar gates Schedule on `WORKLIST_READ` per the R13 change) — yet the **route**
gates on `SCHEDULE_READ`, so direct navigation renders a board that then fails to
load its data.

## Live evidence (API level, real token)

```
GET /api/v2/worklist          → 403 Missing permission: WORKLIST_READ
GET /api/v2/files             → 403 Missing permission: FILE_READ
GET /api/v2/patients/13       → 200 (patient + studies render)
GET /api/v2/appointments      → 200 (booking data OK)
GET /api/v2/reports/reading-list → 200 [] (0 rows)
```

Console: 6× `403 Forbidden` (worklist + files list + qido).
