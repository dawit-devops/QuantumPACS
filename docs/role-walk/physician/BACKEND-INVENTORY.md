# physician — Backend Inventory (Phase 5a)
Date: 2026-08-28 | Baseline commit: ae42f57
Skills invoked: pacs-workflow, dicom-web-query

## Route coverage summary

physician has 17 reachable surfaces. The backend API walk confirmed all expected endpoints return 200 for read operations. DICOMweb Store (STOW-RS) returns 403 (no DICOMWEB_WRITE — correct).

## ORPHANED (should surface)

None found within physician's scope. All clinical/coordination/DICOMweb surfaces are fully wired to the frontend.

## INTERNAL (no UI by design)

All admin-only routes (replicas, users, tenants, roles, logs, etc.) — correctly blocked for clinical-scoped roles.

## DEAD (removal/wiring candidates)

None found.

## Findings specific to physician

- Tracking route is `/ris/tracking`, not `/tracking` — corrected in PLAN.md
- Communications endpoint requires `patient_id` query param (400 without it — frontend provides it from the patient context)
- DICOMweb Store returns 403 (no DICOMWEB_WRITE) — correct error path for physician (read-only DICOMWEB)