# Persona: Diagnostic Imaging Modalities

## Persona Card

| Attribute | Detail |
|-----------|--------|
| **Role** | Diagnostic imaging modalities (CT, MRI, X-ray, Ultrasound, PET/CT scanners from GE, Siemens, Canon, Philips, etc.) |
| **Description** | Imaging hardware devices that connect to QuantumPACS via DICOM DIMSE protocol to verify connectivity, query worklists, send acquired images, and optionally receive studies back |
| **Technical Level** | High — protocol-level (DICOM standard), configuration via AE Title, port, and presentation context |
| **Frequency** | Per-examination — connects per patient study, sends series of images |
| **Devices** | CT gantry, MRI bore, X-ray console, ultrasound machine, PET/CT scanner |
| **Critical Needs** | Reliable C-ECHO verification, MWL query for scheduled exams, fast C-STORE for image ingestion, DICOM conformance compatibility |
| **Frustrations** | No C-ECHO handler (cannot verify connectivity), no MPPS SCP (no real-time scan progress), compressed transfer syntaxes not explicitly configured, C-MOVE/C-GET are stubs |
| **Integration Protocol** | DICOM DIMSE (native) + DICOMweb (STOW-RS/WADO-RS/QIDO-RS) |

## Routes & Protocol Endpoints

### DICOM DIMSE (Native DICOM Protocol)

| Service | Role | Port | SOP Class UID | Status |
|---------|------|------|---------------|--------|
| **C-STORE** | SCP | 11112 | All Storage SOP Classes (via `StoragePresentationContexts`) | **FULL** |
| **C-FIND** | SCP | 11112 | `ModalityWorklistInformationFind` (1.2.840.10008.5.1.4.31) | **FULL** (MWL only) |
| **C-MOVE** | SCP + SCU | 11112 | `PatientRootQueryRetrieveInformationModelMove`, `StudyRootQueryRetrieveInformationModelMove` | **STUB** — registered but no-op |
| **C-GET** | SCP | 11112 | `PatientRootQueryRetrieveInformationModelGet`, `StudyRootQueryRetrieveInformationModelGet` | **STUB** — registered but no-op |
| **C-ECHO** | SCP | 11112 | Verification SOP Class (1.2.840.10008.1.1) | **NOT IMPLEMENTED** — no handler |
| **MPPS (N-CREATE/N-SET)** | SCP | 11112 | Modality Performed Procedure Step (1.2.840.10008.5.1.4.34) | **NOT IMPLEMENTED** |

### DICOMweb (REST API over HTTP)

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| GET | `/api/v2/dicomweb/studies` | `DICOMWEB_READ` | QIDO-RS: search studies |
| GET | `/api/v2/dicomweb/studies/{uid}/series` | `DICOMWEB_READ` | QIDO-RS: search series |
| GET | `/api/v2/dicomweb/studies/{uid}/series/{uid}/instances` | `DICOMWEB_READ` | QIDO-RS: search instances |
| GET | `/api/v2/dicomweb/studies/{uid}` | `DICOMWEB_READ` | WADO-RS: retrieve full study |
| GET | `/api/v2/dicomweb/studies/{uid}/series/{uid}` | `DICOMWEB_READ` | WADO-RS: retrieve series |
| GET | `/api/v2/dicomweb/studies/{uid}/series/{uid}/instances/{uid}` | `DICOMWEB_READ` | WADO-RS: retrieve single instance |
| POST | `/api/v2/dicomweb/studies` | `DICOMWEB_WRITE` | STOW-RS: push DICOM instances |

### Legacy WADO-URI

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| GET | `/api/wado` | `DICOMWEB_READ` | Legacy WADO-URI retrieval |

### DICOM AE Title Configuration

| Parameter | Default | Config Key | Env Variable |
|-----------|---------|------------|--------------|
| **AE Title** | `QUANTUMPACS` | `dicom_ae_title` | `DICOM_AE_TITLE` |
| **C-STORE Port** | `11112` | `dicom_cstore_port` | `DICOM_CSTORE_PORT` |
| MWL Port | `11113` | `dicom_mwl_port` | `DICOM_MWL_PORT` (defined but not wired) |
| C-MOVE Port | `11114` | `dicom_cmove_port` | `DICOM_CMOVE_PORT` (defined but not wired) |

**Note**: All services currently bind to single port 11112 via pynetdicom. MWL, C-MOVE, and C-GET are configured on separate ports in `default_config` but not registered in `lifecycle.py`.

## End-to-End Flows

### Flow 1: Verify Connectivity (C-ECHO — NOT AVAILABLE)

```
Current status: C-ECHO handler is NOT registered in the pynetdicom AE.
A modality attempting C-ECHO will receive a failure response or association rejection.

What should happen (desired):
  1. Modality opens association to QUANTUMPACS:11112
     with Verification SOP Class (1.2.840.10008.1.1)
  2. Modality sends C-ECHO-RQ
  3. PACS responds with C-ECHO-RSP (0x0000 Success)
  4. Modality confirms PACS is reachable

Actual behavior:
  - No EVT_C_ECHO handler exists in server.py handlers list
  - pynetdicom may auto-respond or may reject
  - Recommend modality use C-STORE with test instance as connectivity test
  - Recommend admin use /api/health endpoint which probes DICOM listener port

PACS workaround:
  - Admin can verify DICOM listener is running via:
    GET /api/health → checks dicom_listener component status
  - Modality can send a minimal C-STORE test DICOM file
```

### Flow 2: Query Modality Worklist (C-FIND MWL)

```
1. Modality opens DICOM association to QUANTUMPACS:11112
   with presentation context: ModalityWorklistInformationFind
   (SOP Class UID: 1.2.840.10008.5.1.4.31)

2. Modality sends C-FIND-RQ with query keys:
   - ScheduledProcedureStepSequence[0].ScheduledStationAETitle = "CT01"
   - Modality = "CT"
   - ScheduledProcedureStepSequence[0].ScheduledProcedureStepStartDate = "20260729"

3. QuantumPACS handle_find_async() in dcm/server.py:
   a. Parses query dataset for query keys
   b. Queries worklist_entries table WHERE status = 'scheduled'
   c. Matches on:
      - PatientID (ILIKE partial match)
      - Modality (exact match)
      - StationAETitle (exact match on SPS[0].ScheduledStationAETitle)
      - ScheduledDate (date range on ScheduledProcedureStepStartDate)
      - AccessionNumber (ILIKE partial match)
   d. Returns up to 1000 matching entries

4. Each response is a DICOM dataset with MWL attributes:
   - PatientName, PatientID, PatientBirthDate, PatientSex
   - AccessionNumber, StudyInstanceUID
   - RequestedProcedureID, RequestedProcedureDescription
   - ScheduledProcedureStepSequence with:
     Modality, ScheduledStationAETitle, ScheduledProcedureStepStartDate,
     ScheduledProcedureStepStartTime, ScheduledPerformingPhysicianName

5. Modality uses returned MWL data to auto-populate exam entry on scanner UI

6. If no matches → C-FIND-RSP with status 0x0000 (pending) then 0x0100 (success, no matches)
```

### Flow 3: Send Images via C-STORE

```
1. Modality has acquired all images for a study
2. Modality opens DICOM association to QUANTUMPACS:11112
   with appropriate Storage SOP Class presentation context
   (e.g., CT Image Storage 1.2.840.10008.5.1.4.1.1.2)

3. For each DICOM instance in the study:
   a. Modality sends C-STORE-RQ with:
      - SopClassUID (e.g., CT Image Storage)
      - SopInstanceUID (unique per instance)
      - File meta information (TransferSyntaxUID, MediaStorageSOPClassUID, etc.)
      - Binary DICOM data

   b. QuantumPACS handle_store() in dcm/server.py:
      - Saves dataset + file_meta to BytesIO
      - Bridges to async via asyncio.run_coroutine_threadsafe(timeout=60s)
      - Returns 0x0000 (Success) or 0x0001 (Failure)

   c. Backend store_instance() in dcm/store.py (async):
      i. Lazy init DB pool + ES on first call
      ii. get_meta(ds): Extract DICOM tags → dict
         - PatientID (0010,0020) → patient_id
         - PatientName (0010,0010) → patient_name
         - PatientBirthDate (0010,0030) → patient_birth_date
         - PatientSex (0010,0040) → patient_sex
         - StudyID (0020,0010) → study_id
         - StudyDescription (0008,1030) → study_description
         - StudyInstanceUID (0020,000D) → study_instance_uid
         - AccessionNumber (0008,0050) → accession_number
         - SeriesNumber (0020,0011) → series_number
         - SeriesInstanceUID (0020,000E) → series_instance_uid
         - Modality (0008,0060) → modality
         - SeriesDescription (0008,103E) → series_description
         - SOPInstanceUID (0008,0018) → sop_instance_uid
         - All tags → meta JSONB column
      iii. SHA-256 hash of file bytes
      iv. Check Files.get_by_hash(hash) → dedup skip if exists
      v. Acquire DB connection, start transaction:
         - Get master replica
         - Files.insert_or_select() → upsert patient/study/series hierarchy
         - Copy file bytes to master storage
         - Add replica_files records for all configured replicas
      vi. After transaction (post-commit):
         - match_worklist_performed(): check accession_number → mark worklist as performed
         - evaluate_routing_rules(): copy to destination replicas if conditions match
      vii. Increment dicom_cstore_throughput_bytes Prometheus counter

   d. File stored at path: {patient_id}/{study_id}/{series_number}/{uuid}.dcm
      where uuid is a UUID4-generated filename (not original DICOM filename)

4. After all instances sent, modality may send MPPS (NOT IMPLEMENTED)

5. Modality considers study complete when:
   - All C-STORE responses are 0x0000
   - OR via polling /worklist endpoint on accession number
```

### Flow 4: Retrieve Study via DICOMweb WADO-RS

```
A modality or gateway can retrieve studies via DICOMweb REST API:

GET /api/v2/dicomweb/studies/{study_uid}
Headers: Authorization: Bearer <jwt> or X-API-Key <qpk_...>
Accept: multipart/related; type=application/dicom

Response 200:
  Content-Type: multipart/related; boundary="----=_Part_1_123456"
  Body:
    ------=_Part_1_123456
    Content-Type: application/dicom
    Content-ID: <1.2.840.12345.1.234>
    <binary DICOM data for study instance 1>
    ------=_Part_1_123456
    Content-Type: application/dicom
    Content-ID: <1.2.840.12345.1.235>
    <binary DICOM data for study instance 2>
    ------=_Part_1_123456--
```

### Flow 5: Push Study via DICOMweb STOW-RS (Alternative to C-STORE)

```
A modality gateway or RIS can push images via STOW-RS:

POST /api/v2/dicomweb/studies
Content-Type: multipart/related; boundary="----=_Part_1_123456"
Accept: application/dicom+json
X-Auth-Pacs: <jwt_token>

------=_Part_1_123456
Content-Type: application/dicom
Content-ID: <1.2.840.12345.1.234>
Content-Location: /studies/1.2.840.12345.1.234
<binary DICOM data>
------=_Part_1_123456--

Response 201:
Content-Type: application/json
{
  ["1.2.840.12345.1.234", "1.2.840.12345.1.235", ...]
}

→ Same storage pipeline as C-STORE (dedup, worklist match, routing)

Modality whitelist check: MODALITY must be in VALID_MODALITIES frozenset:
  CR, CT, MR, US, OT, BI, CD, DD, DG, ES, LS, PT, RG, ST, TG, XA, XC, AS, DS, CF, DF, DM,
  EC, FA, CS, LP, MA, MS, NM, DX, GM, HD, IO, IX, PX, RF, SM, SR, VA, MG, EPS, OP,
  OAM, OCT, OPT, OPV, OSS, POS, IVOCT, LEN
```

### Flow 6: Study Routing (Automatic, Triggered by C-STORE)

```
During Flow 3 (C-STORE), routing rules are evaluated:

1. store_instance() calls evaluate_routing_rules(metadata, tenant_id)
2. loads all enabled routing_rules from DB (ordered by priority)
3. For each rule:
   a. Evaluates condition JSON against DICOM metadata
   b. Condition operators: eq, ne, contains, gt, gte, lt, lte, $or
   c. Example condition: {"modality": "CT", "study_description": {"contains": "CHEST"}}
   d. If match: adds {rule_id, rule_name, destination} to results
4. For each matched destination (replica ID):
   a. Copies file via storage.copy() to that replica's backend
   b. Writes replica_files record with status=indexing
5. Results are logged at info level with study_instance_uid and rule names

Routing takes effect at C-STORE/STOW-RS time — no batch processing needed.
```

### Flow 7: Modality-Initiated C-MOVE Request (STUB — No-Op)

```
Current status: C-MOVE SCP is registered but returns 0x0000 (Success) with no operation.

Desired behavior (v3.0+):
  1. Modality sends C-MOVE-RQ to PACS with study UID and destination AE Title
  2. PACS C-MOVE SCP queries study by UID
  3. PACS establishes new association with destination AE (C-STORE role)
  4. PACS sends each DICOM file to destination via C-STORE
  5. Returns C-MOVE response with progress/status

Actual behavior:
  - handle_move() in server.py logs warning 'C-MOVE received but not fully implemented'
  - Returns 0x0000 (Success) immediately without operation
  - C-MOVE SCU (modality requesting push) does not exist in codebase
  - No C-MOVE functionality for modality→PACS or PACS→remote-PACS image transfer
```

### Flow 8: MPPS Scan Progress Reporting (NOT IMPLEMENTED)

```
Current status: No MPPS SCP implementation.

Desired behavior (v3.1):
  1. Modality opens association with MPPS SOP Class
  2. Sends N-CREATE with MPPS attributes (studystate='IN PROGRESS')
  3. During scan, can send N-SET to update progress
  4. At scan end, sends N-SET with studystate='COMPLETED'
  5. PACS updates worklist/mapping accordingly

Actual workaround:
  - match_worklist_performed() in store.py auto-marks MWL as performed
    when first C-STORE arrives with matching accession_number
  - No progression through In Progress states
  - worklist entry jumps from 'scheduled' directly to 'performed' on first image arrival
```

## Metrics & SLAs

| Metric | Target | How Measured |
|--------|--------|-------------|
| C-ECHO response time | < 100ms (when implemented) | pynetdicom timing |
| MWL C-FIND response time | < 500ms | pynetdicom timing |
| C-STORE ingestion per instance | < 2s (LAN) | Prometheus counter |
| C-STORE dedup lookup | < 10ms | SHA-256 hash index |
| Routing rule evaluation | < 50ms per instance | In-memory JSONB evaluation |
| MWL C-FIND max results | 1000 entries | Hard limit in handle_find_async |
| Transfer syntax support | Explicit VR Little Endian (primary) | pynetdicom defaults |
| Storage path computation | Deterministic | `{patient_id}/{study_id}/{series_number}/{uuid}.dcm` |
| DICOMweb STOW-RS upload | < 500ms per instance | Same as C-STORE pipeline |
| Worklist status transition | Immediate on first C-STORE | Post-commit hook |

## Acceptance Criteria

### From PRD / Technical Specifications

1. C-STORE SCP accepts all standard Storage SOP Classes on port 11112
2. C-FIND MWL SCP returns matching worklist entries on port 11112
3. MWL C-FIND supports query keys: PatientID, Modality, AccessionNumber, StationAETitle, ScheduledProcedureStepStartDate
4. Stored images follow storage path convention: `{patient_id}/{study_id}/{series_number}/{uuid}.dcm`
5. SHA-256 dedup prevents duplicate storage
6. Patient→Study→Series→Instance hierarchy upserted idempotently
7. Auto-worklist-match transitions status to 'performed' on C-STORE receipt
8. Auto-routing copies files to matched replica destinations
9. DICOMweb STOW-RS follows identical pipeline to native C-STORE
10. DICOMweb QIDO-RS returns study/series/instance metadata
11. DICOMweb WADO-RS retrieves full study/series/instance data
12. DICOMweb responses use `application/dicom+json` content type (per PS3.18)
13. All DICOM endpoints require JWT authentication (DICOMweb)
14. STOW-RS validates modality against VALID_MODALITIES whitelist

### Derived from Code (Additional)

15. Transfer syntax for MWL C-FIND responses is ExplicitVRLittleEndian
16. File meta uses ExplicitVRLittleEndian TransferSyntaxUID for stored files
17. Storage backends support: local filesystem (master), S3-compatible, Backblaze B2 (replicas)
18. File chunking: no explicit chunking — files read into memory then stored
19. DICOM DIMSE timeout: 60s for C-STORE async bridge (asyncio.run_coroutine_threadsafe timeout)
20. pynetdicom StoragePresentationContexts used as default — no manual SOP class registration per type
21. The AE Title is configurable: `QUANTUMPACS` default, overridden via config.local.yaml or `DICOM_AE_TITLE` env var
22. No AE Title allowlisting — any network-reachable modality can store images
23. Single-port binding: all DICOM services (C-STORE, C-FIND, C-MOVE, C-GET) currently share port 11112
24. MWL port 11113 and C-MOVE port 11114 are defined in default_config but not wired in lifecycle.py
25. DICOM conformance statement (CapabilityStatement) not formally generated for DICOM DIMSE (unlike FHIR CapabilityStatement)

## Implementation Gaps

| Feature | Status | Impact | Target Version |
|---------|--------|--------|---------------|
| C-ECHO SCP | NOT IMPLEMENTED | Modalities cannot verify connectivity via standard DICOM ECHO | v3.1 |
| MPPS SCP (N-CREATE/N-SET) | NOT IMPLEMENTED | No real-time scan progress tracking; worklist jumps scheduled→performed | v3.1 |
| C-MOVE SCP (actual implementation) | STUB (no-op) | PACS cannot respond to C-MOVE requests from modalities | v3.0 |
| C-MOVE SCU | NOT IMPLEMENTED | PACS cannot push studies to remote sites or retrieve from modalities | v3.0+ |
| C-GET SCP (actual implementation) | STUB (no-op) | Same as C-MOVE SCP, no-op | v3.0 |
| C-FIND for Query/Retrieve (non-MWL) | NOT IMPLEMENTED | Modalities cannot query available studies (only MWL for scheduled worklist) | v3.x |
| Compressed transfer syntaxes (JPEG2000, JPEG-LS, RLE) | NOT CONFIGURED | Modalities sending compressed images may fail association negotiation | v3.1 |
| DICOM printer (Basic Film Session) | NOT IMPLEMENTED | No DICOM printing capability | Not planned |
| AE Title allowlisting | NOT IMPLEMENTED | Any network-reachable modality can store images — security at network layer only | v3.x |
| DICOM conformance statement | NOT GENERATED | No formal DICOM conformance statement document for QuantumPACS | Document |
| Separate MWL port (11113) | NOT WIRED | MWL C-FIND shares port 11112 with C-STORE; separate port config exists but unused | v3.x |
| Separate C-MOVE port (11114) | NOT WIRED | C-MOVE SCU/SCP shares port 11112; separate port config exists but unused | v3.x |
| DICOM network encryption (TLS) | NOT CONFIGURED | DICOM DIMSE traffic is unencrypted on port 11112 | v3.x (for production) |
| Study status tracking | MISSING | No study-level status beyond worklist status | v3.x |

## Key Files Reference

| File | Purpose |
|------|---------|
| `backend/dcm/server.py` | DICOM SCP handlers (C-STORE, C-FIND MWL, C-MOVE stub, C-GET stub) |
| `backend/dcm/store.py` | C-STORE pipeline (dedup, upsert, storage, worklist match, routing) |
| `backend/dcm/file.py` | DICOM metadata extraction (`get_meta()`) |
| `backend/lifecycle.py` | DICOM AE startup (port, AE title, presentation contexts, handlers) |
| `backend/config.py` | Default config (ports, AE title, transfer syntaxes) |
| `backend/dcm/config.py` | DICOM conformance and SOP class configuration |
| `backend/api/dicomweb.py` | DICOMweb QIDO-RS / WADO-RS / STOW-RS endpoints |
| `backend/api/routes.py` | Full route registration (DICOM + DICOMweb) |
| `backend/api/permissions.py` | DICOMWEB_READ, DICOMWEB_WRITE permissions |
| `backend/db/files.py` | Files DB model (storage path, dedup lookup, upsert) |
| `docs/Technical-Specifications.md` | DICOM conformance, ports, services specification |
| `docs/PRD.md` | v2 PRD DICOM sections |
| `docs/decisions/ADR-004-dicom-store-scp.md` | C-STORE SCP architecture decision |
| `docs/decisions/ADR-005-dicomweb-proxy.md` | DICOMweb proxy architecture decision |
| `docs/decisions/ADR-006-auto-routing.md` | Auto-routing architecture decision |
| `docs/decisions/ADR-011-replica-sync-notify.md` | Replica sync architecture decision |