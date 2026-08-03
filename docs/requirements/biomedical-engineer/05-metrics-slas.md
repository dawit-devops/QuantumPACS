# Metrics & SLAs — Biomedical Engineer (R10)

| ID | Metric | Target | Measurement | Frequency | Owner |
|----|--------|--------|-------------|-----------|-------|
| M-R10-01 | Equipment registry LCP | ≤ 2.5s | Lighthouse CI, RUM | Per release | Frontend |
| M-R10-02 | Fault alert delivery | ≤ 30s | Synthetic probe | Daily | Backend |
| M-R10-03 | Dashboard freshness | ≤ 5min staleness | Synthetic probe | Daily | Backend |
| M-R10-04 | PM compliance | ≥ 95% on-time | PM schedule DB query | Weekly | Operations |
| M-R10-05 | Downtime logging completeness | ≥ 99% of faults have a logged event | Registry vs alert cross-check | Weekly | Operations |
| M-R10-06 | Uptime reporting accuracy | Reconciles with audit events | DB reconciliation | Monthly | Operations |
| M-R10-07 | QC failure escalation | ≤ 30s to alert | Alert latency probe | Daily | Backend |

## SLA Tiers

- **Availability**: 99.9% for equipment registry during business hours.
- **Support**: P1 (equipment outage blocks exams) response ≤ 15min; P2 ≤ 4h.
- **PM compliance**: ≥ 95% on-time, with overdue items escalated to R03 monthly.
