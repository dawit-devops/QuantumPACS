# patient — Frontend Inventory (Phase 5b)
Date: 2026-08-29 | Browser session: acme.patient (tenant-scoped)
Skills invoked: antd, frontend-react-best-practices, hipaa-compliance

## A. Needs backend wiring (UI exists, backend missing/incomplete)

None found. Portal scope + notifications load correctly.

## B. Better omitted / reduced (overlaps, noise, unmaintained)

| # | Page | Route | Why reduce/omit | Recommendation | Decision |
|---|---|---|---|---|---|
| B1 | Acquisition section | /schedule-board, /schedule, /schedule/resources | The Acquisition section is the technologist/scheduler surface. patient holds SCHEDULE_READ (needed for portal appointments) but does not operate scheduling. | R1: hide Acquisition section for patient. Routes stay deep-linkable. | R1 (applied 716b84b) |
| B2 | Front Desk (Today's Schedule) | /frontdesk/schedule | Front Desk is receptionist-staff surface. patient holds SCHEDULE_READ which unlocked it. | R1: hide Front Desk section for patient. | R1 (applied 716b84b) |

## C. Needs refinement (works but has gaps)

| # | Page | Route | Gap | Recommendation | Decision |
|---|---|---|---|---|---|
| C1 | My Records | /portal | "No records are shared with you yet" — correct empty state for acme.patient (dev-seed not linked to a patient record). | KEEP (dev-seed limitation, not a bug) | KEEP |

## Summary
- 4 surfaces walked: all PASS
- Sidebar for patient: Portal (My Records/Appointments/Results/Follow-ups) + Account only — no Acquisition, no Front Desk, no Files, no clinical/admin
- R1 fix verified in browser
- 0 console errors (only expected /api/v2/tenants 403)