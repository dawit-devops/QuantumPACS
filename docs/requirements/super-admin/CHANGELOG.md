# Changelog — R01 Super Admin (PACS Admin)

All notable changes to this requirements package follow
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.

## [1.2.0] — 2026-08-03
### Added
- Artifact 04: Role-Based Routing & Navigation (Presentation Layer) section — verified route/sidebar/permission mapping from `frontend/src/auth/`, `Sidebar.tsx`, `index.tsx`
- README: Codebase Alignment section (verified 2026-08-03) with implemented vs GATED status

## [1.1.0] — 2026-08-02
### Added
- Artifact 07 (Traceability Matrix): FR/NFR → AC traceability, cross-artifact dependencies, cross-role dependencies, integration contracts
- Artifact 08 (Implementation Roadmap): dependency-ordered implementation plan with status (done/partial/missing), blocking dependencies, and next steps
- GATED ACs identified: AC-R01-37 (health dashboard, blocked on backend aggregate endpoint), AC-R01-38 (backup/restore, no implementation)

## [1.0.0] — 2026-08-01
### Added
- Initial requirements package for Super Admin (PACS Admin) role
- FR-R01-01 through FR-R01-20: tenant provisioning, user/role RBAC,
  storage replicas, DICOM routing, service keys, webhooks, audit logs,
  metrics dashboards, FHIR/HL7 admin, OAuth providers, notifications
- NFR-R01-01 through NFR-R01-14: performance, accessibility, audit,
  session, and retention targets
- All 6 artifacts (01–06) with validator-gated acceptance criteria