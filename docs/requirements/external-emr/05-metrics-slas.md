# Metrics & SLAs — External EMR (R16)

| ID | Metric | Target | Measurement | Frequency | Owner |
|----|--------|--------|-------------|-----------|-------|
| M-R16-01 | Demographics ingestion latency | ≤ 2s p95, non-blocking | Synthetic probe | Daily | Backend |
| M-R16-02 | FHIR read latency | ≤ 200ms p95 | Synthetic probe | Daily | Backend |
| M-R16-03 | Throughput | ≥ 100 req/min sustained | Load test | Per release | Backend |
| M-R16-04 | Error rate | ≤ 0.5% of requests | Request log query | Weekly | Integration |
| M-R16-05 | Dead-letter backlog resolution | ≤ 24h | Queue query | Daily | Integration |
| M-R16-06 | Integration availability | 99.9% | Uptime monitoring | Monthly | Backend |
| M-R16-07 | Report delivery latency | ≤ 5min from finalize | Delivery probe | Daily | Integration |

## SLA Tiers

- **Availability**: 99.9% for FHIR/ADT endpoints during clinical hours.
- **Reliability**: retry 3x → dead-letter; backlog resolved ≤ 24h.
- **Support**: P1 (integration down) response ≤ 15min; P2 ≤ 4h.
