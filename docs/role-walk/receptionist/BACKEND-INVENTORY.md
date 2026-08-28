# receptionist — Backend Inventory (Phase 5a)
Date: 2026-08-29 | Baseline commit: d92268c
Skills invoked: fullstack-guardian, hipaa-compliance

## Route coverage summary

receptionist has 7 reachable surfaces. All frontdesk/coordination read endpoints return 200. Patient registration (POST /api/patients) returns 201. Error paths (Files, Reading) return 403 correctly.

## ORPHANED (should surface)

None found within receptionist's scope.

## INTERNAL (no UI by design)

All admin/clinical/billing routes — correctly blocked.

## DEAD (removal/wiring candidates)

None found.

## Findings specific to receptionist

- **F2**: CreatePatientRequest uses `sex` (M/F/O) not `gender`. A wrong-field caller gets a 500 (CheckViolationError) instead of a validation error. Not a frontend bug (frontend uses `sex`); note only.
- Queue route is `/queue`, not `/frontdesk/queue` (the frontend calls `ris/frontdesk`? — verified the page works via browser).