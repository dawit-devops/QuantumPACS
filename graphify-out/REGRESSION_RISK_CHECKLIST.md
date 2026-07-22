# Regression Risk Checklist — OpenPACS

---

## High-Risk Behavior Areas

### 🔴 Critical — DICOM Ingestion Pipeline
```
Modality → C-STORE → pynetdicom → pydicom parse → asyncpg store → ES index → ReplicaFiles
```
**Risks:**
- pynetdicom upgrade breaks C-STORE acceptance (modalities can't send studies)
- pydicom tag parsing changes corrupt metadata extraction
- asyncpg connection pool changes cause timeouts under load
- ES index failure is silent (no error raised in current code)

**Verification:**
- [ ] Send DICOM study via storescu → confirm file appears in DB
- [ ] Verify PatientID, StudyInstanceUID, SeriesNumber extracted correctly
- [ ] Verify file appears in search results
- [ ] Verify replica sync queues the file within configured delay
- [ ] Load test: 50 concurrent C-STORE operations

### 🔴 Critical — Authentication & Authorization
```
Login → JWT encode → Token in X-Auth-Pacs → JWT decode → User lookup
```
**Risks:**
- PyJWT upgrade changes token format → existing sessions invalidated
- Algorithm confusion vulnerability if `algorithms` not specified
- Token expiry behavior changes

**Verification:**
- [ ] Login with valid credentials returns token
- [ ] Existing tokens still valid after upgrade (issue new tokens to test)
- [ ] Expired tokens return 401
- [ ] Invalid tokens return 401
- [ ] Admin-only endpoints block non-admin tokens
- [ ] Shared access (`?key=...`) still works

### 🔴 Critical — File Upload & Download
```
Upload → Storage → DB → ES → Download/Serve
```
**Risks:**
- aiobotocore/b2sdk upgrade breaks S3/B2 connectivity
- Storage abstraction breaks if interface changes
- File download returns corrupted data
- ZIP/CSV export breaks

**Verification:**
- [ ] Upload single file → confirm stored on correct backend
- [ ] Upload directory → confirm all files stored
- [ ] Download file → compare hash with original
- [ ] Download ZIP of multiple files → confirm all files present
- [ ] Download CSV → confirm metadata correct
- [ ] Test all three backends: Local, S3, B2

### 🟡 High — Search & Browse
```
Search query → ES → Files table → Response
```
**Risks:**
- ES client rewrite changes query behavior (different results for same query)
- PyPika upgrade generates different SQL
- Pagination breaks

**Verification:**
- [ ] Basic text search returns expected files
- [ ] Advanced search with multiple fields works
- [ ] Pagination returns correct page/limit
- [ ] Search highlighting in frontend still works

### 🟡 High — Frontend Routing & Navigation
```
URL → react-router → Component render → API call
```
**Risks:**
- Route params don't match after react-router v6 migration
- Navigation (back/forward) broken
- Deep links broken

**Verification:**
- [ ] Navigate to `/files/{id}` → loads DICOM viewer
- [ ] Navigate to `/patients/{id}` → loads patient page
- [ ] Browser back/forward works correctly
- [ ] Login redirect works after auth
- [ ] All sidebar links navigate to correct pages

### 🟡 High — DICOM Viewer
```
File ID → CornerstoneElement → WADO load → cornerstone display → Tools
```
**Risks:**
- cornerstone-wado-image-loader upgrade breaks image fetching
- cornerstone-tools upgrade changes tool behavior
- Annotation save/restore broken
- Collaborative (WebSocket) sync broken

**Verification:**
- [ ] DICOM image renders in viewport
- [ ] Window/level (WW/WC) works
- [ ] Zoom, pan, rotate work
- [ ] Measurements (length, angle, ROI) display correctly
- [ ] Annotation save to DB → reload → annotations restored
- [ ] WebSocket sync shows annotations from other session
- [ ] Series navigation (slider) switches images

---

## Verification Steps Per Phase

### Before Phase 0 (Foundation):
- [ ] `pip install -r requirements.txt` succeeds
- [ ] `npm install` succeeds (no deprecation warnings baseline)
- [ ] `npm run build` produces working static files
- [ ] Docker build succeeds
- [ ] Database init completes without errors
- [ ] `./start.sh` starts all processes

### Before Phase 1 (Security):
- [ ] Phase 0 verified in staging
- [ ] Test suite exists for auth and ES (write these first)
- [ ] Rollback scripts ready

### Before Phase 2 (Framework):
- [ ] Phase 1 verified in staging for 1 week
- [ ] Both old and new starlette versions run in parallel containers
- [ ] React v16 + v18 render same pages (test in browser)
- [ ] All routes tested manually

### Before Phase 3 (UI):
- [ ] antd v3/v4/v5 rendered side-by-side in dev
- [ ] Each replaced component tested individually
- [ ] Form submissions work (Login, Account, Share, etc.)

---

## Rollback Readiness

| Condition | Action | Time |
|---|---|---|
| Auth broken | Revert PyJWT import → deploy previous image | <10min |
| DICOM ingest fails | Revert pydicom/pynetdicom pins → deploy | <15min |
| Search returns wrong results | Point ES adapter back to old client | <5min |
| Frontend broken after Vite migration | `npm run build` with old react-scripts → deploy | <20min |
| antd migration breaks page | Keep both antd versions via aliases | <30min |
| Any production issue | `kubectl rollout undo` or swap docker tag | <5min |

---

## Pre-Production Gate

Before each phase reaches production:

- [ ] Staging deployment passes all checklist items above
- [ ] Load test at 2x expected traffic (no 5xx, p95 < 500ms)
- [ ] Canary deployment: 10% traffic for 1 hour
- [ ] Monitoring shows no error rate increase
- [ ] Rollback tested and documented
- [ ] Runbook updated for this phase
