# Acceptance Criteria — External PACS (R17)

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R17-01 | FR-R17-01 | Given a C-STORE association, when instances arrive, then each persists with a success status within 10s (p95); duplicates ack idempotently; failures NAK with reason | Integration test + load | Must pass 6.4 |
| AC-R17-02 | FR-R17-02 | Given a C-FIND query, when processed, then matches return with expected keysets within the 30s timeout; empty set is clean | Integration test | Must pass 6.4 |
| AC-R17-03 | FR-R17-03 | Given a C-MOVE request, when matches are found, then instances transfer with sub-operation status; unreachable AE retries 2x then fails logged | Integration test | Must pass 6.4 |
| AC-R17-04 | FR-R17-04 | Given a QIDO-RS request, when processed, then results return in DICOMweb format; invalid params return 400 | Integration test | Must pass 6.4 |
| AC-R17-05 | FR-R17-05 | Given a WADO-RS request, when processed, then pixels/metadata return with correct content type; unauthorized returns 401 | Integration test | Must pass 6.4 |
| AC-R17-06 | FR-R17-06 | Given a STOW-RS store, when processed, then instances persist and return DICOMweb store response | Integration test | Must pass 6.4 |
| AC-R17-07 | FR-R17-07 | Given a stored instance matching a rule, when persistence completes, then it routes and delivery logs; failures log and retry | Integration test + E2E | Must pass 6.4 |
| AC-R17-08 | FR-R17-08 | Given replica/archive sync, when triggered, then sync status and backfill progress track; failures alert | Automated E2E | Must pass 6.4 |
| AC-R17-09 | FR-R17-09 | Given AE node config, when saved, then it persists and connectivity tests report; removed nodes are rejected and logged | Automated E2E | Must pass 6.4 |
| AC-R17-10 | FR-R17-10 | Given the metrics view, when rendered, then store latency, Q/R timing, error rates, and storage usage render with a time range | Automated E2E | Must pass 6.4 |
| AC-R17-11 | NFR-R17-01 | Given sustained store load, when measured, then ack ≤ 10s p95 and throughput ≥ 100 MB/s | Load test | Must pass 6.4 |
| AC-R17-12 | NFR-R17-06 | Given all transfers, when audited, then 100% are logged with AE, study, and result | Audit log scan | Must pass 6.4 |
| AC-R17-13 | NFR-R17-07 | Given the DICOMweb admin dashboard, when measured, then LCP ≤ 2.5s and INP ≤ 200ms | Lighthouse CI, RUM | Must pass 6.4 |
| AC-R17-14 | NFR-R17-02 | Given a C-FIND query, when measured, then it completes within the 30s timeout | Synthetic probe | Must pass 6.4 |
| AC-R17-15 | NFR-R17-03 | Given a failed C-MOVE, when retried, then it retries exactly 2x before failing logged | Integration test | Must pass 6.4 |
| AC-R17-16 | NFR-R17-04 | Given sustained store load, when measured, then throughput ≥ 100 MB/s | Load test | Must pass 6.4 |
| AC-R17-17 | NFR-R17-05 | Given the DICOM service, when measured, then availability ≥ 99.9% | Uptime monitoring | Must pass 6.4 |

## Excluded Scope / Out of Scope

- HL7 order/report exchange (R15/R16).
- Clinical reading and reporting (R12/R18).
- Patient registration and scheduling (R08/R04).
- Billing (R09).
