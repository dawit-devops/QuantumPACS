# Acceptance Criteria — External EMR (R16)

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R16-01 | FR-R16-01 | Given an ADT A01/A04/A08, when processed, then the patient upserts by MRN within 2s and an ACK returns; repeats never duplicate and clinical flows are never blocked | Integration test | Must pass 6.4 |
| AC-R16-02 | FR-R16-02 | Given a demographic correction in PACS, when published, then the EMR receives an update and acknowledges; failure retries 3x then dead-letters | Integration test | Must pass 6.4 |
| AC-R16-03 | FR-R16-03 | Given order context, when received, then the imaging record links to the EMR ServiceRequest/order | Integration test | Must pass 6.4 |
| AC-R16-04 | FR-R16-04 | Given a finalized report, when published, then a DiagnosticReport (or ORU) is available within 5min; failures dead-letter | Integration test | Must pass 6.4 |
| AC-R16-05 | FR-R16-05 | Given a study/report status change, when processed, then resource status reflects it | Integration test | Must pass 6.4 |
| AC-R16-06 | FR-R16-06 | Given a registered client, when it reads Patient/ImagingStudy/DiagnosticReport, then resources return within 200ms p95; unauthorized requests get 401 and are logged | Integration test | Must pass 6.4 |
| AC-R16-07 | FR-R16-07 | Given a processing failure, when exhausted, then the message dead-letters and appears in the reconciliation UI | Integration test + E2E | Must pass 6.4 |
| AC-R16-08 | FR-R16-08 | Given the FHIR monitoring screen, when filtered, then request details render and failed requests are replayable | Automated E2E | Must pass 6.4 |
| AC-R16-09 | FR-R16-09 | Given client config, when saved, then registration/scopes persist and the test endpoint reports status | Automated E2E | Must pass 6.4 |
| AC-R16-10 | FR-R16-10 | Given the metrics view, when rendered, then volume, latency, error rate, and backlog render with a time range | Automated E2E | Must pass 6.4 |
| AC-R16-11 | NFR-R16-01 | Given sustained load, when measured, then ingestion ≤ 2s p95 non-blocking and throughput ≥ 100 req/min | Load test | Must pass 6.4 |
| AC-R16-12 | NFR-R16-05 | Given all FHIR/HL7 traffic, when audited, then 100% is logged with request/response detail | Audit log scan | Must pass 6.4 |
| AC-R16-13 | NFR-R16-07 | Given the FHIR admin dashboard, when measured, then LCP ≤ 2.5s and INP ≤ 200ms | Lighthouse CI, RUM | Must pass 6.4 |
| AC-R16-14 | NFR-R16-02 | Given a FHIR read, when measured, then latency ≤ 200ms p95 | Synthetic probe | Must pass 6.4 |
| AC-R16-15 | NFR-R16-03 | Given sustained load, when measured, then throughput ≥ 100 req/min | Load test | Must pass 6.4 |
| AC-R16-16 | NFR-R16-04 | Given the integration, when measured, then availability ≥ 99.9% | Uptime monitoring | Must pass 6.4 |
| AC-R16-17 | NFR-R16-06 | Given PHI traffic, when audited, then transport is TLS 1.3 and at-rest data is AES-256 | Security audit | Must pass 6.4 |

## Excluded Scope / Out of Scope

- Order scheduling exchange (R15/RIS).
- DICOM image transfer (R17).
- Clinical reading (R12/R18) and nursing safety data entry (R11) — R16 provides flags only.
- Billing (R09).
