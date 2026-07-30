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
- Counts per status tab (All, Scheduled, Performed, Cancelled)
- List of station AE titles for the filter dropdown (unique values from entries or configuration)

**Actions**:
- Filter by status tab — show entries matching selected status
- Filter by station AE title — show entries for a specific modality/device
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

**Business rules affecting UI**:
- Entry status constrained to: `scheduled`, `performed`, `cancelled`
- Auto-status-transition: when C-STORE receives a study with matching accession, status → `performed`, study UID + performed at timestamp populated
- Status transitions may be one-way — cannot re-perform or un-cancel
- Max 1000 results for C-FIND MWL queries by modalities
- Station AE titles may come from configuration, not just existing entries
- Accession number should be unique — duplicate check on create
- Editing may need to notify modalities that have already queried the entry

## Uncertainties

- [ ] Can a performed entry be re-opened or re-scheduled?
- [ ] What happens when an entry is edited after a modality has already queried it?
- [ ] Should cancelled entries be visible indefinitely or auto-cleaned?
- [ ] Does the station AE filter show only entries with that AE, or all entries where the field is empty too?
- [ ] How does the auto-match work when multiple entries share the same accession?

## Questions for Backend

- Is there an endpoint to get the distinct station AE titles, or should I derive them from entries?
- For the calendar view, should I request entries for a date range or the full list?
- What fields are editable on an existing entry vs. read-only after creation?
- When batch-marking as performed, should I provide a study UID or is it auto-generated?
- Should I support filtering by date range in addition to status and station AE?
- Is there a way to detect that a study has arrived for a scheduled entry (to auto-refresh status)?

## Discussion Log

*No discussions yet — waiting for backend feedback.*