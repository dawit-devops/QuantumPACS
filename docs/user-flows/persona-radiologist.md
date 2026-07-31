# Persona: Radiologist

## Persona Card

| Attribute | Detail |
|-----------|--------|
| **Role** | Board-certified radiologist interpreting medical images |
| **Description** | Daily power user who spends hours in the PACS viewer diagnosing studies, manipulating images, placing measurements, and annotating findings |
| **Technical Level** | Low — wants images, not software complexity |
| **Frequency** | Daily, multiple hours per session |
| **Devices** | Desktop workstation (high-DPI, dual monitors), occasionally tablet for remote reads |
| **Critical Needs** | Sub-2s study load, full toolset (scroll, WW/WL, measure, annotate), study-to-study navigation without back-button, annotation persistence |
| **Frustrations** | Fat-client installs, VPN overhead, slow DICOM loading, tools that disappear on scroll, annotations that don't save |
| **Default Role** | `radiologist` (v3 RBAC model — identical permissions to physician in v2) |

## Routes & Permissions

### Sidebar Navigation (visible to Radiologist)

| Menu Item | Path | Permission |
|-----------|------|------------|
| Study List | `/` | `FILE_READ` |
| Account | `/account` | Authenticated |

### API Routes (all require JWT via `X-Auth-Pacs` or `Authorization: Bearer`)

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| GET | `/api/files` | `FILE_READ` | Search/query studies (ES-backed) |
| GET | `/api/files/{id}` | `FILE_READ` | Get file metadata + study/series tree |
| GET | `/api/files/{id}/data` | `FILE_READ` | Download DICOM file for viewer (wadouri) |
| GET | `/api/files/{id}/thumbnail` | `FILE_READ` | JPEG thumbnail (256x256) |
| POST | `/api/files/{id}` | `FILE_WRITE` (v3) / implicit (v2) | Save annotation state + DICOM tag edits |
| POST | `/api/files/{id}/share` | `FILE_WRITE` (v3) / implicit (v2) | Generate expiring share link |
| GET | `/api/files/{id}/changes` | `FILE_READ` | File change audit log |
| GET | `/api/files/download.zip` | `FILE_READ` | Bulk download selected files as ZIP |
| GET | `/api/files/download.csv` | `FILE_READ` | Bulk download metadata as CSV |
| GET | `/api/patients/{id}` | `PATIENT_READ` | Patient demographics + study tree |
| GET | `/api/patients` | `PATIENT_READ` | Patient search |
| GET | `/api/v2/dicomweb/studies` | `DICOMWEB_READ` | QIDO-RS study search |
| GET | `/api/v2/dicomweb/studies/{uid}` | `DICOMWEB_READ` | WADO-RS study retrieval |
| GET | `/api/v2/fhir/ImagingStudy` | `DICOMWEB_READ` | FHIR study search |
| GET | `/api/health` | None | Health check (unauthenticated) |

### Permission Slugs for Radiologist Role

```
FILE_READ, PATIENT_READ, STUDY_READ, DICOMWEB_READ
```

v3 RBAC adds `FILE_WRITE` for annotation saving (absent in v2 built-in role).

## End-to-End Flows

### Flow 1: Login and Navigate to Studies

```
1. User opens browser → /login
2. Enters username + password
3. POST /api/login → { token: <jwt> }
4. Token stored in localStorage + httpOnly cookie
5. Redirect to /
6. GET /api/files (empty search → 10 most recent studies)
7. Files page renders: search box + results table
```

### Flow 2: Search and Find a Study

```
1. In Files page, type search query in search box
   (or click "Advanced" to open modal with 12 DICOM tag fields)
2. Search terms encoded in URL as JSON (bookmarkable)
3. GET /api/files?q={encoded_query}
4. Results table: ID, Patient ID, Patient Name, Study ID,
   Study Description, Series Number, Series Description
5. Click row → navigate to /files/{id}
```

### Flow 3: View and Navigate a Study

```
1. GET /files/{id} → Detail page mounts
2. GET /api/files/{id} → returns file metadata + patient info
   + full study/series/file hierarchy
3. Cornerstone3D initializes (lazy singleton, once per session):
   - ensureGlobalInit(): init CS3D core, tools, dicom-image-loader
   - Create RenderingEngine (OPENPACS_ENGINE) + StackViewport
   - Load image via wadouri:${API_URL}/files/${id}/data
   - 200ms delay → restoreToolState(file.tools_state)
   - Subscribe to WebSocket channel for file
   - Start 500ms sendState interval
4. Breadcrumb shows: Patient > Study > Series > File
   (all levels are dropdown-navigable)
5. Slider/ThumbnailStrip appears if series has >1 file
6. Default tools active: Pan (left), Zoom (middle), WW/WL (right), Stack Scroll (wheel)
```

### Flow 4: Annotate and Measure

```
1. Click toolbar button to set primary tool
   (Length, Angle, Arrow, Rectangle ROI, Ellipse ROI)
2. Click/drag on image to create annotation
3. On each annotation event, saveToolState() triggers
4. WebSocket broadcasts state every 500ms to other sessions
5. Click Eraser → click annotation → removes it
6. Click Pan (default) to revert to cursor navigation
7. Click Save button → POST /api/files/{id} { tools_state: {...} }
   → persists to files.tools_state JSONB column
   → logged to file_changes table as 'anotations changed'
8. Other open sessions receive annotation update via WebSocket
```

### Flow 5: Share Study with Referring Physician

```
1. Switch to Share tab in Detail page
2. Enter duration in hours (e.g., 24)
3. POST /api/files/{id}/share { duration: 24 }
4. Server returns { key: "64-char-hex" }
5. Copy link: {current_url}?key={key}
6. Send link to referring physician
7. Recipient opens link → ?key= read from URL → localStorage.tempKey
8. ProtectedRoute passes (tempKey present)
9. Sidebar hidden, only Image tab visible
10. Viewer loads identically (same Cornerstone3D viewer)
11. Annotations visible if saved to tools_state
12. If key expired → 401 → redirect /login
```

### Flow 6: Inspect Patient History

```
1. Click patient breadcrumb (or Patient ID link) in Detail page
2. Navigate to /patients/{id}
3. Page shows demographics table (ID, Name, Sex, DOB)
4. DirectoryTree displays 3-level hierarchy:
   Study <id> (<description>)
     └── Series <number> (<modality>) <description>
           └── File <name> → /files/{fileId}
5. Click any leaf → navigate to that file's Detail page
6. Use browser back button to return to patient list
```

### Flow 7: Inspect DICOM Metadata

```
1. Open study in Detail page
2. Switch to Data tab
3. Table shows all DICOM tags as key-value pairs
   (from files.meta JSONB column)
4. Search input filters keys by prefix (case-insensitive)
5. Pagination: 20 items per page
6. (Editing gated — metadata editing currently disabled in v2)
```

### Flow 8: Audit Trail Review

```
1. Open study in Detail page
2. Switch to Changes tab
3. Table shows time (UTC), username, change type
4. Paginated server-side
5. Tracked events: read, download, annotations changed, tag edits
```

### Flow 9: Bulk Download

```
1. In Files page (/), check checkbox on target rows
2. Click "Download files" → opens /api/files/download.zip?ids=1,2,3
3. Browser downloads ZIP of DICOM files
   (or "Download data" for CSV metadata export)
```

## Metrics & SLAs

| Metric | Target | How Measured |
|--------|--------|-------------|
| Time to first image (LAN) | ≤ 2s | Playwright timing |
| Time to first image (WAN) | ≤ 5s | Playwright timing |
| Search results (10k studies) | ≤ 500ms | API response timer |
| Page transition (Files → Detail) | ≤ 1s | React component mount |
| Annotation persist | ≤ 500ms | Network timing |
| WebSocket broadcast latency | ≤ 200ms | Application-level timer |
| Bundle size (initial) | ≤ 500 KB gzipped | Vite bundle analysis |
| Time to interactive | ≤ 3s | Lighthouse |
| Max concurrent viewers | ≥ 50 (v2), ≥ 200 (v3) | k6 WebSocket scenario |
| Max study size | ≥ 10,000 instances | Browser memory < 2 GB |
| Scroll smoothness | No perceptible loading between slices | UX requirement |

## Acceptance Criteria

### From PRD / UX-Functionality.md

1. Radiologist can log in and see the Files page with recent studies
2. Global search returns results in < 500ms for 10k studies
3. Advanced search with 12 DICOM tags returns matching studies
4. Clicking a study row opens the Cornerstone3D viewer within 1s
5. All 10 annotation tools are available (Pan, Zoom, WW/WL, Stack Scroll, Length, Angle, Arrow, Rectangle ROI, Ellipse ROI, Eraser)
6. Annotations persist across page reloads (stored in `files.tools_state`)
7. WebSocket sync delivers annotation updates to other sessions within 200ms
8. Share links expire after configured duration and redirect to login when expired
9. Breadcrumb navigation allows study-to-study, series-to-series, file-to-file switching
10. Mobile view shows bottom toolbar with 4 essential tools and truncated breadcrumbs
11. Patient page shows demographics + interactive study/series/file tree
12. Bulk download works for selected rows

### Derived from Code

13. JWT token with `FILE_READ` required for all detail/search endpoints
14. `FILE_WRITE` required for annotation save and share link creation (v3)
15. DICOMweb QIDO-RS fallback: if ES is down, search falls back to PostgreSQL (graceful degradation)
16. Share-key mode hides sidebar, tabs, and all management features — viewer only
17. CORS allows all origins (development; must be tightened before production)

## Implementation Gaps

| Feature | Status | Impact | Target Version |
|---------|--------|--------|---------------|
| Hanging protocols (auto-layout per modality/protocol) | MISSING | Radiologist must manually arrange views | Not planned |
| Multi-Planar Reformat (MPR) | MISSING | Cannot view coronal/sagittal from CT/MRI axial | Not planned |
| Volume rendering / 3D | MISSING | Cannot do 3D reconstructions | Not planned |
| Structured Reporting (SR DICOM) | MISSING | No templated or structured narrative reports | v3.1/v3.2 |
| Comparison viewing (side-by-side prior) | MISSING | Cannot compare current vs prior study | Not planned |
| CAD/AI integration | MISSING | No AI inference overlays | v3.2 |
| Voice commands / speech-to-text dictation | MISSING | No hands-free workflow | Not planned |
| Key image marking | MISSING | Cannot flag critical images | Not planned |
| Critical results flagging | MISSING | No urgent finding escalation workflow | Not planned |
| Study close / read status | MISSING | No radiologist "read" status tracking | Not planned |
| Multi-viewport layout | MISSING | Single stack viewport only | Not planned |
| Cine loop (cardiac/dynamic) | MISSING | No automatic playback | Not planned |
| Keyboard shortcuts | MISSING | Mouse-only tool switching; no hotkeys | v2.1 (target) |
| WW/WL presets (lung, bone, soft tissue) | MISSING | Manual window/level for every study | Not planned |
| Magnifying glass / loupe | MISSING | No local zoom magnification | Not planned |
| Crosshairs / localizer reference | MISSING | No cross-reference lines | Not planned |
| DICOM SEG overlay | MISSING | Cannot display segmentation results | v3.2 |
| Guided tour / onboarding | MISSING | No first-login walkthrough | v2.1 (target) |

## Key Files Reference

| File | Purpose |
|------|---------|
| `docs/UX-Functionality.md` | Persona definition, interaction flows, performance budgets |
| `docs/User-Stories.md` | E2 (search), E3 (viewing), E4 (patient browse), E5 (sharing) stories |
| `frontend/src/detail/Detail.tsx` | Main viewer page: tabs, breadcrumb, navigation |
| `frontend/src/detail/CornerstoneElement.tsx` | Cornerstone3D viewer + 10 tools + WebSocket sync |
| `frontend/src/detail/ThumbnailStrip.tsx` | Series file thumbnails |
| `frontend/src/detail/EditableTable.tsx` | DICOM metadata browser (Data tab) |
| `frontend/src/detail/Changes.tsx` | Audit log table |
| `frontend/src/detail/Share.tsx` | Share link generator |
| `frontend/src/files/Files.tsx` | Study list/search with ES + column filters |
| `frontend/src/files/AdvancedSearch.tsx` | 12-field DICOM tag search modal |
| `frontend/src/patient/Patient.tsx` | Patient demographics + 3-level tree |
| `frontend/src/common/Sidebar.tsx` | Sidebar nav (radiologist sees Files + Account only) |
| `backend/api/permissions.py` | Radiologist permission set definition |
| `backend/api/files.py` | File endpoints (search, detail, upload, share, thumbnail) |
| `backend/api/dicomweb.py` | QIDO-RS / WADO-RS endpoints |
| `backend/api/ws.py` | WebSocket annotation sync |
| `backend/db/files.py` | Files DB model (tools_state, metadata, changes) |