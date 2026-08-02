# Changelog — Radiology Technologist (R06)

All notable changes to this requirements package follow
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.

## [1.1.0] — 2026-08-03
### Added
- Artifact 04: Role-Based Routing & Navigation (Presentation Layer) section — study browser/viewer/worklist implemented; acquisition workflow GATED
- README: Codebase Alignment section (verified 2026-08-03)

## [1.0.0] — 2026-08-02
### Added
- Initial requirements package for Radiology Technologist role
- FR-R06-01: Modality Worklist (auto-refresh, STAT highlighting)
- FR-R06-02: Patient Identity Verification (confirm patient before exam)
- FR-R06-03: Exam Protocol Selection (review parameters before acquisition)
- FR-R06-04: Image Acquisition and QA (real-time preview, reject/accept)
- FR-R06-05: Dose Documentation (auto-log, cumulative tracking, ACR benchmark)
- FR-R06-06: Patient Safety Checks (allergy, pregnancy, contrast)
- FR-R06-07: Exam Completion and Handoff (notify radiologist, push to PACS)
- FR-R06-08: Retake/Incident Logging (structured logging, notifications)
- FR-R06-09: Emergency Protocol Override (justification, audit trail)
- FR-R06-10: Modality-Specific Workflows (CT, MRI, PET, US, Mammography)
- All 8 artifacts (01-08) with complete traceability
- 13 API endpoints flagged for `frontend-to-backend-requirements` skill
- 6 new semantic design tokens for technologist components
- Cross-role dependencies with R04, R05, R12, R15, R16, R17