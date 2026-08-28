# referring_physician — Frontend Inventory (Phase 5b)
Date: 2026-08-29 | Browser session: test.referring_physician
Skills invoked: antd, frontend-react-best-practices

## A. Needs backend wiring (UI exists, backend missing/incomplete)

None found. All clinical/coordination endpoints return 200.

## B. Better omitted / reduced (overlaps, noise, unmaintained)

| # | Page | Route | Why reduce/omit | Recommendation | Decision |
|---|---|---|---|---|---|
| B1 | Files | / | referring_physician has no FILE_READ → backend 403s on every /api/files* call. The VIEWER_ROUTE_PERMISSIONS nav gate (FILE_READ\|STUDY_READ\|VIEWER_READ) advertised a dead page. | F2: gate Files nav item on FILE_READ only. Route stays deep-linkable. | F2 (applied 75107be) |
| B2 | Acquisition section | /worklist, /tracking, /schedule-board, /schedule, /schedule/resources | The Acquisition section is the technologist/scheduler operational surface. referring_physician holds WORKLIST_READ/SCHEDULE_READ but does not operate acquisition. | F3: hide the Acquisition section for referring_physician (role-scoped sidebar filter). Routes stay deep-linkable. | F3 (applied 793b087) |

## C. Needs refinement (works but has gaps)

None found. Reading Worklist renders with real data; sidebar is clean.

## Summary
- 14 surfaces walked: all PASS
- Sidebar for referring_physician now shows only: Account, Reading (Worklist/Teaching/Critical), Coordination — minimal, read-only, referrer-appropriate
- F2 (Files 403) + F3 (Acquisition hide) both verified in browser
- 0 console errors (only expected /api/v2/tenants 403)