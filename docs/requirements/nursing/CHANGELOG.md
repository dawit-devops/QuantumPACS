# Changelog — Radiology Service Nursing Team (R11)

All notable changes to this requirements package follow
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.

## [1.1.2] — 2026-08-03
### Changed
- README: Codebase Alignment re-verified after v3-dev merge 4d136e0 — `/exams/{id}/safety-checks` exists but is a generic EXAM_WRITE-gated checklist in the technologist workflow (no allergy/pregnancy/renal structure, no contrast gate, no nursing role); does not partially cover FR-R11-05; `PermissionRoute` enforces route-level access
- No requirement statuses changed (nursing FRs remain GATED)

## [1.1.1] — 2026-08-03
### Fixed
- Artifact 08: FR-R11-09 (MAR) corrected from "Implemented" to "Partially Implemented" — patient/medication context exists; no nursing-specific MAR workflow (aligns 08 with 07's partial status)

## [1.1.0] — 2026-08-03
### Added
- Artifact 04: Role-Based Routing & Navigation (Presentation Layer) section — read-only Files/patient today; all nursing features GATED
- README: Codebase Alignment section (verified 2026-08-03)

## [1.0.0] — 2026-08-02
### Added
- Initial requirements package for R11 Nursing (10 FRs, 6 NFRs, 7 stories, 16 ACs)
- Artifacts 01–08 complete with traceability and implementation roadmap
- Flagged backend gaps: nursing endpoints, escalation wiring, offline sync, HL7 allergy flags
