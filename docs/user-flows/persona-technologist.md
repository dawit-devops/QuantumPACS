# Persona: Medical Radiation Technologist (MRT)

## Persona Card

| Attribute | Detail |
|-----------|--------|
| **Role** | Medical radiation technologist operating imaging modalities (CT, MRI, X-ray, US), scheduling patients, acquiring images, and ensuring studies are complete |
| **Description** | Operates the imaging hardware, manages the modality workflow from order intake through image acquisition to verification and routing. Responsible for confirming studies arrive correctly and routing them to the right destinations |
| **Technical Level** | Medium — comfortable with PACS UI, understands DICOM concepts (AE Titles, modalities, worklists) |
| **Frequency** | Daily shift work, 8–12 hours, continuous patient throughput |
| **Devices** | Control station at modality gantry, control console workstation |
| **Critical Needs** | Fast worklist access, reliable image receipt confirmation, routing configuration, patient demographic management |
| **Frustrations** | No MPPS real-time status, no QA workflow, no batch operations, no exam card templates |
| **Default Role** | `technologist` |

## Routes & Permissions

### Sidebar Navigation (visible to Technologist)

| Menu Item | Path | Permission |
|-----------|------|------------|
| Study List | `/` | `FILE_READ` |
| Worklist | `/worklist` | `WORKLIST_READ` |
| Metrics | `/metrics` | `METRICS_READ` |
| Account | `/account` | Authenticated |
| Admin submenu (conditional) | — | `WORKLIST_READ`, `ROUTING_READ`, or `SERVICE_KEY_READ` |

### Admin Submenu Items (if technologist has those permissions)

| Menu Item | Path | Permission |
|-----------|------|------------|
| Routing Rules | `/routing` | `ROUTING_READ` |
| Service Keys | `/service-keys` | `SERVICE_KEY_READ` |

### API Routes (all require JWT via `X-Auth-Pacs` or `Authorization: Bearer`)

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| GET | `/api/files` | `FILE_READ` | Search/query studies |
| GET | `/api/files/{id}` | `FILE_READ` | Get file metadata + study/series tree |
| GET | `/api/files/{id}/data` | `FILE_READ` | Download DICOM file |
| GET | `/api/files/{id}/thumbnail` | `FILE_READ` | JPEG thumbnail |
| POST | `/api/files/{id}` | `FILE_WRITE` (v3) | Save annotation state / edit metadata |
| POST | `/api/files/{id}/share` | `FILE_WRITE` (v3) | Generate share link |
| POST | `/api/worklist` | `WORKLIST_WRITE` | Create MWL entry |
| GET | `/api/worklist` | `WORKLIST_READ` | List/search MWL entries |
| GET | `/api/worklist/{id}` | `WORKLIST_READ` | Get single MWL entry |
| PUT | `/api/worklist/{id}` | `WORKLIST_WRITE` | Update MWL entry |
| DELETE | `/api/worklist/{id}` | `WORKLIST_WRITE` | Cancel MWL entry |
| GET | `/api/routing` | `ROUTING_READ` | List routing rules |
| POST | `/api/routing` | `ROUTING_WRITE` | Create routing rule |
| PUT | `/api/routing/{id}` | `ROUTING_WRITE` | Update routing rule |
| DELETE | `/api/routing/{id}` | `ROUTING_WRITE` | Delete routing rule |
| POST | `/api/hl7` | `WORKLIST_WRITE` | HTTP HL7 message receiver |
| GET | `/api/health` | None | Health check |
| GET | `/api/v2/dicomweb/studies` | `DICOMWEB_READ` | QIDO-RS study search |
| POST | `/api/v2/dicomweb/studies` | `DICOMWEB_WRITE` | STOW-RS DICOM upload |
| GET | `/api/metrics` | `METRICS_READ` | System metrics |

### Permission Slugs for Technologist Role

```
FILE_READ, FILE_WRITE, FILE_DELETE, PATIENT_READ, PATIENT_WRITE,
STUDY_READ, STUDY_WRITE, WORKLIST_READ, WORKLIST_WRITE, DICOMWEB_READ
```

Not granted: `USER_*`, `REPLICA_*`, `LOG_READ`, `ROLE_*`, `TENANT_*`, `ROUTING_*` (unless configured), `METRICS_READ` (unless configured), `SERVICE_KEY_*`.

## End-to-End Flows

### Flow 1: Patient Scheduled — Worklist Entry Created

```
Option A: HL7 ORM^O01 via MLLP (Primary)
  1. RIS/HIS sends ORM^O01 over MLLP to :12579
  2. hl7_server.py parses PID, ORC, OBR segments
  3. UP SERT patient demographics
  4. Creates worklist_entries row with status='scheduled'
     Fields: patient_id, patient_name, accession_number, modality,
     station_ae_title, requested_procedure_id/desc, scheduled_date/time
  5. Returns ACK to RIS

Option B: REST API (Manual)
  1. Technologist opens /worklist
  2. Clicks "Create Entry"
  3. Fills form: Patient ID (required), Patient Name, Birth Date, Sex,
     Accession #, Procedure Description, Modality, Scheduled Date/Time, Station AE Title
  4. POST /api/worklist { ... }
  5. Entry created with status='scheduled'
  6. Audit logged: worklist.entry_created
```

### Flow 2: Modality Queries Worklist (DICOM C-FIND MWL)

```
1. CT/MRI/X-ray modality opens DICOM association to QUANTUMPACS:11112
   with ModalityWorklistInformationFind presentation context
2. Sends C-FIND-RQ with query keys:
   - ScheduledProcedureStepSequence[0].ScheduledStationAETitle = "CT01"
   - Modality = "CT"
   - ScheduledProcedureStepStartDate = "20260729"
3. QuantumPACS queries worklist_entries WHERE status='scheduled'
   AND matches query keys (ILIKE on patient_name/patient_id/accession,
   exact on modality/station_ae_title)
4. Returns up to 1000 matching entries as DICOM MWL datasets
   (PatientName, PatientID, AccessionNumber, StudyInstanceUID,
    RequestedProcedureDescription, ScheduledProcedureStepSequence
    with Modality, StationAETitle, StartDate/Time, PerformingPhysician)
5. Modality auto-populates exam parameters from returned MWL data
6. No manual data entry needed on scanner for scheduled exams
```

### Flow 3: Modality Performs Scan and Sends Images (C-STORE)

```
1. Modality acquires images during scan
2. Each DICOM instance sent via C-STORE to :11112
3. handle_store() in dcm/server.py:
   a. Extracts DICOM metadata (PatientID, StudyID, SeriesNumber, etc.)
   b. Computes SHA-256 hash
   c. Checks for duplicate hash → skips if exists (dedup)
   d. Upserts patient → study → series hierarchy in DB
   e. Writes file to master storage backend
   f. Adds replica_files record for all configured replicas
4. POST-COMMIT:
   a. match_worklist_performed():
      → If accession matches scheduled MWL entry,
        status→'performed', study_uid recorded, performed_at set
   b. evaluate_routing_rules():
      → Loads all enabled routing rules by priority
      → Tests conditions against DICOM metadata
      → Copies file to matched destination replicas
5. Returns 0x0000 (Success) to modality
```

### Flow 4: Verify Study Arrival

```
1. Technologist navigates to Files page (/)
2. Searches by Patient ID, Accession Number, or Study ID
   (global search via Elasticsearch or column filter dropdowns)
3. Verifies study appears in results table
4. Click row → navigate to /files/{id}
5. Checks Data tab for DICOM metadata integrity
6. Checks Changes tab for ingestion audit trail
7. Cross-references Worklist page (/worklist):
   → Entry should show status='performed' (was 'scheduled')
   → study_uid now populated
8. No explicit "Verify" or "Complete" action exists —
   verification is manual via search + worklist cross-check
```

### Flow 5: Configure Auto-Routing Rules

```
1. Navigate to Routing Rules page (/routing) (requires ROUTING_READ)
2. Click "Create Rule"
3. Configure:
   - Name: e.g., "Route CT Chest to Fast Storage"
   - Conditions: {"modality": "CT", "study_description": {"contains": "CHEST"}}
   - Destination: replica_2 ID
   - Priority: 0 (evaluated first)
   - Enabled: ON
4. POST /api/routing { name, conditions, destination, priority, enabled }
5. Rule stored in routing_rules table (JSONB conditions)
6. Rule takes effect immediately for all subsequent C-STORE/STOW-RS ingestions
7. Matching studies are copied to destination replica automatically
```

### Flow 6: Upload via DICOMweb (STOW-RS) — For Modality/RIS Push

```
1. External system (RIS, modality gateway) prepares multipart/related HTTP request
2. POST /api/v2/dicomweb/studies
   Content-Type: multipart/related; type=application/dicom
   Body: DICOM PS3.18 STOW-RS format
   Each part: application/dicom with SOP Instance UID in content-location
   X-Auth-Pacs: <jwt_token> (requires DICOMWEB_WRITE)
3. Server validates modality against VALID_MODALITIES whitelist
4. Parses each DICOM part, extracts metadata
5. Calls store_instance() — identical pipeline to C-STORE
6. Returns JSON array of stored SOP Instance UIDs
7. Auto-matches worklist + evaluates routing rules (same as C-STORE)
```

### Flow 7: Upload via Browser (Technologist Workstation)

```
1. Technologist opens Files page (/)
2. Clicks "Upload" button (AdminFiles component)
3. Selects DICOM files from local filesystem
4. Files are sent as multipart form to /api/files/upload
5. Backend parses DICOM via parse_dcm(file), computes SHA-256 hash
6. Identical pipeline to C-STORE: upsert → store → dedup → route
7. Uploaded studies appear in Files list immediately (refresh or new search)
```

### Flow 8: Manage Worklist Entries

```
1. Navigate to /worklist
2. Search/filter by status (scheduled/performed/cancelled), modality, date range
3. View table: Patient Name, Patient ID, Accession #, Modality, Scheduled Date, Status, Actions
4. Edit entry: Click pencil icon → modify fields → PUT /api/worklist/{id}
5. Cancel entry: Click X on scheduled entry → confirmed via Popconfirm
   → DELETE /api/worklist/{id} → status → 'cancelled'
6. Audit logs: worklist.entry_created/updated/cancelled
```

### Flow 9: Handle HL7 ADT Messages (Patient Demographics)

```
1. RIS/HIS sends ADT message over MLLP (:12579)
2. Parsing: extract PID segment fields
3. Event mapping:
   A01/A04/A05/A08 → upsert patient (INSERT ... ON CONFLICT DO UPDATE)
   A03 → deactivate patient (meta.active = false)
   A06/A40 → merge patients (surviving record kept, merged marked inactive)
   A07 → unmerge patients (reactivate merged record)
4. Patient demographics updated in patients table
5. Audit logged for all ADT events
```

### Flow 10: Check Ingestion Metrics

```
1. Navigate to /metrics (requires METRICS_READ)
2. Dashboard shows:
   - Row 1: Patient count, Study count, Series count, File count, User count, Storage used
   - Row 2: Modality distribution bar chart, Component latency chart
   - Row 3: Ingestion 30-day trend line chart, Latest files table
3. System Health panel shows per-component status:
   database: ok, elasticsearch: degraded (if down), redis, storage, dicom_listener, ingestion_service
4. Prometheus metrics at /api/v2/metrics for external monitoring
```

## Metrics & SLAs

| Metric | Target | How Measured |
|--------|--------|-------------|
| MWL C-FIND response time | < 500ms | pynetdicom timing |
| C-STORE throughput | < 2s per instance (LAN) | Prometheus counter |
| Worklist creation | < 200ms API response | Backend timing |
| Routing rule evaluation | < 50ms per instance | In-memory evaluation |
| HL7 MLLP message processing | < 100ms (parse + DB) | Server timing |
| Modality worklist entries visible | Within 1s of scheduling | DB write + C-FIND |
| Worklist status transition (scheduled → performed) | Immediate on first C-STORE receipt | Async post-commit hook |
| Dedup hit rate | Varies by modality/repeat exam | Hash lookup statistics |

## Acceptance Criteria

### From PRD / UX-Functionality.md / User-Stories.md

1. Technologist can log in and access the Worklist page
2. Worklist entries can be created manually with all required fields
3. Worklist entries can be cancelled (status → cancelled)
4. MWL C-FIND returns scheduled entries matching modality, station AE, and date filters
5. C-STORE correctly receives images and stores them in master storage
6. SHA-256 dedup prevents duplicate storage of identical DICOM files
7. Auto-worklist-match transitions status from 'scheduled' to 'performed' on C-STORE receipt
8. HL7 ORM^O01 creates worklist entries with correct field mapping from PID/ORC/OBR segments
9. HL7 ADT messages correctly upsert/deactivate/merge patients
10. Routing rules are configurable via REST API and evaluated on every ingestion
11. STOW-RS upload follows identical pipeline to native C-STORE
12. DICOMweb QIDO-RS search returns matching studies
13. Metrics dashboard shows ingestion volume, storage, modality distribution, and system health
14. Audit trail logs all MWL CRUD operations and file ingestion events

### Derived from Code

15. Worklist status is CHECK-constrained to 'scheduled', 'performed', or 'cancelled' only
16. MWL C-FIND supports query keys: PatientID, Modality, AccessionNumber, ScheduledProcedureStepSequence fields
17. Routing conditions support operators: eq, ne, contains, gt, gte, lt, lte, $or
18. C-STORE returns 0x0000 on success, 0x0001 on failure
19. Storage path convention: `{patient_id}/{study_id}/{series_number}/{uuid}.dcm`
20. HL7 messages are SHA-256 hashed and stored in hl7_messages table for non-repudiation
21. Tenant isolation: all operations scoped to tenant via X-Tenant-ID header or JWT tenant claim

## Implementation Gaps

| Feature | Status | Impact | Target Version |
|---------|--------|--------|---------------|
| MPPS (Modality Performed Procedure Step) — N-CREATE/N-SET SCP | NOT IMPLEMENTED | Modalities cannot report scan start/in-progress/complete; worklist auto-marks performed on C-STORE only | v3.1 |
| Study completeness verification | NOT IMPLEMENTED | No expected vs actual series/instance count check | v3.1 |
| QA / Rejection workflow | NOT IMPLEMENTED | No image quality rejection, no retake notification | v3.1 |
| Batch operations on worklist entries | PARTIAL | Cancel single entry only; no bulk cancel or bulk status update | v3.1 |
| Exam card / protocol templates | NOT IMPLEMENTED | No pre-configured modality/body part/protocol combinations | v3.1 |
| Upload progress feedback | NOT IMPLEMENTED | No progress bar for file uploads (v2.1 target) | v2.1 |
| DICOM export (CD burning / DICOMDIR) | NOT IMPLEMENTED | No media creation standard | Not planned |
| C-MOVE SCU (send studies to remote PACS) | NOT IMPLEMENTED | C-MOVE SCP registered but no-op; no SCU exists | v3.0+ |
| C-ECHO SCP (modality connectivity verification) | NOT IMPLEMENTED | Modalities cannot verify PACS connectivity via C-ECHO | v3.1 |
| Station AE Title filter in MWL frontend | PARTIAL | Backend supports it; frontend worklist UI lacks a station filter | v3.1 |
| In-progress study tracking (no MPPS) | MISSING | No "scan in progress" state — jumps from scheduled directly to performed | v3.1 |
| Duplicate patient detection | NOT IMPLEMENTED | MLLP ADT merge/unmerge works but no proactive dedup on manual entry | v3.1 |
| Study-level status enum | NOT IMPLEMENTED | No study status beyond what DICOM tags provide | v3.x |

## Key Files Reference

| File | Purpose |
|------|---------|
| `docs/UX-Functionality.md` | Persona definition, interaction flows |
| `docs/User-Stories.md` | Technologist epic stories |
| `frontend/src/worklist/Worklist.tsx` | MWL management UI |
| `frontend/src/files/Files.tsx` | Study list/search with filters |
| `frontend/src/routing/RoutingRules.tsx` | Routing rules UI |
| `frontend/src/common/Sidebar.tsx` | Sidebar navigation (tech sees Files + Worklist + Admin) |
| `backend/api/worklist.py` | MWL CRUD API endpoints |
| `backend/api/routing.py` | Routing rule CRUD API |
| `backend/api/dicomweb.py` | DICOMweb STOW-RS / QIDO-RS / WADO-RS |
| `backend/api/hl7.py` | HTTP HL7 message receiver |
| `backend/dcm/server.py` | DICOM SCP (C-STORE, C-FIND MWL handlers) |
| `backend/dcm/store.py` | C-STORE pipeline: dedup → upsert → route → match worklist |
| `backend/services/ingestion/hl7_server.py` | MLLP server, HL7 parser, ADT/ORM handlers |
| `backend/services/ingestion/routing.py` | Routing rule evaluation engine |
| `backend/db/worklist.py` | Worklist DB model + search + mark_performed |
| `backend/db/routing_rule.py` | Routing rule DB model |
| `backend/db/hl7_message.py` | HL7 message persistence model |
| `backend/api/permissions.py` | Technologist permission set |
| `backend/config.py` | Default config (DICOM ports, MLLP port, HL7 settings) |
| `backend/lifecycle.py` | DICOM server + MLLP server startup |