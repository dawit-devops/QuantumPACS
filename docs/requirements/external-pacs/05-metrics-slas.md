# Metrics & SLAs — External PACS (R17)

| ID | Metric | Target | Measurement | Frequency | Owner |
|----|--------|--------|-------------|-----------|-------|
| M-R17-01 | C-STORE ack latency | ≤ 10s per instance p95 | Synthetic probe | Daily | Backend |
| M-R17-02 | C-FIND query timeout | 30s cap | Synthetic probe | Daily | Backend |
| M-R17-03 | C-MOVE retry semantics | 2x retry on failure | Integration test | Per release | Backend |
| M-R17-04 | Storage throughput | ≥ 100 MB/s sustained | Load test | Per release | Backend |
| M-R17-05 | Transfer error rate | ≤ 0.5% of operations | Transfer log query | Weekly | Integration |
| M-R17-06 | DICOM service availability | 99.9% | Uptime monitoring | Monthly | Backend |
| M-R17-07 | Routing delivery success | ≥ 99% of routed instances | Routing log query | Weekly | Integration |

## SLA Tiers

- **Availability**: 99.9% for DICOM SCP + DICOMweb endpoints during clinical hours.
- **Reliability**: C-MOVE retry 2x; C-FIND timeout 30s; C-STORE NAK with reason.
- **Support**: P1 (store/retrieve down) response ≤ 15min; P2 ≤ 4h.
