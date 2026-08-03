# Changelog — External EMR (R16)

All notable changes to this requirements package follow
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.

## [1.1.1] — 2026-08-03
### Changed
- README: Codebase Alignment re-verified after v3-dev merge 4d136e0 — no new EMR-facing surface; FHIR Patient/ImagingStudy/DocumentReference + HL7 ADT unchanged; internal exam status (worklist `performed`) is not exposed to the EMR, FR-R16-05 stays GATED
- No requirement statuses changed

## [1.1.0] — 2026-08-03
### Added
- Artifact 04: System Interface Surface section — HL7 ADT inbound, FHIR Patient, webhooks implemented; report backfill/results-status GATED
- README: Codebase Alignment section (verified 2026-08-03)

## [1.0.0] — 2026-08-02
### Added
- Initial requirements package for R16 External EMR (10 FRs, 7 NFRs, 6 stories, 17 ACs)
- Artifacts 01–08 complete with FHIR/HL7 contracts and implementation roadmap
- Flagged backend gaps: report mapping, demographics outbound, allergy flag extraction
