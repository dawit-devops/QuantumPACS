# receptionist — Frontend Inventory (Phase 5b)
Date: 2026-08-29 | Browser session: acme.receptionist (tenant-scoped)
Skills invoked: antd, frontend-react-best-practices

## A. Needs backend wiring (UI exists, backend missing/incomplete)

None found. All frontdesk/coordination endpoints return 200. Patient registration creates successfully (201).

## B. Better omitted / reduced (overlaps, noise, unmaintained)

| # | Page | Route | Why reduce/omit | Recommendation | Decision |
|---|---|---|---|---|---|
| B1 | Acquisition section | /worklist, /tracking, /schedule-board, /schedule, /schedule/resources | The Acquisition section is the technologist's operational surface. receptionist holds WORKLIST_READ/SCHEDULE_READ (needed for schedule board data) but does not operate acquisition. | R1: hide Acquisition section for receptionist (role-scoped sidebar filter). Routes stay deep-linkable. | R1 (applied d92268c) |

## C. Needs refinement (works but has gaps)

None found. Front Desk surfaces render correctly with real data.

## Summary
- 7 surfaces walked: all PASS
- Sidebar: Front Desk (Registration/Schedule/Queue/Patient Search) + Coordination (Orders/Care Plans/Communications) — no Acquisition (R1), no clinical/admin sections
- R1 fix verified in browser: Acquisition section hidden
- 0 console errors (only expected 403s on /api/v2/tenants and /notifications/unread-count)