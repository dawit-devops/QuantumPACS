# UI/UX Requirements — Biomedical Engineer (R10)

## Role-Based Routing & Navigation (Presentation Layer)

RBAC drives the presentation layer (`hasPermission()` + `RequirePermission`, gated
`Sidebar.tsx` items). Verified against `frontend/src/`.

### Routes Accessible (codebase reality)

| Route | Screen | Access rule |
|-------|--------|-------------|
| `/` | Files / study search (read) | Any authenticated user |
| `/account` | Account | Any authenticated user |
| `/metrics` | Metrics dashboard | Any authenticated user (sidebar item) |
| Equipment registry / PM / QC / downtime | **Not accessible** | No equipment routes or endpoints exist — GATED |

### Navigation Gating (Sidebar.tsx)

| Menu item | Visible when |
|-----------|--------------|
| Files / Metrics / Account / Notifications | Always (authenticated) |
| Admin submenu | Only if granted admin `*_READ` perms |

### Functionality Gating

- **None of the equipment screens exist**: equipment inventory, PM schedules, QC
  testing, downtime tracking, maintenance tickets, vendor contracts, equipment
  fault alerting. All aspirational FRs marked `GATED` (artifacts 01/07/08) — new
  endpoints + permissions flagged to backend.
- Today a biomedical-engineer account can only browse files/metrics read-only.

## Screens & Navigation

| # | Screen | Entry Point | Purpose |
|---|--------|-------------|---------|
| 1 | Equipment Registry | Sidebar / Home | List + status of all equipment |
| 2 | Equipment Detail | Registry → row | Full record, downtime, QC, PM history |
| 3 | PM/QC Queue | Sidebar | Due/overdue PM + QC tasks |
| 4 | Downtime Console | Equipment Detail | Start/stop events, cause, impact |
| 5 | Work Orders | Sidebar | Repair tickets lifecycle |
| 6 | Reports | Sidebar | Uptime, PM compliance, QC failure rates |
| 7 | Contracts | Sidebar | Vendor contracts + warranties |

Navigation: registry-first; equipment detail is the hub (status + history tabs).

## Component & State Spec

| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| EquipmentTable | Rows | Skeleton | "No equipment" | Retry | — | — |
| StatusBadge | Status | — | — | — | Updated status | — |
| DowntimeForm | Start/stop | Spinner | — | Retry | Event closed | When already down |
| PMQueue | Due rows | Skeleton | "No PM due" | Retry | Completed | — |
| QCForm | Values | Spinner | — | Inline errors | Pass/Fail badge | On submit |
| ReportPanel | Charts | Skeleton | "No data in range" | Retry | Charts | — |

## Design System Conformance

- Tokens: `--color-success`, `--color-danger`, `--color-warning`, `--bg-surface`, `--radius-sm`, chart tokens from `docs/design-tokens.json`.
- Components: reuse `Table`, `Form`, `Statistic`, `Progress`, `Tag`, `DatePicker`; new `DowntimeConsole`, `PMQueue`, `QCForm` specs.
- Charts must use accessible color ramps (no red/green-only).

## Accessibility Requirements

- WCAG 2.2 AA: keyboard operability, focus rings, contrast ≥ 4.5:1, screen-reader labels on status badges, chart data also available in tabular form.

## Responsive Behavior

- Desktop-first; tablet for rounding with quick downtime/QC actions; no mobile requirement.

## UX Principles Applied

- Two-tap downtime start/stop; cause picklists over free text; prior-value prefills; explicit status feedback on every save; color-blind-safe data visualization.
