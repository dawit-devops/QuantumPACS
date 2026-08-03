# Changelog — External RIS (R15)

All notable changes to this requirements package follow
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.

## [1.1.1] — 2026-08-03
### Changed
- README: Codebase Alignment re-verified after v3-dev merge 4d136e0 — `/exams/{id}/complete` updates internal status + worklist `performed` (in-app) but sends no outbound HL7 ORM/ORU, so FR-R15-03 stays GATED; MWL C-FIND SCP re-confirmed
- Artifact 07/08: FR-R15-03 blocking-dependency notes updated; statuses unchanged

## [1.1.0] — 2026-08-03
### Added
- Artifact 04: System Interface Surface section — HL7 inbound, worklist CRUD, DICOMweb query, webhooks implemented; MWL/MPPS lifecycle + reconciliation GATED
- README: Codebase Alignment section (verified 2026-08-03)

## [1.0.0] — 2026-08-02
### Added
- Initial requirements package for R15 External RIS (10 FRs, 7 NFRs, 6 stories, 17 ACs)
- Artifacts 01–08 complete with integration contracts and implementation roadmap
- Flagged backend gaps: outbound delivery wiring, reconciliation semantics, MWL mapping
