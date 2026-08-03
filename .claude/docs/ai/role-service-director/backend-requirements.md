# Backend Requirements: R03 Radiology & Imaging Service Director

## Context

The Service Director (senior radiologist) has operational accountability for the
imaging service line. Reads KPI dashboards daily, monitors capacity/staffing,
oversees protocol compliance and SLA performance, and reports to leadership. This
role is **read + analytics only** — no writes to studies/files. Because dashboards
can surface PHI when drilled into study detail, the frontend needs an audit hook
for every drill-down/export.

**Screens (mostly new — a dedicated analytics/reporting UI)**: Service KPI
Dashboard, Modality Capacity Heatmap, Protocol Compliance Scorecard, SLA Tracking,
KPI Drill-through, Report Builder (template-based), Exports, Dashboard Access
Audit.

**Personas**: P1 (senior radiologist) with analytics-only access. **Access
tier**: read + full analytics (tenant-scoped).

## Screens/Components

### Service KPI Dashboard

**Purpose**: Daily review of volume, turnaround, and modality utilization.

**Data I need to display**:
- KPI aggregates: study volume, average/median turnaround by priority (STAT vs
  routine), modality utilization, backlog counts.
- Trend data for each KPI (direction arrows) and a freshness indicator.
- Aggregate-only by default (no patient identifiers on the dashboard).

**Actions**: set a time range, switch/refresh views, drill through a KPI to the
underlying study list.

**States to handle**: loading skeletons, empty (no data in range), error with
retry, stale-data warning if aggregates are older than the freshness target.

**Business rules affecting UI**:
- Aggregate view is the default; drill-down must be audited (who, when, what).
- Only users with analytics permission see these dashboards at all.

### Modality Capacity Heatmap

**Purpose**: Real-time view of modality utilization across time slots.

**Data I need**: scheduled vs. capacity per modality per time bucket, color-coded
utilization levels, a small time range selector.

**Actions**: hover/click a cell for details; switch date range.

### Protocol Compliance Scorecard

**Purpose**: Weekly review of protocol adherence.

**Data I need**: per-protocol compliance percentages, sequence-level gaps,
dose/benchmark comparisons. This is fed by R05 QA scores, not computed in the UI.

**Actions**: expand to gap detail, drill to study list (audited).

### SLA Tracking

**Purpose**: Verify turnaround SLAs (STAT ≤30 min, routine ≤24 h).

**Data I need**: turnaround distributions, breach counts/percentages by priority
and by site/modality, computed from study-created → report-signed timestamps.

**Actions**: filter by period and scope; drill to breached studies.

### Report Builder / Export

**Purpose**: Generate template-based reports (5 templates) and export data.

**Data I need**: the list of report templates (name, parameters) and their
parameter schemas; export job status (CSV ≤30 s / PDF ≤60 s for 10k rows).

**Actions**: pick template, fill parameters, request generation, poll status,
download result.

**States to handle**: template list empty, generation in-flight, export failure.

**Business rules affecting UI**: exports and dashboard views must be logged to
the dashboard-access audit trail.

## Uncertainties
- [ ] Are KPI aggregates precomputed server-side or computed on request? The
  freshness target (≤5 min) matters for how the UI communicates staleness.
- [ ] Does the drill-through to study list reuse the existing study search, or is
  a dedicated analytics drill endpoint needed?
- [ ] Report generation looks asynchronous — is there a status poll contract for
  exports?
- [ ] SLA computation source-of-truth: study created timestamp vs. worklist
  scheduled/performed times.
- [ ] RBAC slugs (`ANALYTICS_READ`, `ANALYTICS_EXPORT`, `REPORT_BUILD`,
  `REPORT_SCHEDULE`, `ALERT_MANAGE`) are proposed but not confirmed to exist.

## Questions for Backend
- Is there a single analytics aggregate endpoint, or should the dashboard call
  several metric endpoints and combine client-side?
- For drill-down audit: should the frontend call a dedicated audit endpoint, or
  is view/export automatically logged server-side?
- Is dashboard freshness push-based (WebSocket) or poll-based?

## Discussion Log

_(pending backend review)_
