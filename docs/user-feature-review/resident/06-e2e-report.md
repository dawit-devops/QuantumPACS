# 06 — E2E Report (resident)

Phase 4 of user-feature-review/resident. Real-backend Playwright suite
(`frontend/e2e/resident-workflow.spec.ts`, `--project=chromium`) run as
`test.resident` against the live stack (frontend :5173, backend :8080) plus
exploratory chrome-devtools walk (screenshots in `evidence/`).

## Results — pass/fail keyed by acceptance criteria (03-handoff.md)

| Hand-off item | AC | Result | Evidence |
|---------------|----|--------|----------|
| P0-1 Schedule Board | 1. `/schedule-board` renders day data, no "Missing permission" banner | **PASS** | spec P0-1; `evidence/06-schedule-board-rendered.png` |
| P0-1 | 2. Role without SCHEDULE_READ: Schedule item hidden | **PASS** (pre-existing gate unchanged) | sidebar gate now on WORKLIST_READ; route gate SCHEDULE_READ |
| P0-1 | 3. No regression for clinical roles (worklist 200) | **PASS** | spec P0-1 asserts `GET /api/worklist` → 200 |
| P0-2 Claimed today | 1. Today-scoped count ≠ queue total | **PASS** | spec P0-2; live: "Claimed today: 1" with queue 0 (old code showed total) — `evidence/07-resident-home-claimed-today.png` |
| P0-2 | 2. Total still visible as "Total claimed" | **PASS** | spec P0-2 asserts label |
| P0-2 | 3. Backend exposes `claimed_today` (no frontend date-math) | **PASS** | spec P0-2 asserts `typeof body.claimed_today === "number"` |
| P1-1 Needs-revision filter | 1. Filter includes `returned` value | **PASS** | spec P1-1 dropdown "needs revision"; `evidence/08-worklist-revision-filter.png` |
| P1-1 | 2. API accepts `status=returned` (draft + review_feedback) | **PASS** | spec P1-1: `GET /api/reports/reading-list?status=returned` → 200 |
| P1-1 | 3. Rows show "Returned" tag with tooltip | **PASS** (pre-existing row rendering, verified in Phase 1) | ResidentHome `Returned` volcano tag |
| P1-2 a11y | 1. No "id or name attribute" console issue on `/reading` | **PASS** | spec P1-2 console listener, zero issues |
| P1-2 | 2. Programmatically associated labels | **PASS** | spec P1-2: comboboxes "Report status"/"Modality" |
| P2-1 Teaching Library | Guided empty state (option a: hide, or guided copy) | **PASS** | spec P2-1: guided copy + no bare "coming soon" |
| P2-2 Notification link | Notification links to `/reading/{examId}` | **PASS** (pre-existing) | spec P2-2 (light check); link payload verified in Phase 3 (`/reading/{exam_id}` in notify_user) |

## Coverage of full flow

- Login as `test.resident` (real UI) → Resident Home → Schedule Board
  (Acquisition) → Reading Worklist (filters incl. needs revision) →
  Teaching Library card → notifications bell.
- Error paths: worklist API 200 as resident (no 403 dead-end regression);
  a11y console monitoring on `/reading`.

## Regressions found in pre-existing surfaces

None. Full pytest suite (1645 passed), ruff, and `tsc --noEmit` green;
receptionist/technologist E2E suites untouched (Schedule sidebar item now
requires WORKLIST_READ — receptionist holds it, per Matrix A; technologist
holds it; no visibility regression).

## Pre-existing failure surfaced (backlogged — not caused by this branch)

`e2e/role-based-access.spec.ts` "Admin deep-link denial … /schedule-board"
fails in this dev environment: `loginAsAdmin` cannot authenticate. The `admin`
password hash in the dev DB (seeded at init by `scripts/dev.sh` via
`openssl rand`) matches no known env var (`pa55w0rd`, `.env SUPERADMIN_PASS`),
so the login form never proceeds. Reproduced on the **pristine baseline**
(same failure with this branch's changes stashed) — pre-existing and
environmental, not a regression from P0-1's sidebar gate change. The route
gate itself is unchanged (`ClinicalRoute permission="SCHEDULE_READ"`).

→ Tracked as backlog item **BL-001** (see `docs/user-feature-review/resident/07-backlog.md`).

## Follow-up fixes requested

| Sev | Item | Note |
|-----|------|------|
| Low | Teaching Library action button | Add "Ask your attending" button when the teaching-file workflow ships (D-5); guided copy ships now to avoid a dead button |
| Low (env) | BL-001 admin E2E login | Dev-DB admin password unknown; fix in dev provisioning (export/rotate SUPERADMIN_PASS to match DB hash or reset it) |

## Artifacts

- `frontend/e2e/resident-workflow.spec.ts` — 6 tests, all passing.
- Evidence: `evidence/05-schedule-board-works.png`, `06-schedule-board-rendered.png`, `07-resident-home-claimed-today.png`, `08-worklist-revision-filter.png`.
