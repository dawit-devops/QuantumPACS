# Persona: External RIS Applications

## Persona Card

| Attribute | Detail |
|-----------|--------|
| **Role** | External Radiology Information System (e.g., Epic Radiant RIS, GE Centricity RIS, Merge RIS, custom RIS) that orders imaging studies, schedules patients, and receives results from QuantumPACS |
| **Description** | Machine/system-level integration for RIS-to-PACS bidirectional workflow — order creation, MWL population, study completion notification, and results delivery |
| **Technical Level** | High — protocol-level integration (HL7 MLLP, DICOM DIMSE, HTTP REST) |
| **Frequency** | Continuous — per-order, per-schedule, per-completion |
| **Devices** | Application server, middleware |
| **Critical Needs** | Reliable order entry (ORM/ADT), MWL delivery to modalities, study completion notification, routing rule management |
| **Frustrations** | No outbound webhook for study completion notification, no MPPS, no DICOM C-MOVE SCU for push retrieval, polling-only completion detection |
| **Integration Pattern** | Mixed push/pull — RIS pushes orders and ADT (MLLP/HTTP), polls PACS for status (REST API / DICOM C-FIND) |

## Routes & Permissions

### MWL Management API

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| GET | `/api/worklist` | `WORKLIST_READ` | List/search MWL entries |
| POST | `/api/worklist` | `WORKLIST_WRITE` | Create MWL entry |
| GET | `/api/worklist/{id}` | `WORKLIST_READ` | Get single MWL entry |
| PUT | `/api/worklist/{id}` | `WORKLIST_WRITE` | Update MWL entry |
| DELETE | `/api/worklist/{id}` | `WORKLIST_WRITE` | Cancel MWL entry |

### MWL API Request/Response Schemas

**Create (`POST /api/worklist`)** — `CreateWorklistRequest` in `backend/api/schemas/worklist.py`:
```json
{
  "patient_id": "P001",
  "patient_name": "Smith^John",
  "patient_birth_date": "19700101",
  "patient_sex": "M",
  "accession_number": "ACC-20260725-001",
  "requested_procedure_id": "REQ-1001",
  "requested_procedure_desc": "CHEST PA AND LAT",
  "scheduled_date": "2026-07-25",
  "scheduled_time": "14:30:00",
  "modality": "CT",
  "station_ae_title": "CT01"
}
```

**Query (`GET /api/worklist`)** — Query params:
- `status`: `scheduled`, `performed`, `cancelled`
- `modality`: exact match
- `date_from`, `date_to`: date range filters
- `search`: text search across patient_name, patient_id, accession_number
- `page`, `per_page`: pagination (max 1000)

### HL7 HTTP Receiver

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| POST | `/api/hl7` | `WORKLIST_WRITE` | Accept raw HL7 message over HTTP (delegates to same handler as MLLP) |

- Content-Type: `application/x-hl7`
- Raw HL7 v2.x message as body
- Same `parse_hl7_message()` as MLLP server

### DICOM MWL C-FIND (Modality Queries PACS)

| Protocol | Port | SOP Class | Description |
|----------|------|-----------|-------------|
| DICOM C-FIND | 11112 | `ModalityWorklistInformationFind` (1.2.840.10008.5.1.4.31) | Modality queries scheduled worklist entries |

### DICOM MWL C-FIND Supported Query Keys

The `handle_find_async()` in `dcm/server.py` parses these DICOM tags from the C-FIND request:

| DICOM Tag | DICOM Keyword | Query Effect |
|-----------|---------------|--------------|
| (0010,0020) | PatientID | Partial match (ILIKE `%value%`) |
| (0008,0060) | Modality | Exact match |
| (0040,0100) → ScheduledProcedureStepSequence[0].ScheduledStationAETitle | ScheduledStationAETitle | Exact match |
| (0040,0100) → ScheduledProcedureStepSequence[0].ScheduledProcedureStepStartDate | ScheduledProcedureStepStartDate | Date range filter |
| (0040,0100) → ScheduledProcedureStepSequence[0].Modality | Modality (in SPS) | Exact match |
| (0008,0050) | AccessionNumber | Partial match (ILIKE `%value%`) |

### DICOM MWL C-FIND Return Keys

| DICOM Tag | DICOM Keyword | Source (worklist DB column) |
|-----------|---------------|---------------------------|
| (0010,0010) | PatientName | `patient_name` |
| (0010,0020) | PatientID | `patient_id` |
| (0010,0030) | PatientBirthDate | `patient_birth_date` |
| (0010,0040) | PatientSex | `patient_sex` |
| (0008,0050) | AccessionNumber | `accession_number` |
| (0020,000D) | StudyInstanceUID | `study_uid` |
| (0040,1001) | RequestedProcedureID | `requested_procedure_id` |
| (0032,1060) | RequestedProcedureDescription | `requested_procedure_desc` |
| (0008,0060) | Modality (in SPS) | `modality` |
| (0040,0001) | ScheduledStationAETitle | `station_ae_title` |
| (0040,0002) | ScheduledProcedureStepStartDate | `scheduled_date` |
| (0040,0003) | ScheduledProcedureStepStartTime | `scheduled_time` |
| (0008,0090) | ReferringPhysicianName | (empty — not in worklist schema) |
| (0032,1032) | RequestingPhysician | (empty) |
| (0040,0006) | ScheduledPerformingPhysicianName | (empty) |
| (0040,0007) | ScheduledProcedureStepDescription | (empty) |

### DICOM MWL Server Configuration

- **Port**: 11112 (shared with C-STORE; `dicom_mwl_port: 11113` defined in config but not wired)
- **SOP Class registered**: `ModalityWorklistInformationFind` (1.2.840.10008.5.1.4.31)
- **Max results**: 1000 entries per C-FIND response
- **Supported in `lifecycle.py`**: `[build_context(ModalityWorklistInformationFind)]` added to AE `supported_contexts`

### Routing Rules Management API

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| GET | `/api/routing` | `ROUTING_READ` | List routing rules (paginated) |
| POST | `/api/routing` | `ROUTING_WRITE` | Create routing rule |
| GET | `/api/routing/{id}` | `ROUTING_READ` | Get single rule |
| PUT | `/api/routing/{id}` | `ROUTING_WRITE` | Update rule |
| DELETE | `/api/routing/{id}` | `ROUTING_WRITE` | Delete rule |

**Routing Rule Schema** (`CreateRoutingRequest` in `backend/api/schemas/routing.py`):
```json
{
  "name": "Route CT Chest to Fast Storage",
  "description": "Optional description",
  "conditions": {"modality": "CT", "study_description": {"contains": "CHEST"}},
  "destination": "2",
  "priority": 0,
  "enabled": true
}
```

**Condition operators**: `eq`, `ne`, `contains`, `gt`, `gte`, `lt`, `lte`, `$or` (disjunction)
**Destination**: Replica ID (integer referencing `replicas` table)
**Evaluation**: Triggered per-instance at C-STORE/STOW-RS ingestion time; all matching rules applied (not first-match-only)

### HL7 MLLP Server Configuration

| Parameter | Default | Config Key |
|-----------|---------|------------|
| MLLP Port | `12579` | `hl7_mllp_port` |
| TLS Cert | (empty) | `hl7_mllp_tls_cert` |
| TLS Key | (empty) | `hl7_mllp_tls_key` |
| Allowed IPs | (empty = all) | `hl7_mllp_allowed_ips` |

### Auth Configuration

External RIS uses the same auth methods as EMR/EHR (API Key, JWT Bearer, OAuth). Recommended role for RIS service accounts: a custom role with `WORKLIST_READ`, `WORKLIST_WRITE`, `PATIENT_READ`, `PATIENT_WRITE`, `DICOMWEB_READ`, `DICOMWEB_WRITE`.

## End-to-End Flows

### Flow 1: RIS Sends an Order → PACS Creates MWL Entry

#### Option A: HL7 ORM^O01 via MLLP (Recommended)

```
1. RIS connects to TCP :12579
2. RIS sends MLLP-framed ORM^O01 message:

   MSH|^~\&|RIS|HOSPITAL|QUANTUMPACS|PACS|202607251430||ORM^O01|MSG001|P|2.5.1
   PID|||P001||Smith^John||19700101|M
   ORC|NW|ACC-20260725-001
   OBR|1|REQ-1001||CHEST PA AND LAT^CHEST 2 VIEWS|||202607251430|||||||CTSCAN||||||CT|||||||

3. QuantumPacs MLLP server:
   a. Reads until MLLP end block (\x1C\x0D)
   b. SHA-256 hash of raw message for non-repudiation
   c. Parses with hl7 library using the `hl7` Python library
   d. Extracts: PID (patient_id, name, dob, sex), ORC (accession_number), OBR (procedure_id, desc, modality, station_ae_title, scheduled_date/time)
   e. Upserts patient (INSERT ... ON CONFLICT)
   f. Checks if accession already exists (idempotent — returns if exists)
   g. Creates worklist_entries row with status='scheduled'
   h. Logs to hl7_messages table (raw hash + parsed JSONB)
   i. Sends ACK (\x0B\x0C...MSA|^|202607251430|MSG001|\x1C\x0D)

4. RIS receives ACK → order confirmed
```

#### Option B: REST API (Manual/Scheduled)

```
POST /api/worklist
X-Auth-Pacs: <jwt_token>
Content-Type: application/json

{
  "patient_id": "P001",
  "patient_name": "Smith^John",
  "patient_birth_date": "19700101",
  "patient_sex": "M",
  "accession_number": "ACC-20260725-001",
  "requested_procedure_id": "REQ-1001",
  "requested_procedure_desc": "CHEST PA AND LAT",
  "modality": "CT",
  "station_ae_title": "CT01",
  "scheduled_date": "2026-07-25",
  "scheduled_time": "14:30:00"
}

Response 201:
{ "data": { "id": "<uuid>" } }

Audit: worklist.entry_created logged
```

#### Option C: HTTP HL7 Relay (RIS Sends Raw HL7 via HTTP)

```
POST /api/hl7
Content-Type: application/x-hl7

<raw HL7 ORM^O01 message>

→ Same handler as MLLP; returns ACK or NACK
```

### Flow 2: RIS Checks MWL Status (Polling)

```
GET /api/worklist?accession_number=ACC-20260725-001
X-Auth-Pacs: <jwt_token>

Response 200:
{
  "data": [{
    "id": "<uuid>",
    "patient_id": "P001",
    "patient_name": "Smith^John",
    "accession_number": "ACC-20260725-001",
    "requested_procedure_desc": "CHEST PA AND LAT",
    "modality": "CT",
    "station_ae_title": "CT01",
    "status": "performed",
    "study_uid": "1.2.840.12345.1.234",
    "scheduled_date": "2026-07-25",
    "performed_at": "2026-07-25T14:35:22Z"
  }]
}

RIS polls periodically to detect when status changes from 'scheduled' to 'performed'
(status → 'performed' occurs when first C-STORE arrives with matching accession_number)
```

Alternative polling:
```
GET /api/worklist?status=performed&date_from=2026-07-25&date_to=2026-07-25
GET /api/worklist?status=scheduled&modality=CT
```

Alternative via DICOM C-FIND (from modality side):
```
  Modality sends C-FIND with ScheduledStationAETitle = "CT01"
  QuantumPACS returns matching worklist entries
  RIS can query results from modality's MWL if modalities share results with RIS
```

### Flow 3: RIS Receives Study Completion Notification

**Current State (v3.0): POLLING ONLY — No Push Notification**

```
RIS must poll periodically:
  1. GET /api/worklist?status=performed&date_from={today}
  2. For each performed entry:
     a. GET /api/v2/fhir/ImagingStudy?accession=ACC-20260725-001
        → Full ImagingStudy resource with series/instance metadata
     b. GET /api/v2/dicomweb/studies/{studyUID}/metadata
        → Full DICOM metadata for all instances
     c. GET /api/v2/fhir/DocumentReference?patient=Patient/P001
        → Any reports for this patient (v3.1 feature — not yet populated)

No webhook system exists yet (webhooks table defined in PRD-v3 but not implemented).
No outbound HL7 ORU^R01 results messaging implemented.
```

**Future (v3.1)**:
```
RIS subscribes to webhook endpoint:
  POST /api/webhooks/subscribe
  { url: "https://ris.example.com/hooks/pacs-event", event_types: ["study.completed"] }

When study completes:
  QuantumPACS POSTs to RIS webhook URL:
  { event: "study.completed", accession_number: "ACC-...", study_uid: "1.2....", patient_id: "P001" }
```

### Flow 4: RIS Receives Patient Demographics Update (ADT)

```
1. Hospital ADT system sends ADT^A01 over MLLP :12579

   MSH|^~\&|ADT_SOURCE|HOSPITAL|QUANTUMPACS|PACS|202607251430||ADT^A01|MSG001|P|2.5.1
   PID|||P001||Smith^John||19700101|M|123 Main St^^City^State^ZIP

2. QuantumPACS hl7_server.py:
   a. Matches PID-3 (PatientID) = P001
   b. Upserts patient: INSERT ... ON CONFLICT (patient_id) DO UPDATE
      → Updates name, DOB, sex, address
   c. Logs to hl7_messages table with parse_status='ok'
   d. Sends ACK

3. ADT^A03 (Discharge):
   → Sets meta.active = false on patient record
   → Audit: patient.deactivated

4. ADT^A06/A40 (Merge):
   → Surviving patient record kept, merged record marked meta.active=false
   → meta.merged_into = surviving_patient_id
   → Audit: patient.merged

5. ADT^A07 (Unmerge):
   → Reverses merge — reactivates merged record
```

### Flow 5: RIS Receives DICOM Study via Modality (Study Auto-Arrives)

```
This flow happens passively — RIS doesn't initiate it, but it benefits from it:

1. Modality performs CT scan → C-STORE images to QuantumPACS :11112
2. QuantumPACS stores images → auto-marks MWL as 'performed' → evaluates routing rules
3. RIS polls /api/worklist and sees status changed to 'performed'
4. RIS then reads study via FHIR: GET /api/v2/fhir/ImagingStudy?patient=Patient/P001
   or DICOMweb: GET /api/v2/dicomweb/studies/{uid}
5. Study now available in RIS for display alongside other patient data
```

### Flow 6: RIS Pushes Images via DICOMweb STOW-RS

```
1. RIS has images ready for a patient (e.g., from a peripheral modality or archive)
2. RIS constructs multipart/related request:

   POST /api/v2/dicomweb/studies
   Content-Type: multipart/related; boundary="----=_Part_1_123456"
   X-Auth-Pacs: <jwt_token>

   ------=_Part_1_123456
   Content-Type: application/dicom
   Content-ID: <1.2.840.12345.1.234>
   Content-Location: /studies/1.2.840.12345.1.234

   <binary DICOM data>
   ------=_Part_1_123456--

3. QuantumPACS validates modality against VALID_MODALITIES whitelist
4. Parses each DICOM instance, extracts metadata
5. Same store_instance() pipeline as C-STORE:
   → Upsert patient/study/series → SHA-256 dedup → store → auto-worklist-match → routing → respond
6. Response: JSON array of stored SOP Instance UIDs
7. 201 Created
```

### Flow 7: RIS Manages Worklist Entries Directly (No HL7/MWL C-FIND)

```
1. RIS creates a worklist entry for a patient scheduled for tomorrow:
   POST /api/worklist { patient_id, patient_name, accession_number, modality: "CT", station_ae_title: "CT01", ... }

2. RIS updates the scheduled time:
   PUT /api/worklist/{id} { scheduled_time: "09:15:00", ... }

3. RIS cancels an entry (no-show):
   DELETE /api/worklist/{id} → status → "cancelled"

4. RIS queries upcoming scans:
   GET /api/worklist?status=scheduled&date_from=2026-07-30&date_to=2026-07-30&modality=CT

5. All operations logged to hl7_messages and audit tables
```

### Flow 8: RIS Configures Study Routing Rules

```
1. RIS admin calls PACS admin API to create routing rules:

   POST /api/routing
   {
     "name": "Route CT Angio to Dedicated Storage",
     "conditions": {"modality": "CT", "study_description": {"contains": "ANGIO"}},
     "destination": "3",
     "priority": 0,
     "enabled": true
   }

2. From this point forward, all CT Angio studies are automatically copied to replica #3 (dedicated fast storage for CT Angio)

3. RIS can also configure rules to route studies to remote AE titles:
   {"conditions": {"modality": "MR"}, "destination": "RIS_REMOTE_AE"}
   (destination as AE title string — requires C-MOVE SCU to be complete, currently stub)
```

## Metrics & SLAs

| Metric | Target | How Measured |
|--------|--------|-------------|
| HL7 MLLP message processing | < 100ms (parse + DB write) | Server timing on hl7_server.py |
| MWL C-FIND response time | < 500ms | pynetdicom timing |
| Worklist entry creation (REST) | < 200ms API response | Backend timing |
| Routing rule evaluation | < 50ms per instance | In-memory JSONB evaluation |
| C-STORE ingestion latency | < 2s per instance (LAN) | Prometheus counter dicom_cstore_throughput_bytes |
| MWL status transition (scheduled → performed) | Immediate on first C-STORE receipt | Async post-commit hook in store.py |
| HL7 ACK response time | < 50ms after message receipt | MLLP server timing |
| Study available in FHIR after C-STORE | < 5s | End-to-end timing |
| Polling interval for completion detection | RIS-defined (recommended: 30-60s) | RIS-side logic |

## Acceptance Criteria

### From PRD-v3.md / PRD.md / UX-Functionality.md

1. RIS can create MWL entries via HL7 ORM^O01 MLLP messages on port 12579
2. RIS can create MWL entries via REST API (POST /api/worklist)
3. RIS can create MWL entries via HTTP HL7 relay (POST /api/hl7)
4. Modalities can C-FIND MWL on DICOM port 11112 and receive scheduled entries
5. MWL entries include PatientID, PatientName, AccessionNumber, Modality, StationAETitle, ScheduledDate/Time, Procedure Description
6. Auto-worklist-match transitions status from 'scheduled' to 'performed' on first DICOM C-STORE with matching accession number
7. Modality images are stored to master storage and replicated to configured replica destinations
8. Routing rules are evaluated on every C-STORE/STOW-RS ingestion
9. RIS can poll MWL status via REST API (filter by status, modality, date range, accession)
10. RIS can retrieve completed studies via FHIR R4 (ImagingStudy search/read)
11. RIS can retrieve studies via DICOMweb QIDO-RS / WADO-RS
12. HL7 ADT messages correctly manage patient demographics (upsert, deactivate, merge, unmerge)
13. All HL7 messages are hashed (SHA-256) and stored for non-repudiation
14. HTTP HL7 relay (POST /api/hl7) works as alternative to MLLP transport
15. Tenant isolation enforced for all RIS integration endpoints

### Derived from Code (Additional)

16. MWL C-FIND limit: 1000 results max per query
17. Worklist status CHECK constraint: 'scheduled', 'performed', 'cancelled' only
18. Routing rules evaluated in priority order (ascending integer); all matching rules applied, not first-match-only
19. Routing conditions support: `eq`, `ne`, `contains`, `gt`, `gte`, `lt`, `lte`, `$or`
20. MWL C-FIND query keys supported: PatientID, Modality, AccessionNumber, StationAETitle, ScheduledProcedureStepStartDate, Modality (in SPS)
21. MLLP protocol uses start block (\x0B) and end block (\x1C\x0D) per MLLP v2 spec
22. HL7 message schema stores raw message, parsed JSONB, parse status, and error messages for failed parses
23. Study auto-linking: when C-STORE arrives matching accession, worklist entry gets `study_uid` and `performed_at` timestamp
24. Storage path convention for C-STORE: `{patient_id}/{study_id}/{series_number}/{uuid}.dcm`
25. DICOMweb STOW-RS uses same store_instance() pipeline as native C-STORE — same routing and worklist matching apply

## Implementation Gaps

| Feature | Status | Impact | Target Version |
|---------|--------|--------|---------------|
| Outbound webhook for study completion | NOT IMPLEMENTED | RIS must poll instead of receiving push notifications; no real-time study completion event | v3.1 |
| Outbound HL7 ORU^R01 results messaging | NOT IMPLEMENTED | RIS cannot receive structured radiology reports via HL7 | v3.1 |
| MPPS (Modality Performed Procedure Step) SCP | NOT IMPLEMENTED | No real-time "scan in progress" status; worklist auto-marks performed on C-STORE only | v3.1 |
| DICOM C-MOVE SCU (RIS pushes retrieval requests) | NOT IMPLEMENTED | C-MOVE SCP registered but no-op; no C-MOVE SCU exists to send studies to remote RIS/PACS | v3.0+ |
| DICOM C-ECHO SCP (connectivity verification) | NOT IMPLEMENTED | Modalities cannot verify PACS connectivity | v3.1 |
| DICOM C-MOVE SCP actual implementation | STUB (returns 0x0000, no-op) | Modalities request C-MOVE but receive empty responses | v3.0 |
| Webhook subscription CRUD API | NOT IMPLEMENTED | No mechanism for RIS to register webhook endpoints | v3.1 |
| DICOM PR (Print) SCP | NOT IMPLEMENTED | No DICOM printing capability | Not planned |
| Non-repudiation: message receipt acknowledgment beyond ACK | PARTIAL | SHA-256 hash stored; no signed receipts | v3.x |
| MWL frontend filter for Station AE Title | MISSING | Backend supports it; frontend worklist UI doesn't expose station filter | v3.1 |
| Upload progress feedback for batch order entry | MISSING | No progress indication for bulk worklist entry creation | v2.1 |
| DICOMweb STOW-RS modality validation error detail | PARTIAL | VALID_MODALITIES whitelist rejects unknown modalities but doesn't provide detailed error mapping to modality type | v3.x |

## Key Files Reference

| File | Purpose |
|------|---------|
| `docs/PRD-v3.md` | v3 requirements for RIS integration (U-v3.1, U-v3.7, U-v3.8) |
| `docs/PRD.md` | v2 PRD with RIS integration sections |
| `docs/decisions/ADR-019-fhir-hl7-integration.md` | HL7 + FHIR integration architecture decision |
| `backend/api/worklist.py` | MWL CRUD REST API endpoints |
| `backend/api/routing.py` | Routing rule CRUD API |
| `backend/api/hl7.py` | HTTP HL7 receiver endpoint |
| `backend/dcm/server.py` | DICOM SCP with C-FIND MWL handler |
| `backend/dcm/store.py` | C-STORE handler with auto-MWL-match + routing evaluation |
| `backend/services/ingestion/hl7_server.py` | MLLP server, HL7 parser, ADT/ORM handlers |
| `backend/services/ingestion/routing.py` | Routing rule evaluation engine |
| `backend/db/worklist.py` | Worklist DB model + search + mark_performed |
| `backend/db/routing_rule.py` | Routing rule DB model |
| `backend/db/hl7_message.py` | HL7 message persistence model (with SHA-256 hash) |
| `backend/db/patient.py` | Patient upsert/merge/deactivate logic |
| `backend/api/permissions.py` | WORKLIST_READ, WORKLIST_WRITE, ROUTING_READ, ROUTING_WRITE permissions |
| `backend/api/schemas/worklist.py` | CreateWorklistRequest, UpdateWorklistRequest schemas |
| `backend/api/schemas/routing.py` | RoutingRuleRequest schema |
| `backend/api/routes.py` | Full route registration (HL7, worklist, routing, dicomweb) |
| `backend/lifecycle.py` | DICOM server + MLLP server startup |
| `backend/config.py` | Default config (ports, AE title, MLLP settings) |
| `backend/services/ingestion/worker.py` | Ingestion worker (Redis Streams consumer) |
| `backend/services/ingestion/handler.py` | Event handlers (store, reindex, delete) |