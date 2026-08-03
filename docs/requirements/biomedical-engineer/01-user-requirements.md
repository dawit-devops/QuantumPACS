# User Requirements — Biomedical Engineer (R10)

**Version**: 1.0.0 (v3.0 scope)
**Status**: Draft
**Date**: 2026-08-02

## Functional Requirements

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-R10-01 | **Equipment Registry**: Maintain a registry of imaging equipment with identifier, modality, manufacturer, model, serial number, location, acquisition date, and operational status. | Must | Modality registry; feeds R03 capacity data |
| FR-R10-02 | **Preventive Maintenance (PM) Schedule**: Track PM due dates and completion per equipment. Show upcoming/due/overdue PM with alerting. | Must | PM calendar per modality |
| FR-R10-03 | **QC Testing Records**: Record daily/weekly QC test results per equipment (e.g., phantom, output consistency) with pass/fail and values. | Must | Structured QC data (ACR/regulatory support) |
| FR-R10-04 | **Downtime Tracking**: Log downtime events with start/end, cause category, impact (blocked exams), and resolution. Compute downtime duration and uptime %. | Must | Feeds R03 downtime impact analysis |
| FR-R10-05 | **Maintenance Tickets / Work Orders**: Create, assign, and resolve work orders for repairs; track status (open, in progress, on hold, resolved) and notes. | Must | Work-order lifecycle |
| FR-R10-06 | **Vendor Contracts & SLAs**: Record vendor service contracts, coverage terms, warranty end dates, and response SLAs per equipment. | Should | Contract registry |
| FR-R10-07 | **Fault Alerting**: Surface real-time alerts when an equipment fault or QC failure is recorded, so engineers can act promptly. | Should | Alert + notification wiring |
| FR-R10-08 | **Uptime & Utilization Reporting**: Report uptime %, downtime by cause, PM compliance %, and QC failure rates. Feed the R03 Service Director dashboards. | Must | Aggregate analytics |
| FR-R10-09 | **Parts & Consumables Inventory**: Track replacement parts and consumables with stock levels and low-stock alerts. | Could | Inventory module |
| FR-R10-10 | **Equipment Change Audit**: Audit all registry/status changes (who, what, when) for compliance. | Must | Audit log integration |

## Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-R10-01 | Equipment/dashboard screens load time | LCP ≤ 2.5s, INP ≤ 200ms | Lighthouse CI, RUM |
| NFR-R10-02 | Fault alert delivery latency | ≤ 30s from event | Synthetic probe |
| NFR-R10-03 | Dashboard data freshness | ≤ 5min staleness | Synthetic probe |
| NFR-R10-04 | Uptime computation accuracy | Uptime % reconciles with audit events | DB reconciliation |
| NFR-R10-05 | WCAG 2.2 AA compliance | 100% (dashboard + forms) | axe-core CI + manual |
| NFR-R10-06 | Color-blind-safe charts | No red/green-only encoding | Visual audit |

## Codebase Status (verified 2026-08-03)

**GATED**: All FR-R10-NN equipment requirements are aspirational v3.0 — no equipment
registry, PM/QC, downtime, ticket, vendor, or alert routes/endpoints exist.
Biomedical-engineer accounts today have only Files/metrics read-only views. Requires
new backend equipment module + permissions flagged to backend. See artifacts 04/07/08.

## Assumptions & Constraints

- A1: Equipment downtime data must be linkable to study/exam impact (which exams were blocked).
- A2: Vendor contracts are recorded metadata; no external vendor-system integration in v3.
- A3: R10 metrics (uptime, PM compliance) are consumed read-only by R03 dashboards.
- A4: No PHI is required by this role — equipment data is not patient data.
