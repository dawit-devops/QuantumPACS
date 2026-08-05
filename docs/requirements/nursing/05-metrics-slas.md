# Metrics & SLAs — Radiology Service Nursing Team (R11)

| ID | Metric | Target | Measurement | Frequency | Owner |
|----|--------|--------|-------------|-----------|-------|
| M-R11-01 | Nursing worklist LCP | ≤ 2.5s | Lighthouse CI, RUM | Per release | Frontend |
| M-R11-02 | Worklist staleness | ≤ 5s | Synthetic probe | Daily | Backend |
| M-R11-03 | Vitals/checklist save | ≤ 500ms optimistic | Backend timing | Continuous | Backend |
| M-R11-04 | Adverse reaction escalation | ≤ 15min to physician ack | Escalation probe | Per incident | Operations |
| M-R11-05 | Contrast safety-gate compliance | 100% (no contrast without confirmation) | Audit log scan | Weekly | Operations |
| M-R11-06 | Checklist completion rate | ≥ 98% before exam | DB query on visit prep | Weekly | Operations |
| M-R11-07 | Offline sync recovery | ≤ 2min after reconnect | Synthetic offline test | Per release | Frontend |

## SLA Tiers

- **Availability**: 99.9% for worklist/vitals during clinical hours.
- **Safety**: adverse-reaction escalation acknowledgment ≤ 15min (ACR-aligned).
- **Support**: P1 (nursing workflow down) response ≤ 15min; P2 ≤ 4h.
