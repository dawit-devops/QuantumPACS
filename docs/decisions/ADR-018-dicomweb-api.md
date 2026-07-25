# ADR-018: DICOMweb API at /api/v2/dicomweb/

## Status
Accepted

## Date
2026-07-25

## Context

QuantumPACS v2.0 serves DICOM images exclusively through custom REST endpoints (`GET /api/files/{id}/data` with WADO-URI-style `wadouri:` URL construction in the frontend). There is no DICOMweb (DICOM PS3.18) RESTful API. This means:

- **No interoperability**: EHRs and RIS apps that speak DICOMweb cannot integrate with QuantumPACS. They must either use DIMSE (C-STORE on port 11112) or a custom integration.
- **No standard query**: External applications cannot search for studies using DICOM tag-based queries over HTTP. They must use the custom `POST /api/files` search or Elasticsearch directly.
- **No standard retrieve**: External applications cannot retrieve studies/series/instances as multipart DICOM over HTTP. They must use the internal `GET /api/files/{id}/data` which returns one file at a time.
- **No standard store**: External applications cannot push DICOM instances over HTTP. They must use C-STORE on port 11112, which requires DICOM networking stack.

DICOMweb (PS3.18) defines three RESTful services:
- **QIDO-RS** (Query based on ID for DICOM Objects) — search studies/series/instances via HTTP GET with query parameters
- **STOW-RS** (Store over the Web) — push DICOM instances via HTTP POST with multipart body
- **WADO-RS** (Web Access to DICOM Objects) — retrieve studies/series/instances via HTTP GET, return multipart DICOM
- **WADO-URI** — legacy URI-based retrieve (simpler URL pattern)

## Decision

Implement **full DICOMweb** (QIDO-RS + STOW-RS + WADO-RS + WADO-URI) at `/api/v2/dicomweb/` for v3.0.

### Endpoint Mapping

| DICOMweb Service | HTTP | Path | v3 Endpoint |
|------------------|------|------|-------------|
| QIDO-RS studies | GET | `/studies` | `/api/v2/dicomweb/studies?PatientID=...` |
| QIDO-RS series | GET | `/series` | `/api/v2/dicomweb/series?StudyInstanceUID=...` |
| QIDO-RS instances | GET | `/instances` | `/api/v2/dicomweb/instances?SeriesInstanceUID=...` |
| WADO-RS study | GET | `/studies/{uid}` | `/api/v2/dicomweb/studies/{studyUID}` |
| WADO-RS study metadata | GET | `/studies/{uid}/metadata` | `/api/v2/dicomweb/studies/{studyUID}/metadata` |
| WADO-RS series | GET | `/studies/{uid}/series/{uid}` | `/api/v2/dicomweb/studies/{studyUID}/series/{seriesUID}` |
| WADO-RS series metadata | GET | `/studies/{uid}/series/{uid}/metadata` | `/api/v2/dicomweb/.../series/{seriesUID}/metadata` |
| WADO-RS instance | GET | `/studies/{uid}/series/{uid}/instances/{uid}` | `/api/v2/dicomweb/.../instances/{instanceUID}` |
| WADO-RS instance metadata | GET | `/studies/{uid}/series/{uid}/instances/{uid}/metadata` | `/api/v2/dicomweb/.../instances/{instanceUID}/metadata` |
| WADO-RS frames | GET | `/studies/{uid}/series/{uid}/instances/{uid}/frames/{frames}` | `/api/v2/dicomweb/.../frames/{frameNumbers}` |
| STOW-RS | POST | `/studies` | `POST /api/v2/dicomweb/studies` |
| WADO-URI | GET | `/wado` | `/api/v2/wado?requestType=WADO&studyUID=...` |

### Content Types

| Service | Request Content-Type | Response Content-Type |
|---------|---------------------|-----------------------|
| QIDO-RS | — | `application/dicom+json` |
| WADO-RS retrieve | — | `multipart/related; type=application/dicom` |
| WADO-RS metadata | — | `application/dicom+json` |
| WADO-RS frames | — | `application/octet-stream` (raw) or `image/png` (rendered) |
| STOW-RS | `multipart/related; type=application/dicom` | `application/dicom+json` |
| WADO-URI | — | `application/dicom` |

### Implementation Strategy

1. **QIDO-RS**: Maps DICOM tag query parameters to PostgreSQL columns. Returns DICOM JSON Model (PS3.18 §6.3.3). Supports `offset`/`limit` pagination with `X-Total-Count` header.
2. **WADO-RS**: Reads files from storage backend, assembles multipart response. Uses `TransferSyntax` from stored metadata to negotiate acceptable transfer syntaxes.
3. **STOW-RS**: Parses multipart body, extracts DICOM datasets per part, delegates to the same `files.add()` code path used by C-STORE. Returns `0000` (Success) or `0110` (Processing Failure) per instance in the response.
4. **WADO-URI**: Thin wrapper around WADO-RS internal handler, translating URL query parameters to the internal retrieve interface.

### STOW-RS ↔ C-STORE Bridge

DICOM instances received via STOW-RS produce identical database and storage state as those received via C-STORE. Both paths:
- Extract DICOM metadata via `dcm/file.py::parse_dcm`
- Compute SHA-256 hash for deduplication
- Write file to storage backend (local/S3/B2)
- Upsert patient, study, series records
- Insert file record with DICOMweb self-reference URL
- Publish `study.stored` event to Redis Streams `events:ingestion`

## Consequences

### Positive

- **Interoperability**: Any DICOMweb-compliant client (EHR, RIS, external viewer) can query, store, and retrieve studies over standard HTTPS.
- **IHE Conformance**: Enables participation in IHE Connectathon for the "Web Access to DICOM Objects" (WADO) and "Cross-Enterprise Document Sharing" profiles.
- **Frontend simplification**: The Cornerstone3D viewer can load studies directly via WADO-RS instead of per-file WADO-URI, reducing the number of HTTP requests for multi-instance studies.

### Negative

- **DICOM JSON model complexity**: The DICOM JSON model (PS3.18 §6.3.3) requires mapping DICOM VR types to JSON types (e.g., `DS` → number, `PN` → object with `Alphabetic` property). The mapping library must be built or sourced.
- **Multipart handling**: Python's `multipart` parsing libraries (especially for streaming) are less mature than DICOM networking libraries. May require custom multipart parser for STOW-RS.
- **Conformance risk**: DICOMweb is a large spec. Without IHE Connectathon testing, edge cases in frame retrieval or bulk data URIs may be non-conformant. Mitigation: self-certification test suite runs in CI.

## References

- PRD-v3.md §3.6 — DICOMweb Implementation
- IMPLEMENTATION_PLAN-v3.md Phase 3 — DICOMweb (QIDO-RS, STOW-RS, WADO-RS, WADO-URI)
- DICOM PS3.18: "Web Services"
- IHE Radiology Technical Framework Supplement: "Web Access to DICOM Objects" (WADO)