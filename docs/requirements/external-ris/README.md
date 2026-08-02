# Requirements Package — R15 External RIS

| Field | Value |
|-------|-------|
| **Version** | 1.1.0 |
| **Status** | draft |
| **Generated** | 2026-08-03 |
| **Changelog** | [CHANGELOG.md](CHANGELOG.md) |

## Codebase Alignment (verified 2026-08-03)

**Interface surface**: API-only (no web UI). See artifact 04 — "System Interface
Surface": worklist CRUD, HL7 receiver (`POST /hl7`), DICOMweb query, FHIR
ServiceRequest/DocumentReference scaffolding, webhook delivery all exist.

**Implemented**: HL7 ORM/ORU inbound, worklist CRUD, DICOMweb query, webhook push.
**GATED**: full MWL/MPPS lifecycle, report delivery push, dead-letter + manual
reconciliation UI, message retry policies — flagged to backend.

## Role Summary

**Persona**: External Radiology Information System exchanging orders, scheduling,
and results with QuantumPACS. System-to-system (no end-user UI).
**Access tier**: Integration — HL7 ORM/ORU, DICOM MWL C-FIND.
**Context**: The operational surface is the existing HL7 admin/dashboard used by
R01/R02; the RIS itself integrates over MLLP.

## Artifact Index

| # | Artifact | File |
|---|----------|------|
| 01 | User Requirements | `01-user-requirements.md` |
| 02 | End-to-End Workflow Maps | `02-workflow-maps.md` |
| 03 | User Stories | `03-user-stories.md` |
| 04 | UI/UX Requirements | `04-ui-ux-requirements.md` |
| 05 | Metrics & SLAs | `05-metrics-slas.md` |
| 06 | Acceptance Criteria (validator-gated) | `06-acceptance-criteria.md` |
| 07 | Traceability Matrix | `07-traceability.md` |
| 08 | Implementation Roadmap | `08-implementation-roadmap.md` |

## Cross-Role Dependencies

- **R01/R02 Admin** — operates the HL7 integration config and message dashboard.
- **R04 Service Coordinator** — scheduled orders populate the schedule board.
- **R06/R07 Technologist/Technician** — orders populate modality worklists.
- **R12/R18 Radiologist** — finalized reports delivered via ORU.
- **R16 External EMR** — shared patient demographics; R17 for image exchange.

## Flagged Gaps (backend — must be raised before sprint commitment)

- Outbound status/report delivery (ORM/ORU) not confirmed wired to report finalization.
- Reconciliation/retry semantics for outbound queue not confirmed.
- MWL C-FIND result cap and modality/AE mapping need verification.
