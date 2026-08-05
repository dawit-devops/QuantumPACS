# User Requirements — Radiology Service Director (R03)

**Version**: 1.0.0 (v3.0 scope)
**Status**: Final
**Date**: 2026-08-02

---

## Functional Requirements (v3.0 Must Priority)

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-R03-01 | **Service KPI Dashboard**: Display aggregated KPIs — study volume (daily/weekly/monthly), turnaround time (STAT/routine), modality utilization %, staffing coverage. Auto-refresh ≤5min. Extends existing `/v2/dashboard/metrics` endpoint. | Must | Reuses Card, Table components; new `KPICard` widget |
| FR-R03-02 | **Real-time Modality Capacity Heatmap**: Calendar heatmap showing scheduled vs actual vs capacity per modality per timeslot. Color-coded (green/yellow/red/critical). WebSocket/SSE for ≤5min staleness. | Must | New `HeatmapCell` component; `events:ingestion` stream consumer |
| FR-R03-03 | **Protocol Compliance Scorecard**: Per-modality/protocol compliance % against ACR benchmarks. Shows compliant/non-compliant counts, dose metrics. Drill-through to study list. Consumes R05 QA structured data. | Must | New `ScorecardTable` component; protocol registry needed |
| FR-R03-04 | **SLA Tracking & Breach Alerts**: STAT turnaround ≤30min p95, routine ≤24h p95. Real-time breach list with study ID, modality, minutes overdue, responsible role. Visual indicator (badge) on KPI card. | Must | Turnaround = `report.signed_at` - `study.created`; breach = threshold exceeded |
| FR-R03-05 | **KPI Drill-through to Study List**: Click any KPI card → opens Files table pre-filtered to that metric (e.g., click "CT Utilization 85%" → filter modality=CT). URL bookmarkable with filter state. Reuses existing Files table component. | Must | Leverages `Files.tsx` search/filter; URL encoding per `UX-Functionality.md` |
| FR-R03-10 | **Report Builder (Template-based)**: Select from 5 pre-defined templates → set parameters (date range, modality, filters) → generate CSV/PDF. Templates: Monthly Volume, Turnaround by Modality, Protocol Compliance, Capacity Utilization, SLA Breach Detail. | Must | Modal workflow; not drag-drop canvas; streams export from backend |
| FR-R03-12 | **Widget Export**: All dashboard widgets exportable as CSV (≤30s for 10k rows) and PDF with charts (≤60s). Streaming backend response to avoid browser memory pressure. | Must | Backend streams; frontend shows progress; `Content-Disposition: attachment` |
| FR-R03-14 | **Dashboard Access Audit**: All dashboard views, widget interactions, exports, and report generations logged with user ID, timestamp, widget/template, tenant. HIPAA minimum necessary — no PHI in audit unless drill-through accessed (then justification required). | Must | Extends `file_changes` audit pattern; new `dashboard_audit` table |
| FR-R03-15 | **RBAC Service Director Role**: New built-in role `service_director` with permissions: `METRICS_READ`, `ANALYTICS_READ`, `ANALYTICS_EXPORT`, `REPORT_BUILD`. No `FILE_WRITE`, `USER_ADMIN`, `TENANT_*`. Tenant-scoped. | Must | Add to `backend/api/permissions.py` BUILT_IN_ROLES |

---

## Functional Requirements (v3.1 Deferred — Should/Could)

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-R03-06 | **Staffing vs Demand Forecast (7-day)**: Projected study volume from R15 RIS schedule vs current staffing. Heatmap with gap highlighting. | Should | Requires HL7 ORM future-dated procedures |
| FR-R03-07 | **Equipment Downtime Impact Analysis**: Correlate R10 equipment downtime events with capacity gaps and SLA breaches. | Should | Equipment registry integration |
| FR-R03-08 | **Protocol Gap Analysis**: Identify studies missing required sequences per protocol (e.g., CT Chest without contrast phase). | Should | DICOM tag validation rules engine |
| FR-R03-09 | **SLA Breach Root-Cause Categorization**: Multi-factor attribution — technologist delay, radiologist delay, system downtime, external dependency. | Could | Requires timestamped workflow events |
| FR-R03-11 | **Scheduled Report Delivery**: Email PDF/CSV on cron; pin to dashboard; webhook delivery. | Could | Background job scheduler (Celery/Redis) |
| FR-R03-13 | **Configurable Alerting**: Per-KPI threshold rules with notification channels (in-app, email, webhook). | Could | Alert rule engine; `events:notify` stream |

---

## Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-R03-01 | Dashboard initial load (LCP) | ≤ 2.5s | Lighthouse CI, RUM |
| NFR-R03-02 | Widget data freshness (auto-refresh) | ≤ 5min staleness | Synthetic probe (Grafana) |
| NFR-R03-03 | Drill-through navigation | ≤ 1s | Playwright timing |
| NFR-R03-04 | Export generation (10k rows CSV) | ≤ 30s | Backend timing |
| NFR-R03-05 | Export generation (PDF with charts) | ≤ 60s | Backend timing |
| NFR-R03-06 | Concurrent dashboard users | ≥ 20 | k6 WebSocket scenario |
| NFR-R03-07 | API p95 latency (analytics endpoints) | ≤ 300ms | k6 nightly |
| NFR-R03-08 | WCAG 2.2 AA compliance | 100% pass | axe-core CI + manual |
| NFR-R03-09 | Color-blind safe palettes (charts) | All charts | Manual + color-blind simulator |
| NFR-R03-10 | Keyboard operability (all widgets) | 100% | Tab navigation test script |

---

## Codebase Status (verified 2026-08-03)

**GATED**: All FR-R03-NN analytics/reporting requirements are aspirational v3.0 —
no `/analytics/*` or `/reports/*` routes or endpoints exist in the codebase. Today
only `GET /metrics` + `/dashboard/metrics` are available (read-only). Requires new
backend endpoints + `ANALYTICS_*`/`REPORT_*` permissions flagged to backend. See
artifacts 04/07/08 for the verified presentation-layer mapping.

## Assumptions & Constraints

| # | Assumption / Constraint | Impact |
|---|-------------------------|--------|
| A1 | PHI: Aggregates only in dashboards; drill-through requires justification audit log | FR-R03-14, NFR-R03-08 |
| A2 | 7 new API endpoints required (flagged for `frontend-to-backend-requirements`) | FR-R03-01 through FR-R03-10 |
| A3 | Real-time updates: WebSocket/SSE for capacity heatmap; polling acceptable for KPIs (5min) | FR-R03-02, NFR-R03-02 |
| A4 | R15 RIS: HL7 ORM^O01 v2.5 provides scheduled procedures; standard field mapping used | FR-R03-02, FR-R03-06 |
| A5 | R16 EMR: FHIR R4 Patient provides demographics; no PHI in aggregate dashboards | FR-R03-01, FR-R03-05 |
| A6 | R05 QA: Structured QA scores stored in DB; protocol registry schema extension may be needed | FR-R03-03, FR-R03-08 |
| A7 | Report Builder: Template-based only (5 templates); no custom drag-drop canvas in v3.0 | FR-R03-10 |
| A8 | Export: Streaming backend response required; no client-side PDF generation | FR-R03-12 |
| A9 | Design system: Extend existing tokens; no one-off styling | All UI requirements |
| A10 | Tenant isolation: All analytics scoped to tenant via `X-Tenant-ID` / JWT tenant claim | All FRs |

---

## API Gap Summary (for Backend Team)

| Endpoint | Method | Description | Response Shape |
|----------|--------|-------------|----------------|
| `/api/v2/analytics/dashboard` | GET | KPI aggregates | `{totals, modalities, ingestion_30d, turnaround_stats}` |
| `/api/v2/analytics/capacity` | GET | Heatmap + scheduled counts | `{date, modality, scheduled, capacity, utilization_pct}[]` |
| `/api/v2/analytics/protocol-compliance` | GET | Scorecard + gaps | `{protocol_id, name, modality, compliance_pct, gaps[]}[]` |
| `/api/v2/analytics/sla` | GET | Turnaround + breaches | `{stat_p95, routine_p95, breaches[{study_id, type, minutes}]}[]` |
| `/api/v2/reports/generate` | POST | Template report generation | Stream CSV/PDF |
| `/api/v2/reports/templates` | GET | List report templates | `{id, name, description, parameters[]}[]` |
| `/api/v2/audit/dashboard-access` | POST | Log dashboard view/export | `{user_id, widget, action, timestamp}` |

---

## Permission Additions (backend/api/permissions.py)

```python
# New permission slugs
ANALYTICS_READ = 'ANALYTICS_READ'
ANALYTICS_EXPORT = 'ANALYTICS_EXPORT'
REPORT_BUILD = 'REPORT_BUILD'
REPORT_SCHEDULE = 'REPORT_SCHEDULE'
ALERT_MANAGE = 'ALERT_MANAGE'

# Add to PERMISSION_GROUPS
PERMISSION_GROUPS['Analytics'] = [
    ANALYTICS_READ, ANALYTICS_EXPORT, REPORT_BUILD, REPORT_SCHEDULE, ALERT_MANAGE
]

# New built-in role
BUILT_IN_ROLES['service_director'] = [
    Permission.METRICS_READ.value,
    ANALYTICS_READ,
    ANALYTICS_EXPORT,
    REPORT_BUILD,
]
```