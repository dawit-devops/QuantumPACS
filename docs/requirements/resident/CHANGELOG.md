# Changelog — Radiology Trainee/Resident (R13)

All notable changes to this requirements package follow
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.

## [1.2.0] — 2026-08-03
### Changed
- Shared R12 reporting stack shipped (merge 4d136e0): draft editor + autosave (`GET/PUT /reports/{exam_id}`), templates, reading worklist, peer review, reading presets, notifications — no longer blocked on R12 reporting
- FR-R13-03: GATED → Partially Implemented (draft creation + autosave shipped; attending-submit/badge/completeness GATED)
- FR-R13-01/02/06: Partial status refined (shared worklist/viewer/Files infra; supervised-specific slices GATED)
- NFR-R13-02: GATED → Covered (draft autosave timing measurable against shared editor)
- FR-R13-04: remains GATED — peer-review endpoints cover final signed reports only; resident-draft co-sign workflow not built
- README: Codebase Alignment rewritten; version 1.2.0
- DELTA.md added documenting the 4d136e0 alignment

## [1.1.1] — 2026-08-03
### Fixed
- Artifact 08: FR-R13-06 (exam list) corrected from "Implemented" to "Partially Implemented" — only shared Files-browser infra exists; exam-log filters/CSV export/metrics remain GATED (aligns 08 with 07's partial status)

## [1.1.0] — 2026-08-03
### Added
- Artifact 04: Role-Based Routing & Navigation (Presentation Layer) section — no resident-specific functionality exists; all supervised-reading features GATED
- README: Codebase Alignment section (verified 2026-08-03)

## [1.0.0] — 2026-08-02
### Added
- Initial requirements package for R13 Resident (10 FRs, 10 NFRs, 10 stories, 20 ACs)
- Artifacts 06–08 completed (acceptance criteria, traceability matrix, implementation roadmap) to finish the package started with artifacts 01–05
- Flagged backend gaps: report endpoints (R12), resident worklist push, de-identification, consult routing
