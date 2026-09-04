# referring_physician — Backend Inventory (Phase 5a)
Date: 2026-08-29 | Baseline commit: 75107be
Skills invoked: pacs-workflow, dicom-web-query

## Route coverage summary

referring_physician has 14 reachable surfaces. All clinical/coordination read endpoints return 200. Files returns 403 (no FILE_READ) — resolved by hiding the Files nav item (F2).

## ORPHANED (should surface)

None found within referring_physician's scope. All surfaces are fully wired.

## INTERNAL (no UI by design)

All admin routes (replicas, users, tenants, etc.) and DICOMweb routes — correctly blocked for this read-only clinical role (no DICOMWEB_READ grant).

## DEAD (removal/wiring candidates)

None found.

## Findings specific to referring_physician

- **F2**: Files nav item was reachable via VIEWER_ROUTE_PERMISSIONS (STUDY_READ/VIEWER_READ) but backend requires FILE_READ → 403 on data load. Fixed by gating nav item on FILE_READ. The route `/` stays deep-linkable.
- **Files upload** (POST /api/files/upload): 403 — no FILE_WRITE (correct, read-only).
- **DICOMweb STOW**: 403 — no DICOMWEB_WRITE (correct).