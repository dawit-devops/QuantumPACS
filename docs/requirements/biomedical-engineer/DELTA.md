# Delta — Biomedical Engineer (R10) — 2026-08-03

## Summary
- **Trigger**: re-verification after v3-dev merge 4d136e0 (exams/QA/reports routes shipped)
- **Version change**: 1.1.1 → 1.1.2 (PATCH)
- **Stakeholder**: PACS requirements architect

## Changed Requirements
none; re-verification only

Verified against post-merge codebase (4d136e0):
- `/exams/{id}/dose` (EXAM_WRITE) now exists as part of the technologist exam workflow, but R10 contains **no dose-related FRs** — no partial coverage claim warranted.
- No equipment registry, PM/QC, downtime, work-order, vendor-contract, or fault-alert endpoints/routes exist — FR-R10-01..09 remain GATED.
- FR-R10-10 (audit via shared `/logs`) partial status unchanged.
- `PermissionRoute` enforces role-based access at the URL boundary; in-app notification bell (WS push) not wired for equipment fault alerting (FR-R10-07 remains GATED).

## Impact on Existing Artifacts
| Artifact | Changed? | Summary |
|----------|----------|---------|
| README.md | Yes | Post-merge re-verification note; version 1.1.1 → 1.1.2 |
| 01-user-requirements.md | No | Statuses unchanged |
| 06-acceptance-criteria.md | No | No GATED markers; unchanged |
| 07-traceability.md | No | FR-R10-10 partial / equipment FRs GATED unchanged |
| 08-implementation-roadmap.md | No | Statuses unchanged |
| CHANGELOG.md | Yes | Added 1.1.2 entry |
| DELTA.md | Yes | This file |
