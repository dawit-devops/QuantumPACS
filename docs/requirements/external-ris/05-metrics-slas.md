# Metrics & SLAs — External RIS (R15)

| ID | Metric | Target | Measurement | Frequency | Owner |
|----|--------|--------|-------------|-----------|-------|
| M-R15-01 | Message ingestion latency | ≤ 2s p95 | Synthetic probe | Daily | Backend |
| M-R15-02 | ACK response time | ≤ 5s | Synthetic probe | Daily | Backend |
| M-R15-03 | Throughput | ≥ 100 msg/min sustained | Load test | Per release | Backend |
| M-R15-04 | Error rate | ≤ 0.5% of messages | Message store query | Weekly | Integration |
| M-R15-05 | Dead-letter backlog resolution | ≤ 24h from creation | Queue query | Daily | Integration |
| M-R15-06 | Integration availability | 99.9% | Uptime monitoring | Monthly | Backend |
| M-R15-07 | Report delivery (ORU) latency | ≤ 5min from finalize | Delivery probe | Daily | Integration |

## SLA Tiers

- **Availability**: 99.9% for the HL7 listener during clinical hours.
- **Reliability**: retry 3x → dead-letter; reconciliation backlog resolved within 24h.
- **Support**: P1 (integration down) response ≤ 15min; P2 ≤ 4h.
