# super_admin — Frontend Feature Inventory (Phase 5b)

Date: 2026-08-27
Method: enumerate all 83 frontend routes from `index.tsx` + 258 sidebar items
from `Sidebar.tsx`; cross-reference frontend API calls (245 paths) against
backend routes (344); verify each page's API resolves to a registered route.

Skills invoked: ant-design, frontend-react-best-practices

## Cross-reference summary

- Frontend routes: **83** (4 public + 79 authenticated)
- Frontend API call paths: **245** (unique, dynamic segments normalized)
- Frontend calls with NO matching backend route: **0** (all resolve)
- Backend orphaned handlers (have backend, no frontend): **19** (see BACKEND-INVENTORY.md)

## A. Needs backend wiring (UI exists, backend missing/incomplete)

**NONE.** Every frontend API call path resolves to a registered backend route.
The backend is more complete than the frontend (19 orphaned handlers).

## B. Better omitted / reduced (feature adds noise, overlaps, or is unmaintained)

| # | Page | Route | Why reduce/omit | Recommendation |
|---|---|---|---|---|
| B1 | Visits (FrontDeskVisits, 818 lines) | `/frontdesk/visits` | Legacy "Visits & Check-In" page renamed to Today's Schedule per S4-refactor. Component exists, route registered, but sidebar links to `/frontdesk/schedule` instead. No component navigates to this route. | Remove route + component, OR keep as redirect to `/frontdesk/schedule` |
| B2 | Today's Schedule (FrontDeskSchedule) | `/frontdesk/schedule` | — | Keep (active sidebar item) |
| B3 | Schedule Board, Calendar, Frontdesk Schedule | `/schedule-board`, `/schedule`, `/frontdesk/schedule` | Three schedule surfaces target different roles (technologist schedule board, CalendarView calendar, frontdesk today). Minor overlap. | Keep (role-specific, informational) |

## C. Needs refinement (works but has gaps)

| # | Page | Route | Gap | Recommendation |
|---|---|---|---|---|
| C1 | Logs | `/logs` | Missing event-types filter (backend has `/logs/event-types` but frontend only calls `/logs` + `/logs/actors`) | DEFERRED (user decision: wire in logs walk) |
| C2 | Reconciliation | `/billing/reconciliation` | New page — PASS after O8 build | PASS |
| C3 | Denial Rework | `/billing/denials` | Import Denial — PASS after O9 build | PASS |
| C4 | RevenueDashboard, ClaimsStatus | `/billing/revenue`, `/billing/claims` | `valueStyle` deprecation in antd v6 Statistic (same as fixed in Reconciliation) | DEFERRED (cosmetic; all billing pages at once) |
| C5 | Clinical routes (worklist, exams, reading, QA, frontdesk, portal, etc.) | various | Excluded from super_admin by ClinicalRoute (by design, G8 verified) | PASS — by design |

## Decision gate

| Item | Recommendation | Decision |
|---|---|---|
| B1 — Remove `/frontdesk/visits` route + Visits.tsx? | REMOVE: legacy, superseded, no navigator links to it | _(pending)_ |
| B1 — Or redirect to `/frontdesk/schedule`? | REDIRECT: safer, preserves bookmarks | _(pending)_ |
| C1 — Wire logs event-types filter? | DEFERRED (per earlier decision) | DEFERRED |
| C4 — Fix antd Statistic deprecation on RevenueDashboard + ClaimsStatus? | DEFER: cosmetic, batch with other billing pages | DEFERRED |