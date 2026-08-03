# Changelog — Referring Clinician (R14)

All notable changes to this requirements package follow
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.

## [1.2.1] — 2026-08-03
### Changed
- README: Codebase Alignment re-verified after v3-dev merge 4d136e0 — `GET /reports/{exam_id}` exists behind REPORT_READ (radiologist only; physician role + share-link lack it, ShareView renders no report) so FR-R14-04 stays GATED; in-app bell/WS-push notification infra exists but no clinician routing/email, so FR-R14-06 stays GATED; `PermissionRoute` enforces route-level access
- Artifact 07/08: FR-R14-04/06 GATED blocking-dependency notes updated; statuses unchanged

## [1.2.0] — 2026-08-03
### Added
- Artifact 04: Role-Based Routing & Navigation (Presentation Layer) section — share-link-only access (`/view/:key`, `tempKey` mode)
- README: Codebase Alignment section (verified 2026-08-03)
### Changed
- Artifact 08 roadmap: corrected false "Implemented" claims — report retrieval/status tracking/notifications/patient selector moved to GATED (depend on R12 reporting); share-link viewer + OAuth admin marked implemented

## [1.1.0] — 2026-08-02
### Added
- Artifact 07 (Traceability Matrix): FR/NFR → AC traceability, cross-artifact dependencies, cross-role dependencies
- Artifact 08 (Implementation Roadmap): dependency-ordered implementation plan with status tracking and next steps

## [1.0.0] — 2026-08-01
### Added
- Initial requirements package for Referring Clinician role
