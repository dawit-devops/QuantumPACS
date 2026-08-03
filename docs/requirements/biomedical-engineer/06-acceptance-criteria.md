# Acceptance Criteria — Biomedical Engineer (R10)

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R10-01 | FR-R10-01 | Given the registry, when it loads, then equipment rows render with status within 2.5s; create/update persists with an audit entry | Automated E2E | Must pass 6.4 |
| AC-R10-02 | FR-R10-02 | Given PM schedules, when the queue opens, then due/overdue items render; completing a PM updates compliance % | Automated E2E | Must pass 6.4 |
| AC-R10-03 | FR-R10-03 | Given a QC result, when it fails, then equipment status flags and a fault alert triggers within 30s | Automated E2E + probe | Must pass 6.4 |
| AC-R10-04 | FR-R10-04 | Given a fault, when downtime starts, then an open event appears and blocks exam scheduling; closing computes duration and uptime % | Automated E2E | Must pass 6.4 |
| AC-R10-05 | FR-R10-05 | Given a work order, when created/assigned/resolved, then status transitions persist with notes and audit | Automated E2E | Must pass 6.4 |
| AC-R10-06 | FR-R10-06 | Given a contract record, when saved, then coverage and warranty end persist; expiry warnings appear within 90 days of end | Automated E2E | Must pass 6.4 |
| AC-R10-07 | FR-R10-07 | Given a fault or QC failure, when recorded, then an alert is delivered within 30s | Synthetic probe | Must pass 6.4 |
| AC-R10-08 | FR-R10-08 | Given report filters, when requested, then uptime by cause, PM compliance %, and QC failure rates render with date range; R03 can consume the aggregate | Automated E2E + integration test | Must pass 6.4 |
| AC-R10-09 | FR-R10-09 | Given inventory records, when stock falls below threshold, then a low-stock alert appears | Automated E2E | Must pass 6.4 |
| AC-R10-10 | FR-R10-10 | Given any registry/status change, when saved, then who/what/when is recorded in the audit log | Security audit + E2E | Must pass 6.4 |
| AC-R10-11 | NFR-R10-01 | Given dashboard screens, when measured, then LCP ≤ 2.5s and INP ≤ 200ms | Lighthouse CI, RUM | Must pass 6.4 |
| AC-R10-12 | NFR-R10-06 | Given threshold charts, when rendered, then no red/green-only encoding is used | Visual evidence | Must pass 6.4 |
| AC-R10-13 | NFR-R10-02 | Given a fault, when recorded, then alert delivery completes ≤ 30s | Synthetic probe | Must pass 6.4 |
| AC-R10-14 | NFR-R10-03 | Given dashboard data, when rendered, then freshness ≤ 5min staleness | Synthetic probe | Must pass 6.4 |
| AC-R10-15 | NFR-R10-04 | Given uptime data, when computed, then it reconciles with audit events | DB reconciliation | Must pass 6.4 |
| AC-R10-16 | NFR-R10-05 | Given the equipment UI, when audited, then WCAG 2.2 AA passes (keyboard, focus, contrast ≥ 4.5:1) | axe-core CI + manual | Must pass 6.4 |

## Excluded Scope / Out of Scope

- Direct modality firmware/software diagnostics (device vendor).
- Any patient data or clinical workflow access (not required for equipment health).
- Vendor-system integration for contracts or remote diagnostics (future).
- Radiologist/technologist operational workflows (R12/R06/R07).
