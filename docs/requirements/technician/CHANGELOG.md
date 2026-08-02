# Changelog — Radiology Technician (R07)

All notable changes to this requirements package follow
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.

## [1.1.0] — 2026-08-03
### Added
- Artifact 04: Role-Based Routing & Navigation (Presentation Layer) section — study browser/viewer/worklist implemented; fluoroscopy/mammography workflows GATED
- README: Codebase Alignment section (verified 2026-08-03)

## [1.0.0] — 2026-08-02
### Added
- Initial requirements package for Radiology Technician role
- FR-R07-01: Modality Worklist (auto-refresh, STAT highlighting)
- FR-R07-02: Patient Identity Verification (confirm patient before exam)
- FR-R07-03: Exam Protocol Selection (review parameters before acquisition)
- FR-R07-04: Image Acquisition and QA (real-time preview, reject/accept)
- FR-R07-05: Dose Documentation (auto-log, cumulative tracking, ACR benchmark)
- FR-R07-06: Patient Safety Checks (allergy, pregnancy, contrast for fluoroscopy)
- FR-R07-07: Exam Completion and Handoff (notify radiologist, push to PACS)
- FR-R07-08: Retake/Incident Logging (structured logging, notifications)
- FR-R07-09: Fluoroscopy-Specific Workflow (live mode, spot/cine, DAP tracking)
- FR-R07-10: Mammography-Specific Workflow (CC/MLO, compression monitoring, AGD)
- All 8 artifacts (01-08) with complete traceability
- 16 API endpoints flagged for `frontend-to-backend-requirements` skill
- 8 new semantic design tokens for technician components
- Cross-role dependencies with R04, R05, R12, R15, R16, R17