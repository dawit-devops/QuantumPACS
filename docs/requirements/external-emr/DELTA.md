# Delta — External EMR (R16) — 2026-08-03

## Summary
- **Trigger**: re-verification after v3-dev merge 4d136e0 (exams/QA/reports routes shipped)
- **Version change**: 1.1.0 → 1.1.1 (PATCH)
- **Stakeholder**: PACS requirements architect

## Changed Requirements
none; re-verification only

Verified against post-merge codebase (4d136e0):
- FHIR Patient read/search, ImagingStudy + DocumentReference, HL7 ADT receiver, webhooks unchanged — statuses recorded at 02:18 (FR-R16-01/06/08/09/10 implemented; 02/04/05 GATED; 03/07 partial) remain accurate.
- `/exams/{id}/complete` now moves the internal worklist entry to `performed`, but this status is **not** published to the EMR via FHIR resource status or ORU — FR-R16-05 (results status) stays GATED.
- Report backfill (FR-R16-04) remains blocked on R12 report delivery (no DiagnosticReport/ORU outbound).

## Impact on Existing Artifacts
| Artifact | Changed? | Summary |
|----------|----------|---------|
| README.md | Yes | Post-merge re-verification note; version 1.1.0 → 1.1.1 |
| 01-user-requirements.md | No | Statuses unchanged |
| 06-acceptance-criteria.md | No | No GATED markers; unchanged |
| 07-traceability.md | No | Statuses unchanged |
| 08-implementation-roadmap.md | No | Statuses unchanged |
| CHANGELOG.md | Yes | Added 1.1.1 entry |
| DELTA.md | Yes | This file |
