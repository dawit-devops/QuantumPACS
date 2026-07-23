# Backend Requirements: DICOM Modality Worklist (MWL) SCP

## Context

We're adding a DICOM Modality Worklist (MWL) SCP to QuantumPACS. This allows modalities (CT, MR, XA, etc.) to query a worklist of scheduled procedures via DICOM C-FIND MWL (SOP Class UID 1.2.840.10008.5.1.4.31), and allows admins and technologists to manage those worklist entries through the web UI.

Currently, technologists must manually enter patient demographics at the modality console for each exam. MWL eliminates this by letting the modality pull scheduled procedures from the PACS, reducing data entry errors and exam delays.

**Who uses it:**
- **Modalities (CT, MR, etc.)** — pull worklist via DICOM C-FIND MWL
- **PACS Admins** — create/edit/delete worklist entries, manage modality AETs, view connection status
- **Technologists** — view scheduled procedures, mark as performed, see modality match status

**What success looks like:**
- A CT modality can query the worklist by date, modality, patient ID, or accession number and receive matching DICOM MWL responses
- An admin can create a worklist entry with full patient demographics and scheduled procedure details via the web UI
- Worklist entries track whether they've been performed (matched to a received study)
- Modality connection status is visible in the admin panel
- The system logs all MWL queries for audit

---

## Screens/Components

### Worklist Entry List Page (Admin + Technologist)

**Purpose**: Main table view of all scheduled procedures. Users can search, filter, and navigate to detail/edit views.

**Data I need to display**:
- **Scheduled station AET** — which modality is supposed to perform the exam
- **Modality** — CT, MR, XA, etc.
- **Scheduled date/time** — when the procedure is scheduled (date + start time + optional end time)
- **Patient demographics**: patient ID, patient name, birth date, sex
- **Accession number** — unique order identifier from the RIS/HIS
- **Requested procedure description** — name of the requested exam (e.g., "CT CHEST W/CONTRAST")
- **Requesting physician** — name of ordering/referring physician
- **Status** — whether this entry is `scheduled`, `in_progress` (modality has queried it but not yet sent images), `performed` (images received and matched), or `cancelled`
- **Matched study ID** — if performed, which study in the system was matched (link to existing study)
- **Matched patient ID** — internal patient DB ID if the entry linked to an existing patient record
- **Created/updated timestamps** — for audit
- **Who created/modified** the entry (user reference)
- **Total count** of results for pagination

**Actions**:
- **Filter by**: modality, status, station AET, date range (scheduled date), free-text search across patient name/ID/accession number
- **Sort by**: any column (scheduled date, patient name, status, created)
- **Page** through results with configurable page size
- **Click a row** → navigate to the worklist entry detail view
- **"Add entry" button** (admin only) → opens create form modal
- **Bulk operations** (admin only): select multiple entries, mark as cancelled, delete

**States to handle**:
- **Loading**: Skeleton/spinner while fetching worklist data, especially on initial load
- **Empty**: "No scheduled procedures found" with a prompt to create one (admin) or adjust filters. Distinguish between "no entries at all" vs "no entries matching filters"
- **Error**: Backend unavailable, permission denied (non-admin tries admin actions). Show error message with retry option
- **Special**: An entry may be linked to a study that has since been deleted — show the link as broken/missing rather than crashing
- **Partial match**: Entry is `in_progress` (modality queried it but no images yet). Could indicate a stalled exam

**Business rules affecting UI**:
- Only admins can create, edit, or delete entries. Technologists can view and mark as performed
- Once marked `performed`, an entry should be read-only except for admin override
- An entry should not be deletable if it has a matched study (admin must unlink first)
- Status transitions: `scheduled` → `in_progress` (automatic when modality queries) → `performed` (automatic when images received, or manual) → `cancelled` (admin only)
- Filtering by status should default to show `scheduled` and `in_progress` entries (hiding performed/cancelled unless explicitly requested)

---

### Create/Edit Worklist Entry Form (Admin only)

**Purpose**: Modal form for creating a new scheduled procedure or editing an existing one.

**Data I need to display**:
- **Patient section**:
  - Patient ID (required)
  - Patient name (required, DICOM PN format — `Last^First^Middle^Suffix`)
  - Patient birth date (date picker)
  - Patient sex (dropdown: M, F, O)
  - Option to search and link to an existing patient in the system (by patient ID or name search) — this pre-fills demographics
- **Requested procedure section**:
  - Accession number (required, unique across active entries)
  - Requested procedure ID (optional, for RIS integration)
  - Requested procedure description (required, free text)
  - Requesting physician (free text)
  - Referring physician (free text, optional)
  - Reason for the requested procedure (optional)
- **Scheduling section**:
  - Scheduled station AET (required, free text or dropdown populated from known modalities)
  - Modality (required, dropdown: CT, MR, XA, US, CR, MG, NM, PET, etc.)
  - Scheduled date (date picker, required)
  - Scheduled start time (time picker, required)
  - Scheduled end time (time picker, optional — some modalities compute duration)
  - Scheduled performing physician (optional)
  - Scheduled procedure step ID (optional, auto-generated if not provided)
- **Entry status**: default `scheduled`; only shown in edit mode
- **Metadata**: optional free-form notes/instructions for the technologist

**Actions**:
- **Search existing patient** → lookup by patient ID or name, auto-fill demographics if found
- **Save / Create** → validates required fields (patient ID, name, accession number, station AET, modality, date/time), submits to backend
- **Cancel** → closes modal without saving
- **On edit**: "Delete entry" button with confirmation (admin only)

**States to handle**:
- **Loading**: Fetching data for edit mode (populating form from existing entry); fetching patient search results
- **Validation errors**: Inline field errors for missing/ malformed data. Server-side validation errors returned as modal-level error message
- **Duplicate accession number**: Backend reject with message "Accession number already in use"
- **Conflict**: Entry was updated by another user since the form was opened (optimistic locking — show a warning and let user reload)
- **Save success**: Modal closes, table refreshes, success toast notification
- **Save failure**: Server error, network error — keep modal open, show error
- **Patient not found**: For patient search returning no results, allow manual entry of demographics

**Business rules affecting UI**:
- Accession number must be unique across active (non-cancelled, non-performed) entries
- Editing a `performed` entry is blocked for non-admins; admin sees a confirmation warning
- Deleting an entry that has a matched study should be blocked or require forced confirmation
- Scheduled date/time should be in the future by default, but allow past dates (for back-filling)
- Station AET could be free-text or selected from a known list — let backend suggest where to store the known AET list

---

### Worklist Entry Detail View

**Purpose**: Read-only view of a single worklist entry with full detail and matched study information.

**Data I need to display**:
- All fields from the create/edit form, displayed as labeled values
- **Status timeline**: history of status changes with timestamps (e.g., `scheduled` → `in_progress` at 2026-07-23 09:15:00 → `performed` at 2026-07-23 09:45:00)
- **Matched study info** (if performed):
  - Study UID
  - Study description
  - Modality
  - Number of series / instances received
  - Date received
  - Link to the study detail page in the PACS (navigate to `/files/{id}` or `/patients/{id}`)
- **Matched patient info** (if linked): link to patient detail page
- **DICOM MWL query history**: list of recent C-FIND requests by modalities for this entry — timestamp, calling AET, matched/returned
- **Audit log**: who created, who last modified, timestamps
- **Notes / instructions** for the technologist

**Actions**:
- **Edit** (admin) → opens the edit form modal pre-populated
- **Mark as performed manually** (technologist/admin) → when a study was received but auto-matching failed, or for manual override
- **Mark as cancelled** (admin) → soft-deletes from worklist
- **Print worklist entry** (browser print) → printer-friendly format for physical filing
- **Link to existing study** (admin) → manually link this entry to a study that was already received (search study by accession number or patient/date)

**States to handle**:
- **Loading**: Fetching full detail including status history and matched study
- **Not found**: Entry was deleted between list and detail view — show "Entry not found" with link back to list
- **Orphaned match**: Study referenced by this entry no longer exists — show "Study deleted" with warning
- **Partial data**: Some optional fields may be empty — do not show the field row rather than showing blank labels

**Business rules affecting UI**:
- The `in_progress` status is set automatically by the DICOM MWL SCP when a modality queries this entry — it's not a UI action
- Manual mark-as-performed should include a note field explaining why (audit trail)
- Linking to an existing study should verify the study's patient ID matches this entry's patient ID

---

### Modality Connection Status Panel (Admin only)

**Purpose**: Dashboard panel showing currently connected modalities, recent MWL queries, and overall MWL service health.

**Data I need to display**:
- **MWL SCP service status**: running/stopped indicator
- **Known modality AETs**: a list of AET titles that have recently queried the worklist, with:
  - AET title
  - Last query timestamp
  - Number of queries in the last 24h / 7d
  - Number of studies received from this AET in the same period
  - Current connection status (connected/disconnected if we can track TCP connections)
- **Recent MWL queries**: timestamp, calling AET, query parameters (patient ID, accession number, date range, modality), number of matches returned, response time
- **Failed queries**: C-FIND requests that returned errors (e.g., malformed query, unsupported filter) — for debugging modality configuration issues
- **Overall query volume**: simple chart or count of MWL queries per hour/day

**Actions**:
- **Filter recent queries**: by AET, date range, success/failure
- **Paginate through query history**
- **Test MWL connection**: button to simulate a C-FIND MWL query from the server to a given AET (for troubleshooting)
- **Export query log**: download recent MWL query audit trail as CSV

**States to handle**:
- **Loading**: Initial data fetch for queries and AET list
- **Empty**: No modalities have queried the worklist yet (first deployment) — show setup instructions
- **Error**: Cannot determine SCP status, or DB is unreachable
- **No recent queries**: Show "No queries in the last 24 hours" rather than an empty table

**Business rules affecting UI**:
- This panel may need a WebSocket or polling mechanism to show live-ish status (like the replicas page does with 2s polling)
- Modality AET data is derived from query logs, not a separate registration — an AET appears here once it makes its first query
- The query log should be pruned periodically (configurable retention) — indicate if/when pruning last ran

---

### Integrated Patient/Study Lookup

**Purpose**: When creating/editing a worklist entry, being able to search and link to existing patients and studies reduces duplicate data entry.

**Data I need to display**:
- **Patient search results**: matched patient ID, name, birth date, sex, number of existing studies
- **Patient detail summary** (on select): demographics confirmed, list of recent studies for that patient

**Actions**:
- **Search patients** by patient ID or name (partial match) → returns top results
- **Select a patient** → auto-fills the worklist entry's patient demographics section
- **Look up existing study** by accession number (for manual matching on detail view)

**States to handle**:
- **Loading**: Searching (debounced on input)
- **No results**: Patient not found in the system — proceed with manual entry
- **Multiple matches**: Show list, let user pick the right one
- **Error**: Search backend unavailable — allow manual entry

**Business rules affecting UI**:
- Patient search should query the `patients` table, not require Elasticsearch (graceful degradation)
- Auto-fill from existing patient can save the backend from creating a duplicate patient record when the study arrives

---

### Sidebar / Navigation Updates

**Purpose**: Add MWL-related navigation to the admin submenu and potentially a dedicated top-level menu item for technologists.

**Data I need**:
- Permissions: whether to show "Worklist" in the sidebar at all
- For admins: entry under the Admin submenu ("Worklist") + a "Modality Status" entry
- For technologists (non-admin): a top-level menu item "Worklist" that shows the entry list page (read-only + mark as performed)

**Actions**:
- **Navigate to /worklist** → worklist entry list page
- **Navigate to /worklist/modalities** → modality connection status panel (admin only)
- **Navigate to /worklist/{id}** → entry detail view

**States to handle**:
- **No permission**: Non-admin cannot see admin-only MWL pages (handled by backend auth, but frontend should hide the nav items)

**Business rules affecting UI**:
- Technologists see only the worklist entry list (no create/edit/delete, no modality status)
- Admins see both
- Add icons: `ScheduleOutlined` or `CalendarOutlined` for the worklist

---

## Uncertainties

- [ ] Not sure how `in_progress` status should be set — does the DICOM MWL C-FIND response include a flag we can use? Or should we infer `in_progress` when a modality queries an entry and then images arrive later?
- [ ] Don't understand if the backend can detect a modality disconnecting (TCP connection drop) or if we only track query timestamps
- [ ] Not sure about matching logic for performed entries — should auto-matching happen by accession number only, or by patient + date + modality? What if accession number isn't provided by the modality in C-STORE?
- [ ] Guessing that station AET will always be provided by the modality in the C-FIND request — is that correct?
- [ ] Not sure if we should allow linking a worklist entry to a study that was received *before* the entry was created (back-filling use case)
- [ ] Don't know how scheduled procedure step ID should be generated — auto-increment? UUID? RIS-provided?
- [ ] Uncertain about the known AET list — should it be a separate admin-managed table, or derived from query logs?
- [ ] Not sure if the MWL SCP should run on the same port as C-STORE (11112) or a different port (e.g., 11113)
- [ ] Don't know if we need to support DICOM MWL C-FIND with modality worklist SOP class only, or also support related query SOP classes

## Questions for Backend

- Would it make sense to store modality AETs as a simple config table that admins can manage, or just derive them from query logs?
- Should auto-performed matching happen at C-STORE time (when study arrives, check if accession number matches a worklist entry) or as a periodic batch job?
- Can the DICOM MWL SCP and C-STORE SCP coexist in the same pynetdicom `AE` instance, or do we need separate servers?
- Is there existing DICOM tag mapping I can reference for the fields that worklist entries need to expose via C-FIND response?
- Should I expect the MWL query log (for the modality status panel) to come from the same DB table as system audit logs, or is there a dedicated MWL query log?
- Does the backend plan to expose the status transition timestamps (status history) as a flat field on the entry, or as a separate array/history endpoint?
- For patient search when creating an entry — should I use the existing patient search mechanism or is a new endpoint planned?
- Is there a simpler way to handle the known modality AET list than maintaining a separate table? Could we use the DICOM C-ECHO verification to auto-discover modalities?

## Discussion Log

*(To be filled after backend review)*
