# User Requirements — External PACS (R17)

**Version**: 1.0.0 (v3.0 scope)
**Status**: Draft
**Date**: 2026-08-02

## Functional Requirements

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-R17-01 | **DICOM C-STORE Receive**: Accept C-STORE associations (instances) from external PACS/modalities; persist to storage; return success/failure status per instance. | Must | DICOM SCP |
| FR-R17-02 | **DICOM C-FIND**: Serve query/retrieve C-FIND (study/series/instance level) with the expected keysets and a query timeout. | Must | Query timeout 30s |
| FR-R17-03 | **DICOM C-MOVE**: Serve C-MOVE retrieve requests; transfer matching instances to the requesting AE; support retrieval retry semantics. | Must | Retrieve retry 2x |
| FR-R17-04 | **DICOMweb QIDO-RS**: Expose DICOMweb QIDO-RS study/series/instance search with the same capabilities as C-FIND. | Must | DICOMweb admin exists |
| FR-R17-05 | **DICOMweb WADO-RS**: Expose WADO-RS for pixel/metadata retrieval (frames, bulk data, thumbnail) used by the viewer. | Must | Viewer WADO-RS |
| FR-R17-06 | **DICOMweb STOW-RS**: Accept STOW-RS stores (instances, bulk) from external systems. | Must | STOW-RS |
| FR-R17-07 | **Instance Routing**: Route stored instances to target AE/storage per configured routing rules (DICOM send) and log delivery. | Should | Routing rules exist |
| FR-R17-08 | **Archive Synchronization**: Synchronize studies across storage replicas and remote archives (retrieve-on-demand, backfill) with status tracking. | Should | Replica management |
| FR-R17-09 | **AE Node Management**: Manage DICOM AE nodes (local + remote titles, addresses, port, transfer syntaxes) with connectivity testing. | Must | DICOMweb admin/station AEs |
| FR-R17-10 | **Metrics & Monitoring**: Track store latency, query/retrieve timing, error rates, storage usage, and transfer failures; expose to R01/R02. | Must | DICOM admin metrics |

## Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-R17-01 | C-STORE acknowledgment | ≤ 10s per instance p95 | Synthetic probe |
| NFR-R17-02 | C-FIND query timeout | 30s cap | Synthetic probe |
| NFR-R17-03 | C-MOVE retrieve retry | 2x on failure | Integration test |
| NFR-R17-04 | Storage throughput | ≥ 100 MB/s sustained | Load test |
| NFR-R17-05 | DICOM service availability | 99.9% | Uptime monitoring |
| NFR-R17-06 | Audit of all transfers | 100% logged (AE, study, result) | Audit log scan |
| NFR-R17-07 | Admin surface (DICOMweb admin/replicas) load time | LCP ≤ 2.5s, INP ≤ 200ms, CLS < 0.1 | Lighthouse CI, RUM |

## Codebase Status (verified 2026-08-03)

**Implemented**: QIDO-RS/WADO-RS (`/dicomweb/studies*`), WADO-URI (`/wado`), file
upload (C-STORE-equivalent), bulk download, routing rules (`/routing`). **GATED**: C-MOVE
retrieve workflow, archive synchronization UI, migration/backfill tooling. See
artifacts 04/07/08.

## Assumptions & Constraints

- A1: DICOM (C-STORE/C-FIND/C-MOVE) over DICOM protocol + DICOMweb (QIDO/WADO/STOW) over HTTPS.
- A2: Failure semantics: C-FIND timeout 30s, C-MOVE retry 2x, C-STORE ack ≤ 10s.
- A3: The frontend surface is the DICOMweb admin + replicas screens (R01/R02); the external PACS has no UI.
- A4: Instance routing reuses the routing-rules engine; all-matching-rules-applied semantics.
- A5: Archive sync integrates with replica management (local/S3/B2).
