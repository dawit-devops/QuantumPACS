# Backend Requirements: Metrics Dashboard

## Context
System-wide statistics and health dashboard at `/metrics`. Used by PACS Admins (primary) and Technologists. Shows stat cards, system health, modality distribution, component latency, ingestion trend, and latest files. Has time range selector and auto-refresh toggle.

## Screens/Components

### Stat Cards (6 cards in a row)
**Purpose**: Show cumulative system-wide totals at a glance

**Data I need to display**:
- Patient count — total patients in system
- Study count — total studies
- Series count — total series
- File count — total DICOM files
- User count — registered user accounts
- Storage — total storage used (bytes); I format as B/KB/MB/GB/TB on the frontend

**Actions**:
- User changes time range → does this affect totals? (currently assumed yes, all refetch on range change)
- User toggles auto-refresh → poll interval starts/stops at 30s

**States to handle**:
- **Loading**: Skeleton cards displayed with pulse animation
- **Empty**: Zeros shown for all counters (plausible for fresh system)
- **Error**: PageState shows error message with Retry button
- **Special**: Counter animation from previous to current value over 800ms — needs numeric values, not pre-formatted strings

**Business rules affecting UI**:
- Time range may or may not affect totals — unclear from current implementation
- Storage is displayed frontend-formatted; raw bytes preferred

### System Health Panel
**Purpose**: Per-component status indicators for operational awareness

**Data I need to display**:
- List of system components — currently: database, elasticsearch, redis, storage, dicom_listener, ingestion_service
- For each component: status string and latency_ms number
- Status values I handle: `ok` → green checkmark, `degraded` → orange warning, anything else → red close-circle

**Actions**:
- None — informational panel only, refreshes on same cadence as rest of dashboard

**States to handle**:
- **Loading**: Panel shows skeleton
- **Empty**: If components object is empty or absent, shows a single green "OK" tag (assumes all-clear)
- **Error**: If health endpoint fails entirely (404/500/network), the whole health fetch resolves to null via `.catch(() => null)` and the panel shows the all-clear fallback — this may be wrong
- **Special**: Unknown component keys are mapped to human-readable names via frontend label map; if backend adds new components without frontend knowing, raw key is shown

### Modality Distribution (vertical bar chart)
**Purpose**: Count of studies grouped by imaging modality

**Data I need to display**:
- Mapping of modality labels to study counts — currently `{ CT: 15, MR: 10, XA: 8 }`
- Labels are displayed as-is (CT, MR, XA); unclear if these are DICOM codes or display names

**Actions**:
- None — static chart, updates on refresh

**States to handle**:
- **Loading**: Skeleton shown
- **Empty**: Empty object → empty chart with no bars (acceptable)
- **Error**: Handled by parent PageState

**Business rules affecting UI**:
- Time range: currently `range` parameter is sent with the request; unclear if modality counts should be time-filtered or cumulative
- Top 5 modality colors are assigned from an array; if more than 5, colors repeat

### Component Latency (horizontal bar chart)
**Purpose**: Response latency per system component

**Data I need to display**:
- Component names x-axis, latency in ms y-axis (bar length)
- Bar color derived from component status: ok=green, degraded=amber, error=red

**Actions**:
- None — visualization only

**States to handle**:
- **Loading**: Skeleton shown
- **Empty**: If no components, shows green "OK" tag (same as health panel fallback)
- **Error**: Parent PageState

### Ingestion Trend (30-day line chart)
**Purpose**: Number of studies ingested per day over trailing period

**Data I need to display**:
- Array of `{ date, count }` objects for each day in the period
- Dates plotted on x-axis, counts on y-axis as a filled line

**Actions**:
- User changes time range → likely changes which data is returned (e.g., 7d would show 7 data points)

**States to handle**:
- **Loading**: Skeleton shown
- **Empty**: Empty array → no line rendered (acceptable, shows blank chart area)
- **Error**: Parent PageState
- **Special**: Time range selector currently affects the metrics request — ingestion data may be the only section actually affected, but the entire metrics response is refetched

### Latest Files Table
**Purpose**: Quick-glance list of most recently ingested files

**Data I need to display**:
- File ID, filename (`name`), and creation timestamp (`created`)
- No pagination; shows all items returned (unlimited — if backend returns many, frontend shows all)

**Actions**:
- None — informational table, no row click actions

**States to handle**:
- **Loading**: Skeleton shown
- **Empty**: Empty table with "No data" message (Ant Design default)
- **Error**: Parent PageState

## Data Relationship Summary

Currently two parallel requests:
1. `v2/dashboard/metrics?range={timeRange}` → totals, modalities, ingestion_30d, latest_files
2. `v2/health` → status, components with status + latency_ms

Time range affects request 1; auto-refresh at 30s fires both requests.

## Uncertainties
- [ ] Are stat card totals cumulative (all-time) or scoped to the selected time range? Currently I assume they are scoped, since they're fetched with the `range` param, but "Users" being time-ranged doesn't make sense.
- [ ] Is component latency measured in ms? Currently I use field `latency_ms` — is this always ms or could it be in a different unit?
- [ ] Does the time range actually affect all sections of the metrics response, or is it just for the ingestion data? Refetching everything on range change works but may be wasteful.
- [ ] How often is `storage_bytes` updated? Is it real-time or periodically recalculated?
- [ ] What status values can a health component return beyond "ok" and "degraded"? I treat anything else as "error" — is that correct?
- [ ] Are modality labels DICOM standard codes (CT, MR, etc.) or should they be display names (Computed Tomography, Magnetic Resonance)?
- [ ] Does ingestion data include today's partial count, or only completed days?
- [ ] Should the latest files table be limited to a specific number (e.g., top 10), or is the current unlimited approach fine?
- [ ] What happens if a component is missing from the health response (e.g., elasticsearch is down and not reported)?

## Questions for Backend
- Can the dashboard data come in a single request, or are two separate endpoints intentional? Open to either.
- Are new components likely to be added to the health response without warning? Should I dynamically handle unknown components?
- Is there a way to get historical component latency for charting trends over time, or is current-snapshot only?
- Should the time range selector be global across all panels, or should certain panels (e.g., stat totals) always show all-time data regardless of the selector?
- Would it make sense to paginate the latest files table? If so, what's a reasonable default limit?

## Discussion Log

*Initial document created based on current frontend implementation at `frontend/src/metrics/Metrics.tsx`.*
