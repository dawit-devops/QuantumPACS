# 05 — Implementation Report: care_coordinator (Phase 3)

Branch: `phase/user-feature-review-care-coordinator` (off `phase/user-feature-review-technologist`).
Spec: `specs/user-feature-review-care-coordinator.md`. All hand-off items implemented and **verified live**.

## What shipped

### P0-1 — Schedule Board dead end fixed (cross-role)
`MATRIX_B_PHYS` + `MATRIX_B_COORD` now carry read-only `WORKLIST_READ`, so the
`SCHEDULE_READ` route gate can no longer render a board whose data (`GET
/api/v2/worklist`) 403s. **Migration 063** appends the grants to existing DB
rows without touching other grants (preserves facility edits — unlike 062's
whole-set restore). Verified: `test.care_coordinator` and `test.physician` both
load the board with day data; the sidebar Schedule item now appears for them.

### P1-1 — Files dead end fixed
Read-only `FILE_READ` granted to `MATRIX_B_COORD` (and `MATRIX_B_PHYS` — the
R13 comment already asserted physician holds it, and physician had the same
403; scope addition noted below). The always-visible Files page now loads its
list. **No** FILE_WRITE/FILE_DELETE.

### P0-2 — Orders: the role's first real surface
- Backend: `GET /api/v2/orders` (gated `ORDER_READ`) — `visit_orders` joined to
  the patient + latest schedule/exam/report (best-effort MRN join; no FK exists
  between orders and imaging).
- Frontend: `/orders` page (new `coordinator/` workspace) — summary headline
  ("N open · M waiting >24h · K reported today"), status-Tag lifecycle
  (requested → scheduled → in progress → performed → reported), age chips
  (>24h orange, >72h red), report deep-link to `/reading/:examId`, row click →
  patient page, actionable empty state. Filter `aria-label`s mirror the
  shipped worklist pattern.

### P1-2 — Role-appropriate landing
care_coordinator now resolves to a new **coordination** workspace → lands on
`/orders`, not the radiologist's worklist. Other roles verified unchanged
(physician `/reading`, technologist `/exams`, radiologist `/reading`,
receptionist `/frontdesk/registration`).

### P2-1 — Reports & Results on the patient page
Patient payload gains `reports` (reports JOIN exams by MRN); the patient page
renders a REPORT_READ-gated "Reports & Results" card with status Tags and an
empty state. Verified for patient 13.

### P2-2 — Actionable permission failures
`ErrorDisplay` now detects "Missing permission" — hides the **Retry** button
(it can never succeed on a 403), names the missing grant, announces via
`role="alert"`, and offers "Go to home" (the user's `landingRouteFor`).

## Files touched

**Backend:** `api/permissions.py` · `migrations/versions/063_add_coordination_read_grants.py` (new) · `db/orders.py` (new) · `api/orders.py` (new) · `api/routes.py` · `db/patient.py` · tests: `test_orders_api.py` (new), `test_rbac_matrix.py`, `test_migrations.py`

**Frontend:** `navigator.ts` · `common/Sidebar.tsx` · `index.tsx` · `coordinator/Orders.tsx` (new) · `patient/Patient.tsx` · `api/patient.ts` · `common/ErrorDisplay.tsx`

## Verification
- **Backend:** 1700 passed · 1 skipped · 4 xfailed · ruff clean
- **Frontend:** `tsc --noEmit` + `npm run build` green
- **Live (browser, real backend):** landing `/orders`; Coordination/Schedule/Files in sidebar; schedule board + files list load (care_coordinator AND physician); Reports card renders; Orders row renders, row-click → patient; landings of 4 other roles unchanged; probe data cleaned up (visit_orders back to 0)
- Evidence: screenshots `17–22` in `evidence/`

## Deviations (documented)
1. **`FILE_READ` granted to physician too** — hand-off scoped P1-1 to
   care_coordinator, but the R13 comment already claimed physician holds it and
   physician had the identical Files dead end; consistent with the
   "every viewer role holds FILE_READ" principle.
2. **Orders is read-only** — ORDER_WRITE actions (status updates, the tabs
   drawer for care plans/encounters/prior auth) deferred per design conflict #1
   (minimal slice first).
3. **Tenant-selector 403** (`GET /v2/tenants`) is pre-existing, silently
   caught, and invisible (the selector only renders with >1 tenant) — left
   untouched.
