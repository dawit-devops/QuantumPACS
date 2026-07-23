# Backend Requirements: HL7 v2.x ADT/ORM Message Ingestion

## Context

Hospitals send ADT (Admission/Discharge/Transfer) and ORM (Order) messages via HL7 v2.x over MLLP. We need to ingest these, parse them, and create/update patient records and study/worklist entries in the PACS. Admins need visibility into connection health, message throughput, and parsing errors.

Existing pages to extend:
- **Admin sidebar menu** (`frontend/src/common/Sidebar.tsx`) — add an "HL7" submenu section
- **Patient detail page** (`frontend/src/patient/Patient.tsx`) — show HL7 sync source badge
- **Existing admin patterns** (Replicas, Users, Logs) — use same table/pagination/error patterns

## Screens/Components

### HL7 Dashboard
**Purpose**: At-a-glance status of the HL7 listener and message pipeline. This is the landing page for the HL7 admin section.

**Data I need to display**:
- Connection status indicator (connected / disconnected / error) with color-coded tag (green / red / orange)
- Uptime duration since last connection
- Current listener configuration (port, facility ID, app name)
- Throughput metrics:
  - Total messages received (all time)
  - Messages received today
  - Messages received in the last hour
  - Successful parse rate (percentage)
- Error rate counter (messages with errors in the last 24h)
- Recent activity feed — last 10 messages with timestamp, type, patient ID, status
- A sparkline or simple trend indicator for daily message volume (last 7 days)
- An "alert banner" if the listener has been disconnected for > N seconds or if error rate exceeds a threshold

**Actions**:
- Click a recent message → navigate to full message detail in HL7 Message Log
- Toggle listener start/stop → expect confirmation modal, then status updates in real time
- Navigate to full message log → link to HL7 Message Log screen
- Navigate to connection configuration → link to Connection Config screen

**States to handle**:
- **Loading**: Skeleton cards / spinners while metrics load
- **Empty**: First-run state — "No messages received yet. Waiting for HL7 connection…"
- **Error**: Cannot reach backend / backend reports listener crash — show error banner with reconnect hint
- **Disconnected**: Listener not running — muted status, "Start listener" action visible
- **Reconnecting**: Transient state showing "Reconnecting…" with a pulse animation
- **High error rate**: Warning banner with link to error log

**Business rules affecting UI**:
- Only admin users can start/stop the listener (check `isAdmin()` in existing pattern)
- The dashboard should auto-refresh every 10 seconds (or via WebSocket push) for the status and recent messages
- If error rate > 10% of messages in the last hour, show a warning that persists until dismissed or rate drops

---

### HL7 Message Log
**Purpose**: Searchable, filterable table of all received HL7 messages with parsing outcome. Used for diagnostics and auditing.

**Data I need to display**:
- Table with columns:
  - Timestamp received (human-readable + relative, e.g., "2 min ago")
  - Message type (ADT vs ORM)
  - Event type (A01, A02, A04, O01, etc.)
  - Patient ID (MRN from the message)
  - Patient name
  - Sender / sending facility
  - Parsing status tag: **Success** (green), **Partial** (orange — parsed but some fields failed), **Error** (red — unparseable)
  - Study order ID (for ORM messages only)
- Expandable row showing raw HL7 message text
- Total message count for the current filter

**Filters** (above the table):
- Date range picker (presets: last hour, today, last 7 days, custom)
- Message type dropdown (All / ADT / ORM)
- Status dropdown (All / Success / Partial / Error)
- Patient ID text search (fuzzy match)
- Sending facility dropdown (derived from received messages)
- Event type dropdown (All / A01 / A02 / etc.)

**Actions**:
- Click a row → expand to show raw HL7 message and parsed field map side-by-side
- Click a patient ID → navigate to existing Patient detail page
- Click a study order ID (ORM) → navigate to study/worklist view
- Export filtered results as CSV
- Copy raw message to clipboard

**States to handle**:
- **Loading**: Table skeleton
- **Empty (no filter)**: "No messages yet"
- **Empty (after filter)**: "No messages match your filter"
- **Error**: "Could not load message log" with retry button
- **Partial parse row**: Row has a warning icon; expanded view shows which fields failed and why
- **Very large results**: Pagination with page size control (10/25/50/100), consistent with existing `PAGINATION.limit` pattern
- **Malformed message row**: Row shows red error tag; expanded view shows error details (position in message, unexpected segment/field, raw bytes)

**Business rules affecting UI**:
- Pagination must match existing pattern (`handleTableChange` / `fetch` with `results` and `page` params)
- Raw HL7 messages can be large (>100KB for some ORMs) — the raw content should only load when row is expanded (lazy), not on initial table load
- CSV export should respect current filters, not all data

---

### Patient Sync Status View
**Purpose**: Show which patients were created or updated via HL7, and whether their data is in sync. Integrates into the existing patient management flow.

**Data I need to display**:
- Patient list with sync source badges:
  - **DICOM** (blue) — created via DICOM import (existing behavior)
  - **HL7** (purple) — created via HL7 ADT message
  - **Manual** (gray) — manually entered
  - **Both** (teal) — touched by both HL7 and DICOM
- For HL7-sourced patients:
  - Last HL7 message timestamp
  - Last HL7 message type that updated them
  - Sync status: `in-sync` / `pending-update` / `conflict`
- A toggle/filter to show only HL7-sourced patients

**Actions**:
- Filter by sync source (All / DICOM / HL7 / Manual)
- Click a patient row → navigate to existing Patient detail page
- For `pending-update` or `conflict` patients, show a "Re-sync" action

**States to handle**:
- **Loading**: Skeleton table
- **Empty (no HL7 patients)**: "No patients created via HL7 yet"
- **Conflict**: A patient was modified in both HL7 and DICOM with conflicting fields — surface which fields differ, let admin choose which source wins (or merge manually)

**Business rules affecting UI**:
- The existing `Patient` table schema has `patient_id`, `name`, `birth_date`, `sex`, `meta` (JSONB). The sync source could be stored in `meta` or a new column — frontend just needs a field to read
- `pending-update` status means an HL7 message arrived but the patient record hasn't been updated yet (e.g., because of a validation hold)
- Only admin users (or users with an "hl7_admin" role) should see this view

---

### HL7 Connection Configuration
**Purpose**: Admin screen to configure the HL7 MLLP listener settings.

**Data I need to display**:
- Current configuration values:
  - Listening port
  - Local facility ID / application name (sending facility)
  - Character encoding (default: ASCII, options: UTF-8, Latin-1)
  - Auto-start on server boot toggle
  - Reconnection settings (max retries, retry interval)
  - Accepted sender IP whitelist (list of allowed hospital IPs)
  - Log level for HL7 processing (DEBUG / INFO / WARN / ERROR)
- "Test connection" button that attempts a loopback send/receive

**Actions**:
- Edit any configuration field
- Save configuration (persist, may require listener restart)
- Test connection
- Reset to defaults

**States to handle**:
- **Loading**: Form skeleton
- **Saving**: Disable form while save is in flight, show "Saving…"
- **Save success**: Toast success message
- **Save error**: Toast with error detail; form stays editable (don't lose unsaved changes)
- **Test connection**: Loading spinner during test, then success/failure indicator
- **Listener needs restart after save**: Yellow warning banner "Configuration changed — restart listener for changes to take effect"

**Business rules affecting UI**:
- Only admin users
- Changing port or encoding requires listener restart; changing whitelist does not
- Test connection should not disrupt the running listener (use a separate test socket)

---

### Alerting / Sync Failure Notifications
**Purpose**: Show alerts and notification history for HL7 pipeline issues.

**Data I need to display**:
- Active alerts list:
  - Alert type (Connection Lost, High Error Rate, Parse Spike, Listener Crash)
  - Severity (Critical, Warning, Info) with color-coded tag
  - Triggered timestamp
  - Duration (if still active)
  - Acknowledged status
- Alert history table (resolved + active) with same columns plus resolved timestamp
- Quick stats: X active alerts, Y acknowledged today

**Actions**:
- Acknowledge an active alert (dismisses from active view, moves to history)
- Click an alert → navigate to filtered Message Log showing relevant messages
- Configure alert thresholds (e.g., "Alert if > 5% error rate in 15 min window")

**States to handle**:
- **Loading**: Skeleton
- **Empty (no alerts)**: "No active alerts. All systems nominal."
- **Critical alert**: Red banner at top of HL7 Dashboard, persistent until acknowledged

**Business rules affecting UI**:
- Only admin users
- Alerts auto-resolve when the condition clears (e.g., connection re-established)
- Acknowledging a critical alert removes the dashboard banner but keeps the alert in history

---

### Extensions to Existing Screens

**Patient detail page** (`frontend/src/patient/Patient.tsx`):
- Add "Source" row to the patient info table showing sync source badge (DICOM / HL7 / Manual / Both)
- Add "Last HL7 Update" timestamp row if applicable
- Add "HL7 Message Log" link that navigates to filtered Message Log for that patient

**Sidebar** (`frontend/src/common/Sidebar.tsx`):
- Add "HL7" submenu under the Admin section (admin-only, consistent with existing `isAdmin()` guard):
  - Dashboard (icon: `ApiOutlined` or `SendOutlined`)
  - Message Log (icon: `AlignLeftOutlined`)
  - Patient Sync (icon: `TeamOutlined`)
  - Configuration (icon: `SettingOutlined`)

---

## Uncertainties

- [ ] Not sure if HL7 messages should be stored in a new table or appended to the existing `log` table — they have different retention/search needs
- [ ] Don't understand how partial parse is defined — is it "message received successfully but some optional fields failed" or something else?
- [ ] Guessing that ORM messages map to existing `studies` table via `study_id` — confirm the field mapping
- [ ] Not sure if we need real-time updates via WebSocket (existing `/ws` endpoint) or if polling is fine
- [ ] The existing `patients` table has `meta` JSONB — is HL7 metadata stored there, or do we need a separate column for `hl7_source`?
- [ ] Not clear on whether patients that arrive via HL7 batch vs. real-time single message need different handling in the UI
- [ ] Don't know if we need to support HL7 v2.3 vs 2.5 vs 2.6 differently in the frontend display

## Questions for Backend

1. **Patient sync source**: The existing patient detail page shows patient info from the `patients` table. Can we add a field (or use `meta`) to indicate whether a patient came from HL7, DICOM, or manual? I need this for the source badge in the detail view.

2. **Message storage model**: Do HL7 messages get their own table, or should they be queryable via the existing logs pattern? I need search, filter, and pagination — the existing `logs` table doesn't seem designed for structured HL7 data.

3. **Real-time updates**: The dashboard should feel live. Is WebSocket the right approach (using existing `/ws` infrastructure), or would backend-sent events / simple polling be easier to implement?

4. **Study/order linking**: For ORM messages, I need to link to the existing study/worklist view. Can you confirm that ORM messages will produce entries in the `studies` table (with a `study_id` that matches the HL7 order ID)?

5. **Error granularity**: When a message fails to parse, I want to show the user what went wrong (segment, field, value). Is the backend planning to capture per-field error details, or will it be a single error string?

6. **Alert thresholds**: Should alert thresholds be hardcoded or configurable per deployment? If configurable, should they live in the same config system (`config.local.yaml`) or in DB?

7. **CSV export volume**: The message log could grow large. Should CSV export be async (generate, then download) or sync (stream rows)? If async, I need a way to check export status.

8. **Event types to support**: Which ADT event types (A01–A64) and ORM event types (O01–O09) are we supporting initially? I'll show/hide columns based on this.

9. **WebSocket vs polling for dashboard**: Would it make sense to push HL7 connection status + recent message updates over the existing WebSocket channel, so the dashboard auto-updates without polling?

10. **Acceptable sender whitelist**: Is the list of accepted hospital IPs a backend-side concern only, or should the frontend configuration screen expose it for admin editing?

## Discussion Log

*No backend responses yet — document created for initial review.*
