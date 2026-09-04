# QuantumPACS — User Experience & Functionality Specification

**Version**: 2.0.0
**Status**: Final
**Date**: 2026-07-23

---

## 1. Design Philosophy

QuantumPACS follows four core UX principles:

1. **Zero-footprint first** — No software installation. The entire diagnostic workflow runs in a browser.
2. **Radiologist-speed** — Every interaction is optimized for reading speed. Study loading, tool switching, and navigation complete in under 2 seconds.
3. **Defense in depth** — Authentication, authorization, audit trails, and expiring share links protect PHI at every layer.
4. **Progressive disclosure** — Simple search on first load; advanced tools (DICOM tag search, admin panels, annotation sharing) become available as the user's workflow demands them.

---

## 2. User Personas (Detailed)

### 2.1 Radiologist

| Attribute | Detail |
|-----------|--------|
| **Role** | Board-certified radiologist interpreting medical images |
| **Technical level** | Low — wants images, not software complexity |
| **Frequency** | Daily, multiple hours per session |
| **Devices** | Desktop workstation (high-DPI, dual monitors), occasionally tablet for remote reads |
| **Critical needs** | Sub-2s study load, full toolset (scroll, WW/WL, measure, annotate), study-to-study navigation without back-button, annotation persistence |
| **Frustrations** | Fat-client installs, VPN overhead, slow DICOM loading, tools that disappear on scroll, annotations that don't save |

### 2.2 Technologist

| Attribute | Detail |
|-----------|--------|
| **Role** | Operates CT/MRI/US modalities, verifies image quality and patient data |
| **Technical level** | Medium — comfortable with modality consoles and basic IT workflows |
| **Frequency** | Daily, many short sessions |
| **Devices** | Workstation near modality console, thin client |
| **Critical needs** | Quick C-STORE confirmation, study completeness check (correct series count), patient data accuracy, retake notification |
| **Frustrations** | Slow uploads, missing confirmation feedback, ambiguous error messages on failed sends |

### 2.3 PACS Administrator

| Attribute | Detail |
|-----------|--------|
| **Role** | Manages system configuration, storage, users, and uptime |
| **Technical level** | High — comfortable with Linux, PostgreSQL, Docker |
| **Frequency** | Weekly active management, daily monitoring |
| **Devices** | SSH + browser, any device |
| **Critical needs** | User lifecycle management, replica health monitoring, storage capacity tracking, log auditing, backup/restore procedures |
| **Frustrations** | Opaque storage backends, difficult troubleshooting, no capacity forecasting |

### 2.4 Hospital IT

| Attribute | Detail |
|-----------|--------|
| **Role** | Infrastructure engineer deploying and maintaining deployed systems |
| **Technical level** | High |
| **Frequency** | One-time deployment, periodic upgrades |
| **Devices** | SSH + browser |
| **Critical needs** | Single Docker image deployment, documented port/protocol requirements, TLS configuration, LDAP/OAuth integration roadmap |
| **Frustrations** | Complex multi-service setups, undocumented port requirements, proprietary hardware dependencies |

### 2.5 Referring Physician

| Attribute | Detail |
|-----------|--------|
| **Role** | Non-radiologist physician reviewing images and reports for patient care |
| **Technical level** | Low |
| **Frequency** | Occasional, per-patient referral |
| **Devices** | Browser (desktop or mobile), no specialized hardware |
| **Critical needs** | One-click access via share link, no login, basic viewer (scroll, WW/WL, zoom), reasonable load time on mobile |
| **Frustrations** | Multiple PACS logins, proprietary viewers requiring Java/ActiveX, slow loading on hospital WiFi |

### 2.6 Super Admin / System Integrator

| Attribute | Detail |
|-----------|--------|
| **Role** | Deploys QuantumPACS, configures storage backends, integrates with EHR/RIS |
| **Technical level** | High — PACS integration experience, REST APIs |
| **Frequency** | One-time setup, periodic reconfiguration |
| **Devices** | SSH, API client (curl/Postman), browser |
| **Critical needs** | REST API documentation, DICOM conformance statement, webhook/notification hooks, multi-site replication configuration |
| **Frustrations** | Undocumented edge cases, breaking changes between versions, migration complexity |

---

## 3. Interaction Flows (End-to-End)

### Flow 1: Study Acquisition (C-STORE Push)

```
Modality ──C-STORE──▶ DICOM Listener :11112
                         │
                         ├── Parse DICOM metadata (stop_before_pixels)
                         ├── SHA-256 hash (dedup)
                         ├── Upsert patient/study/series into PostgreSQL
                         ├── Copy file data to master storage backend
                         ├── INSERT into files + replica_files tables
                         ├── Index into Elasticsearch (async via sync daemon)
                         └── Return 0x0000 (Success)
                              │
                              ▼
                    Technologist sees study in search
                    within < 5 seconds
```

**UI States**:
- Technologist on Files page: hits refresh or re-search, new study appears in table
- No explicit upload progress bar — C-STORE is modality-initiated

### Flow 2: Study Search & Navigation

```
User lands on Files page (/)
  │
  ├── URL state is parsed from query string
  ├── GET /api/files with search params
  ├── ES search returns matching studies
  │
  ├── [Global search] Type in search box → URL updates → auto-fetch
  ├── [Column filter] Click column filter → Enter text → Search/Reset
  ├── [Advanced search] Click "Advanced" → Modal with 12+ DICOM fields
  │
  ├── Results table renders with highlighted search terms
  ├── Click row → navigate to /files/:id
  ├── Click Patient ID → navigate to /patients/:patient_db_id
  │
  └── Pagination / sorting / URL history all preserved
```

**Edge Cases**:
- Empty search returns 10 most recent studies
- ES unavailable → empty results, user notified via empty table
- Invalid search URL → gracefully defaults to match-all
- Network error → `message.error()` toast

### Flow 3: Image Viewing & Annotation

```
Detail page (/files/:id) — Image tab
  │
  ├── Cornerstone3D initializes (lazy, once globally)
  │     ├── @cornerstonejs/core
  │     ├── @cornerstonejs/tools (10 tools registered)
  │     └── dicom-image-loader with auth header
  │
  ├── Viewport renders DICOM via wadouri: URL
  │     ├── Stack viewport (scrolling)
  │     ├── Zoom/WW/WC overlaid on bottom corners
  │     └── 200ms delay → restore persisted tool state
  │
  ├── Tool bar (14 buttons):
  │     ├── Rotate (90° CW)
  │     ├── Horizontal flip / Vertical flip
  │     ├── Invert colors
  │     ├── Pan tool (default left-click)
  │     ├── Zoom (middle-click)
  │     ├── Window/Level (right-click)
  │     ├── Length measurement
  │     ├── Angle measurement
  │     ├── Arrow annotation
  │     ├── Rectangle ROI
  │     ├── Ellipse ROI
  │     ├── Eraser
  │     ├── Save annotations (persist to server)
  │     ├── Clear all annotations
  │     └── Download raw DICOM
  │
  ├── Annotation sync via WebSocket:
  │     ├── Every 500ms, dirty annotations are broadcast
  │     └── Other open viewer sessions receive state
  │
  ├── Series navigation:
  │     └── Slider (when series has >1 file) → prev/next file
  │
  └── Breadcrumb dropdowns:
        ├── Switch studies
        ├── Switch series
        └── Switch files
```

**UI States**:
| State | Display | Duration |
|-------|---------|----------|
| Loading initial | Blank viewport with spinner | < 2s target |
| Tool active | Cursor changes, button highlighted | Until tool deactivated |
| Annotation save | Brief spinner on Save button | < 500ms |
| WebSocket sync | No visible indicator (background) | Continuous |
| Error | `message.error('Failed to initialize viewer')` | Until dismissed |
| Empty file | Viewer blank, no error | Perpetual |

### Flow 4: Patient Browsing

```
Patient page (/patients/:id)
  │
  ├── GET /api/patients/:id
  ├── Patient info table (Patient ID, Name, Sex, DOB)
  │
  └── Ant DirectoryTree (3-level):
        Study <id> (<desc>)
          └── Series <num> (<modality>)
                └── File <name> (leaf, clickable → /files/:fileId)
```

**Empty State**: If patient has no studies, the tree area is blank (no "No studies found" message).
**Loading State**: Table shows spinner, tree area is empty.
**Error State**: Toast with error message.

### Flow 5: File Sharing

```
Share tab on Detail page
  │
  ├── User enters duration in hours (InputNumber)
  ├── Clicks "Share" → POST /api/files/:id/share
  │
  ├── [Success] Key returned → Modal appears with link
  │     ├── Link format: <current_url>?key=<64-char-hex>
  │     └── "Copy" button (execCommand)
  │
  └── [Error] message.error('Share failed')
```

**Recipient Flow**:
```
Recipient opens link → App reads ?key= from URL
  → localStorage.setItem('tempKey', key)
  → ProtectedRoute passes (tempKey is truthy)
  → Sidebar hidden (tempKey mode)
  → Detail page renders with Image tab only
  → Auth middleware checks key against shared_files table
  → Expired share → 401 → redirect to /login
```

### Flow 6: File Metadata Editing

```
Data tab on Detail page
  │
  ├── Table shows key-value pairs from DICOM metadata
  ├── Search/filter metadata keys
  ├── Click value → inline Input appears (if field is editable)
  ├── Enter/blur → PATCH /api/files/:id with {tag: {key, value}}
  └── Change logged to file_changes table
```

**Note**: Currently no fields are marked editable (`editableFields = []`). The infrastructure is in place but gated.

### Flow 7: File Deletion (Admin)

```
Admin tab on Detail page
  │
  ├── Single red "Delete" button (no confirmation dialog)
  ├── Loading: button shows "Deleting..." (disabled)
  ├── DELETE /api/files/:id
  ├── 1-second delay (sleep)
  └── Navigate to /
```

**Risk**: No confirmation dialog — immediate deletion on click.

### Flow 8: User Management (Admin)

```
Users page (/users)
  │
  ├── Table: ID, Username, Role (ADMIN/USER tag), Status (ACTIVE tag), Actions
  │
  ├── [Add user] → Modal with username + admin checkbox
  │     └── On create → Modal shows generated password
  │
  ├── [Reset password] → POST /api/users/new_password
  │     └── Modal shows new password (click to dismiss)
  │
  └── [Deactivate] → Popconfirm → POST /api/users/deactivate
```

### Flow 9: Replica Management (Admin)

```
Replicas page (/replicas)
  │
  ├── Auto-refreshing table (2-second poll)
  ├── Columns: ID, Type, Master/Replica tag, Location, Delay, Status, Files, Actions
  │
  ├── [Add replica] → Modal:
  │     ├── Type: Local (path), S3 (region + key/secret), B2 (app key ID + key)
  │     └── Delay in minutes
  │
  ├── [Update delay] → Modal with InputNumber
  ├── [Set master] → PATCH /api/replicas/:id with {master: true}
  └── [Delete] → Popconfirm → DELETE /api/replicas/:id
```

### Flow 10: System Logs (Admin)

```
Logs page (/logs)
  │
  ├── Paginated table: Time (UTC), Log (last 2 lines)
  ├── Expandable rows: full log text
  └── Server-side sorting
```

### Flow 11: Password Change

```
Account page (/account)
  │
  ├── Form: New password (twice, must match)
  ├── POST /api/change_password
  └── Success/error toast
```

### Flow 12: Logout

```
Sidebar → Logout button
  ├── POST /api/logout (fire-and-forget)
  ├── Clear localStorage (userId, admin, token)
  └── Navigate to /login
```

---

## 4. Design System & Component States

### 4.1 Theme Tokens

| Token | Value | Usage |
|-------|-------|-------|
| `colorPrimary` | `#0077B6` | Buttons, links, active states |
| `colorInfo` | `#6366F1` | Info badges, secondary accents |
| `colorSuccess` | `#10B981` | Status OK, success toasts |
| `colorWarning` | `#F59E0B` | Warnings, pending states |
| `colorError` | `#EF4444` | Errors, delete buttons |
| `colorBgLayout` | `#F8FAFC` | Page background |
| `colorText` | `#1E293B` | Body text |
| `borderRadius` | `6px` | Components |
| `fontFamily` | Inter (with system fallbacks) | All text |

### 4.2 Component State Matrix

| Component | Loading | Empty | Error | Success | Edge Case |
|-----------|---------|-------|-------|---------|-----------|
| Search table (Files) | Ant Table spinner | 0 rows, total=0 | Toast | Rows with highlighted text | ES down → 0 rows |
| Patient tree | Table spinner only | Tree area blank | Toast | Full hierarchy | No studies → blank |
| DICOM viewer | Spinner | N/A | Toast + blank viewport | Full rendering | Single-instance stack |
| Metadata table | N/A | "no data" | Toast | Rows | Empty file.meta → no rows |
| Share dialog | Button spinner | N/A | Toast | Copy link modal | Expired share → 401 |
| Change log (Changes) | Table spinner | Empty rows | Toast | Rows | N/A |
| File admin (delete) | "Deleting..." disabled | N/A | Toast | Redirect to / | No confirmation dialog |
| User table | Table spinner | Empty rows | Toast | Rows | N/A |
| Replica table | Table spinner + 2s poll | Empty rows | Toast | Rows with status tags | Network partition → stale data |
| Logs table | Table spinner | Empty rows | Toast | Rows | N/A |
| Login form | "Sign In" spinner | N/A | Toast | Redirect to / | Wrong password → toast |
| Account form | Button spinner | N/A | Toast | Green toast | N/A |

### 4.3 Toast Behavior

| Type | Color | Duration | Dismiss |
|------|-------|----------|---------|
| Success | Green | 3s | Auto + manual |
| Error | Red | 5s | Auto + manual |
| Info | Blue | 3s | Auto + manual |

### 4.4 Responsive Breakpoints

| Breakpoint | Width | Behavior |
|------------|-------|----------|
| `xs` | < 576px | Sidebar collapased, table padding reduced |
| `sm` | 576px+ | Sidebar collapsed, pagination items=5 |
| `md` | 768px+ | Full sidebar, normal padding |
| `lg` | 992px+ | Sidebar visible with trigger |
| `xl` | 1200px+ | Optimal viewing layout |

---

## 5. Accessibility

### Current State

| Criteria | Status | Details |
|----------|--------|---------|
| Semantic HTML | Partial | Ant Design components provide basic ARIA |
| Keyboard navigation | Partial | Tools use button elements, table sorting/selection via keyboard |
| Screen reader | Limited | No explicit aria-labels on custom viewer controls |
| Focus management | Limited | Login form auto-focuses username |
| Color contrast | Passes | Brand colors meet WCAG AA (contrast ≥ 4.5:1) |
| Motion sensitivity | No preference | No `prefers-reduced-motion` handling |

### Target (v2.1)

- WCAG 2.1 AA compliance for all non-viewer UI
- Alt-text for all icons and tool buttons
- Focus rings on all interactive elements
- `prefers-reduced-motion` disables animation
- Screen reader announcements for study load state

---

## 6. Onboarding & Help

### Current State

- **Login page**: Shows branding and version tagline
- **No guided tour**: Users expected to be PACS-literate
- **No contextual help**: No tooltips beyond browser defaults
- **Self-describing UI**: Icons + labels on sidebar, tab labels, button text

### Target (v2.1)

- First-login tour (3-step overlay: search, viewer, sharing)
- Tooltip descriptions on all viewer toolbar buttons
- Keyboard shortcut reference (`?` key)
- Inline help link → docs.quantumpacs.ai

---

## 7. Internationalization

### Current State

- **Locale**: English only
- **Date/times**: UTC display in logs and change history
- **No RTL support**

### Target (v2.2)

- i18next integration
- Locale detection from browser `Accept-Language`
- Initial support: English, Spanish, French, German, Japanese
- DICOM tag values displayed in original encoding (not translated)

---

## 8. Performance Budgets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Time to first image | ≤ 2s (LAN), ≤ 5s (WAN) | Playwright timing |
| Search results | ≤ 500ms for 10k studies | API response timer |
| Page transition (Files → Detail) | ≤ 1s | React component mount |
| Annotation persist | ≤ 500ms | Network timing |
| WebSocket broadcast latency | ≤ 200ms | Application-level timer |
| Bundle size (initial) | ≤ 500 KB gzipped | Vite bundle analysis |
| Time to interactive | ≤ 3s | Lighthouse |

---

## 9. Non-Functional Requirements

| Requirement | Specification |
|-------------|---------------|
| Concurrent users | ≥ 50 simultaneous viewer sessions |
| Max study size | ≥ 10,000 instances per study |
| Uptime | ≥ 99.9% (excluding planned maintenance) |
| Browser support | Chrome 100+, Firefox 100+, Safari 15+, Edge 100+ |
| Network latency tolerance | Up to 500ms RTT between API and DB |
| Storage scalability | Horizontally via pluggable backends |
| Backup RPO | ≤ 24 hours (configurable) |
| Disaster recovery | Replica promotion from any storage backend |
