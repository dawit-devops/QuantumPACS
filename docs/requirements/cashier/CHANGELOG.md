# Changelog — Radiology Service Cashier (R09)

All notable changes to this requirements package follow
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.

## [1.1.2] — 2026-08-03
### Changed
- README: Codebase Alignment re-verified after v3-dev merge 4d136e0 — no billing endpoints added (`routes.py` unchanged for billing); built-in `cashier` role has PATIENT_READ/WRITE only; `PermissionRoute` enforces route-level access
- No requirement statuses changed (all billing FRs remain GATED)

## [1.1.1] — 2026-08-03
### Fixed
- Artifact 08: FR-R09-09 (read-only clinical context) corrected from "Implemented" to "Partially Implemented" — patient/study context exists; no billing context in billing flow (aligns 08 with 07's partial status)

## [1.1.0] — 2026-08-03
### Added
- Artifact 04: Role-Based Routing & Navigation (Presentation Layer) section — read-only Files/patient today; all billing GATED
- README: Codebase Alignment section (verified 2026-08-03)

## [1.0.0] — 2026-08-02
### Added
- Initial requirements package for R09 Cashier (10 FRs, 6 NFRs, 6 stories, 16 ACs)
- Artifacts 01–08 complete with traceability and implementation roadmap
- Flagged backend gaps: billing endpoints, payment processor, claims feed, refund approvals
