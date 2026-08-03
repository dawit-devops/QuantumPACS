# User Stories — External RIS (R15)

## US-R15-01: Receive and acknowledge orders
**Story**: As the external RIS, I want to send orders and receive an ACK, so that I know the PACS accepted them.
**Priority**: Must

### Acceptance Criteria
- **Given** an ORM^O01 order, **when** it arrives, **then** it persists within 2s and an ACK (AA) returns within 5s.
- **Given** an unparseable message, **when** processed, **then** a NAK with error detail returns and the message is retained.
- **Given** a duplicate accession, **when** processed, **then** the existing order merges rather than duplicating.

## US-R15-02: Keep worklist in sync with scheduling changes
**Story**: As the external RIS, I want reschedules and cancellations to propagate, so that the modality worklist is accurate.
**Priority**: Must

### Acceptance Criteria
- **Given** a reschedule message, **when** applied, **then** the worklist entry's date/time updates.
- **Given** a cancel message, **when** applied, **then** the entry transitions to cancelled.

## US-R15-03: Receive exam status updates
**Story**: As the external RIS, I want exam completion/cancellation status with study UID, so that my records stay current.
**Priority**: Must

### Acceptance Criteria
- **Given** an exam is marked performed, **when** the event fires, **then** an ORM/ORU with accession + study UID is delivered and acked.
- **Given** the RIS is unreachable, **when** delivery fails, **then** the message retries 3x then dead-letters with a manual resend UI.

## US-R15-04: Receive finalized reports
**Story**: As the external RIS, I want finalized reports as ORU^R01, so that results reach ordering physicians.
**Priority**: Must

### Acceptance Criteria
- **Given** a report is finalized, **when** it publishes, **then** an ORU^R01 with the report is delivered and acked.
- **Given** delivery fails, **then** the dead-letter queue retains it with reconciliation UI.

## US-R15-05: Query the modality worklist
**Story**: As the external RIS (or modality), I want to C-FIND MWL queries, so that scheduled exams are retrievable.
**Priority**: Should

### Acceptance Criteria
- **Given** a C-FIND MWL query, **when** processed, **then** matching entries return (≤1000) with expected fields.
- **Given** no matches, **then** an empty result set returns with no error.

## US-R15-06: Inspect and replay messages
**Story**: As an integration admin, I want to inspect and replay messages, so that I can reconcile failures.
**Priority**: Must

### Acceptance Criteria
- **Given** the HL7 dashboard, **when** I filter by direction/type/status, **then** message details render with payload, control ID, and processing result.
- **Given** a dead-lettered message, **when** I replay it, **then** it reprocesses and the reconciliation backlog updates.

## Dependencies
- US-R15-01..06 → HL7 MLLP listener + message store (exists as HL7 dashboard)
- US-R15-04 → R12 report finalization event
- US-R15-05 → MWL SCP (dicom-mwl-scp)
