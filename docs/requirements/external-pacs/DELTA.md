# Delta — External PACS (R17) — 2026-08-03

## Summary
- **Trigger**: re-verification after v3-dev merge 4d136e0 (exams/QA/reports routes shipped)
- **Version change**: 1.1.0 → 1.1.1 (PATCH)
- **Stakeholder**: PACS requirements architect

## Changed Requirements
none; re-verification only

Verified against post-merge codebase (4d136e0):
- DICOMweb QIDO-RS/WADO-RS (`/dicomweb/studies*`), WADO-URI (`/wado`), file upload (C-STORE-equivalent), bulk download, routing (`/routing`) all unchanged.
- DICOM C-STORE SCP + MWL SCP (`backend/dcm/server.py`) unchanged.
- Merge added exam/QA/report routes only — no effect on R17 FRs. Statuses recorded at 02:18 remain accurate (FR-R17-01/04/05/09/10 implemented; 02/03/06 partial; 07 GATED).

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
