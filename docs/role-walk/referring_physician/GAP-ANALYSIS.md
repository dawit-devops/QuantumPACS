# referring_physician — Gap Analysis (Phase 2)
Date: 2026-08-29
Sources: RBAC_matrix_spec.md §5 (Matrix A REF), permissions.py (MATRIX_A_REF), navigator.ts, Sidebar.tsx, ADR-017
Skills invoked: iam-audit (least privilege)

## Gaps

| # | Surface | Documented (ADR/spec) | Actual (code) | Severity | Evidence (file:line) | Notes |
|---|---|---|---|---|---|---|
| G1 | ADR-017 "files: read" claim | ADR-017: "files/patients/studies: read" | Code has no FILE_READ in MATRIX_A_REF. Files page is reachable via STUDY_READ/VIEWER_READ (VIEWER_ROUTE_PERMISSIONS any-of). Read-only access is correct — just the ADR's "files: read" shorthand is imprecise | LOW | ADR-017:78; permissions.py:242-247 (MATRIX_A_REF); PermissionsRoute.tsx:33-37 (VIEWER_ROUTE_PERMISSIONS) | Minor docs drift: the ADR's "files" shorthand overstates the actual grant. The behavior (read-only file access) is correct |
| G2 | No FILE_READ | Spec Matrix A REF: no FILE_READ column (FILE_READ/FILE_WRITE row shows blank for REF) | Code matches spec — no FILE_READ in MATRIX_A_REF | PASS | RBAC_matrix_spec.md Matrix A REF column | Matches spec |
| G3 | Pure read-only | Spec Matrix A REF: no write grants at all | Code matches spec exactly (10 grants, all reads) | PASS | RBAC_matrix_spec.md Matrix A REF; permissions.py MATRIX_A_REF | Spec-aligned |
| G4 | No DICOMWEB_READ / FILE_READ legacy | Physician has LEGACY_PHYSICIAN adding DICOMWEB_READ + FILE_READ; referring_physician has no legacy union | Code matches — no DICOMWEB_READ, no FILE_READ | PASS | permissions.py: no LEGACY_REFERRING_PHYSICIAN | By design: referring physician is a simpler, read-only referrer — no DICOMweb console needed |
| G5 | Front Desk hidden | R1 from physician walk (sidebar hide for clinical roles) | Applies to referring_physician too (clinical-scoped) | PASS | Sidebar.tsx (R1 fix) | Verified in Phase 3 of physician walk |

## Summary
- No gaps requiring action. The code matches spec Matrix A REF exactly.
- ADR-017 "files: read" is slightly imprecise but the behavior (read-only file access) is correct.
- referring_physician is a clean, minimal, read-only role — the simplest in the platform.