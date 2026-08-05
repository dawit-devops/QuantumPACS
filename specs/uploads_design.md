# Feature: Upload Improvements

## Existing State

Upload works end-to-end: multipart POST, parse DICOM, hash, insert hierarchy, copy to storage. But lacks validation, error feedback, and has a retry bug.

## Changes

### Backend

**1. File size validation** — Reject files > configurable limit before any processing. Default 500MB. Check `Content-Length` header or actual read.

**2. DICOM magic byte check** — Verify first 4 bytes are `\x00\x00\x00\x00\x08\x00\x00\x00` (DICOM preamble magic at byte 128+4 = DICM) or file starts with `\xDICM`. Reject non-DICOM files with 400.

**3. DICOM conformance check** — After `dcmread()`, verify required tags exist: `PatientID`, `StudyInstanceUID`, `SeriesInstanceUID`, `SOPInstanceUID`. Return 400 with specific error code if missing.

**4. Duplicate response** — When `insert_or_select` returns an existing record (hash match), return 200 `{'id': existing_id, 'duplicate': True}` instead of 204.

**5. Disconnect handling** — Wrap upload in try/finally that cleans up partial storage writes on exception.

### Frontend

**1. Fix retry bug** — Change `new File([], file.name)` to `new File([file], file.name)` on line 152 of UploadZone.tsx. Actually, we need to keep the original file reference. Store files in a ref map.

**2. Error display** — Parse error response body and show it in the upload status instead of generic "Upload failed (status)".

**3. Size pre-check** — Check `file.size` against max before uploading, mark as error immediately if too large.

### Security

| Check | Status |
|-------|--------|
| Auth required | ✅ Already behind `FILE_WRITE` permission |
| Input validation | ✅ File type + size + DICOM conformance checks added |
| Rate limiting | Not needed (upload is resource-intensive, already throttled by file size) |
| Logging | Upload errors should be logged |
