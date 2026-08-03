# Changelog — Qa Team (R05)

All notable changes to this requirements package follow
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.

## [1.3.0] — 2026-08-03
### Changed
- FR-R05-01 (QA review queue): GATED → Implemented — `GET /qa/queue` + `QAQueue.tsx`
- FR-R05-02 (QA review workflow): GATED → Implemented — `/qa/reviews/{exam_id}` GET/PUT + `POST /qa/reviews` + `QAReviewForm.tsx`
- FR-R05-03 (protocol registry CRUD): GATED → Implemented — `/qa/protocols` + `/qa/protocols/{id}` + `ProtocolRegistry.tsx`
- FR-R05-04 (QA score persistence): GATED → Implemented — `qa_scores` write via review submit
- FR-R05-05 (corrective action inbox): GATED → Implemented — `/qa/corrective-actions` + resolve + `CorrectiveActions.tsx`
- FR-R05-06 (incident/retake logging): GATED → Implemented — `/qa/incidents` + resolve + `Incidents.tsx`
- FR-R05-07 (RBAC QA role): GATED → Implemented — `qa_team` role + `QA_*`/`PROTOCOL_MANAGE` permissions shipped
- FR-R05-10 (peer review workflow): GATED → Implemented — `/qa/reviewers`, `/peer-reviews`, `/peer-reviews/{id}/submit`; new AC-R05-153 added
- FR-R05-08/09/11/12/13: remain GATED (v3.1/v3.2) with accurate blocking deps
- Artifact 07 traceability: FR-R05-10 + NFR rows fixed; per-FR implementation statuses updated
- Artifact 08 roadmap: implemented vs GATED split rewritten; blocking deps narrowed
- README: Codebase Alignment rewritten with actual routes/permissions/pages
- DELTA.md added documenting the alignment

## [1.2.0] — 2026-08-03
### Added
- Artifact 04: Role-Based Routing & Navigation (Presentation Layer) section — no `/qa/*` routes exist; QA tools GATED
- README: Codebase Alignment section (verified 2026-08-03)
### Changed
- Artifact 08 roadmap: corrected false "Implemented" claims — QA queue/review/protocol/incident/corrective-action/peer-review moved to GATED with blocking dependencies; status demoted to draft

## [1.1.0] — 2026-08-02
### Added
- Artifact 07 (Traceability Matrix): FR/NFR → AC traceability, cross-artifact dependencies, cross-role dependencies
- Artifact 08 (Implementation Roadmap): dependency-ordered implementation plan with status tracking and next steps

## [1.0.0] — 2026-08-01
### Added
- Initial requirements package for Qa Team role
