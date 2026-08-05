# Metrics & SLAs — Radiology Service Cashier (R09)

| ID | Metric | Target | Measurement | Frequency | Owner |
|----|--------|--------|-------------|-----------|-------|
| M-R09-01 | Billing screen LCP | ≤ 2.5s | Lighthouse CI, RUM | Per release | Frontend |
| M-R09-02 | Payment recording latency | ≤ 500ms optimistic | Backend timing | Continuous | Backend |
| M-R09-03 | Receipt generation | ≤ 1s | Backend timing | Continuous | Backend |
| M-R09-04 | Duplicate-charge rate | 0 (idempotency enforced) | Audit log scan | Weekly | Backend |
| M-R09-05 | Shift-close variance rate | ≤ 1% of shifts with variance | Reconciliation records | Weekly | Operations |
| M-R09-06 | PCI scope compliance | No PAN stored | Security audit | Quarterly | Security |
| M-R09-07 | Denied-claim action lag | Flag within 24h of denial | Claims feed check | Daily | Operations |

## SLA Tiers

- **Availability**: 99.9% for billing/payment during business hours.
- **Support**: P1 (payments down) incident response ≤ 15min; P2 ≤ 4h.
- **Reconciliation**: shift close must complete or escalate within 30min of end of shift.
