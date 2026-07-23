# Backend Requirements: Existing UI Screens

## Context

Documenting the data needs of all existing QuantumPACS frontend screens to provide a complete reference for backend developers. The system is already implemented — this document describes the current data contracts from the frontend's perspective. Use this as a starting point for any refactoring, API versioning, or backend changes.

**Who uses it**: All authenticated PACS users (technologists, radiologists, admins, referring physicians via share links)

---

## Screens/Components

---

### Login Page (`/login`)

**Purpose**: Authenticate users and establish a session.

**Data I need to display**:
- Branding/logo (QuantumPACS with gradient logo)
- Version tagline ("v1.0 — Diagnostic Clarity, Quantum Fast")
- No data from backend until login succeeds

**Actions**:
- Submit username + password → receive auth token, user ID, admin flag
- On success: store token, userId, admin flag in localStorage → redirect to `/`
- On failure: show error message (red toast)

**States to handle**:
- **Loading**: Button shows spinner, inputs disabled
- **Error**: Red toast with error description
- **Success**: Redirect away (no success message needed)
- **Already logged in**: If localStorage has valid token + userId, redirect to `/`

**Business rules affecting UI**:
- No login page for share-link users — they bypass auth entirely
- Deactivated users should get a 401 with clear message (not "invalid credentials")
- Token expiry not checked client-side — rely on 401 responses

---

### Files/Search Page (`/`)

**Purpose**: Search, browse, and navigate to studies. The main landing page after login.

**Data I need to display**:

For each study result in the table:
- File/study ID (clickable → `/files/:id`)
- Patient ID (clickable → `/patients/:patient_db_id`)
- Patient's Name (with search term highlighting)
- Study ID (with highlighting)
- Study Description (with highlighting)
- Series Number (with highlighting)
- Series Description (with highlighting)
- Modality

Additionally:
- Total result count for pagination
- Current page, page size, sort field and direction

**Actions**:
- Global search: free-text query → filtered results
- Column-specific filter: search within one column
- Advanced search: 12+ DICOM tag fields with custom add/remove
- Row click → navigate to `/files/:id`
- Patient ID click → navigate to `/patients/:patient_db_id`
- Pagination: page navigation, page size change
- Sorting: click column header, toggle asc/desc
- Row selection: checkbox to select multiple rows
- Bulk download ZIP: selected file IDs → download archive
- Bulk download CSV: selected file IDs → metadata export
- Upload button → open upload modal (admin only)
- All search state encoded in URL (bookmarkable, back-button friendly)

**States to handle**:
- **Loading**: Table spinner (Ant Table built-in)
- **Empty (no results)**: Table with 0 rows, pagination total=0
- **Empty (no search)**: Show 10 most recent studies
- **Error**: Red toast on API failure
- **ES unavailable**: Empty results (graceful degradation, no error toast)
- **Loading more**: Pagination spinner during page change
- **Search in progress**: Table spinner during search execution

**Business rules affecting UI**:
- Search is the primary data access pattern — no pre-loaded study list
- URL drives state (query string JSON) — initial load reads URL params
- Global search and column filter are mutually exclusive (one clears the other)
- Advanced search and global search are also mutually exclusive
- Upload button only visible for admin users
- Bulk download disabled when no rows selected
- Pagination limit adjusts on mobile breakpoint (reduced via sidebar collapse)
- Search terms highlighted in yellow across relevant columns

---

### Upload Modal (child of Files page)

**Purpose**: Upload DICOM files through the browser.

**Data I need to display**:
- Upload status for each file (uploading, done, error)

**Actions**:
- Select files via file picker (multiple)
- Select directory via directory picker
- Upload triggers POST with multipart file data
- On complete: uploaded file removed from upload list
- On error: file stays in list with error indicator

**States to handle**:
- **Empty**: No files selected
- **Uploading**: Progress indicator per file
- **Done**: File removed from visible list
- **Error**: File stays visible with error state
- **Directory upload**: No visible file list (hidden by CSS)

**Business rules affecting UI**:
- Files are processed server-side identically to C-STORE
- Non-DICOM files silently skipped server-side
- Upload endpoint requires auth (admin in practice)

---

### Advanced Search Modal (child of Files page)

**Purpose**: Multi-field DICOM tag search for precise queries.

**Data I need to display**:
- 12 predefined field rows: Patient ID, Patient's Name, Patient's Age, Patient's Gender, Study ID, Study Description, Series Number, Series Modality, Series Description, Referring Physician, Performing Physician, SOP Class UID
- Custom field rows (user-added): label + value inputs

**Actions**:
- Edit label/value for each field
- Add custom field row
- Remove custom field row (predefined rows are fixed)
- Submit → execute search with all field criteria

**States to handle**:
- **Open/closed**: Modal visibility controlled by parent
- **Default**: 12 predefined rows, no custom rows
- **Custom added**: Extra rows with remove buttons
- **Search submitted**: Modal closes, parent executes search

**Business rules affecting UI**:
- Predefined rows cannot be removed
- All criteria are ANDed (study must match ALL specified fields)
- Submitting clears any active global search

---

### Patient Page (`/patients/:id`)

**Purpose**: View patient demographics and browse study/series hierarchy.

**Data I need to display**:

Patient info table:
- Patient ID
- Patient Name
- Patient Sex
- Patient Birth Date

Study tree (three levels):
- Studies → Series → Files
- Each study node shows: `<study_id> (<description>)` or just `<study_id>` if no description
- Each series node shows: `<number> (<modality>)` with optional description
- File nodes are leaf nodes (clickable)

**Actions**:
- Click file leaf node → navigate to `/files/:fileId`
- Expand/collapse study and series nodes
- Page loaded via URL param `:id` (patient DB ID)

**States to handle**:
- **Loading**: Table shows spinner, tree area is blank
- **Empty (no studies)**: Table populated, tree area is blank (no "no studies" message)
- **Not found (404)**: Error toast, redirect to `/`
- **Error**: Error toast on API failure

**Business rules affecting UI**:
- Patient is looked up by database ID, not DICOM PatientID
- Tree is fetched as nested data (patient → studies → series → files) in one API call
- Non-leaf nodes not clickable (only expand/collapse)
- Descriptions wrapped in parentheses when present

---

### Detail Page (`/files/:id`)

**Purpose**: View DICOM images, metadata, manage sharing, and review audit trail. The most complex page in the application.

**Data I need to display**:

The full file record with nested patient/study/series tree:
- Current file ID, name, metadata
- Patient info (name, ID) for breadcrumb
- Full study list for this patient (for breadcrumb dropdown)
- Full series list for current study (for breadcrumb dropdown)
- All files in current series (for series slider navigation)
- File metadata key-value pairs (all DICOM tags)
- Change history entries
- Share link status
- Tools_state (persisted annotation state)

**Five tabs** (conditional):
1. **Image** — Always visible. The Cornerstone3D viewer.
2. **Data** — Always visible. Editable metadata table.
3. **Share** — Hidden when accessed via tempKey (share link mode).
4. **Changes** — Hidden when accessed via tempKey.
5. **Admin** — Hidden when accessed via tempKey AND only visible for admin users.

**Actions**:
- Image tab: View, scroll, measure, annotate, rotate/flip/invert, save annotations, download raw DICOM
- Data tab: Filter metadata keys, inline edit values
- Share tab: Enter duration (hours), generate share link, copy to clipboard
- Changes tab: Browse paginated change history
- Admin tab: Delete file (no confirmation)
- Breadcrumb: Switch studies via dropdown, switch series via dropdown, switch files via dropdown
- Series navigation: Slider to navigate between files in current series

**States to handle**:
- **Loading**: Fetching file data (loading boolean)
- **Not found (404)**: Error toast "File not found", redirect to `/`
- **Error**: "File fail to load" toast
- **Viewer loading**: Cornerstone3D initializing (spinner)
- **Viewer error**: "Failed to initialize viewer" toast
- **Annotation saving**: Brief loading state on save button
- **Share created**: Modal with share link + copy button
- **Share error**: "Share failed" toast
- **Changes loading**: Table pagination spinner
- **Delete loading**: "Deleting..." on button, then redirect after 1s delay
- **Delete error**: "Deletion failed" toast
- **Delete via share link**: Admin tab not available at all

**Business rules affecting UI**:
- Share link users (tempKey) see ONLY the Image tab
- Non-admin users without tempKey see Image, Data, Share, Changes tabs
- Admin users see all 5 tabs
- Cornerstone3D uses a global singleton for the rendering engine
- Tools are registered once globally (lazy init in viewer)
- WebSocket annotation sync requires a separate 1-minute token
- Annotations are persisted via PATCH, not automatically saved
- File deletion has NO confirmation dialog (intentional design — high-risk)
- Breadcrumb only visible on Image tab and when patient data loaded
- Series navigation slider only appears when series has >1 file
- Metadata table has NO editable fields currently (`editableFields = []`)
- WebSocket sync interval is 500ms
- Viewer uses `wadouri:` image loader with auth header

---

### Image Viewer (CornerstoneElement, child of Detail)

**Purpose**: Render DICOM images with diagnostic tools and annotation sync.

**Data I need to display**:
- DICOM image rendered in Cornerstone3D viewport
- Zoom level overlay (bottom-left)
- Window width/center overlay (bottom-right)
- Tool state (persisted annotations from `tools_state`)
- Series file slider (when multiple files in series)
- Toolbar with 14 action buttons

**Actions**:
- Scroll through image stacks (mouse wheel)
- Adjust window/level (right-click drag)
- Pan (left-click drag, default)
- Zoom (middle-click drag)
- Measure: Length, Angle, Rectangle ROI, Ellipse ROI
- Annotate: Arrow annotations
- Erase annotations
- Rotate 90° CW
- Horizontal/vertical flip
- Invert colors
- Save annotations to server
- Clear all annotations
- Download raw DICOM file
- Navigate series via slider
- Real-time annotation sync via WebSocket

**States to handle**:
- **Initializing**: Cornerstone3D libraries loading (first-time)
- **Loading image**: Viewport showing loader
- **Rendered**: Image visible, tools ready
- **Tool active**: Button highlighted, cursor changed
- **Annotation dirty**: Unsaved annotations (auto-sync via WS, manual persist for server save)
- **Persisting**: Save button loading
- **Persisted**: Server save complete
- **WebSocket connected**: Annotations syncing in background
- **WebSocket disconnected**: Annotations still work locally, sync resumes on reconnect
- **Error**: Viewer initialization failed

**Business rules affecting UI**:
- RenderingEngine is a global singleton (one engine for the whole app)
- ToolGroup uses specific mouse bindings: left=Pan (passive), middle=Zoom, right=WW/WL
- Active annotation tools override left-click from Pan
- Annotation state versioned and sent via WebSocket every 500ms if dirty
- On mount, sends `open` message to WS to subscribe to file updates
- On WebSocket open, existing state is pushed to new subscriber
- `tools_state` is a JSONB blob — format is Cornerstone3D's internal annotation state
- The `beforeSend` callback for dicom-image-loader attaches the auth header
- Viewer uses a `key` prop hack to force re-mount for Cornerstone3D re-initialization

---

### Account Page (`/account`)

**Purpose**: Change own password.

**Data I need to display**:
- Password form (two fields: new password + confirm)

**Actions**:
- Submit new password → POST to change endpoint
- Client-side validation: passwords must match

**States to handle**:
- **Loading**: Button shows spinner
- **Success**: Green success toast
- **Error**: Red error toast

**Business rules affecting UI**:
- Only own password can be changed (not other users')
- No "current password" field required — session token is sufficient
- Password policy enforced server-side (PBKDF2, 600k iterations)

---

### Users Page (`/users`) — Admin only

**Purpose**: Manage user accounts.

**Data I need to display**:

For each user in the table:
- ID (sortable)
- Username (sortable)
- Role: "ADMIN" (green tag) or "USER" (blue tag) based on admin flag
- Status: "ACTIVE" (green tag) or deactivated state (gray tag)
- Action buttons: Reset password, Deactivate (only for active users)

**Actions**:
- Add user: Open modal → enter username + admin toggle → create → show generated password
- Reset password: Generate new password → show in modal
- Deactivate: Popconfirm → POST deactivate → reload table
- Pagination and sorting

**States to handle**:
- **Loading**: Table spinner
- **Empty**: No users (unlikely, at minimum admin exists)
- **Error**: Error toast
- **Add user modal**: Open/closed, form validation
- **Password shown**: Modal with generated password (shown once)
- **Deactivate confirm**: Popconfirm visible

**Business rules affecting UI**:
- Only visible to admin users (sidebar menu condition)
- Cannot deactivate self (assumed — confirm with backend)
- New user passwords are randomly generated (12-char alphanumeric)
- Deactivated users cannot log in but their data remains
- Username is case-insensitive (CITEXT in DB)

---

### Replicas Page (`/replicas`) — Admin only

**Purpose**: Configure and monitor storage replication.

**Data I need to display**:

For each replica in the table:
- ID (plain text)
- Type (e.g., "local", "s3", "b2")
- Master status: "MASTER" (green tag) or "REPLICA" (blue tag)
- Location (path, region, or bucket name depending on type)
- Delay in minutes
- Status (sortable): "OK" (green tag) or other states
- Files count
- Action buttons: Update delay, Set master, Delete

**Actions**:
- Auto-refresh table every 2 seconds
- Add replica: Modal → select type (Local/S3/B2) → enter type-specific config → set delay → create
- Update delay: Modal with InputNumber for minutes
- Set master: PATCH to promote this replica
- Delete: Popconfirm → DELETE → remove
- Pagination and sorting

**States to handle**:
- **Loading**: Initial table spinner
- **Auto-refreshing**: Table updates every 2s in background
- **Empty**: No replicas configured (new deployment)
- **Error**: Error toast on failure
- **Add modal**: Type-specific form fields (conditional)
  - Local: path input
  - S3: region, access key, secret key
  - B2: app key ID, app key
- **Edit delay modal**: InputNumber for minutes
- **Delete confirm**: Popconfirm

**Business rules affecting UI**:
- Only visible to admin users
- Master status is boolean — only one replica should be master
- Changing master promotes the selected replica and demotes the current one
- Delay configures how long the sync daemon waits before copying to this replica
- Deleting a replica does NOT delete the stored files — just removes from configuration
- Status transitions: indexing → ok (or error on failure)
- Type-specific configuration stored in `meta` JSONB field
- 2-second polling interval for auto-refresh

---

### Logs Page (`/logs`) — Admin only

**Purpose**: View system audit logs.

**Data I need to display**:

For each log entry:
- Time (UTC, formatted via `new Date(data * 1000).toUTCString()`)
- Log text (preview: last 2 lines)
- Full log text on expand

**Actions**:
- Paginate through log entries
- Expand row to see full log text
- Server-side sorting (by time)

**States to handle**:
- **Loading**: Table spinner
- **Empty**: No log entries
- **Error**: Error toast
- **Expanded row**: Shows full log text

**Business rules affecting UI**:
- Only visible to admin users
- Logs are append-only (no delete from UI)
- Timestamps are in seconds (Unix epoch) — multiplied by 1000 for JS Date
- No search/filter capability (plain table)
- Server-side pagination

---

### Not Found Page (`*` catch-all)

**Purpose**: Display when no route matches.

**Data I need to display**:
- "Oops! Page not found" heading
- "Go to home page" link

**Actions**:
- Click link → navigate to `/`

**States to handle**:
- Always the same — static content

**Business rules affecting UI**:
- No auth required
- No API calls

---

### Sidebar (global navigation)

**Purpose**: Navigate between sections. Conditionally hidden for share-link users.

**Data I need to display**:
- Active section highlighted
- Submenu open state for admin section

**Menu items:
- Files (all authenticated users) — icon: FileSearchOutlined
- Account (all authenticated users) — icon: UserOutlined
- Admin submenu (admin only) — icon: LockOutlined
  - Replicas — icon: DatabaseOutlined
  - Users — icon: TeamOutlined
  - Logs — icon: AlignLeftOutlined
- Logout (all authenticated users) — icon: LogoutOutlined

**Actions**:
- Click menu item → navigate to route
- Collapse sidebar (responsive: disappears on mobile breakpoint)
- Logout → POST /api/logout → clear localStorage → redirect to `/login`

**States to handle**:
- **Collapsed**: Icons only, labels hidden (Ant Sider built-in)
- **Mobile (breakpoint lg)**: `collapsedWidth=0` — sidebar fully hidden
- **Share-link mode**: Sidebar hidden entirely (no navigation needed)
- **Admin section open**: Submenu expanded
- **Active item**: Current route highlighted

**Business rules affecting UI**:
- Admin menu items only visible when `isAdmin()` returns true (localStorage `admin === 'true'`)
- Logout clears all localStorage auth keys
- Sidebar hidden when `tempKey` exists in localStorage
- On mobile breakpoint, also reduces pagination limit to 5 items
- Active key derived from URL path (first segment or "files" for `/`)

---

### Share Link Mode (cross-cutting)

**Purpose**: Allow referring physicians to view studies without authentication.

**Data I need to display**:
- Full viewer (Image tab only)
- No sidebar
- No other tabs (Data, Share, Changes, Admin all hidden)

**Actions**:
- All viewer actions available (scroll, measure, annotate, etc.)
- Annotation persistence NOT available (no save to server)
- No file sharing, no audit trail viewing, no deletion

**States to handle**:
- **Valid share key**: Viewer loads, tempKey in localStorage
- **Expired share key**: 401 response, redirect to `/login`
- **Deleted file**: 404 response, redirect to `/`

**Business rules affecting UI**:
- Share key is a 64-char hex string stored as `tempKey` in localStorage
- Extracted from `?key=` URL parameter on initial page load
- `ProtectedRoute` checks `tempKey` as alternative to `userId` for auth
- Server-side auth middleware checks key against `shared_files` table
- Share link mode disables ALL server-side mutations (no saves, no deletes, no shares)

---

### Client-Side State (cross-cutting)

**Data stored in localStorage**:
| Key | Source | Purpose |
|-----|--------|---------|
| `userId` | Login response | Auth check in ProtectedRoute |
| `admin` | Login response | Admin menu visibility, tab visibility |
| `token` | Login response | X-Auth-Pacs header on all requests |
| `tempKey` | URL `?key=` param | Share link auth bypass |

**Custom hooks available**:
- `useFetch(url, options)` — returns `{exec, loading, showLoading, data, error, controller}`
  - Executes fetch with auth headers
  - Handles 401 by redirecting to `/login`
  - `showLoading` has 300ms delay (avoid flash for fast responses)
  - Supports abort controller for cancellation
- `useFormInput(initialState)` — controlled input state management
- `usePrevious(value)` — previous value tracking

**HTTP layer**:
- `request(url, options)` — core fetch wrapper
  - Prepends `API_URL` to relative paths
  - Attaches `X-Auth-Pacs` header (token or tempKey fallback)
  - Handles JSON encoding/decoding
  - On 401: navigates to `/login`
  - Abort errors (code 20) silently ignored
- `open(url)` — fetches download token then opens download URL
- `isAdmin()` — reads `admin` from localStorage

---

## Uncertainties

- [ ] What determines the exact ES search query structure? Does the frontend pass raw query params that are forwarded to ES?
- [ ] The files endpoint accepts both GET and POST — what's the difference? Is POST for complex queries that exceed URL length limits?
- [ ] How does the tools_state format map to Cornerstone3D's internal annotation format? Is there a versioning contract?
- [ ] What happens if tools_state gets too large (>1MB) for the PATCH endpoint? Is there a size limit?
- [ ] How are pagination `total` values calculated? Is it exact or approximate (for ES performance)?
- [ ] What's the exact format of the search state JSON in the URL? The `?` prefix + JSON encoding is opaque to backend.
- [ ] How does the WebSocket token endpoint relate to the main auth token? Is it always a separate 1-minute token?
- [ ] The "logout" endpoint seems to exist but what does it actually do server-side? Tokens are stateless JWTs.

## Questions for Backend

- Would it make sense to add read-access audit logging (who viewed which study, when)? Currently only mutations are logged.
- Should the empty search (no query) return most recent N studies, or should there be a configurable default?
- Is there a simpler way to handle the share link auth flow? Currently it uses a separate tempKey flow that bypasses normal auth.
- Should we formalize the URL search state format instead of the current opaque JSON encoding?
- The `editableFields` list is currently empty — which metadata fields should be user-editable, and what business rules apply?

## Discussion Log

*To be filled as backend responds.*
