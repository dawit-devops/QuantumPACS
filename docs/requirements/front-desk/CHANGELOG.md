# Changelog — Front Desk / Receptionist (R08)

All notable changes to this requirements package follow
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.

## [1.1.2] — 2026-08-03
### Changed
- README: Codebase Alignment re-verified after v3-dev merge 4d136e0 — `PermissionRoute` enforces role-based route access; `/schedule-board` is an R04 worklist-derived read view, not a scheduling API; `POST /hl7` confirmed inbound-only (no outbound ADT sender)
- No requirement statuses changed (FR-R08-01..10 remain Partial/GATED as recorded)

## [1.1.1] — 2026-08-03
### Fixed
- Artifact 08: FR-R08-01 (patient search) corrected from "Implemented" to "Partially Implemented" — patient lookup via Files/patient page exists; dedup + registration flow GATED (aligns 08 with 07's partial status)

## [1.1.0] — 2026-08-03
### Added
- Artifact 04: Role-Based Routing & Navigation (Presentation Layer) section — read-only Files/patient today; all registration/scheduling GATED
- README: Codebase Alignment section (verified 2026-08-03)

## [1.0.0] — 2026-08-02
### Added
- Initial requirements package for R08 Front Desk (10 FRs, 6 NFRs, 7 stories, 16 ACs)
- Artifacts 01–08 complete with traceability and implementation roadmap
- Flagged backend gaps: order intake, consent storage, check-in events, schedule API
