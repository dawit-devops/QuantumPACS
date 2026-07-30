# Backend Requirements: Study List (Files Page)

## Context

The Study List (aka Files page) is the main landing page at `/`. Used by Radiologists (primary), Technologists, Clinicians, and PACS Admins to find and access studies. This is a search-heavy interface.

Current frontend implementation:
- Global search bar (Input.Search) that triggers search via URL query params
- Column filter dropdowns on each table column (patient ID, name, study ID, description, series number, description)
- Advanced Search modal with 12 DICOM tag fields (Patient ID, Name, Age, Gender, Study ID, Study Description, Series Number, Series Modality, Series Description, Referring Physician, Performing Physician, SOP Class UID)
- Table with columns: ID (link → detail), Patient ID (link → patient), Patient Name, Study ID, Study Description, Series Number, Series Description
- Row selection for bulk download (ZIP + CSV)
- Pagination via server (pageSize from config)
- Mobile view: cards instead of table
- Upload button → AdminFiles modal
- Search state encoded in URL as JSON (bookmarkable)
- DICOMweb QIDO-RS fallback when ES unavailable
- Empty state: "No files match your search" or "No files uploaded"

## Screens/Components

### Data Table / Search Results

**Purpose**: Display paginated list of DICOM studies matching the current search/filter criteria. Primary interface for navigating to study detail and patient pages.

**Data I need to display per row**:
- Unique file/study identifier (linkable to detail page)
- Patient identifier (linkable to patient page)
- Patient name
- Study identifier / Study UID
- Study description
- Series number
- Series description
- Modality (for tag display on mobile cards)
- Creation/upload date
- Patient database ID (for patient page link)

**Actions**:
- Click row → navigate to study detail page
- Click patient ID / name → navigate to patient page
- Select multiple rows → bulk download as ZIP or CSV
- Trigger refresh of results
- Navigate between pages of results

**States to handle**:
- Loading: Skeleton rows or spinner while fetching
- Empty (no studies exist): "No files uploaded" message, upload CTA
- Empty (no results match): "No files match your search" message, suggestion to broaden filters
- Error: Network failure or server error with retry button
- Results transition: Show "Showing X-Y of Z results" count
- Mobile: Card layout instead of table

**Business rules affecting UI**:
- URL-encoded search/filter state determines results — page must be bookmarkable
- Page size is configurable (server-side default, frontend reads from config)
- Download button requires `FILE_READ` or `FILE_DOWNLOAD` permission
- Upload button requires `FILE_WRITE` permission
- Search must degrade gracefully when Elasticsearch is unavailable (fallback to DB/DICOMweb QIDO-RS)

### Global Search Bar

**Purpose**: Free-text search bar at the top of the page for quick searching across multiple fields.

**Data I need to display**:
- Input with search icon
- Current search query reflected in URL

**Actions**:
- Type query → URL updates with encoded search params → results reload
- Clear search → reset to default results

**States to handle**:
- Empty (no query): Shows default results (all accessible studies, paginated)
- Loading: Spinner or debounce indicator
- Error: Toast notification if search fails

**Business rules affecting UI**:
- Search query encoded in URL as JSON for bookmarkability
- Global search scope must be defined (which fields does it search across?)

### Column Filters

**Purpose**: Per-column dropdown filters on patient ID, name, study ID, description, series number, series description.

**Data I need to display**:
- Filter icon/indicator on active column filters
- Dropdown with filter input
- Current filter values reflected in URL

**Actions**:
- Set column filter value → URL updates → results reload
- Clear column filter → URL updates → results reload
- Clear all filters → reset to default results

**States to handle**:
- Active (filter applied): Column header shows filter indicator
- Inactive (no filter): Clean column header
- Loading: Spinner while filters are applied

**Business rules affecting UI**:
- Column filters should compose with global search and advanced search
- All filter state encoded in URL

### Advanced Search Modal

**Purpose**: Modal with 12 DICOM tag fields for precise multi-field search.

**Data I need to display**:
- Input fields: Patient ID, Name, Age, Gender, Study ID, Study Description, Series Number, Series Modality, Series Description, Referring Physician, Performing Physician, SOP Class UID
- Current filter values reflected in modal when opened from a filtered state

**Actions**:
- Fill fields → apply → URL updates → results reload → modal closes
- Clear all → reset filters → results reload
- Close modal without applying

**States to handle**:
- Empty: All fields blank
- Filled: Some fields have values (restore from current search state when reopening)
- Loading: Spinner while saving/applying

**Business rules affecting UI**:
- All 12 fields may not always be available depending on data source (DB vs DICOMweb)
- Advanced search overrides or composes with column filters
- All search/filter state encoded in URL for bookmarkability

### Upload Modal (AdminFiles)

**Purpose**: Upload new DICOM files to the system.

**Data I need to display**:
- File upload area / drag-and-drop zone
- Upload progress indicator
- Success/error per file

**Actions**:
- Select files → upload → show progress → refresh results on completion
- Cancel upload

**States to handle**:
- Empty: Upload area with drag-and-drop prompt
- Uploading: Progress bar per file or overall
- Success: Notification, list refreshes
- Error: Error message per file with retry option

**Business rules affecting UI**:
- Requires `FILE_WRITE` permission to show upload button
- Upload button only visible to authorized users

## Uncertainties

- Does the search index include all DICOM tags or just specific fields?
- Is the global search a full-text search across multiple fields or a specific single-field search?
- Should I show study count in the UI ("143 studies found")?
- Is there a limit on how many results can be returned?
- How do column filters work — exact match, substring, or prefix search?
- Do column filters apply AND or OR logic when combined with global search?

## Questions for Backend

- What fields are searchable in the global search vs. per-column vs. advanced search?
- How does pagination work — cursor-based or offset-based?
- Can I get a total count of results for the "X-Y of Z" display?
- Should I expect DICOMweb QIDO-RS results to have the same fields as ES/DB results?
- For the advanced search, are all 12 DICOM fields always available, or does it depend on the data source?
- Mobile card view needs modality tag and description — are these always populated?
- What is the exact response format for a search result row? Can we have a shared type/schema?
- How is tenant isolation handled in search queries — does the backend filter by tenant automatically or does the frontend need to pass a tenant ID?
- What's the default sort order when no sort is specified?
- Are there any rate limits or max result page constraints?

## Discussion Log

