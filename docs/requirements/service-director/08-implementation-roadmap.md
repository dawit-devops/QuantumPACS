# Implementation Roadmap — Service Director (R03)

## Artifact Status Overview

| # | Artifact | File | Status |
|---|----------|------|--------|
| 01 | User Requirements | `01-user-requirements.md` | done |
| 02 | Workflow Maps | `02-workflow-maps.md` | done |
| 03 | User Stories | `03-user-stories.md` | done |
| 04 | UI/UX Requirements | `04-ui-ux-requirements.md` | done |
| 05 | Metrics & SLAs | `05-metrics-slas.md` | done |
| 06 | Acceptance Criteria | `06-acceptance-criteria.md` | done |
| 07 | Traceability Matrix | `07-traceability.md` | partial |
| 08 | Implementation Roadmap | `08-implementation-roadmap.md` | partial |

## FR/NFR Implementation Status

### Missing (Not Started)

| FR/NFR ID | Summary | Reason | AC | Effort |
|-----------|---------|--------|----|--------|
| FR-R03-01 | **Service KPI Dashboard**: Display aggregated KPIs — study volume (daily/weekly/ | Not yet scoped | — | L |
| FR-R03-02 | **Real-time Modality Capacity Heatmap**: Calendar heatmap showing scheduled vs a | Not yet scoped | — | L |
| FR-R03-03 | **Protocol Compliance Scorecard**: Per-modality/protocol compliance % against AC | Not yet scoped | — | L |
| FR-R03-04 | **SLA Tracking & Breach Alerts**: STAT turnaround ≤30min p95, routine ≤24h p95.  | Not yet scoped | — | L |
| FR-R03-05 | **KPI Drill-through to Study List**: Click any KPI card → opens Files table pre- | Not yet scoped | — | L |
| FR-R03-06 | **Staffing vs Demand Forecast (7-day)**: Projected study volume from R15 RIS sch | Not yet scoped | — | L |
| FR-R03-07 | **Equipment Downtime Impact Analysis**: Correlate R10 equipment downtime events  | Not yet scoped | — | L |
| FR-R03-08 | **Protocol Gap Analysis**: Identify studies missing required sequences per proto | Not yet scoped | — | L |
| FR-R03-09 | **SLA Breach Root-Cause Categorization**: Multi-factor attribution — technologis | Not yet scoped | — | L |
| FR-R03-10 | **Report Builder (Template-based)**: Select from 5 pre-defined templates → set p | Not yet scoped | — | L |
| FR-R03-11 | **Scheduled Report Delivery**: Email PDF/CSV on cron; pin to dashboard; webhook  | Not yet scoped | — | L |
| FR-R03-12 | **Widget Export**: All dashboard widgets exportable as CSV (≤30s for 10k rows) a | Not yet scoped | — | L |
| FR-R03-13 | **Configurable Alerting**: Per-KPI threshold rules with notification channels (i | Not yet scoped | — | L |
| FR-R03-14 | **Dashboard Access Audit**: All dashboard views, widget interactions, exports, a | Not yet scoped | — | L |
| FR-R03-15 | **RBAC Service Director Role**: New built-in role `service_director` with permis | Not yet scoped | — | L |
| NFR-R03-01 | Dashboard initial load (LCP) | Not yet scoped | — | L |
| NFR-R03-02 | Widget data freshness (auto-refresh) | Not yet scoped | — | L |
| NFR-R03-03 | Drill-through navigation | Not yet scoped | — | L |
| NFR-R03-04 | Export generation (10k rows CSV) | Not yet scoped | — | L |
| NFR-R03-05 | Export generation (PDF with charts) | Not yet scoped | — | L |
| NFR-R03-06 | Concurrent dashboard users | Not yet scoped | — | L |
| NFR-R03-07 | API p95 latency (analytics endpoints) | Not yet scoped | — | L |
| NFR-R03-08 | WCAG 2.2 AA compliance | Not yet scoped | — | L |
| NFR-R03-09 | Color-blind safe palettes (charts) | Not yet scoped | — | L |
| NFR-R03-10 | Keyboard operability (all widgets) | Not yet scoped | — | L |

## Blocking Dependencies

| Blocking Dependency | Blocks | AC | Impact |
|---------------------|--------|----|--------|

## Next Steps (highest priority)

2. **Scope missing requirements** — 25 FR/NFRs not yet implemented
3. **Update roadmap each sprint** as FR/NFR status changes
