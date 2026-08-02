# Backend Requirements: R10 Biomedical Engineer

## Context

The Biomedical Engineer maintains imaging equipment: equipment registry, PM
schedules, QC testing, downtime tracking, maintenance tickets, vendor contracts,
fault alerting, uptime/utilization reporting, and parts inventory. This role
consumes **no PHI** — equipment data is not patient data. Feeds R03 Service
Director capacity/downtime dashboards. No equipment module exists in the
codebase — fully GATED.

**Screens (existing)**: none — biomedical-engineer accounts currently have only
the Files study browser + Metrics dashboard in read-only mode.

**Screens (new/planned — all GATED on an equipment backend)**: Equipment
Registry, PM Schedule, QC Records, Downtime Tracking, Maintenance Tickets,
Vendor Contracts, Fault Alerts, Uptime/Utilization Reports, Parts Inventory.

**Personas**: P10 (Biomedical Engineer). **Access tier**: equipment read/write
(`EQUIPMENT_READ`/`EQUIPMENT_WRITE`, proposed).

## Screens/Components

### Equipment Registry

**Purpose**: Maintain the authoritative list of imaging equipment.

**Data I need to display**: identifier, modality, manufacturer, model, serial
number, location, acquisition date, operational status.

**Actions**: CRUD equipment records; every change audited (who, what, when).

**States to handle**: loading, empty, error with retry.

**Business rules affecting UI**: modality registry feeds R03 capacity data;
status drives PM/QC actions.

### PM Schedule / QC Records

**Purpose**: Track preventive maintenance and QC testing.

**Data I need**: PM due/overdue/upcoming per equipment, QC results (phantom,
output consistency) with pass/fail + values.

**Actions**: log QC results, mark PM complete, surface overdue alerts.

**States to handle**: calendar/schedule view, overdue highlighting,
color-blind-safe pass/fail encoding (never red/green alone).

### Downtime / Tickets / Vendor Contracts

**Purpose**: Track failures and repair lifecycle.

**Data I need**: downtime events (start/end, cause, impacted exams), work orders
(status open/in-progress/on-hold/resolved), vendor contracts (coverage, warranty
end, response SLAs).

**Actions**: create/assign/resolve tickets, log downtime, record contract terms.

**Business rules affecting UI**: downtime must be linkable to study/exam impact
(which exams were blocked); metrics (uptime, PM compliance) are consumed
read-only by R03.

### Fault Alerting / Reports

**Purpose**: Proactive alerting and aggregate reporting.

**Data I need**: real-time fault/QC-failure alerts (≤30s), uptime % by cause, PM
compliance %, QC failure rates.

**Actions**: view alerts, generate uptime/utilization reports.

**States to handle**: alert badge, report empty/loading/error.

## Uncertainties

- [ ] **Entire equipment module is GATED** — no equipment, PM/QC, downtime,
  ticket, vendor, or alert endpoints exist. Must be raised with backend.
- [ ] Is downtime linked to exams via study UIDs, and does the UI need that
  linkage surfaced?
- [ ] Do vendor contracts require any external-system integration, or is all
  metadata recorded locally?
- [ ] Permission slugs (`EQUIPMENT_READ`/`EQUIPMENT_WRITE`) proposed but not in
  `permissions.py`.

## Questions for Backend

- What is the roadmap for equipment endpoints (registry, PM/QC, downtime,
  tickets, alerts)?
- How should uptime % be computed — from audit events, or a dedicated downtime
  aggregate endpoint?
- Should fault alerts be pushed via the existing notification/WebSocket path?

## Discussion Log

_(pending backend review)_
