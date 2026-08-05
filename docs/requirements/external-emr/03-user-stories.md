# User Stories — External EMR (R16)

## US-R16-01: Upsert patient demographics from ADT
**Story**: As the external EMR, I want my ADT messages to upsert patient records, so that demographics are always current without blocking clinical flows.
**Priority**: Must

### Acceptance Criteria
- **Given** an ADT A01/A04/A08, **when** processed, **then** the patient upserts by MRN within 2s and an ACK returns; the same message twice never duplicates.
- **Given** the PACS is mid-registration, **when** the message arrives, **then** the UI is never blocked.
- **Given** an unparseable message, **when** processed, **then** a NAK returns and the message is retained.

## US-R16-02: Expose FHIR read endpoints to the EMR
**Story**: As the external EMR, I want FHIR R4 reads (Patient, ImagingStudy, DiagnosticReport), so that I can retrieve imaging data programmatically.
**Priority**: Must

### Acceptance Criteria
- **Given** a registered FHIR client, **when** it reads Patient/ImagingStudy/DiagnosticReport, **then** resources return within 200ms p95.
- **Given** an unregistered or unauthorized client, **when** it requests, **then** a 401 returns and the attempt is logged.
- **Given** a CapabilityStatement request, **when** queried, **then** supported resources and SMART-on-FHIR services are declared.

## US-R16-03: Deliver reports as DiagnosticReport
**Story**: As the external EMR, I want finalized reports as DiagnosticReport resources, so that ordering clinicians see results.
**Priority**: Must

### Acceptance Criteria
- **Given** a report is finalized, **when** it publishes, **then** a DiagnosticReport referencing patient + ImagingStudy is available to authorized clients.
- **Given** publication fails, **then** the event dead-letters with a reconciliation UI.

## US-R16-04: Manage FHIR clients
**Story**: As an integration admin, I want to register clients and scopes and run tests, so that access is controlled.
**Priority**: Must

### Acceptance Criteria
- **Given** the FHIR admin config, **when** I register a client with scopes, **then** it persists and the test endpoint returns a result.
- **Given** I revoke a client, **when** it next requests, **then** access is denied.

## US-R16-05: Monitor FHIR traffic
**Story**: As an integration admin, I want request volume, latency, and errors visible, so that I can react to issues.
**Priority**: Must

### Acceptance Criteria
- **Given** the FHIR monitoring screen, **when** filtered by time range, **then** volume, latency, error rate, and backlog render.
- **Given** a failed request, **when** inspected, **then** full request/response detail is available for replay.

## US-R16-06: Sync demographics back to the EMR
**Story**: As the PACS, I want to publish demographic corrections to the EMR, so that both systems converge.
**Priority**: Should

### Acceptance Criteria
- **Given** a demographics correction in PACS, **when** published, **then** the EMR receives an update (FHIR Patient or ADT) and acknowledges.
- **Given** delivery fails, **then** it retries and dead-letters with reconciliation.

## Dependencies
- US-R16-01 → HL7 ADT listener (exists)
- US-R16-02/03 → FHIR R4 API (fhir-r4-api)
- US-R16-04/05 → FHIR admin screens (exist)
- US-R16-03 → R12/R18 report finalization event
