# Acceptance Criteria — External RIS (R15)

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R15-01 | FR-R15-01 | Given an ORM^O01 order, when processed, then the order/worklist entry persists within 2s and an ACK returns within 5s; duplicates merge by accession | Integration test | Must pass 6.4 |
| AC-R15-02 | FR-R15-02 | Given a reschedule/cancel message, when applied, then the worklist entry reflects the change | Integration test | Must pass 6.4 |
| AC-R15-03 | FR-R15-03 | Given an exam status change, when published, then ORM/ORU with accession + study UID is delivered and acked; failure retries 3x then dead-letters | Integration test | Must pass 6.4 |
| AC-R15-04 | FR-R15-04 | Given a finalized report, when published, then ORU^R01 delivers within 5min and is acked; failures retain in dead-letter | Integration test | Must pass 6.4 |
| AC-R15-05 | FR-R15-05 | Given a C-FIND MWL query, when processed, then matching entries return (≤1000); empty set returns cleanly | Integration test | Must pass 6.4 |
| AC-R15-06 | FR-R15-06 | Given any inbound message, when received, then an ACK/NAK returns with correct detail; malformed messages NAK with error | Integration test | Must pass 6.4 |
| AC-R15-07 | FR-R15-07 | Given a processing failure, when exhausted, then the message routes to dead-letter and appears in the reconciliation UI | Integration test + E2E | Must pass 6.4 |
| AC-R15-08 | FR-R15-08 | Given the HL7 dashboard, when filtered, then message details render; dead-lettered messages can be replayed | Automated E2E | Must pass 6.4 |
| AC-R15-09 | FR-R15-09 | Given config changes, when saved, then endpoints/credentials/mappings persist and connectivity tests report status | Automated E2E | Must pass 6.4 |
| AC-R15-10 | FR-R15-10 | Given the metrics view, when rendered, then volume, ack latency, error rate, and backlog render with a time range | Automated E2E | Must pass 6.4 |
| AC-R15-11 | NFR-R15-01 | Given sustained load, when measured, then ingestion latency ≤ 2s p95 and throughput ≥ 100 msg/min | Load test | Must pass 6.4 |
| AC-R15-12 | NFR-R15-06 | Given all messages, when audited, then 100% are logged with direction/type/control ID/result | Audit log scan | Must pass 6.4 |
| AC-R15-13 | NFR-R15-07 | Given the HL7 admin dashboard, when measured, then LCP ≤ 2.5s and INP ≤ 200ms | Lighthouse CI, RUM | Must pass 6.4 |
| AC-R15-14 | NFR-R15-02 | Given an inbound message, when processed, then an ACK returns within 5s | Synthetic probe | Must pass 6.4 |
| AC-R15-15 | NFR-R15-03 | Given a message stream, when measured, then ordering is preserved per control ID | Integration test | Must pass 6.4 |
| AC-R15-16 | NFR-R15-04 | Given sustained load, when measured, then throughput ≥ 100 msg/min | Load test | Must pass 6.4 |
| AC-R15-17 | NFR-R15-05 | Given the HL7 listener, when measured, then availability ≥ 99.9% | Uptime monitoring | Must pass 6.4 |

## Excluded Scope / Out of Scope

- FHIR R4 order exchange (R16/`fhir-r4-api`) — RIS uses HL7 + MWL.
- DICOM image transfer (R17).
- Clinical reading workflows (R12/R18).
- Billing/claims exchange (R09).
