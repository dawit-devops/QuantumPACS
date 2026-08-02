# Requirements Package — R10 Biomedical Engineer

| Field | Value |
|-------|-------|
| **Version** | 1.1.1 |
| **Status** | draft |
| **Generated** | 2026-08-03 |
| **Changelog** | [CHANGELOG.md](CHANGELOG.md) |

## Codebase Alignment (verified 2026-08-03)

**Presentation layer**: role-based; see artifact 04 — "Role-Based Routing &
Navigation". Biomedical-engineer accounts today have only Files/metrics read-only
views.

**GATED**: all equipment features — equipment inventory, PM schedules, QC testing,
downtime tracking, maintenance tickets, vendor contracts, fault alerting. No
equipment routes or endpoints exist; requires new backend module + permissions
flagged to backend.

## Role Summary

**Persona**: Biomedical engineer maintaining imaging equipment: registry, PM/QC,
downtime tracking, work orders, vendor contracts, and reporting.
**Access tier**: Equipment health (no PHI required).
**Context**: Supports modality availability; downtime and PM data feed R03
service-director dashboards.

## Artifact Index

| # | Artifact | File |
|---|----------|------|
| 01 | User Requirements | `01-user-requirements.md` |
| 02 | End-to-End Workflow Maps | `02-workflow-maps.md` |
| 03 | User Stories | `03-user-stories.md` |
| 04 | UI/UX Requirements | `04-ui-ux-requirements.md` |
| 05 | Metrics & SLAs | `05-metrics-slas.md` |
| 06 | Acceptance Criteria (validator-gated) | `06-acceptance-criteria.md` |
| 07 | Traceability Matrix | `07-traceability.md` |
| 08 | Implementation Roadmap | `08-implementation-roadmap.md` |

## Cross-Role Dependencies

- **R03 Service Director** — consumes uptime, PM compliance, and downtime impact metrics.
- **R04 Service Coordinator** — downtime blocks modality scheduling.
- **R06/R07 Technologist/Technician** — equipment status visible in worklists.
- **R01/R02 Admin** — equipment registry management, audit retention.

## Flagged Gaps (backend — must be raised before sprint commitment)

- No equipment registry, PM/QC, downtime, or work-order endpoints exist.
- No fault-alert event wiring (notifications).
- No integration between downtime events and exam scheduling (block modality when down).
- Equipment metrics aggregates for R03 are not built.
