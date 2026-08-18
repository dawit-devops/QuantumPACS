# Persona: Clinician (Referring Physician / Subspecialist)

## Persona Card

| Attribute | Detail |
|-----------|--------|
| **Role** | Clinician — referring physician, subspecialist, or hospitalist who reviews imaging studies sent by radiologists or received via share links |
| **Description** | Occasional PACS user in a composite role encompassing Radiologist (daily viewer) and Referring Physician (link-only recipient) perspectives. Clinicians view studies, read reports, review annotations, and make clinical decisions based on imaging findings — but do not operate modalities or manage PACS infrastructure |
| **Technical Level** | Low for referring physicians; Medium for subspecialists performing self-reads |
| **Frequency** | As needed — per patient encounter, typically < 15 min per review session |
| **Devices** | Desktop workstation (primary), tablet (secondary for remote review), laptop (occasional) |
| **Critical Needs** | One-click access via share links, fast study load, readable annotations, no login barrier for shared links, mobile support for off-hours review |
| **Frustrations** | Login required for access (instead of seamless share-link experience), annotations not visible if not saved, slow load times for large studies |
| **Default Role** | Composite of `radiologist` / `physician` permissions |

> Note: In v2 code, `radiologist` and `physician` roles have identical permission sets. The distinction is semantic only. v3 plans may differentiate them (e.g., radiologist gets `FILE_WRITE` for annotation save, physician remains view-only), but this has not been implemented yet.

## Routes & Permissions

### Sidebar Navigation (visible to Clinician)

| Menu Item | Path | Permission |
|-----------|------|------------|
| Study List | `/` | `FILE_READ` |
| Account | `/account` | Authenticated |

### API Routes (Clinician View — same as Radiologist)

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| GET | `/api/files` | `FILE_READ` | Search/query studies |
| GET | `/api/files/{id}` | `FILE_READ` | Get file metadata + study/series tree |
| GET | `/api/files/{id}/data` | `FILE_READ` | Download DICOM file for viewer |
| GET | `/api/files/{id}/thumbnail` | `FILE_READ` | JPEG thumbnail (256x256) |
| POST | `/api/files/{id}` | `FILE_WRITE` (v3) | Save annotations (radiologist); read-only view for referring physician via share-key |
| POST | `/api/files/{id}/share` | `FILE_WRITE` (v3) | Create share link (requires permission) |
| GET | `/api/files/{id}/changes` | `FILE_READ` | File change audit log |
| GET | `/api/files/download.zip` | `FILE_READ` | Bulk download |
| GET | `/api/files/download.csv` | `FILE_READ` | Bulk metadata export |
| GET | `/api/patients/{id}` | `PATIENT_READ` | Patient demographics + study tree |
| GET | `/api/patients` | `PATIENT_READ` | Patient search |
| GET | `/api/v2/dicomweb/studies` | `DICOMWEB_READ` | QIDO-RS study search |
| GET | `/api/v2/dicomweb/studies/{uid}` | `DICOMWEB_READ` | WADO-RS study retrieval |
| GET | `/api/v2/fhir/ImagingStudy` | `DICOMWEB_READ` | FHIR study search |
| GET | `/api/health` | None | Health check |
| GET | `/api/metrics` | `METRICS_READ` | Dashboard metrics |

### Permission Slugs for Clinician Role

v3 RBAC model assigns these per role:

| Role | Permissions | Use Case |
|------|-------------|-----------|
| `radiologist` (self-read) | `FILE_READ, FILE_WRITE, PATIENT_READ, STUDY_READ, DICOMWEB_READ` | Perform reads, save annotations, create share links |
| `physician` (referring) | `FILE_READ, PATIENT_READ, STUDY_READ, DICOMWEB_READ` | View-only; no annotation save, no share creation |
| `clinician` (generic) | Same as combined above | When no role distinction exists |

### Share-Key Mode (Referring Physician Without Login)

When accessing via `?key=` URL parameter:

| Feature | Behavior |
|---------|----------|
| Authentication | `localStorage.tempKey` checked by `ProtectedRoute` — no JWT required |
| Sidebar | **Hidden** (no navigation, no account menu) |
| Tabs | **Image tab only** (Data, Share, Changes, Admin tabs hidden) |
| Measurement tools | View-only (Pan, Zoom, WW/WL active; annotation tools **disabled** — no Save, Clear, Erase) |
| File management | **No access** (no download, upload, delete, share) |
| Annotations | **Read-only** (viewing existing annotations saved in `tools_state` — cannot add new ones) |
| Expiry | Key checked against `shared_files.created + duration`; expired → 401 → `/login` |
| DICOM metadata | Not accessible (Image tab only) |
| Audit trail | Not accessible |

## End-to-End Flows

### Flow 1: Radiologist Shares Study → Clinician Opens Share Link

```
1. Radiologist has completed study review and saved annotations
2. Radiologist clicks "Share" tab in Detail page
3. Enters duration: 24 hours
4. POST /api/files/{id}/share { duration: 24 }
5. Server returns { key: "64-char-hex" }
6. Radiologist copies link: https://pacs.example.com/files/{id}?key={key}
7. Radiologist sends link to Clinician via email/SMS/EMR message

Clinician receives link and opens in browser:

8. Browser loads https://pacs.example.com/files/{id}?key={64-char-hex}
9. ProtectedRoute reads ?key= from URL → localStorage.setItem('tempKey', key)
10. Auth check: tempKey is truthy → passes without requiring login
11. Sidebar hidden (no navigation, no admin)
12. Detail page renders in share-key mode:
    - Image tab active (only visible tab)
    - Breadcrumb shows: Patient > Study > Series > File
    - Viewer initializes with same Cornerstone3D stack viewport
    - Saved annotations from tools_state are restored and visible
13. Clinician views images and annotations
14. No Save, Erase, or annotation tools available in share-key mode
15. Clinician can zoom, pan, WW/WL (view-only manipulation)
16. If key expired → 401 → redirect to /login
17. Clinician cannot see Data tab, Changes tab, or Admin tab
```

### Flow 2: Clinician Logs In and Finds a Study

```
1. Clinician opens browser → /login
2. Enters username + password (or uses SSO if configured)
3. POST /api/login → JWT issued
4. Token stored → redirected to /
5. Files page renders with recent studies
6. Searches for study:
   a. Global search box (type patient name or accession number)
   b. OR Advanced Search modal (12 DICOM tag fields)
   c. Results table appears with matching studies
7. Clinician clicks study row → /files/{id}
8. Study loads in Cornerstone3D viewer
```

### Flow 3: Clinician Reviews Study and Annotations (Share-Key Mode)

```
1. Clinician opens via share link → share-key mode
2. Cornerstone3D viewer initializes:
   - Renders study image via wadouri: URL
   - Restores annotations from tools_state (if radiologist saved them)
   - WebSocket subscribed for real-time annotation sync (only if other radiologist has same study open)
3. Radiologist's annotations visible:
   - Length measurements with distance values
   - Angle measurements with degree values
   - Arrow annotations with labels
   - ROI (Rectangle/Ellipse) with area + mean/SD values
4. Clinician navigates through series:
   - Slider for instances within series
   - Thumbnail strip for visual series navigation
   - Breadcrumb dropdowns to switch series/study/patient
5. Clinician manipulates image (view-only):
   - Pan (left-click drag)
   - Zoom (middle-click drag / scroll wheel)
   - WW/WL (right-click drag)
   - Rotate 90° CW (toolbar button)
   - H-Flip, V-Flip, Invert (toolbar buttons)
6. Clinician CANNOT:
   - Add new annotations (save/eraser tools disabled)
   - Save any changes
   - Download the DICOM file
   - View DICOM metadata (Data tab hidden)
   - View audit trail (Changes tab hidden)
```

### Flow 4: Clinician Browses Patient History

```
1. In Detail page, click patient breadcrumb link
2. Navigate to /patients/{id}
3. Patient demographics shown: ID, Name, Sex, DOB
4. DirectoryTree shows 3-level hierarchy:
   Study <study_id> (<description>)
     └── Series <number> (<modality>) <description>
           └── File <name> (clickable → /files/{fileId})
5. Clinician clicks a previous study → navigates to that file
6. Study loads in viewer (if share-key was provided via link, or if logged in with permissions)
7. Comparison: clinician can mentally compare current vs prior study by navigating back and forth
   (Note: no automated side-by-side comparison tool exists)
```

### Flow 5: Clinician Searches for Studies (Logged-In)

```
1. Clinician navigates to / (Files page)
2. Search methods available:
   a. Global search: type text → ES full-text search across all indexed fields
   b. Column filter: per-column dropdown filters (ID, Patient ID, Patient Name, Study ID, etc.)
   c. Advanced Search: 12 predefined DICOM tag fields + custom field support (AND conjunction)
3. Results table shows: ID (link), Patient ID (link → /patients/:id), Patient Name, Study ID,
   Study Description, Series Number, Series Description
4. Clinician clicks row → /files/{id} to view study
5. Pagination and sort supported (URL-encoded state, bookmarkable)
6. Bulk actions available if FILE_WRITE permission: download ZIP, download CSV
```

### Flow 6: Clinician Reviews DICOM Metadata (Logged-In, Has FILE_READ)

```
1. Open study in Detail page → /files/{id}
2. Switch to Data tab
3. Table shows all DICOM tags as key-value pairs
   - Search input filters keys by prefix (case-insensitive)
   - Pagination: 20 items per page
4. Metadata comes from files.meta JSONB column
5. Includes: Patient, Study, Series, Modality metadata
6. Includes: Size (KB), SOP Class UID, Transfer Syntax UID
7. (Editing gated — metadata editing currently disabled in v2)
```

### Flow 7: Clinician Reviews Audit Trail (Logged-In, Has FILE_READ)

```
1. Open study in Detail page → /files/{id}
2. Switch to Changes tab
3. Table shows: Time (UTC), Username, Change Type (Tag with orange color)
4. Paginated server-side
5. Tracked events include:
   - 'read' when file was accessed
   - 'download' when file was downloaded
   - 'anotations changed' when annotations were saved
   - '<tag_key>' when specific DICOM tag was edited
6. Each row: new Date(data * 1000).toUTCString()
7. Audit sourced from GET /api/files/{id}/changes → FileChange.for_file()
```

### Flow 8: Mobile Clinician Review (Tablet/Phone)

```
1. Clinician opens PACS on tablet/phone
2. Sidebar collapses (hidden on < 992px)
3. Bottom toolbar appears with 4 essential tools:
   Pan, Length, Rectangle ROI, Eraser
   (44x44px touch targets for accessibility)
4. Bottom fixed MobileNav with 3 items: Files, Metrics, Account
5. Breadcrumb text truncated on small screens:
   - Patient: name only (no patient_id)
   - Study: 'S:<study_id>'
   - Series: 'Ser:<number>'
   - File: data.name only
6. Viewer renders normally but viewport dimensions adjust:
   - <= 420px: 350x350px viewer
   - 600-767px: 500x500px viewer
   - >= 768px: 700x700px viewer
7. Touch gestures supported:
   - Pan: touch drag
   - Zoom: pinch gesture
   - Stack scroll: swipe
8. Share-key mode on mobile: same restrictions as desktop share-key mode
```

## Metrics & SLAs

| Metric | Target | How Measured |
|--------|--------|-------------|
| Share link load time (viewer) | < 2s after link open | Playwright timing |
| Share-key auth bypass | < 10ms (localStorage check) | ProtectedRoute mount |
| Study load for clinician | ≤ 2s (LAN) / ≤ 5s (WAN) | Same as radiologist budget |
| Annotation visibility after radiologist saves | ≤ 500ms (WebSocket broadcast) | 500ms interval |
| Mobile viewport rendering | Immediate | React mount |
| Search results for clinician | ≤ 500ms (for 10k studies) | API response timer |
| Share link expiry enforcement | Immediate on access when expired | Middleware check |
| Time to study from patient tree | ≤ 1s | React navigation |

## Acceptance Criteria

### From PRD / UX-Functionality.md / User-Stories.md

1. Clinician can access study via share link without logging in (`?key=` URL parameter)
2. Share link grants access to Image tab/viewer only — no sidebar, no admin, no data/audit tabs
3. Share key is stored in localStorage and checked by ProtectedRoute
4. Expired share keys redirect to `/login` with 401 status
5. Share key duration is configurable (hours) at creation time
6. Clinician with JWT login can search studies by any field (global + column + advanced search)
7. Clinician can navigate patient study history via patient breadcrumb → study tree
8. Clinician can view and interact with radiologist's annotations (measurements visible)
9. Clinician can manipulate image viewport (zoom, pan, WW/WL, rotate, flip, invert)
10. Mobile view provides touch-optimized toolbar and compact breadcrumb labels
11. Share-mode clinician cannot save annotations, download files, or view metadata
12. Radiologist's annotations persist across page reloads and are restored on viewer load
13. WebSocket sync delivers annotation updates within 200ms to all open sessions
14. Bulk download works for clinicians with appropriate permissions
15. Audit trail (Changes tab) shows complete history of file access and modifications
16. DICOMweb QIDO-RS search works as fallback when ES is unavailable
17. FHIR R4 API returns correct Patient/ImagingStudy resources for clinician queries

### Derived from Code (Additional)

18. Share-key mode: `ProtectedRoute` checks `tempKey` state — if truthy, auth skipped
19. Share-tab hidden when `tempKey` is present (`!tempKey` condition in base layout)
20. Annotation tools disabled in share-key mode — only viewer interaction tools (Pan, Zoom, WW/WL) active
21. `FILE_READ` permission sufficient for clinician to view all studies and metadata
22. `FILE_WRITE` permission required for annotation save and share link creation (v3)
23. Share key: 64-char hex string generated via `secrets.token_urlsafe(32)` → 64 hex chars
24. Share expiry calculated as `created_at + duration_hours` → checked on each API request
25. Radiologist and Physician roles currently have identical permission sets (identical access)
26. No separate "referring physician" role exists in v2 — role distinction is planned for v3 RBAC
27. WebSocket annotation sync subscribes via `open` message with file URL; broadcasts every 500ms via Redis channel `channel:file:{file_id}`

## Implementation Gaps

| Feature | Status | Impact | Target Version |
|---------|--------|--------|---------------|
| Structured report viewing | MISSING | Clinicians cannot read structured radiology reports — must rely on share links + annotations | v3.1/v3.2 |
| Side-by-side prior comparison | MISSING | Clinicians cannot automatically compare current vs prior study | Not planned |
| Report subscription / notification | MISSING | Clinicians do not receive push notification when radiologist completes reading | v3 (webhooks) |
| Push notifications (in-app) | MISSING | No notification bell, alert system, or in-app alerts | v3.x |
| Email/SMS result delivery | MISSING | No email or SMS when study is ready for review | Not on roadmap |
| Structured report editor | MISSING | Radiologist report creation, templating, sign-off not implemented | v3.1/v3.2 |
| Critical results flagging/escalation | MISSING | Urgent findings not escalated to referring clinicians automatically | Not planned |
| Mobile app (native) | MISSING | Only responsive PWA; no dedicated iOS/ Android app | Not planned |
| Voice-driven review | MISSING | No speech-to-text or voice commands for hands-free review | Not planned |
| CAD/AI integration display | MISSING | No AI inference overlay in viewer | v3.2 |
| Multi-viewport comparison layouts | MISSING | Single stack viewport only; no 2x2 or side-by-side layouts | Not planned |
| DICOM SEG overlay | MISSING | No AI segmentation overlays in viewer | v3.2 |
| Cross-hospital study access | MISSING | Clinician cannot view studies from other hospital tenants without cross-tenant permissions | v3 (tenant federation) |
| Encrypted share links | MISSING | Share links are 64-char hex but not encrypted; anyone with link can access | v3.x |
| Link revocation | MISSING | No mechanism for radiologist to revoke a previously generated share link | v3.x |
| Download audit for clinicians | PARTIAL | Download events logged in Changes tab but no clinician-specific download notification | v3.x |
| Keyboard shortcut reference | MISSING | No `?` key help; no keyboard shortcuts (mouse-only) | v2.1 (target) |
| Guided tour for clinicians | MISSING | No first-login walkthrough for referring physicians | v2.1 (target) |

## Key Files Reference

| File | Purpose |
|------|---------|
| `docs/UX-Functionality.md` | Clinician persona definition with Radiologist/Referring Physician composite |
| `docs/User-Stories.md` | Clinician-related user stories (E2-E5) |
| `frontend/src/detail/Detail.tsx` | Main viewer page with share-key mode logic |
| `frontend/src/detail/CornerstoneElement.tsx` | Cornerstone3D viewer (same stack viewport for all clinician types) |
| `frontend/src/detail/Share.tsx` | Share link generator component |
| `frontend/src/detail/ThumbnailStrip.tsx` | Series navigation |
| `frontend/src/detail/EditableTable.tsx` | Data tab (DICOM metadata) |
| `frontend/src/detail/Changes.tsx` | Audit log table |
| `frontend/src/files/Files.tsx` | Search interface |
| `frontend/src/patient/Patient.tsx` | Patient tree |
| `frontend/src/common/base.tsx` | Layout wrapper with share-key mode logic |
| `frontend/src/common/Sidebar.tsx` | Sidebar (hidden for share-key mode) |
| `frontend/src/auth/TenantSelector.tsx` | Tenant context switcher (visible to all authenticated users) |
| `backend/api/permissions.py` | Radiologist / Physician permission definitions |
| `backend/api/files.py` | File endpoints (search, detail, share, download) |
| `backend/api/auth.py` | Share-key authentication (`TokenAuth.authenticate()`, tempKey bypass) |
| `backend/api/ws.py` | WebSocket annotation sync |
| `backend/api/dicomweb.py` | DICOMweb QIDO/WADO endpoints |
| `backend/api/fhir.py` | FHIR R4 endpoints |
| `frontend/src/ws.ts` | WebSocket client with auto-reconnect |
| `backend/api/rbac.py` | `requires_permission()` decorator |
| `backend/db/files.py` | File model (tools_state, changes) |
| `backend/db/share_files.py` | SharedFiles model (share key generation, expiry) |