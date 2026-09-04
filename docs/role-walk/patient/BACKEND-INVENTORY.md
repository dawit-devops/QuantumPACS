# patient — Backend Inventory (Phase 5a)
Date: 2026-08-29 | Baseline commit: 716b84b
Skills invoked: hipaa-compliance

## Route coverage summary

patient has 4 reachable portal surfaces. All endpoints return 200 (or correct empty scope). Error paths (admin, billing, reading, files, DICOMweb) all return 403.

## ORPHANED (should surface)

None found within patient's scope.

## INTERNAL (no UI by design)

All admin/clinical/billing routes — correctly blocked.

## DEAD (removal/wiring candidates)

None found.

## Findings specific to patient

- Portal scope is empty in dev (acme.patient not linked to a patient record). This is a dev-seed limitation — in production the patient scope links via user_tenant_grants or similar.
- All error paths correctly return 403.
- Notifications self-scoped (NOTIFICATIONS_SELF) works: 200.
