# Requirements Package — R17 External PACS

| Field | Value |
|-------|-------|
| **Version** | 1.1.0 |
| **Status** | draft |
| **Generated** | 2026-08-03 |
| **Changelog** | [CHANGELOG.md](CHANGELOG.md) |

## Codebase Alignment (verified 2026-08-03)

**Interface surface**: API-only (no web UI). See artifact 04 — "System Interface
Surface": DICOMweb QIDO-RS/WADO-RS, WADO-URI, file upload (C-STORE-equivalent),
bulk download, routing rules all exist.

**Implemented**: QIDO-RS/WADO-RS study→series→instance drill-down, WADO-URI, upload,
bulk download, routing. **GATED**: C-MOVE retrieve workflow, archive synchronization
UI, migration/backfill tooling — flagged to backend.

## Role Summary

**Persona**: External PACS exchanging images with QuantumPACS over DICOM and
DICOMweb. System-to-system (no end-user UI).
**Access tier**: Integration — DICOM C-STORE/C-FIND/C-MOVE, DICOMweb
QIDO/WADO/STOW.
**Context**: The operational surface is the existing DICOMweb admin + replicas +
routing screens used by R01/R02.

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

- **R01/R02 Admin** — operates AE config, routing, replicas, metrics.
- **R06/R07 Technologist/Technician** — exam completion triggers PACS push (C-STORE).
- **R12/R18 Radiologist** — viewer consumes WADO-RS; priors via query/retrieve.
- **R04 Service Coordinator** — study lookup via C-FIND when scheduling.
- **R15/R16** — shared order/patient identities.

## Flagged Gaps (backend — must be raised before sprint commitment)

- WADO-RS progressive/lossy support for the viewer not confirmed.
- C-MOVE retry semantics (2x) need verification.
- Routing delivery success tracking (≥99%) needs a delivery log contract.
- Archive synchronization with replicas (backfill/retrieve-on-demand) not confirmed.
