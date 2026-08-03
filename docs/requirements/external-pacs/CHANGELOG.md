# Changelog — External PACS (R17)

All notable changes to this requirements package follow
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.

## [1.1.1] — 2026-08-03
### Changed
- README: Codebase Alignment re-verified after v3-dev merge 4d136e0 — merge touched exam/QA/report routes only; DICOMweb QIDO/STOW/WADO, DICOM C-STORE, routing, worklist unchanged
- No requirement statuses changed

## [1.1.0] — 2026-08-03
### Added
- Artifact 04: System Interface Surface section — QIDO-RS/WADO-RS, WADO-URI, upload, bulk download, routing implemented; C-MOVE/archive-sync GATED
- README: Codebase Alignment section (verified 2026-08-03)

## [1.0.0] — 2026-08-02
### Added
- Initial requirements package for R17 External PACS (10 FRs, 7 NFRs, 7 stories, 17 ACs)
- Artifacts 01–08 complete with DICOM/DICOMweb contracts and implementation roadmap
- Flagged backend gaps: WADO-RS progressive, C-MOVE retry, routing delivery log, archive sync
