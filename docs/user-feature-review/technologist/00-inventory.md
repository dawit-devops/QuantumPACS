# 00 — Inventory: What the technologist actually has (technologist)

Phase 1 of `user-feature-review technologist`. Role resolved from
`BUILT_IN_ROLES` (Matrix A imaging row) and walked live as `test.technologist`
/ `Test@123456`. Evidence in `docs/user-feature-review/technologist/evidence/`.

---

## Role & grants

**Canonical grants (15)** — `MATRIX_A_TECH ∪ LEGACY_TECHNOLOGIST`:

```
CHART_READ, CRITICAL_RESULTS_WRITE, DICOMWEB_READ, EXAM_READ, EXAM_WRITE,
FILE_READ, FILE_WRITE, ORDER_READ, PATIENT_READ, RESULTS_READ, SCHEDULE_READ,
STUDY_READ, VIEWER_READ, WORKLIST_READ, WORKLIST_WRITE
```

Landing (navigator.ts): `/exams` — workspace **acquisition**. Clinical-scoped
role: admin-console surfaces are hidden even where a legacy grant
(`DICOMWEB_READ`) passes.

## ⚠️ Dev-environment data drift (read this first)

The **dev DB's** `roles.permissions` for `technologist` carries **92 grants**
(updated 2026-08-13 — after migration 048's trim on 08-09). Same for
`radiologist` (92), `resident` (27 vs canonical 18), `cashier` (8 vs 7).
Login mints tokens from the **DB role row** (`db/users.get_user_role`), not
`BUILT_IN_ROLES`, so the live walkthrough below reflects the inflated role.
Canonical-reachability is verified from the route/sidebar gates in code;
the browser evidence shows the drift consequence (Reading/QA/Admin/Front
Desk/Portal all render for the test user).

## Canonical reachable surfaces (by gate)

| # | Surface | Route | Gate | API calls | Live evidence |
|---|---------|-------|------|-----------|---------------|
| 1 | **My Exams** (Technologist Worklist) | `/exams` | EXAM_READ | `GET /exams` (status/modality/search; `per_page=500` for tab counts) | `10-exams-worklist.png` |
| 2 | **Exam Console** | `/exams/:id` | EXAM_READ (writes EXAM_WRITE) | `exams/{id}`, `identity-confirm`, `protocol`, `acquisitions`, `acquisitions/{id}/accept\|reject`, `safety-checks`, `complete`, `incidents`, `overrides`, `protocols` | `12-exam-console.png` |
| 3 | **Modality Worklist** (DICOM MWL) | `/worklist` | WORKLIST_READ | `GET /worklist` (+ create: WORKLIST_WRITE) | `13-modality-worklist.png` |
| 4 | **Schedule Board** | `/schedule-board` | SCHEDULE_READ (route) / WORKLIST_READ (sidebar) | `GET /worklist` day data | `14-schedule-board.png` |
| 5 | **Files** (study browser) | `/` | FILE_READ\|STUDY_READ\|VIEWER_READ | `POST /api/files` (ES search) | `17-files.png` |
| 6 | **Viewer** | `/files/:id` | VIEWER_ROUTE_PERMISSIONS | WADO `/files/{id}` pixels | (via files rows) |
| 7 | **Patient page** | `/patients/:id` | PATIENT_READ | patient + chart endpoints | — |
| 8 | **Account** (incl. notification prefs) | `/account` | auth-only | `notifications/preferences` | `16-account.png` |

## What the canonical role CANNOT reach (all redirect to `/exams` via PermissionRoute)

- Reading workspace: `/reading`, `/reading/home`, `/peer-review` (REPORT_READ / PEER_REVIEW_READ absent)
- QA workspace: `/qa/*` (QA_READ absent)
- Admin console: `/admin`, `/replicas`, `/users`, `/roles`, `/tenants`, `/logs`,
  `/service-keys`, `/routing`, `/hl7`, `/fhir/*`, `/integrations`, `/dicomweb`*
  (*adminOnly scope gate closes it despite the legacy DICOMWEB_READ grant),
  `/admin/maintenance|backups|settings`
- Front Desk: `/frontdesk/*` (REGISTRATION_READ / QUEUE_READ absent)
- Portal: `/portal` (PORTAL_READ absent)
- Metrics: `/metrics` (METRICS_READ / ANALYTICS_READ absent)

## Walkthrough highlights (as `test.technologist`, 2026-08-14)

**My Exams (`/exams`)** — the landing. 3 assigned rows (RES-ACC-001,
E2E-RAD-MR-1, E2E-RAD-CT-1), columns Priority/Accession/Patient/Modality/
Protocol/Status/Elapsed. Strengths observed live:
- 30s auto-refresh (`useVisibilityGatedInterval` — pauses when hidden)
- **aria-live arrival announcements** by accession (`tech-wl-live` region)
- status chips with live per-status counts (whole assignment, not just page)
- elapsed-time tags color-coded (gold ≥15m, orange ≥30m)
- filters persisted in `sessionStorage` across the console round-trip
- STATUS priority sort (STAT → urgent → routine), red STAT tag

**Exam Console (`/exams/:id`)** — 5-step workflow (Verify Patient → Protocol →
Acquire & QA → Dose & Safety → Complete). Write actions verified live
(EXAM_WRITE): Confirm Patient, Start Protocol, Acquire Image, Accept/Reject,
Retake, Log Incident, Emergency Override, Record Safety Checks, Complete Exam.
Right rail: cumulative dose ledger + per-series table + ACR benchmark progress
bar (warning/exception states), per-item safety checkboxes (pregnancy carries
an ionizing-radiation warning), complete-with-handoff card. Reject reasons map
onto incident types; rejected acquisitions keep Retake / Log Incident actions.
Ctrl+Shift+W returns to the worklist from anywhere.

**Modality Worklist (`/worklist`)** — 14 entries, Table/Calendar views,
station-AE filter, **Create Entry** modal (WORKLIST_WRITE) with patient /
accession / procedure / modality / scheduled date-time / station AE fields.

**Schedule Board (`/schedule-board`)** — day view with modality columns
(CT/MR/PET/DX/MG/US/FL), 2 performed / 0 scheduled today, Book Appointment
(blocked for the canonical role — SCHEDULE_WRITE absent).

**Files (`/`)** — 10 study rows render (ES is up in this env); search,
advanced, upload, download.

**Notification bell** — renders, empty inbox, "Manage notification
preferences" links to `/account/notifications` (12 toggles).

## Drift consequence (browser-verified)

With the inflated 92-grant role the sidebar renders **every** section
(Reading, QA, Admin, Front Desk, My Records, Metrics) and `/qa/queue` shows a
real QA queue (PROBE-ACC-1 pending). The Account page renders **94 permission
tags** vs the canonical 15. This is a test-infrastructure integrity problem —
see `03-handoff.md` P0-1.

## Console / network

- Zero `pageerror`s on any surface; only pre-existing antd v6 deprecation
  warnings (`Alert message`, `Statistic valueStyle`, `Space direction`).
- No failed API requests observed (ES up, backend healthy).

## Evidence files

`00-landing-exams.png` · `10-exams-worklist.png` · `11-exams-completed-filter.png`
· `12-exam-console.png` · `13-modality-worklist.png` · `14-schedule-board.png`
· `15-files.png` · `16-account.png` · `17-files.png` · `18-bell.png` ·
`19-mwl-create.png` · `20-qa-queue-drift.png` (+ `walkthrough.log` if present)
