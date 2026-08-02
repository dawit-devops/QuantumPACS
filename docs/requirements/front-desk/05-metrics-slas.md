# Metrics & SLAs — Front Desk / Receptionist (R08)

| ID | Metric | Target | Measurement | Frequency | Owner |
|----|--------|--------|-------------|-----------|-------|
| M-R08-01 | Registration/search screen LCP | ≤ 2.5s | Lighthouse CI, RUM | Per release | Frontend |
| M-R08-02 | Patient search round-trip | ≤ 500ms p95 | Synthetic probe | Daily | Backend |
| M-R08-03 | Registration save (optimistic) | ≤ 500ms | Backend timing | Continuous | Backend |
| M-R08-04 | Duplicate-registration rate | ≤ 0.5% of new registrations | DB query on patient records | Monthly | Clinical ops |
| M-R08-05 | Check-in to visible-in-clinical-workflow | ≤ 5s staleness | WebSocket event delta | Continuous | Backend |
| M-R08-06 | HL7 ADT sync delivery | ≤ 60s from save, retry until delivered | Message dashboard | Daily | Integration |
| M-R08-07 | Waiting queue staleness | ≤ 5s | Synthetic probe | Daily | Backend |

## SLA Tiers

- **Availability**: 99.9% for registration/search during business hours.
- **Support**: incident response ≤ 15min for P1 (registration unavailable), ≤ 4h for P2.
- **Data quality**: demographic record accuracy audited monthly (R05).
