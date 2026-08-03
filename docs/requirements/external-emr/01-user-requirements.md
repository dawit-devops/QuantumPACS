# User Requirements — External EMR (R16)

**Version**: 1.0.0 (v3.0 scope)
**Status**: Draft
**Date**: 2026-08-02

## Functional Requirements

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-R16-01 | **Patient Demographics Inbound (HL7 ADT)**: Receive ADT messages (A01 admit, A04 registration, A08 update) and upsert patient demographics without blocking clinical flows. | Must | Async backfill, no blocking |
| FR-R16-02 | **Patient Demographics Outbound**: Publish patient demographic updates made in QuantumPACS back to the EMR (ADT or FHIR Patient update). | Should | Reverse sync |
| FR-R16-03 | **Order Context (FHIR ServiceRequest / HL7 ORM)**: Receive order context referencing the EMR's ServiceRequest or order so imaging can be linked to the clinical record. | Should | Cross-referencing |
| FR-R16-04 | **Report Backfill (FHIR DiagnosticReport / HL7 ORU)**: Deliver finalized reports to the EMR as FHIR DiagnosticReport resources or ORU messages. | Must | Results delivery |
| FR-R16-05 | **Results Status**: Update the EMR on study/report status (received, in-progress, final) via resource status fields. | Should | Status synchronization |
| FR-R16-06 | **FHIR R4 API Exposure**: Expose FHIR R4 read endpoints (Patient, ImagingStudy, DiagnosticReport, CapabilityStatement) for EMR consumption with SMART-on-FHIR backend services. | Must | FHIR admin exists in frontend |
| FR-R16-07 | **Error Handling & Dead-Letter**: On processing failure, retry with backoff (3x), then dead-letter with manual reconciliation UI. | Must | Failure semantics |
| FR-R16-08 | **Message/Request Logging & Replay**: Log all inbound/outbound FHIR/HL7 traffic with detail and replay capability. | Must | FHIR monitoring screen |
| FR-R16-09 | **Config & Client Management**: Manage FHIR clients (registration, scopes, test endpoint) and HL7 connection config; run connectivity tests. | Must | FHIR admin config |
| FR-R16-10 | **Metrics & Monitoring**: Track request volume, latency, error rates, and reconciliation backlog; expose to R01/R02. | Must | FHIR admin metrics |

## Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-R16-01 | Demographics ingestion latency (no blocking) | ≤ 2s p95, never blocks UI | Synthetic probe |
| NFR-R16-02 | FHIR read latency | ≤ 200ms p95 | Synthetic probe |
| NFR-R16-03 | Throughput | ≥ 100 req/min sustained | Load test |
| NFR-R16-04 | Integration availability | 99.9% | Uptime monitoring |
| NFR-R16-05 | Audit of all traffic | 100% logged | Audit log scan |
| NFR-R16-06 | PHI in transit/at rest encryption | TLS 1.3 + AES-256 | Security audit |
| NFR-R16-07 | Admin surface (FHIR config/monitoring) load time | LCP ≤ 2.5s, INP ≤ 200ms, CLS < 0.1 | Lighthouse CI, RUM |

## Codebase Status (verified 2026-08-03)

**Implemented**: HL7 ADT receiver (`POST /hl7`), FHIR Patient read/search
(`/fhir/Patient`), ImagingStudy + DocumentReference scaffolding, webhooks.
**GATED**: report backfill job, results-status workflow, async demographics sync with
conflict resolution. See artifacts 04/07/08.

## Assumptions & Constraints

- A1: HL7 ADT (v2.5) and FHIR R4 are the transports; MLLP for ADT, HTTPS for FHIR.
- A2: Demographics sync is async and non-blocking; failures never block registration (R08) or clinical flows.
- A3: Allergy/pregnancy flags arrive via ADT for R11 safety screening.
- A4: The operational surface is the FHIR admin + HL7 admin screens (R01/R02); the EMR itself has no UI.
- A5: FHIR client registration and scopes are managed via the existing FHIR admin config.
