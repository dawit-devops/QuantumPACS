# Backend Requirements: FHIR R4 API

## Context

We're adding an FHIR R4 API layer to QuantumPACS so that external EHR systems (Epic, Cerner, etc.) can query patient demographics, imaging study metadata, and structured reports directly. This is a **backend-first feature** — the primary consumers are third-party systems, not our own frontend. However, there are a handful of frontend touch points for configuration, monitoring, and documentation that we need backend data to support.

**Who uses it:**
- **External EHR systems** — read patient/imaging data via FHIR, discover capabilities via CapabilityStatement, receive documents via DocumentReference
- **Internal PACS admins** — configure FHIR server settings, monitor request traffic, view error rates
- **PACS standard users** — indirect benefit (their data becomes accessible to referring physicians)

**What success looks like:**
- EHR can read a Patient resource by MRN and see all their ImagingStudies
- EHR can search for ImagingStudies by patient, accession number, date range, or modality
- EHR receives structured reports as DocumentReference resources
- EHR discovers our FHIR endpoint via CapabilityStatement at `[base]/metadata`
- SMART-on-FHIR backend services flow works for authorized EHR systems
- Admins can flip FHIR on/off, configure the base URL published in resources, and see traffic health without digging into raw logs

---

## Screens/Components

### FHIR Configuration Page (Admin only)

**Purpose**: Admin dashboard for enabling/disabling the FHIR module and configuring how QuantumPACS presents itself to external systems.

**Data I need to display**:

- Whether the FHIR server is currently **enabled** or **disabled** (global toggle)
- **Published base URL** — the external-facing URL the FHIR endpoint lives at (e.g., `https://pacs.hospital.org/fhir`). This gets baked into every resource's `meta` and the CapabilityStatement. Default could be the server's own host, but admins may need to override for reverse-proxy setups.
- **SMART-on-FHIR client registrations** — a list of registered client applications:
  - Client ID
  - Client name / description
  - Allowed redirect URIs (for authorization code flow)
  - Whether it uses backend services (client credentials) grant
  - Active/inactive status
  - Last used timestamp (if available)
- **CapabilityStatement customization**:
  - Server name / publisher name (shown in CapabilityStatement)
  - Supported FHIR version (static R4 but worth surfacing)
- **Allowed EHR IP ranges or CIDR blocks** (optional, if we do network-level access control) — list of entries with label + CIDR
- **CORS origin overrides** for the FHIR base URL (default could be wildcard, but EHRs sending direct REST calls may need explicit origins)

**Actions**:

- **Toggle FHIR enabled/disabled** → When disabled, all FHIR endpoints return a 503 or 501 with an OperationOutcome. Need a confirmation dialog since this affects external integrations.
- **Edit published base URL** → Updates the URL used in resource `meta` and CapabilityStatement. Need validation that it's a valid URL with `/fhir` or similar path.
- **Register a SMART-on-FHIR client** → Form with client name, redirect URIs, grant type selection. Outcome: new client credentials generated (client_id + client_secret), shown once.
- **Revoke/deactivate a client** → Confirmation dialog, then client can no longer authenticate.
- **Edit allowed IP ranges** → Add/remove CIDR entries.
- **Edit CORS origins** → Add/remove allowed origin strings.
- **Test connection** → Button that hits the CapabilityStatement endpoint and confirms the FHIR server is reachable. Returns status + response time.

**States to handle**:

- **Loading**: Fetching current FHIR config from backend. Show skeleton/spinner.
- **Empty**: No SMART clients registered yet. Show "No clients configured" with a CTA to add one.
- **Saving**: Form submission in progress. Disable form, show spinner on save button.
- **Error — save failure**: Backend rejected the update. Show specific error message (validation, DB error).
- **Error — backend unreachable**: Can't fetch current config. Show full-page error with retry button.
- **Disabled state**: When FHIR is globally disabled, visually indicate that all other config fields are irrelevant. Maybe collapse or gray out the section below the toggle with a note: "Enable FHIR to configure."
- **Client secret shown once**: After client creation, show the secret in a modal with a copy button and a warning that it won't be shown again.
- **Validation errors**: Invalid URL format, missing redirect URI, duplicate client name, invalid CIDR.

**Business rules affecting UI**:

- Only **admin** users can see this page. Non-admin users should not see the nav item or be able to navigate to it.
- If FHIR is globally disabled, the CapabilityStatement endpoint should not be reachable, and SMART-on-FHIR auth should reject all requests.
- Disabling FHIR mid-session should not disrupt in-progress EHR requests (eventual consistency / grace period). UI should show a warning: "Existing sessions may persist for [token expiry] minutes."

### FHIR Monitoring Dashboard (Admin only)

**Purpose**: At-a-glance health and traffic monitoring for the FHIR API, analogous to the existing System Logs page but filtered to FHIR-specific metrics.

**Data I need to display**:

- **Request volume over time** — count of FHIR requests per resource type (Patient, ImagingStudy, DocumentReference, CapabilityStatement, metadata) and per HTTP method (GET, POST, PUT, DELETE), aggregated over configurable time windows (last hour, last 24 hours, last 7 days).
- **Error rate** — percentage and raw count of FHIR responses by status code family (2xx, 4xx, 5xx). Drill-down into 4xx to see which OperationOutcome codes dominate (e.g., "unknown patient", "invalid identifier", "unauthorized").
- **Latency percentiles** — p50, p95, p99 response time for FHIR requests, optionally by resource type.
- **Active SMART-on-FHIR sessions** — count of active client credentials grants, optionally by client ID.
- **Top clients** — which SMART-on-FHIR client IDs are making the most requests. Useful for auditing.
- **Recent FHIR requests** — a scrolling list of recent FHIR requests showing:
  - Timestamp
  - HTTP method + FHIR resource path
  - Response status
  - Response time (ms)
  - Calling client ID (if authenticated)
  - Calling IP (if available)
- **FHIR-specific error log** — structured view of failed FHIR requests with the OperationOutcome details (issue type, severity, diagnostics text).

**Actions**:

- **Filter by time range** — Preset buttons (1h, 24h, 7d, 30d) and custom date range picker.
- **Filter by resource type** — Multi-select checkboxes for Patient, ImagingStudy, DocumentReference, CapabilityStatement, other.
- **Filter by status code** — Checkboxes for 2xx, 4xx, 5xx.
- **Filter by client ID** — Dropdown populated from known SMART clients.
- **Export to CSV** — Download the current table view as a CSV file.
- **Refresh** — Manual refresh button. Page should also auto-refresh at a configurable interval (default 30s).
- **View raw request details** — Click a row to expand and see the full request/response headers and body (truncated if large).

**States to handle**:

- **Loading**: Initial fetch and subsequent filter changes show skeleton/spinner on the chart areas and table.
- **Empty / No data**: FHIR hasn't been used yet. Show "No FHIR requests yet. Advertise your FHIR endpoint to EHR systems to get started."
- **Error — can't load metrics**: Backend metrics endpoint unreachable. Show error banner with retry.
- **Error — partial data**: Some metrics loaded but others failed. Show what we have plus a warning.
- **All zeros / FHIR disabled**: If FHIR is disabled and there's no data, show a state linking to the FHIR Configuration page to enable it.
- **Large dataset**: If there are millions of requests, the table must paginate. Charts should aggregate, not render individual points.
- **Time zone**: Display timestamps in local timezone with a "(UTC)" indicator. Let the user toggle between UTC and browser local time.

**Business rules affecting UI**:

- Only **admin** users can access this page.
- Request log retention is backend-determined (configurable). The UI should show a note: "Logs retained for [N] days" based on what backend reports.
- Metrics data may be delayed by up to a minute (async logging). UI should note near-real-time nature.

### FHIR Documentation / Interactive Explorer (All authenticated users, but mostly admin/referring physicians)

**Purpose**: An in-browser FHIR API explorer so that admins can test endpoints without an external tool, and referring physicians can understand what's available. Think a lightweight Swagger UI.

**Data I need to display**:

- **CapabilityStatement rendered as HTML** — human-readable version of what the server supports:
  - Server name, publisher, version
  - Supported resource types (Patient, ImagingStudy, DocumentReference) with their supported interactions (read, search, create, update)
  - Supported search parameters for each resource type
  - Security scheme description (SMART-on-FHIR)
  - Operation endpoints (if any)
  - Format support (JSON, XML — JSON only to start)
- **Interactive "Try it" panel** for each supported resource:
  - Dropdown of available interactions (read by ID, search by parameters)
  - Input fields for required parameters (e.g., patient identifier, search filters)
  - A "Send" button that makes a live request to the FHIR API using the viewer's own auth session
  - Response display: formatted JSON with syntax highlighting, status code, response time
- **OperationOutcome decoder** — when a request fails, explain the OperationOutcome in plain language, possibly with remediation hints.

**Actions**:

- **Explore CapabilityStatement** → Click through resource types to see what's supported. No backend call needed beyond the initial CapabilityStatement fetch.
- **Try a read request** → Enter a resource type + ID → see the returned resource JSON.
- **Try a search request** → Select a resource type → fill in search parameters (name, identifier, date, etc.) → see the returned Bundle JSON.
- **Copy response** → Button to copy the raw JSON response to clipboard.
- **Download response** → Save the response as a `.json` file.

**States to handle**:

- **Loading CapabilityStatement**: Fetching `[base]/metadata` on page mount.
- **CapabilityStatement unavailable**: If FHIR is disabled or metadata endpoint fails, show an error with a link to the FHIR Configuration page.
- **Executing a "Try it" request**: Loading state on the request panel (spinner or progress indicator).
- **Try it success**: Formatted JSON response with green status indicator.
- **Try it error**: Red status indicator with the OperationOutcome rendered as a readable error message, plus the raw JSON below.
- **Empty search results**: Bundle with `total = 0`. Show "No results found for your query."
- **Validation errors on search inputs**: Required fields missing, invalid date format, etc. Show inline validation messages.
- **Auth session expired**: If the viewer's token has expired, show a "Please log in again" message with a link to login.
- **Large response**: If the Bundle is large, display it in a collapsed view with a "Show all [N] entries" expand button.

**Business rules affecting UI**:

- The explorer uses the **viewer's own PACS auth session** (X-Auth-Pacs token or JWT) to talk to the FHIR API. The backend should accept our own tokens on the FHIR endpoints for testing purposes. This is separate from SMART-on-FHIR auth.
- The explorer does **not** need SMART-on-FHIR credentials — it's exclusively for internal testing.
- We should not cache the CapabilityStatement aggressively in the UI since it rarely changes, but if it does change, the user should be able to refresh.

---

### Sidebar Navigation Update

**Purpose**: Add FHIR-related nav items under the existing Admin submenu.

**Data / Behavior needed**:

- If the user is admin, show three new items under the Admin section of the sidebar (between Logs and Logout):
  - "FHIR Config" → `/fhir/config`
  - "FHIR Monitoring" → `/fhir/monitoring`
  - "FHIR Docs" → `/fhir/docs`
- The route paths should match whatever the frontend routes expect. Backend doesn't need to serve these pages — just confirm there's no conflict with existing API routes.

---

## Uncertainties

- [ ] Not sure if the FHIR base URL should be a separate config item or always derived from the server's host. Reverse proxy setups suggest it must be configurable.
- [ ] Don't understand whether SMART-on-FHIR backend services will be enough for our target EHRs, or if we also need authorization code flow for user-level access.
- [ ] Guessing that ImagingStudy search parameters will mostly mirror our existing DICOM query model (patient, study date, accession, modality, etc.) — unclear if there are FHIR-mandated search params we must support.
- [ ] Not sure if we need XML support or if JSON-only FHIR is acceptable. Most EHRs handle JSON.
- [ ] Unclear about DocumentReference content encoding — should reports be stored as FHIR Binary resources referenced from DocumentReference, or can they be inline markdown/HTML?
- [ ] Not sure if CapabilityStatement should be served as a static pre-generated document or dynamically generated from introspection.
- [ ] Guessing that FHIR request metrics/logging should go to a separate table or log stream to avoid polluting the existing application log. Open to backend's call on this.

## Questions for Backend

1. **Auth integration strategy**: Will the FHIR endpoints use the same `X-Auth-Pacs` token for internal users (so the docs explorer works), while external EHRs use SMART-on-FHIR bearer tokens? Or should internal testing use a different mechanism? See the sidebar note above — I need internal users to be able to test without SMART-on-FHIR credentials.

2. **Configuration storage**: Where should the FHIR config (enabled flag, base URL, client registrations, IP allowlist) live? YAML config file (like existing `config.local.yaml`), a new database table, or both? If DB, can we expect the config endpoint to return a simple JSON object?

3. **Metrics/logging scope**: Are you okay with the monitoring page requesting aggregate metrics (counts, latencies) from a backend endpoint rather than raw log entries? The existing Logs page shows raw entries — for FHIR I'd prefer pre-aggregated stats + a separate recent-requests list. Would it make sense to store FHIR request logs in a dedicated `fhir_audit` table?

4. **SMART-on-FHIR scope**: For the MVP, can we target only **backend services** (client credentials grant, no user authorization)? Most of our EHR integrations will be system-to-system. If we need user-level auth later, we can add authorization code flow.

5. **DocumentReference source**: Where do structured reports come from? Will there be a report-generation pipeline that writes to a `reports` table, or should DocumentReference point to existing DICOM SR instances? If the latter, how do we distinguish SR from image DICOM files?

6. **CapabilityStatement generation**: Do you have a preference between serving a static JSON file or generating it dynamically? For the frontend docs page, I need at minimum the resource types, interactions, and search parameters — dynamic generation that backend can guarantee is correct would be ideal.

7. **Patient identity mapping**: Our `patients` table uses an internal `patient_id` (which comes from DICOM tag (0010,0020)). Do we serve that as the FHIR Patient.identifier, or do we need a separate MRN mapping table? EHRs typically match on MRN + assigning authority.

8. **FHIR endpoint routing**: Will FHIR endpoints live at a sub-path (e.g., `/api/fhir/...`) or on a separate port/subdomain? This affects the base URL config and CORS setup.

9. **Delete behavior**: For DELETE on Patient, do we hard-delete, soft-delete (mark inactive), or return 405? DICOM doesn't really delete patients, so what's the expected FHIR behavior here?

10. **Search result limits**: What's the expected max page size for FHIR searches? EHRs often use `_count=100` or similar. What should our backend support? The frontend explorer needs to know the limit for UX messaging.

## Discussion Log

*To be updated after backend team reviews.*
