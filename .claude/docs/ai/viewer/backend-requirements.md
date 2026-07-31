# Backend Requirements: Detail/Viewer Page

## Context

The Detail/Viewer page at `/files/{id}` is the core diagnostic interface. Used primarily by Radiologists (daily power users) and Clinicians (reviewers). Includes Cornerstone3D DICOM viewer, tabs for metadata/data, share functionality, audit trail, and measurement panel.

**Personas**: Radiologist (primary daily use), Clinician (review), Technologist (verification)

## Screens/Components

### Viewer Tab (Image)

**Purpose**: Render DICOM images in Cornerstone3D viewport with full toolset for diagnosis

**Data I need to display**:
- DICOM image pixel data for rendering in Cornerstone3D
- Multi-frame/stack of images in a series (thumbnail strip navigation)
- Current series total image count and position
- Patient name, ID for overlay
- Study description, series number for context

**Actions**:
- Load and render DICOM images in Cornerstone3D viewport
- Navigate between instances in a series (scroll, arrow keys, thumbnail click)
- Switch tools: Pan, Zoom, WW/WL, Length, Angle, Arrow, Rectangle ROI, Ellipse ROI, Eraser
- Apply viewer controls: Rotate 90°, Flip H/V, Invert
- Save annotations → persist to server
- Clear all annotations
- Fullscreen toggle
- Keyboard shortcuts for all tools

**States to handle**:
- Loading: spinner/progress bar while image loads
- Progressive loading: low-res first, then full quality
- Error: viewport shows error overlay if image can't load
- Empty: no file/instance found
- Annotation loading: restoring saved tools_state
- Multi-instance: thumbnail strip + scroll navigation
- Mobile: floating bottom toolbar

**Business rules affecting UI**:
- Image loading via WADO URI or DICOMweb WADO-RS
- Annotations persisted to tools_state JSONB column
- WebSocket broadcasts annotation state changes to other viewers
- 200ms delay on mount before restoring tool state (hack for cornerstone init)
- Keyboard shortcuts disabled when input/textarea focused

### Data Tab (Metadata)

**Purpose**: Display all DICOM metadata as key-value pairs

**Data I need to display**:
- Full DICOM tag list from the file's metadata (thousands of tags possible)
- Each tag: group, element, tag name, value
- Searchable/filterable by tag name or value
- Paginated (20 items per page currently)

**Actions**:
- Browse/search through DICOM tags
- Edit specific tags (if FILE_WRITE permission)

**States to handle**:
- Loading: spinner
- Empty: no metadata available
- Paginated: large result sets
- Search: filter by tag name

### Share Tab

**Purpose**: Create secure share links for referring physicians

**Data I need to display**:
- List of existing share links for this file (if any)
- Each link: creation date, expiration, status (active/expired)
- Shareable URL

**Actions**:
- Create new share link with configurable duration (hours)
- Copy share link to clipboard
- Revoke existing share link
- View share link status

**States to handle**:
- No existing shares: empty state with create action
- Active shares: list with copy/revoke
- Expired shares: show as expired
- Loading/error during creation

**Business rules affecting UI**:
- Share key = 64-char hex string
- Duration configurable at creation
- Expired links return 401
- Share-key mode: viewer-only (Image tab only, no other tabs, no download, no sidebar)
- Requires FILE_WRITE to create shares

### Changes Tab (Audit Trail)

**Purpose**: View audit trail for this file

**Data I need to display**:
- Chronological list of events for this file
- Each event: timestamp (UTC), user who performed it, event type, description
- Event types: read, download, annotations changed, tag edits
- Paginated list

**Actions**:
- Browse through audit events
- No create/edit (read-only)

**States to handle**:
- Empty: no events recorded
- Loading: spinner
- Paginated: large result sets

### Measurement Panel

**Purpose**: Side panel listing all annotations on current image

**Data I need to display**:
- List of all saved annotations for the current file
- Per annotation: type (Length, Angle, Arrow, ROI), value (cm, degrees, area, mean/SD), series number
- Active state when annotation is focused

**Actions**:
- Click annotation → center viewport on that annotation
- Delete annotation from panel
- Export all measurements as CSV

**States to handle**:
- No annotations: empty state
- Panel collapsed: badge count on toggle button
- Panel expanded: full list
- Annotation focused: highlight in both panel and viewport

**Business rules affecting UI**:
- Annotations parsed from the same tools_state that Cornerstone3D uses
- focusAnnotationUID pattern: set UID → viewer centers on it → clear after 100ms
- CSV export is client-side (no server needed)

## Uncertainties

- [ ] Does the WADO-RS endpoint support progressive/lossy image loading (low-res first)?
- [ ] Are share links per-file or per-study? Current UI shows per-file but comment suggests per-study.
- [ ] Should I support saving partial annotations or only full tools_state replacement?
- [ ] For multi-frame DICOM, is each frame a separate file or is it one file with multiple frames?

## Questions for Backend

- What's the preferred image loading path — wadouri direct or WADO-RS?
- Does the backend support multi-frame DICOM? How are frames addressed?
- For the Data tab, is there a search endpoint for DICOM tags, or should I filter client-side?
- Can I share a link to a specific series within a study, or only the entire study?
- What happens when I save annotations while another user is viewing the same file?
- Is there a way to get a signed URL for direct image access (for progressive loading)?

## Discussion Log
