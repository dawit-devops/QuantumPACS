# Backend Requirements — DICOM File Upload

## Current Implementation

### Endpoint
`POST /api/files/upload` — single-file multipart upload. Returns `204 No Content` on success, no response body.

### Auth
`X-Auth-Pacs` header (JWT). Requires `FILE_WRITE` permission (`@requires_permission(Permission.FILE_WRITE)`).

### Upload Pipeline
```
request.form() → form['file'] (UploadFile)
  → parse_dcm(file)       # pydicom.dcmread(stop_before_pixels=True), extracts patient/study/series metadata
  → hash_file(file)        # SHA-256 of full file content
  → Files(conn).insert_or_select(file_data)  # upserts patient/study/series hierarchy, returns file record
  → Storage.get(master)    # resolves storage backend for master replica
  → storage.copy(file, filedata)  # copies file bytes to storage
  → ReplicaFiles(conn).add(master_id, [{id, path, size}])  # records file on replica
```

### Current Frontend Behavior (UploadZone.tsx + UploadProgress.tsx)
- Drag-and-drop zone or `<input type="file" multiple accept=".dcm,application/dicom">`
- Per-file XHR with `upload.progress` event → percentage (`e.loaded / e.total * 100`)
- `AbortController` per file → `xhr.abort()` on cancel
- Per-file status badge: pending → uploading → done | error | cancelled
- Cancel All aborts all pending/uploading controllers
- Retry creates a new `AbortController` and re-issues the XHR
- Done files auto-remove after 3s, cancelled after 2s
- Does **not** validate DICOM before sending (browser `accept` attribute only)

### Current Backend Behavior
- No file size validation
- No DICOM conformance validation beyond `dcmread(stop_before_pixels=True)`
- `insert_or_select` implies dedup via SHA-256 hash — returns existing record if hash matches
- No auto-routing evaluation after upload (C-STORE path may differ)
- No progress headers sent (returns `204` immediately)
- No multi-file or ZIP support

---

## Required Coverage

### Upload Initiation
- [x] Single file via file picker
- [x] Multiple file selection (`<input multiple>`)
- [x] Drag-and-drop (browser native `DataTransfer.files`)
- [ ] API accepts multiple files in one request (optional, per-file XHR is fine)

### Progress Tracking
- [x] Per-file percentage via `upload.progress` (browser computes from `Content-Length` or chunked encoding)
- [ ] Backend sends `Content-Length` or chunked response for accurate progress
- [ ] Estimated time remaining (frontend-side calculation, nice-to-have)

### Results
- [x] Success per file (204 → status: done)
- [ ] Error response body with machine-readable error code + message (currently returns 204 on success, errors come as HTTP status codes)

### Cancellation
- [x] Per-file cancel (AbortController → xhr.abort())
- [x] Cancel all (iterate all pending/uploading controllers)
- [ ] Backend should handle abrupt disconnects gracefully (mid-write cleanup)

### Retry
- [x] Re-attempt failed uploads with new AbortController
- [ ] Retry currently broken — sends `new File([], file.name)` instead of original blob (loses content)

### Validation
- [ ] Backend validates `Content-Type` or magic bytes for DICOM before processing
- [ ] File size limits (configurable)
- [ ] Acceptable MIME types / extensions (configurable)
- [ ] DICOM conformance check beyond `pydicom.dcmread` (required tags present, valid UIDs)

### Deduplication
- [x] SHA-256 hash computed on upload
- [x] `Files.insert_or_select` returns existing record if hash matches
- [ ] What response for duplicate? Currently 204 (same as success) — should return 200/409 with existing file ID?

### Auto-Routing
- [ ] Does upload trigger routing rule evaluation? (C-STORE does — upload should too for consistency)
- [ ] If yes, same `RoutingHandler` evaluation with same event type

---

## Uncertainties & Questions

| # | Question | Status |
|---|----------|--------|
| 1 | What file types are accepted — only `.dcm` or any file with DICOM MIME type `application/dicom`? | Unresolved |
| 2 | Is there a maximum file size (per file) or total upload size (per session)? | Unresolved |
| 3 | Does the backend validate DICOM conformance (required tags, valid UIDs) beyond `dcmread()`? | Unresolved |
| 4 | What response should a duplicate file (same SHA-256 hash) return? Current 204 is indistinguishable from success. | Unresolved |
| 5 | Should the `insert_or_select` return the existing file ID on dedup match so frontend can show "already exists"? | Unresolved |
| 6 | Should progress tracking send bytes transferred or percentage? Backend needs to send `Content-Length` for `e.lengthComputable=true`. | Unresolved |
| 7 | Can users upload a ZIP of DICOM files, or only individual files? | Unresolved |
| 8 | Is there a need for a multi-file upload endpoint that accepts multiple files in one request? (Current: per-file XHR) | Unresolved |
| 9 | Does upload trigger auto-routing rule evaluation? | Unresolved |
| 10 | If upload triggers routing, should it use the same event type as C-STORE? | Unresolved |
