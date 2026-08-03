# Changelog — Teleradiologist (R18)

All notable changes to this requirements package follow
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.

## [Unreleased]
### Changed
- Package status promoted from `draft` to `approved` — core feature set implemented and all validation gates pass.

## [1.3.0] — 2026-08-03
### Changed
- FR-R18-03: GATED → Implemented (SSO/OAuth/OIDC + tenant switching shipped 2026-08-03 — `/oauth/*`, `TenantSelector.tsx`)
- FR-R18-07: GATED → Implemented (preliminary reports shipped — draft → preliminary → final state machine, `ReportEditor.tsx`)
- FR-R18-08: GATED → Implemented (sign-off to final via `POST /reports/{exam_id}/sign`; per-site credential check not enforced)
- FR-R18-04/05: GATED → Implemented (viewer parity + WAN load capability via shared R12 viewer/DICOMweb)
- FR-R18-01: GATED → Partially Implemented (reading worklist shipped; site/assignment filters GATED)
- FR-R18-22/24: GATED → Partially Implemented (W/L + layout presets per modality via `/reading-presets*`; 3-monitor profiles + scenario templates GATED)
- NFR-R18-03/04/05/11: GATED → Covered (verifiable against shipped viewer/editor/OAuth)
- Offline packages, critical-findings escalation, consult queue, multi-site dashboard, voice dictation, mobile viewer, prefetch, priors, messaging remain GATED
- README: Codebase Alignment + API lists rewritten; version 1.3.0
- DELTA.md added documenting the 4d136e0 alignment

## [1.2.0] — 2026-08-03
### Added
- Artifact 04: Role-Based Routing & Navigation (Presentation Layer) section — remote viewer/worklist (same as R12); telerad-specific features GATED
- README: Codebase Alignment section (verified 2026-08-03)

## [1.1.0] — 2026-08-02
### Added
- Artifact 07 (Traceability Matrix): FR/NFR → AC traceability, cross-artifact dependencies, cross-role dependencies
- Artifact 08 (Implementation Roadmap): dependency-ordered implementation plan with status tracking and next steps

## [1.0.0] — 2026-08-01
### Added
- Initial requirements package for Teleradiologist role
