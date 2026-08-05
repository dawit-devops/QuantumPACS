# Backend Requirements: Worklist

## Context

The Worklist page at `/worklist` is used by Technologists (primary) and PACS Admins. It manages the Modality Worklist (MWL) — scheduled imaging procedures that modalities query via DICOM C-FIND and that technologists manage manually.

**Personas**: Technologist (primary), PACS Admin, Modalities (C-FIND MWL)

## Screens/Components

### Worklist Table/Calendar View

**Purpose**: Display scheduled imaging procedures with the ability to filter, create, edit, and batch-process entries.

**Data I need to display**:
- Worklist entry list with status badges
- Per entry: patient name, patient ID, accession number, requested procedure ID, procedure description, modality, station AE title, scheduled date/time, status (scheduled / performed / cancelled), study UID (if performed), performed at timestamp
- Counts per status tab (All, Scheduled, Performed, Cancelled) — currently computed from the current page's rows (see Uncertainties)
- List of station AE titles for the filter dropdown (fetched up front, merged with values seen in the current results)

**Actions**:
- Filter by status tab — show entries matching selected status
- Filter by station AE title — show entries for a specific modality/device
- Free-text search (debounced ~300 ms) — one search term across patient/study fields
- Filter by date range — show entries scheduled within the selected start/end dates
- Toggle between table view and calendar view
- Select one or more entries → batch mark as performed, batch cancel
- Edit individual entry: modify patient info, procedure details, scheduled time
- Mark entry as performed (when study has been completed/uploaded)
- Cancel entry (when procedure is cancelled)
- Create new entry: fill patient demographics, procedure details, modality, station

**States to handle**:
- **Empty**: "No scheduled procedures" message when no entries match current filters
- **Loading**: Skeleton or spinner while fetching entry list
- **Error**: Failed to load entries — show retry option
- **Batch selection**: Selection toolbar appears with action count when rows are selected
- **Calendar view**: Days with entries highlighted, entries shown per day
- **Create/edit modal**: Form validation, modality picker, station AE input
- **Status transition feedback**: Optimistic update with confirmation toast
- **Special**: Entries with no scheduled date group under "Unscheduled" in the calendar view; cancelled entries are excluded from batch selection; create/edit modal offers a modality picker, sex M/F/O, and free-text station AE with known-station suggestions

**Business rules affecting UI**:
- Entry status constrained to: `scheduled`, `performed`, `cancelled`
- Auto-status-transition: when C-STORE receives a study with matching accession, status → `performed`, study UID + performed at timestamp populated
- Status transitions may be one-way — cannot re-perform or un-cancel
- Max 1000 results for C-FIND MWL queries by modalities
- Station AE titles may come from configuration, not just existing entries
- Accession number should be unique — duplicate check on create
- Editing may need to notify modalities that have already queried the entry
- Only scheduled entries expose mark-performed / cancel; performed entries are read-only and show their performed-at timestamp
- Cancelled entries cannot be selected for batch operations

## Uncertainties

- [ ] Can a performed entry be re-opened or re-scheduled?
- [ ] What happens when an entry is edited after a modality has already queried it?
- [ ] Should cancelled entries be visible indefinitely or auto-cleaned?
- [ ] Does the station AE filter show only entries with that AE, or all entries where the field is empty too?
- [ ] How does the auto-match work when multiple entries share the same accession?
- [ ] Is the station AE list authoritative (configuration) or derived? The UI merges a fetched list with values seen in results.
- [ ] Tab badges count entries on the current page only — with server-side pagination they'll be wrong for large datasets. Can the API return true per-status totals?
- [ ] Batch mark-performed / cancel are fired as one request per row; partial failures are swallowed and the UI reports success. Is a batch operation warranted?
- [ ] The cancel action is sent as a delete — I'm assuming it maps to a soft status transition since cancelled rows remain visible.
- [ ] Which fields does the free-text search cover (name, patient ID, accession, procedure)? I send one term and let the backend decide.

## Questions for Backend

- I fetch a station AE title list and merge it with values seen in entries — is that fetched list authoritative or config-driven?
- For the calendar view, should I request entries for a date range or the full list?
- What fields are editable on an existing entry vs. read-only after creation?
- When batch-marking as performed, should I provide a study UID or is it auto-generated?
- Date-range filtering is already implemented via query params — confirm it's server-side and doesn't need client-side filtering.
- Is there a way to detect that a study has arrived for a scheduled entry (to auto-refresh status)?

## Discussion Log

*No discussions yet — waiting for backend feedback.*