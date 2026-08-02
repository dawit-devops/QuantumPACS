# User Stories — Biomedical Engineer (R10)

## US-R10-01: Maintain the equipment registry
**Story**: As a biomedical engineer, I want to add and update equipment records, so that I always know what is in service and where.
**Priority**: Must

### Acceptance Criteria
- **Given** I open the registry, **when** it loads, **then** equipment rows render with status within 2.5s LCP.
- **Given** I create or update equipment, **when** I save, **then** the change persists and an audit entry is recorded.
- **Accessibility**: table keyboard-navigable; contrast ≥ 4.5:1.

## US-R10-02: See and complete PM due items
**Story**: As a biomedical engineer, I want a due/overdue PM list, so that equipment never falls out of compliance.
**Priority**: Must

### Acceptance Criteria
- **Given** PM schedules exist, **when** I open the PM queue, **then** due and overdue items render with priority.
- **Given** I complete a PM, **when** I record it, **then** the schedule updates and compliance % recalculates.
- **Performance**: queue render INP ≤ 200ms.

## US-R10-03: Record QC results with failure escalation
**Story**: As a biomedical engineer, I want to record QC results and escalate failures, so that failing equipment is flagged and removed from service.
**Priority**: Must

### Acceptance Criteria
- **Given** I enter a QC result, **when** it fails, **then** the equipment status flags and a fault alert is triggered within 30s.
- **Given** prior values exist, **when** the form opens, **then** previous values prefill for comparison.

## US-R10-04: Log and close downtime with impact
**Story**: As a biomedical engineer, I want to log downtime with exam impact, so that the service director sees the real cost.
**Priority**: Must

### Acceptance Criteria
- **Given** an equipment fault, **when** I start downtime, **then** an open event appears and blocks exam scheduling on that modality.
- **Given** I close the event with cause and resolution, **then** duration and uptime % update and R03 metrics refresh within 5min.
- **Given** an event remains open beyond 24h, **then** it appears in an "open events" reminder list.

## US-R10-05: View uptime and compliance reports
**Story**: As a biomedical engineer, I want uptime and PM compliance reports, so that I can report to leadership.
**Priority**: Must

### Acceptance Criteria
- **Given** report filters, **when** I request a report, **then** uptime by cause, PM compliance %, and QC failure rates render with a date range.
- **Given** a chart uses thresholds, **when** it renders, **then** no red/green-only encoding is used (color-blind-safe).

## US-R10-06: Manage vendor contracts
**Story**: As a biomedical engineer, I want to record vendor contracts and response SLAs, so that I know when coverage expires.
**Priority**: Should

### Acceptance Criteria
- **Given** a contract record, **when** saved, **then** coverage terms and warranty end persist.
- **Given** a warranty is within 90 days of expiry, **when** the registry renders, **then** an expiry warning appears.

## Dependencies
- US-R10-02/03 → PM/QC endpoints (new)
- US-R10-04 → exam scheduling integration (blocks modality when down)
- US-R10-05 → metrics aggregates (shared with R03)
