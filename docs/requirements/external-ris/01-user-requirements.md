# User Requirements — External RIS (R15)

**Version**: 1.0.0 (v3.0 scope)
**Status**: Draft
**Date**: 2026-08-02

## Functional Requirements

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-R15-01 | **Order Exchange Inbound (HL7 ORM)**: Receive order messages (ORM^O01) and create/update orders and scheduled worklist entries. Map accession, requested procedure, modality, scheduling, and referring physician. | Must | Primary integration contract |
| FR-R15-02 | **Scheduling Sync**: Apply order status changes and scheduled date/time from the RIS to the worklist; reflect reschedules and cancellations. | Must | Order status lifecycle |
| FR-R15-03 | **Status Updates Outbound**: Send exam status updates back to the RIS (scheduled → performed/cancelled, study UID, performed time) via HL7 ORM/ORU. | Must | Reverse direction |
| FR-R15-04 | **Report Delivery (ORU)**: Deliver finalized reports as ORU^R01 result messages to the RIS. | Must | Report delivery channel |
| FR-R15-05 | **MWL Query Support (DICOM C-FIND MWL)**: Serve Modality Worklist C-FIND queries from the RIS/modalities with the expected fields (accession, patient, procedure, scheduling). | Should | DICOM MWL SCP |
| FR-R15-06 | **Message Acknowledgment (HL7 ACK)**: Acknowledge every received HL7 message with an ACK; NAK on malformed/unprocessable messages with error detail. | Must | HL7 reliability |
| FR-R15-07 | **Error Handling & Dead-Letter**: On processing failure, retry with backoff (3x), then route to a dead-letter queue with a manual reconciliation UI. | Must | Failure semantics |
| FR-R15-08 | **Message Logging & Replay**: Log all messages with direction, type, control ID, timestamp, and processing result; support replay and detail inspection. | Must | HL7 dashboard exists in frontend |
| FR-R15-09 | **Config & Connection Management**: Configure RIS endpoints, credentials, message types to accept, and mapping rules; test connectivity. | Must | HL7 admin config screen |
| FR-R15-10 | **Metrics & Monitoring**: Track message volume, ack latency, error rates, and reconciliation backlog; expose to R01/R02 dashboards. | Must | HL7 admin metrics |

## Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-R15-01 | Message ingestion latency (message to persisted) | ≤ 2s p95 | Synthetic probe |
| NFR-R15-02 | ACK response time | ≤ 5s from receipt | Synthetic probe |
| NFR-R15-03 | Message ordering preservation | Per-control-ID, no reordering | Integration test |
| NFR-R15-04 | Throughput | ≥ 100 msg/min sustained | Load test |
| NFR-R15-05 | Integration availability | 99.9% | Uptime monitoring |
| NFR-R15-06 | Audit of all messages | 100% logged (who/what/when) | Audit log scan |
| NFR-R15-07 | Admin surface (HL7 dashboard/config) load time | LCP ≤ 2.5s, INP ≤ 200ms, CLS < 0.1 | Lighthouse CI, RUM |

## Codebase Status (verified 2026-08-03)

**Implemented**: HL7 receiver (`POST /hl7`), worklist CRUD (`/worklist*`), DICOMweb
query (`/dicomweb/studies*`), FHIR ServiceRequest/DocumentReference scaffolding,
webhooks. **GATED**: full MWL/MPPS lifecycle, report delivery push (depends on R12
reporting), dead-letter + manual reconciliation UI, message retry policies. See
artifacts 04/07/08.

## Assumptions & Constraints

- A1: HL7 v2.5 MLLP is the transport; ORM^O01 inbound, ORM/ORU outbound.
- A2: Failure semantics are retry 3x → dead-letter → manual reconciliation.
- A3: MWL C-FIND returns a maximum of 1000 results.
- A4: The frontend surface for this role is the HL7 admin/dashboard (R01/R02 use it; the RIS itself has no UI).
- A5: Message payloads may contain PHI — must be logged securely, never in URLs, and retained per policy.
