# Changelog — Staff Radiologist (R12)

All notable changes to this requirements package follow
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.

## [Unreleased]
### Changed
- Package status promoted from `draft` to `approved` — core feature set implemented and all validation gates pass.

## [1.3.0] — 2026-08-03
### Changed
- FR-R12-09: GATED → Implemented (structured reporting shipped 2026-08-03 — `GET/PUT /reports/{exam_id}`, `POST /reports/{exam_id}/sign`, `GET /reports/templates`)
- FR-R12-15: GATED → Implemented (reading presets shipped 2026-08-03 — `/reading-presets*` window_level + layout per modality)
- FR-R12-14: GATED → Implemented (study-arrival notifications — `exam.completed` role notification + `/ws` push)
- NFR-R12-10: GATED → Implemented (report autosave flush + dirty-retry in `ReportEditor.tsx`)
- FR-R12-12: GATED → Partially Implemented (peer review of final signed reports shipped; resident-draft attending-review queue remains GATED)
- AC-R12-20/21/27/29: un-gated with backend test/integration verification methods; AC-R12-30 (report templates) and AC-R12-31 (peer review) added
- README: Codebase Alignment rewritten with real routes/pages/permissions
- DELTA.md added documenting the 4d136e0 alignment

## [1.2.0] — 2026-08-03
### Added
- Artifact 04: Role-Based Routing & Navigation (Presentation Layer) section — viewer/patient/metrics routes verified; reporting GATED
- README: Codebase Alignment section (verified 2026-08-03)

## [1.1.0] — 2026-08-02
### Added
- Artifact 07 (Traceability Matrix): FR/NFR → AC traceability, cross-artifact dependencies, cross-role dependencies
- Artifact 08 (Implementation Roadmap): dependency-ordered implementation plan with status tracking and next steps

## [1.0.0] — 2026-08-01
### Added
- Initial requirements package for Staff Radiologist role
