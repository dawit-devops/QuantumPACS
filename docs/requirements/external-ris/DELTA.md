# Delta — External RIS (R15) — 2026-08-03

## Summary
- **Trigger**: re-verification after v3-dev merge 4d136e0 (exams/QA/reports routes shipped)
- **Version change**: 1.1.0 → 1.1.1 (PATCH)
- **Stakeholder**: PACS requirements architect

## Changed Requirements
none; re-verification only

Verified against post-merge codebase (4d136e0):
- `/exams` + `/exams/{id}/complete` (EXAM_WRITE) now exist. `ExamCompleteHandler` marks the exam `completed`, moves the source worklist entry to `performed` with `performed_at`, and notifies the `radiologist` role in-app. **No outbound HL7 ORM/ORU message is sent to the external RIS** — FR-R15-03 (status updates outbound via HL7) remains GATED; the internal status-transition half exists but the delivery contract does not. Not marked partial: the FR's core contract (delivery to RIS) is unmet.
- HL7 `POST /hl7` receiver + admin, worklist CRUD, DICOMweb query, webhooks unchanged (already implemented at 02:18).
- MWL C-FIND SCP (`backend/dcm/server.py`, ModalityWorklistInformationFind) re-confirmed.
- `PermissionRoute` enforces role-based route access (R15 is API-only; no impact).

## Impact on Existing Artifacts
| Artifact | Changed? | Summary |
|----------|----------|---------|
| README.md | Yes | Post-merge re-verification note; version 1.1.0 → 1.1.1 |
| 01-user-requirements.md | Yes | Codebase Status: re-verification note appended (no status change) |
| 06-acceptance-criteria.md | No | No GATED markers; unchanged |
| 07-traceability.md | Yes | GATED table: FR-R15-03 row + MWL note updated (statuses unchanged) |
| 08-implementation-roadmap.md | Yes | FR-R15-03 blocking-dependency note updated (status unchanged) |
| CHANGELOG.md | Yes | Added 1.1.1 entry |
| DELTA.md | Yes | This file |
