# User Stories — Radiology Service Director (R03)

**Version**: 1.0.0 (v3.0 scope)
**Status**: Final
**Date**: 2026-08-02

---

## Story Index (v3.0 Must Priority)

| Story ID | Title | Priority | FR Links |
|----------|-------|----------|----------|
| US-R03-01 | Service KPI Dashboard | Must | FR-R03-01, NFR-R03-01, NFR-R03-02 |
| US-R03-02 | Real-time Modality Capacity Heatmap | Must | FR-R03-02, NFR-R03-02, NFR-R03-06 |
| US-R03-03 | Protocol Compliance Scorecard | Must | FR-R03-03, NFR-R03-03 |
| US-R03-04 | SLA Tracking & Breach Alerts | Must | FR-R03-04, NFR-R03-02, NFR-R03-12 |
| US-R03-05 | KPI Drill-through to Study List | Must | FR-R03-05, NFR-R03-03 |
| US-R03-06 | Report Builder (Template-based) | Must | FR-R03-10, NFR-R03-04, NFR-R03-05 |
| US-R03-07 | Widget Export (CSV/PDF) | Must | FR-R03-12, NFR-R03-04, NFR-R03-05 |
| US-R03-08 | Dashboard Access Audit | Must | FR-R03-14, NFR-R03-08 |
| US-R03-09 | RBAC Service Director Role | Must | FR-R03-15 |

---

## US-R03-01: Service KPI Dashboard

**Story**: As a Radiology Service Director, I want a consolidated KPI dashboard showing study volume, turnaround times, modality utilization, and staffing coverage so that I can assess service health at a glance each morning.

**Priority**: Must

### Acceptance Criteria

**AC-R03-01-01** (Functional): **Given** I am logged in as a Service Director, **when** I navigate to `/dashboard`, **then** the dashboard loads with four KPI cards: Study Volume (trend sparkline), Turnaround Time (STAT/routine p95), Modality Utilization (%), Staffing Coverage (%), each showing current value + 7-day trend.

**AC-R03-01-02** (Performance): **Given** the dashboard loads, **when** all widgets render, **then** LCP ≤ 2.5s (Lighthouse CI), and Time to Interactive ≤ 3s.

**AC-R03-01-03** (Data Freshness): **Given** the dashboard is displayed, **when** 5 minutes elapse, **then** each widget auto-refreshes via background fetch, and an ARIA live region announces "Dashboard updated, 4 KPIs refreshed" without focus loss.

**AC-R03-01-04** (Loading State): **Given** I navigate to `/dashboard`, **when** widget data is fetching, **then** each KPI card shows a skeleton loader (shimmer) matching the card dimensions, and the card is announced as "loading" to screen readers.

**AC-R03-01-05** (Empty State): **Given** no study data exists for the tenant, **when** the dashboard loads, **then** each KPI card shows "No data available" with a "Run first study" CTA button (links to Files page), not a blank card.

**AC-R03-01-06** (Error State): **Given** an analytics API call fails, **when** the error occurs, **then** the affected KPI card shows an error banner with "Failed to load" and a "Retry" button; other widgets remain functional.

**AC-R03-01-07** (Accessibility - WCAG 2.2 AA): **Given** I use keyboard-only navigation, **when** I tab through the dashboard, **then** focus order is logical (top-left to bottom-right), each KPI card has a visible focus ring (2px solid `--color-primary`), and all values are announced by screen readers (role="region" aria-label="Study Volume: 1,247 studies, up 12%").

**AC-R03-01-08** (Color Contrast): **Given** any KPI card displays a trend indicator (up/down/neutral), **when** viewed in color-blind simulator (protanopia/deuteranopia), **then** the trend is distinguishable by both color AND icon (↑/↓/→), not color alone.

**AC-R03-01-09** (Responsive): **Given** I view the dashboard on a tablet (768px), **when** the viewport width is < 992px, **then** KPI cards stack in a single column with full-width cards, maintaining all functionality.

---

## US-R03-02: Real-time Modality Capacity Heatmap

**Story**: As a Radiology Service Director, I want a real-time heatmap showing scheduled vs actual vs capacity per modality per timeslot so that I can identify overbooking and gaps before the daily huddle.

**Priority**: Must

### Acceptance Criteria

**AC-R03-02-01** (Functional): **Given** I open the Capacity tab, **when** the heatmap loads, **then** it displays a 7-day × 24-hour grid per modality (CT, MR, US, DX, MG, FL), each cell color-coded: green (<80%), yellow (80-95%), red (95-110%), critical (>110% utilization).

**AC-R03-02-02** (Real-time Updates): **Given** a new HL7 ORM^O01 message arrives scheduling a study, **when** the message is processed, **then** the corresponding heatmap cell updates within 5 minutes via WebSocket/SSE, without full page reload.

**AC-R03-02-03** (Data Source): **Given** the heatmap renders, **when** I hover a cell, **then** a tooltip shows: Modality, Date, Timeslot, Scheduled count, Capacity, Utilization %, Equipment status (up/down).

**AC-R03-02-04** (Drill-through): **Given** I click a red/critical cell, **when** the click occurs, **then** a modal opens showing the scheduled studies for that slot with patient name, accession, procedure, referring physician, and "Notify Coordinator" button.

**AC-R03-02-05** (Performance): **Given** the heatmap loads with 7 days × 6 modalities × 24 slots = 1,008 cells, **when** rendering completes, **then** total render time ≤ 1s, and no layout shift (CLS < 0.1).

**AC-R03-02-06** (Accessibility - Keyboard): **Given** I navigate the heatmap with keyboard, **when** I use arrow keys, **then** focus moves logically between cells (left/right = timeslot, up/down = day), Enter opens the detail modal, Escape closes modal and returns focus to cell.

**AC-R03-02-07** (Accessibility - Color-Blind): **Given** I view the heatmap with protanopia simulation, **when** I inspect the color legend, **then** each utilization band has a distinct pattern overlay (green=none, yellow=diagonal lines, red=dense dots, critical=crosshatch) in addition to color.

**AC-R03-02-08** (ARIA Live Region): **Given** a cell updates via WebSocket, **when** the update occurs, **then** an ARIA live region (polite) announces "CT Monday 08:00 updated: 22 scheduled, 20 capacity, 110% utilization" without stealing focus.

**AC-R03-02-09** (Empty/Error States): **Given** no schedule data exists for a modality, **when** the heatmap renders, **then** that modality's grid shows "No schedule data" in each cell with a muted pattern; if API fails, a toast appears and the grid shows a retry button per modality row.

---

## US-R03-03: Protocol Compliance Scorecard

**Story**: As a Radiology Service Director, I want a protocol compliance scorecard showing per-modality/protocol compliance against ACR benchmarks so that I can identify protocols needing quality improvement.

**Priority**: Must

### Acceptance Criteria

**AC-R03-03-01** (Functional): **Given** I open the Protocol tab, **when** the scorecard loads, **then** it displays a table with columns: Protocol Code, Name, Modality, Studies Reviewed, Compliance %, Avg Dose (DLP), Status (Pass/Fail), Trend (7-day sparkline).

**AC-R03-03-02** (Drill-through): **Given** I click a protocol row with <95% compliance, **when** the click occurs, **then** a side panel opens showing: missing sequences per study, dose outliers, assigned corrective actions, and a "View Studies" button linking to Files table filtered to that protocol.

**AC-R03-03-03** (Data Source): **Given** the scorecard renders, **when** I hover the compliance % cell, **then** a tooltip shows: numerator (passing studies), denominator (total reviewed), ACR benchmark threshold, last QA review date.

**AC-R03-03-04** (Accessibility - Table): **Given** I navigate the scorecard table with keyboard, **when** I tab into the table, **then** arrow keys navigate cells, Home/End jump to row ends, and the table has proper `role="grid"` with column headers announced.

**AC-R03-03-05** (Color Contrast): **Given** the Status column uses color badges (green Pass, red Fail), **when** viewed in grayscale, **then** each badge includes text label ("Pass"/"Fail") and an icon (✓/✗), not color alone.

**AC-R03-03-06** (Performance): **Given** 50 protocols × 100 studies each, **when** the scorecard loads, **then** API response p95 ≤ 300ms, and table renders with virtualized rows (react-window) for smooth scrolling.

---

## US-R03-04: SLA Tracking & Breach Alerts

**Story**: As a Radiology Service Director, I want real-time SLA tracking with breach alerts so that I can escalate delayed STAT reads and monitor routine turnaround compliance.

**Priority**: Must

### Acceptance Criteria

**AC-R03-04-01** (Functional - STAT): **Given** a STAT study exceeds 30 minutes from `study.created` to `report.signed_at`, **when** the breach occurs, **then** a breach badge appears on the SLA KPI card (red, pulsing), and the breach list updates with study ID, modality, minutes overdue, assigned radiologist.

**AC-R03-04-02** (Functional - Routine): **Given** a routine study exceeds 24 hours turnaround, **when** the breach occurs, **then** it appears in the breach list with amber badge (non-pulsing), and the routine p95 KPI updates.

**AC-R03-04-03** (Breach List): **Given** I open the SLA tab, **when** the breach list loads, **then** it shows: Study ID, Patient (initials only), Modality, Type (STAT/Routine), Minutes Overdue, Assigned Radiologist, Status (Pending/Escalated/Resolved), with pagination (20/page).

**AC-R03-04-04** (Escalation): **Given** a STAT breach exceeds 60 minutes, **when** the threshold is crossed, **then** an in-app notification is sent to the assigned radiologist and the Service Coordinator (R04), and an audit log entry is created.

**AC-R03-04-05** (Accessibility - Alerts): **Given** a breach alert appears, **when** announced via ARIA live region (assertive), **then** screen readers announce "Critical: STAT study ACC12345 overdue by 45 minutes" and focus is NOT moved (non-modal).

**AC-R03-04-06** (Performance): **Given** breach detection runs every minute, **when** checking 10,000 active studies, **then** the background job completes ≤ 10s, and API p95 for breach list ≤ 300ms.

---

## US-R03-05: KPI Drill-through to Study List

**Story**: As a Radiology Service Director, I want to click any KPI card and drill through to the study list pre-filtered to that metric so that I can investigate outliers without manually building search queries.

**Priority**: Must

### Acceptance Criteria

**AC-R03-05-01** (Functional): **Given** I click the "CT Utilization 85%" KPI card, **when** the navigation occurs, **then** the Files page opens at `/files?modality=CT&date_range=last_7d`, the search box shows the applied filter, and the table displays only CT studies from the last 7 days.

**AC-R03-05-02** (URL Bookmarkable): **Given** I drill through from a KPI, **when** the Files page loads, **then** the URL encodes all filter state (modality, date range, sort), and I can bookmark/share the URL to reproduce the exact view.

**AC-R03-05-03** (Breadcrumb Context): **Given** I am on the drilled-through Files page, **when** I view the breadcrumb, **then** it shows "Dashboard > CT Utilization > Studies" with the KPI name as a clickable link back to the dashboard.

**AC-R03-05-04** (Performance): **Given** I click a KPI card, **when** the Files page loads with filtered results, **then** the transition completes ≤ 1s (including API search + table render).

**AC-R03-05-05** (Accessibility - Focus Management): **Given** I click a KPI card via keyboard (Enter/Space), **when** the Files page loads, **then** focus moves to the first interactive element (search box or first table row), and the page title updates to "Studies - CT Utilization Filter".

---

## US-R03-06: Report Builder (Template-based)

**Story**: As a Radiology Service Director, I want to generate standardized reports from pre-defined templates with parameter selection so that I can produce board-ready PDFs and CSVs without manual spreadsheet work.

**Priority**: Must

### Acceptance Criteria

**AC-R03-06-01** (Template Selection): **Given** I open the Report Builder, **when** the modal opens, **then** it displays 5 template cards: Monthly Volume Summary, Turnaround by Modality, Protocol Compliance, Capacity Utilization, SLA Breach Detail; each shows name, description, and estimated generation time.

**AC-R03-06-02** (Parameter Modal): **Given** I select "Monthly Volume Summary", **when** the parameter modal opens, **then** it shows: Date Range (preset: Last Month / Custom), Modality Filter (multi-select: All / CT / MR / US / DX / MG / FL), Output Format (CSV / PDF), with sensible defaults pre-selected.

**AC-R03-06-03** (Generation - CSV): **Given** I set parameters and click "Generate CSV", **when** the request completes, **then** a CSV file downloads with filename `monthly_volume_2026-07.csv`, columns: Date, Modality, Study Count, Series Count, Total Size (GB), and generation time ≤ 30s shown in toast.

**AC-R03-06-04** (Generation - PDF): **Given** I set parameters and click "Generate PDF", **when** the request completes, **then** a PDF file downloads with filename `monthly_volume_2026-07.pdf`, containing: title page, summary table, charts (bar: volume by modality, line: daily trend), and generation time ≤ 60s shown in toast.

**AC-R03-06-05** (Loading State): **Given** I click "Generate", **when** the report is processing, **then** the button shows a spinner with "Generating... 23%", the modal is disabled but dismissible, and a progress indicator updates every 5s via polling.

**AC-R03-06-06** (Error Handling): **Given** report generation fails (timeout, data error), **when** the error occurs, **then** the modal shows an error banner with "Generation failed: [reason]", a "Retry" button, and a "Change Parameters" link; no partial file downloads.

**AC-R03-06-07** (Accessibility - Modal): **Given** I open the Report Builder modal via keyboard, **when** the modal opens, **then** focus is trapped within the modal, Escape closes it and returns focus to the triggering button, and all form fields have associated labels.

**AC-R03-06-08** (Accessibility - Progress): **Given** a report is generating, **when** progress updates, **then** an ARIA live region (polite) announces "Report generation 45% complete" without focus change.

---

## US-R03-07: Widget Export (CSV/PDF)

**Story**: As a Radiology Service Director, I want to export any dashboard widget as CSV or PDF so that I can include specific charts in presentations and emails.

**Priority**: Must

### Acceptance Criteria

**AC-R03-07-01** (Export Button): **Given** I hover any KPI card or chart widget, **when** the hover occurs, **then** an export dropdown appears with "Export CSV" and "Export PDF" options (icon-only on mobile, icon+text on desktop).

**AC-R03-07-02** (CSV Export): **Given** I click "Export CSV" on the Modality Utilization chart, **when** the download starts, **then** a CSV downloads with filename `modality_utilization_2026-08-02.csv`, columns matching the widget data (Modality, Scheduled, Capacity, Utilization %, Date), and completes ≤ 30s.

**AC-R03-07-03** (PDF Export): **Given** I click "Export PDF" on the Turnaround Trend chart, **when** the download starts, **then** a PDF downloads with filename `turnaround_trend_2026-08-02.pdf`, containing the chart as vector graphic (not rasterized), axis labels, legend, and timestamp; completes ≤ 60s.

**AC-R03-07-04** (Streaming): **Given** I export a widget with 10,000 data points, **when** the export runs, **then** the backend streams the response (chunked transfer), the browser shows download progress immediately, and memory usage stays < 100MB.

**AC-R03-07-05** (Accessibility): **Given** I use keyboard navigation, **when** I focus a widget and press Enter on the export button, **then** the dropdown opens with focus on the first option, arrow keys navigate, Enter selects, Escape closes.

---

## US-R03-08: Dashboard Access Audit

**Story**: As a Radiology Service Director, I want all dashboard access and export actions logged so that we maintain HIPAA-compliant audit trails for analytics access.

**Priority**: Must

### Acceptance Criteria

**AC-R03-08-01** (View Logging): **Given** I load the dashboard, **when** the page mounts, **then** an audit entry is created: `{user_id, tenant, action: 'dashboard_view', widgets: ['volume','turnaround','utilization','staffing'], timestamp, ip_address}`.

**AC-R03-08-02** (Drill-through Logging): **Given** I drill through from a KPI to the study list, **when** the navigation occurs, **then** an audit entry: `{user_id, action: 'kpi_drillthrough', source_kpi: 'ct_utilization', target_url: '/files?modality=CT...', timestamp}`.

**AC-R03-08-03** (Export Logging): **Given** I export a widget or generate a report, **when** the download starts, **then** an audit entry: `{user_id, action: 'export', type: 'csv'|'pdf', widget_or_template: 'modality_utilization', record_count: 150, timestamp}`.

**AC-R03-08-04** (Report Generation Logging): **Given** I generate a scheduled report, **when** the report completes, **then** an audit entry: `{user_id, action: 'report_generate', template_id: 'tpl-01', format: 'pdf', recipients: ['cmio@hospital.org'], timestamp}`.

**AC-R03-08-05** (HIPAA Minimum Necessary): **Given** any audit entry is created, **when** the entry is written, **then** no PHI (patient name, MRN, accession) is included unless the action was a drill-through to a specific study (then only study_uid is logged with justification: 'drillthrough_from_kpi').

**AC-R03-08-06** (Audit Query): **Given** I am an Auditor (R03 with `auditor` role), **when** I query `/api/v2/audit/dashboard-access?user_id=X&date_range=last_30d`, **then** results return paginated with all fields above, and export to CSV available.

---

## US-R03-09: RBAC Service Director Role

**Story**: As a PACS Administrator, I want a built-in `service_director` role with analytics permissions so that I can assign the Service Director role without custom role configuration.

**Priority**: Must

### Acceptance Criteria

**AC-R03-09-01** (Role Exists): **Given** I navigate to `/roles` as admin, **when** the roles table loads, **then** `service_director` appears in the built-in roles list (non-deletable), with permissions: `METRICS_READ`, `ANALYTICS_READ`, `ANALYTICS_EXPORT`, `REPORT_BUILD`.

**AC-R03-09-02** (Permission Enforcement): **Given** a user has `service_director` role, **when** they access `/dashboard`, **then** access is granted; **when** they access `/users` or `/tenants`, **then** access is denied (403).

**AC-R03-09-03** (Token Includes Permissions): **Given** a `service_director` user logs in, **when** the JWT is issued, **then** the token's `permissions` claim includes the four analytics permissions, and `role` claim is `service_director`.

**AC-R03-09-04** (Tenant Scoping): **Given** a `service_director` user in Tenant A accesses analytics, **when** the API executes, **then** all queries are scoped to Tenant A's database (no cross-tenant data leakage).

**AC-R03-09-05** (UI Visibility): **Given** a `service_director` user logs in, **when** the sidebar renders, **then** only "Dashboard" and "Account" are visible; Admin submenu is hidden.

---

## v3.1 Deferred Stories (Reference)

| Story ID | Title | Priority | Reason for Deferral |
|----------|-------|----------|---------------------|
| US-R03-10 | Staffing vs Demand Forecast | Should | Requires HL7 future-dated ORM parsing; v3.1 RIS integration |
| US-R03-11 | Equipment Downtime Impact | Should | Requires equipment registry API; v3.1 Biomed integration |
| US-R03-12 | Protocol Gap Analysis | Should | Requires DICOM tag validation rules engine; v3.1 |
| US-R03-13 | SLA Breach Root-Cause | Could | Requires timestamped workflow events; v3.1+ |
| US-R03-14 | Scheduled Report Delivery | Could | Requires background job scheduler; v3.1 |
| US-R03-15 | Configurable Alerting | Could | Requires alert rule engine; v3.1 |

---

## Cross-Reference Matrix

| AC ID | FR/NFR Link | Verification Method | Validator Gate |
|-------|-------------|---------------------|----------------|
| AC-R03-01-01 | FR-R03-01 | Automated test (Playwright) | Contrast, focus, 4 states, tokens |
| AC-R03-01-02 | NFR-R03-01 | Lighthouse CI | LCP ≤ 2.5s, TTI ≤ 3s |
| AC-R03-01-03 | NFR-R03-02 | Synthetic probe | ARIA live, no focus loss |
| AC-R03-01-04 | FR-R03-01 | Visual test | Skeleton matches card dims |
| AC-R03-01-05 | FR-R03-01 | Visual test | CTA button present |
| AC-R03-01-06 | FR-R03-01 | Error injection test | Retry button works |
| AC-R03-01-07 | NFR-R03-08 | axe-core + manual | Focus order, ARIA labels |
| AC-R03-01-08 | NFR-R03-09 | Color-blind simulator | Icon + color for trends |
| AC-R03-01-09 | NFR-R03-10 | Responsive test | Single column < 992px |
| AC-R03-02-01 | FR-R03-02 | Visual test | 7-day × 24h × 6 modalities |
| AC-R03-02-02 | NFR-R03-02 | WS integration test | ≤ 5min update |
| AC-R03-02-03 | FR-R03-02 | Visual test | Tooltip on hover |
| AC-R03-02-04 | FR-R03-02 | Click test | Modal with study list |
| AC-R03-02-05 | NFR-R03-03 | Performance test | ≤ 1s render, CLS < 0.1 |
| AC-R03-02-06 | NFR-R03-08/10 | Keyboard test | Arrow nav, Enter/Escape |
| AC-R03-02-07 | NFR-R03-09 | Simulator test | Pattern overlays |
| AC-R03-02-08 | NFR-R03-02 | ARIA test | Polite live region |
| AC-R03-02-09 | FR-R03-02 | Error injection | Retry per modality row |
| AC-R03-03-01 | FR-R03-03 | Visual test | Table with all columns |
| AC-R03-03-02 | FR-R03-03 | Click test | Side panel with gaps |
| AC-R03-03-03 | FR-R03-03 | Hover test | Tooltip with details |
| AC-R03-03-04 | NFR-R03-08/10 | Keyboard test | Grid role, arrow nav |
| AC-R03-03-05 | NFR-R03-09 | Grayscale test | Text + icon on badges |
| AC-R03-03-06 | NFR-R03-07 | Load test | p95 ≤ 300ms, virtualized |
| AC-R03-04-01 | FR-R03-04 | Time simulation test | Badge appears at 30min |
| AC-R03-04-02 | FR-R03-04 | Time simulation test | Amber badge at 24h |
| AC-R03-04-03 | FR-R03-04 | Visual test | Breach list with pagination |
| AC-R03-04-04 | FR-R03-04 | Threshold test | Notification at 60min |
| AC-R03-04-05 | NFR-R03-08 | ARIA test | Assertive, no focus steal |
| AC-R03-04-06 | NFR-R03-07 | Load test | Job ≤ 10s, API ≤ 300ms |
| AC-R03-05-01 | FR-R03-05 | Click test | Files page with filter |
| AC-R03-05-02 | FR-R03-05 | URL test | Bookmarkable URL |
| AC-R03-05-03 | FR-R03-05 | Visual test | Breadcrumb context |
| AC-R03-05-04 | NFR-R03-03 | Timing test | ≤ 1s transition |
| AC-R03-05-05 | NFR-R03-08/10 | Focus test | Focus on search/first row |
| AC-R03-06-01 | FR-R03-10 | Visual test | 5 template cards |
| AC-R03-06-02 | FR-R03-10 | Form test | All params with defaults |
| AC-R03-06-03 | NFR-R03-04 | Timing test | CSV ≤ 30s |
| AC-R03-06-04 | NFR-R03-05 | Timing test | PDF ≤ 60s |
| AC-R03-06-05 | FR-R03-10 | Visual test | Progress spinner + % |
| AC-R03-06-06 | FR-R03-10 | Error injection test | Error banner + retry |
| AC-R03-06-07 | NFR-R03-08/10 | Keyboard test | Focus trap, Escape |
| AC-R03-06-08 | NFR-R03-08 | ARIA test | Polite progress announcements |
| AC-R03-07-01 | FR-R03-12 | Hover test | Export dropdown |
| AC-R03-07-02 | NFR-R03-04 | Download test | CSV ≤ 30s, correct cols |
| AC-R03-07-03 | NFR-R03-05 | Download test | PDF ≤ 60s, vector chart |
| AC-R03-07-04 | NFR-R03-04 | Memory test | Streaming, < 100MB |
| AC-R03-07-05 | NFR-R03-08/10 | Keyboard test | Dropdown focus, arrow nav |
| AC-R03-08-01 | FR-R03-14 | DB query test | Audit entry created |
| AC-R03-08-02 | FR-R03-14 | DB query test | Drillthrough logged |
| AC-R03-08-03 | FR-R03-14 | DB query test | Export logged with count |
| AC-R03-08-04 | FR-R03-14 | DB query test | Report logged with recipients |
| AC-R03-08-05 | FR-R03-14 | Code review | No PHI unless drillthrough |
| AC-R03-08-06 | FR-R03-14 | API test | Auditor can query/export |
| AC-R03-09-01 | FR-R03-15 | Visual test | Role in built-in list |
| AC-R03-09-02 | FR-R03-15 | 403 test | Denied on /users, /tenants |
| AC-R03-09-03 | FR-R03-15 | JWT decode test | Permissions in token |
| AC-R03-09-04 | FR-R03-15 | Cross-tenant test | No data leakage |
| AC-R03-09-05 | FR-R03-15 | Visual test | Sidebar only Dashboard |