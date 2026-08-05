# Backend Requirements: DICOMweb API

## Context

DICOMweb (PS3.18) endpoints serve multiple personas — the Cornerstone3D viewer, the Study List page (QIDO-RS fallback when Elasticsearch is unavailable), and EMR/RIS systems for integration. Currently implemented at `/dicomweb/studies` (resolved via `API_URL + /dicomweb/...`). The full public path is `/api/v2/dicomweb/studies/...`.

**Current frontend implementation**:
- WADO-RS URI construction in `frontend/src/dicomweb/dicomweb.ts:101` — `wadors:${API_URL}/dicomweb/studies/{study}/series/{series}/instances/{instance}`
- QIDO-RS fallback search: `request('v2/dicomweb/studies', { query: params })` in `frontend/src/files/Files.tsx:135`
- Frontend constructs study/series/instance UIDs from file metadata to build WADO-RS URL
- `searchStudies()`, `getSeries()`, `getInstances()` in `dicomweb.ts` use the `request()` helper (JWT via `X-Auth-Pacs` header)
- Current `request()` helper only handles JSON responses — WADO-RS multipart response must bypass this

---

## 1. QIDO-RS Search

### Purpose
Search for studies, series, or instances by DICOM tags. Used as the fallback search when Elasticsearch is unavailable on the Study List page. Used by external EMR/RIS for integration.

### Endpoints

| Level | Path | Purpose |
|-------|------|---------|
| Studies | `GET /dicomweb/studies` | Search studies by patient ID, accession number, study UID |
| Series | `GET /dicomweb/studies/{study_uid}/series` | List series within a study |
| Instances | `GET /dicomweb/studies/{study_uid}/series/{series_uid}/instances` | List instances within a series |

### Supported Search Parameters

Currently implemented in `backend/api/dicomweb.py:61-80`:
- `PatientID` — exact match on `patients.patient_id`
- `AccessionNumber` — exact match on `studies.accession_number`
- `StudyInstanceUID` — exact match on `studies.study_instance_uid`

**Not currently supported** (but frontend may need):
- `PatientName` — fuzzy/partial match (falls back to full-text ES search)
- `Modality` — filter by modality
- `StudyDate` — date range filter
- `StudyDescription` — partial match
- `ReferringPhysicianName`, `PerformingPhysicianName`
- `SOPClassUID`
- Series-level and instance-level search parameters beyond UID

### Response Format

Returns `application/dicom+json` — DICOM JSON Model (PS3.18 §6.3.3).

**Study-level response** (`row_to_study_json` in `dcm/dicom_json.py`):
```json
{
  "0020000D": { "vr": "UI", "Value": ["1.2.3.4.5.6.7.8"] },
  "00100020": { "vr": "LO", "Value": ["P001"] },
  "00100010": { "vr": "PN", "Value": [{"Alphabetic": "Smith^John"}] },
  "00100030": { "vr": "DA", "Value": ["19800101"] },
  "00100040": { "vr": "CS", "Value": ["M"] },
  "00080050": { "vr": "SH", "Value": ["ACC001"] },
  "00081030": { "vr": "LO", "Value": ["CHEST PA"] }
}
```

**Series-level response** (`row_to_series_json`):
```json
{
  "00200011": { "vr": "IS", "Value": ["1"] },
  "00080060": { "vr": "CS", "Value": ["CT"] },
  "0008103E": { "vr": "LO", "Value": ["CHEST"] },
  "0020000E": { "vr": "UI", "Value": ["1.2.3.4.5.6.7.9"] }
}
```

**Instance-level response** (`row_to_instance_json`):
```json
{
  "00080018": { "vr": "UI", "Value": ["1.2.3.4.5.6.7.10"] },
  "00200013": { "vr": "IS", "Value": ["1"] },
  "00080016": { "vr": "UI", "Value": ["1.2.840.10008.5.1.4.1.1.2"] }
}
```

### Pagination
- `limit` (default 100) and `offset` (default 0) query parameters
- `X-Total-Count` header in study-level responses for `"X-Y of Z"` display
- Series and instance level return all results (no pagination)

### Auth
- Requires `DICOMWEB_READ` permission (`@requires_permission(Permission.DICOMWEB_READ)`)
- JWT via `X-Auth-Pacs` header

### Error Responses

| Status | Meaning | UI Handling |
|--------|---------|-------------|
| 401 | Unauthenticated (missing/invalid JWT) | Redirect to login |
| 403 | No `DICOMWEB_READ` permission | Show "access denied" message, disable QIDO-RS fallback |
| 500 | Server/database error | Retry with ES, then fall back gracefully |
| Empty array | No results matching criteria | Show "No files match your search" |

---

## 2. WADO-RS Image Retrieval

### Purpose
Retrieve DICOM instances (or entire studies/series) for rendering in Cornerstone3D. The primary image loading path for the viewer.

### Endpoints

| Level | Path | Response Type |
|-------|------|---------------|
| Instance | `GET /dicomweb/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}` | `application/dicom` (single) |
| Series | `GET /dicomweb/studies/{study_uid}/series/{series_uid}` | `multipart/related; type=application/dicom` |
| Study | `GET /dicomweb/studies/{study_uid}` | `multipart/related; type=application/dicom` |
| Instance metadata | `GET /dicomweb/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}/metadata` | `application/dicom+json` |
| Series metadata | `GET /dicomweb/studies/{study_uid}/series/{series_uid}/metadata` | `application/dicom+json` |
| Study metadata | `GET /dicomweb/studies/{study_uid}/metadata` | `application/dicom+json` |
| Frames | `GET /dicomweb/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}/frames/{frame_numbers}` | `application/octet-stream` or `multipart/related` |

### Current Implementation

**Single instance retrieval** (`_wado_retrieve_instance` in `api/dicomweb.py:233`):
- Looks up `replica_files` by `sop_instance_uid`
- Fetches file from storage backend via `Storage.get(master).fetch()`
- Returns raw DICOM bytes as `application/dicom`

**Series/study retrieval** (`_wado_retrieve_series`/`_wado_retrieve_study`):
- Fetches all files in the series/study from storage
- Builds multipart response with `WADO_BOUNDARY`
- Each part: `Content-Type: application/dicom\r\n\r\n` + raw DICOM bytes
- Response: `multipart/related; type=application/dicom; boundary=WADO_BOUNDARY`

### Transfer Syntax Support
- **Current**: Returns stored DICOM bytes as-is (whatever transfer syntax was stored)
- **No negotiation**: The `Accept` header or `transferSyntax` query parameter is not checked
- **No transcoding**: No on-the-fly conversion between transfer syntaxes
- **No progressive/lossy loading**: Returns full-quality DICOM every time

### Frontend Image Loading

The frontend constructs WADO-RS URIs using the `wadors:` URI scheme for Cornerstone3D:

```typescript
// frontend/src/dicomweb/dicomweb.ts:101
export function wadoRsUrl(studyUid: string, seriesUid: string, instanceUid: string): string {
  return `wadors:${API_URL}/dicomweb/studies/${studyUid}/series/${seriesUid}/instances/${instanceUid}`;
}
```

Cornerstone3D's `cornerstone-wado-image-loader` handles the `wadors:` URI scheme. It:
1. Parses the URI to extract study/series/instance UIDs
2. Makes a WADO-RS request for the instance
3. Parses the DICOM response to extract pixel data
4. Renders in the viewport

The current `request()` helper in `dicomweb.ts` (line 4-11) only handles JSON — WADO-RS multipart responses are handled entirely by the Cornerstone3D image loader, not by custom frontend code.

### Auth
- Requires `DICOMWEB_READ` permission
- JWT via `X-Auth-Pacs` header

### Error Responses

| Status | Meaning | UI Handling |
|--------|---------|-------------|
| 404 | Instance/series/study not found | Viewport shows "Image not found" overlay |
| 503 | No storage available (replica offline) | Retry with backoff; show "Storage unavailable" |
| 401/403 | Same as QIDO-RS | Redirect or access denied |
| 500 | Storage read error | Show error overlay with retry button |

---

## 3. STOW-RS Upload

### Purpose
Accept DICOM instances via HTTP POST (multipart/related). Uses the same storage pipeline as C-STORE (extract metadata, SHA-256 dedup, patient/study/series upsert, auto-routing evaluation).

### Endpoint
`POST /dicomweb/studies`

### Implementation

In `DicomWebStudies.post()` (`api/dicomweb.py:145-175`):

1. Reads raw request body
2. Parses `multipart/related; type=application/dicom` using `_parse_multipart_related()`
3. For each DICOM part:
   - Parses with `pydicom.dcmread()`
   - Validates modality against `VALID_MODALITIES` set (22+ modalities)
   - Calls `store_instance(ds, buf)` — same pipeline as C-STORE
4. Returns list of stored `SOPInstanceUIDs` as `application/dicom+json`

### Storage Pipeline (same as C-STORE)
1. `dcm/file.py::parse_dcm` — extract DICOM metadata
2. SHA-256 hash computation for dedup
3. Write file to storage backend (local/S3/B2)
4. Upsert patient, study, series records
5. Insert file record with DICOMweb self-reference URL
6. Publish `study.stored` event to Redis Streams `events:ingestion`

### Modality Validation

```python
VALID_MODALITIES = frozenset({
    'CR', 'CT', 'MR', 'US', 'OT', 'BI', 'CD', 'DD', 'DG', 'ES', 'LS',
    'PT', 'RG', 'ST', 'TG', 'XA', 'XC', 'AS', 'DS', 'CF', 'DF', 'DM',
    'EC', 'FA', 'CS', 'LP', 'MA', 'MS', 'NM', 'DX', 'GM', 'HD',
    'IO', 'IX', 'PX', 'RF', 'SM', 'SR', 'VA', 'MG', 'EPS', 'OP',
    'OAM', 'OCT', 'OPT', 'OPV', 'OSS', 'POS', 'IVOCT', 'LEN',
})
```

Unrecognized modalities return 400 with `{'error': 'Invalid modality: {modality}'}`.

### Differences from File Upload (`POST /api/files/upload`)

| Aspect | File Upload (`/api/files/upload`) | STOW-RS (`POST /dicomweb/studies`) |
|--------|----------------------------------|-------------------------------------|
| Request format | `multipart/form-data` (single file) | `multipart/related; type=application/dicom` (multiple parts) |
| Response | `204 No Content` | `200 OK` with list of stored SOPInstanceUIDs |
| Parsing | `parse_dcm(file)` then hash | `pydicom.dcmread()` then `store_instance()` |
| Validation | None beyond dcmread | Modality validation |
| Auth | `FILE_WRITE` permission | `DICOMWEB_WRITE` permission |
| Frontend usage | UploadZone.tsx (drag-and-drop XHR) | Machine-to-machine (EMR/RIS) |
| Multi-file | Per-file XHR only | Multiple DICOM instances in one request body |

### Auth
- Requires `DICOMWEB_WRITE` permission (`@requires_permission(Permission.DICOMWEB_WRITE)`)
- JWT via `X-Auth-Pacs` header

### Error Responses

| Status | Meaning | UI Handling |
|--------|---------|-------------|
| 400 | Malformed DICOM or invalid modality | Show error per file |
| 401/403 | Auth failure | Redirect or access denied |
| 500 | Storage/store pipeline failure | Show generic upload error |
| Duplicate (SHA-256 match) | File already stored | Currently returns success (same as C-STORE) — no distinction |

---

## 4. Authentication Requirements

| Endpoint | Permission | Token Header |
|----------|------------|-------------|
| QIDO-RS GET (all levels) | `DICOMWEB_READ` | `X-Auth-Pacs` |
| WADO-RS GET (all levels + metadata + frames) | `DICOMWEB_READ` | `X-Auth-Pacs` |
| STOW-RS POST | `DICOMWEB_WRITE` | `X-Auth-Pacs` |
| WADO-URI | `DICOMWEB_READ` | `X-Auth-Pacs` |

All endpoints use `requires_permission` decorator from `api/rbac.py`. JWT tokens are decoded by `api/tokens.py:verify_token()`.

---

## 5. Uncertainties & Questions

### WADO-RS
- Does WADO-RS support multipart response with multiple instances in one request? **Yes** — series/study level returns `multipart/related`.
- What transfer syntaxes does WADO-RS support for uncompressed and compressed DICOM? **Currently stored-as-is; no negotiation or transcoding**.
- Is there a way to request specific frame from a multi-frame DICOM via WADO-RS? **Not implemented** — the frames endpoint path exists per ADR-018 but is not wired in code.
- Should WADO-RS be the primary or fallback for image loading? **Currently primary** via `wadors:` URI scheme in Cornerstone3D.
- Does Cornerstone3D's `cornerstone-wado-image-loader` support progressive/lossy loading via `accept` header? **Unknown** — needs investigation.
- Is there a way to request a specific transfer syntax via the `transferSyntax` query parameter? **ADR-018 mentions negotiation but not implemented**.
- What happens when Cornerstone3D requests an instance with a `wadors:` URI but the backend returns a different transfer syntax? **Currently returns stored bytes regardless**.

### QIDO-RS
- Does QIDO-RS support all DICOM tags as search parameters or only those in the default response set? **Only PatientID, AccessionNumber, StudyInstanceUID currently**.
- Should the frontend attempt QIDO-RS or ES first? **ES first, QIDO-RS as fallback** (current behavior).
- What is the max result count for QIDO-RS queries? **Default limit=100, configurable via `limit` param**.
- Are fuzzy/partial matches supported for PatientName? **No — exact match only via current SQL**.
- Should series/instance-level QIDO-RS support filters beyond UID? **Not currently needed by frontend but expected for EMR/RIS integration**.

### STOW-RS
- Is STOW-RS meant for browser-based upload or only machine-to-machine? **Machine-to-machine** — browser uploads use `/api/files/upload` with per-file `multipart/form-data`.
- Should the UploadZone frontend use STOW-RS instead of the custom upload endpoint? **No** — per-file XHR with progress tracking is better UX.
- Does STOW-RS trigger auto-routing evaluation? **Yes** — same `study.stored` event as C-STORE.

### General
- What's the DICOMweb base URL path? **`/api/v2/dicomweb/`** — currently constructed as `/dicomweb/...` from `API_URL + path`.
- Are there rate limits for DICOMweb endpoints? **Not implemented**.
- Should metadata endpoints return `application/dicom+json` for all levels? **Per ADR-018 yes, but metadata endpoints not wired in `routes.py`**.
- Are there CORS considerations for external EMR/RIS calling DICOMweb directly? **CORS allows all origins currently** — tighten before production.

---

## 6. Questions for Backend

1. **Transfer syntax negotiation**: Should WADO-RS accept a `transferSyntax` query parameter or `Accept` header to request a specific transfer syntax (e.g., JPEG 2000 lossless vs. uncompressed)?

2. **Progressive loading**: The Cornerstone3D image loader supports progressive loading (low-res first, then full quality). Can the backend serve a lossy-encoded preview (e.g., JPEG) for initial render, then full DICOM for diagnosis?

3. **Frame-level retrieval**: Multi-frame DICOM (e.g., ultrasound, MRI) needs per-frame access. Is the frames endpoint at `/instances/{uid}/frames/{frames}` going to be implemented? What format will frames return — `application/octet-stream` raw pixel data or rendered `image/png`?

4. **QIDO-RS expanded parameters**: For the Study List page, we need search by PatientName (fuzzy), Modality, StudyDate (range), and StudyDescription. Will QIDO-RS support these, or should they stay in ES-only?

5. **Metadata endpoint wiring**: The ADR-018 describes `/metadata` endpoints but `routes.py` doesn't route them. Are they coming? The frontend needs them for the Data tab (DICOM tag browser).

6. **STOW-RS and the file upload endpoint**: Should the frontend upload endpoint (`/api/files/upload`) be deprecated in favor of STOW-RS, or should they coexist? The STOW-RS path doesn't support per-file progress tracking.

7. **Duplicate detection for STOW-RS**: When STOW-RS receives a duplicate (SHA-256 match), it returns 200 success (same as new store). Should it return a different status (e.g., 200 but indicate "already exists") so the caller can distinguish?

8. **DICOMweb behind API gateway**: Is the DICOMweb base path `/api/v2/dicomweb/` or just `/dicomweb/`? The frontend uses `API_URL + /dicomweb/...` but the v2 alias is `/api/v2/dicomweb/...`.

9. **Bulk data URI support**: Does the backend support DICOMweb bulk data URIs (PS3.18 §6.5) for large pixel data? This could enable streaming of large DICOM objects.

10. **QIDO-RS response field consistency**: The frontend's `mapStudy()` maps both DICOM JSON model format (`0020000D.Value[0]`) and flat column format (`study_instance_uid`). Will the backend always return DICOM JSON model format, or does it sometimes return flat format?
