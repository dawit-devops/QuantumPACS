# QuantumPACS Component Specifications

> States, variants, and behavior for every UI component.

| Component | Variants | States | Key Tokens |
|-----------|----------|--------|-----------|
| **Login** | Default | idle, validating, submitting, error | `--login-gradient-*`, `--color-primary` |
| **Sidebar** | Collapsed, Expanded | idle, hover, selected, active | `--sidebar-*` |
| **Files Table** | Empty, Populated, Filtered | loading, empty, populated, filtered, error | `--table-radius`, `--table-highlight-bg` |
| **File Detail / Viewer** | Loading, Loaded, Error | loading, loaded, error, no-series | `--card-radius` |
| **Admin Files** | Empty, Populated | loading, empty, populated | `--card-radius` |
| **Search Bar** | Default, Active, Filtered | idle, focused, typing, filtered-active | `--border-color`, `--color-primary` |

---

## 1. Login

```
┌─────────────────────────────────┐
│   [QuantumPACS Logo]           │
│   ─────────────────────         │
│   Username  [____________]      │
│   Password  [____________]      │
│   [ SIGN IN ]                  │
│   ─────────────────────         │
│   © 2026 OpenPACS              │
└─────────────────────────────────┘
```

**Behavior:**
- On submit → POST `/api/login` with `{username, password}`
- Success → store JWT in localStorage, redirect to `/files`
- Error → inline error message, shake animation on button

**States:**

| State | Visual | Behavior |
|-------|--------|----------|
| idle | Clean form, "Sign In" enabled | — |
| validating | Fields highlight green/red on blur | Validate non-empty |
| submitting | Button shows spinner, disabled | POST in flight |
| error | red message "Invalid credentials" below form, fields shake | Enable form again |

---

## 2. Sidebar

```
┌──────────┬──────────────────────┐
│ [Logo]   │  (collapsed: hidden) │
│ ≡        │  Toggle button       │
│ 📁 Files │  Icon + label        │
│ ⚙️ Admin │  Icon + label        │
│ 🚪 Logout│  Icon + label        │
│          │                      │
│ ───────  │  User info footer    │
│ 👤 user  │                      │
└──────────┴──────────────────────┘
```

**Behavior:**
- Collapsible via trigger button at top
- Menu items navigate via `react-router-dom` `useNavigate`
- Logout clears JWT and redirects to `/login`
- Admin item visible only for `role != 'admin'` → hidden
- Collapsed state persists in localStorage

**States:**

| State | Collapsed W | Expanded W | Notes |
|-------|-------------|------------|-------|
| idle | 80px | 220px | Default |
| hover (item) | bg highlight | bg highlight | Token: `--sidebar-selected-bg` |
| selected (item) | blue indicator | blue indicator + bold label | Matches `window.location.pathname` |
| collapsed | icons only | — | Labels hidden, tooltip on hover |

---

## 3. Files Table

```
┌──────────────────────────────────────────────┐
│ [Search...                    ] [Upload ▼]   │
├──────┬────────┬────────┬──────┬──────────────┤
│ ✓    │ Name   │ Modality│ Size│ Date        │
├──────┼────────┼────────┼──────┼──────────────┤
│ ☐    │ ────── │ CT     │ 2MB  │ 2026-07-23  │
│ ☐    │ ────── │ MR     │ 4MB  │ 2026-07-22  │
│ ☐    │ ────── │ DX     │ 1MB  │ 2026-07-21  │
└──────┴────────┴────────┴──────┴──────────────┘
│                         [1] [2] [3] [...]    │
└──────────────────────────────────────────────┘
```

**Columns:** checkbox | patient name | patient ID | modality | study description | study date | instances | actions

**Behavior:**
- Paginated (default 20 per page)
- Search filters client-side with debounce (300ms)
- Checkbox + header checkbox for batch select
- Click row → navigate to `/files/:id`
- Upload button → POST `/api/files/upload`
- `highlightStyle` on search match uses `--table-highlight-bg` (#ffc069)

**States:**

| State | Table | Search | Notes |
|-------|-------|--------|-------|
| loading | Skeleton rows (5) | Disabled | `Spin` overlay |
| empty | "No files found" illustration | Enabled | Empty state with upload CTA |
| populated | Data rows | Enabled | — |
| filtered | Filtered rows | Active search icon (blue) | `SearchOutlined` color `--color-blue-500` |
| error | Error Alert banner | Enabled | Retry button |

---

## 4. File Detail / Viewer

```
┌──────────────────────────────────────────────┐
│ ← Back to Files    Patient: DOE^JOHN        │
├──────────────────────┬───────────────────────┤
│                      │  Series Metadata      │
│  [Cornerstone3D      │  ┌─────────────────┐  │
│   Viewport]          │  │ Series │ Mod │ # │  │
│                      │  ├─────────────────┤  │
│                      │  │ T2 Axial │ MR │24│  │
│                      │  │ T1 Sag   │ MR │18│  │
│                      │  └─────────────────┘  │
│                      │                       │
│  ── Toolbar ──       │  Instance Table       │
│  [WW/WL] [Zoom]      │  ┌──────┬──────────┐  │
│  [Pan] [Reset]       │  │ #    │ Location │  │
│                      │  ├──────┼──────────┤  │
│                      │  │ 1/24 │ -12.5mm  │  │
│                      │  │ 2/24 │ -10.0mm  │  │
│                      │  └──────┴──────────┘  │
└──────────────────────┴───────────────────────┘
```

**Behavior:**
- Fetches study metadata + series on mount
- Cornerstone3D viewport renders DICOM via WADO URI
- Series list click → load new series in viewport
- Toolbar: window/level, zoom, pan, reset viewport
- Keyboard shortcuts: arrow keys navigate instances, scroll wheel zooms
- Responsive: viewport stacks above metadata on mobile (<600px)

**States:**

| State | Viewport | Series List | Instance Table |
|-------|----------|-------------|----------------|
| loading | Skeleton rectangle | Skeleton rows | Skeleton rows |
| loaded | DICOM image rendered | Series listed | Current instance highlighted |
| error | "Unable to load" icon | Disabled | Empty |
| no-series | "No series found" | Empty message | Hidden |

---

## 5. Admin Files

```
┌──────────────────────────────────────────────┐
│ Admin: File Management                        │
│                                               │
│ [ Upload Directory ]  [ ▼ Bulk Actions ]     │
│                                               │
│ ┌── Filter ──────────────────────────────┐   │
│ │ Modality: [All ▼]  Status: [All ▼]     │   │
│ └─────────────────────────────────────────┘   │
│                                               │
│ [Data Table with ALL files across users]      │
│ ── columns: checkbox, name, user, modality,   │
│    size, uploaded, status, [delete]           │
│                                               │
│ Pagination: [1][2][3]...[10]                  │
└──────────────────────────────────────────────┘
```

**Behavior:**
- Admin-only route (`/admin/files`) — redirect to `/files` if non-admin
- Shows all files across all users (admin privilege)
- Upload directory button triggers `<input type="file" webkitdirectory>`
- Bulk actions: delete selected, change status
- Filter by modality, status, date range

**States:**

| State | Table | Filters | Upload |
|-------|-------|---------|--------|
| loading | Skeleton | Disabled | Disabled |
| empty | "No files uploaded yet" | Enabled | Enabled |
| populated | Data rows | Enabled | Enabled |
| uploading | Progress bar above table | Disabled | Hidden upload list |

---

## 6. Search Bar

```
┌─────────────────────────────────┐
│ 🔍 Search patients, studies…   │
└─────────────────────────────────┘
```

Used within the Files page header panel.

**Behavior:**
- Debounced input (300ms) triggers filter
- Search icon turns blue when filter active
- Clear button appears when text present
- Highlight matches in table cells via `highlightStyle`

**States:**

| State | Icon | Input | Clear | Table |
|-------|------|-------|-------|-------|
| idle | gray search | placeholder | hidden | full data |
| focused | gray search | cursor blink | hidden | full data |
| typing | gray search | filter text | visible | filtered |
| filtered-active | blue search | filter text | visible | filtered + highlighted |
