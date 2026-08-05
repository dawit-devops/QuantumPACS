# User Stories — External PACS (R17)

## US-R17-01: Store instances via C-STORE
**Story**: As the external PACS, I want to push instances via C-STORE and get per-instance status, so that I know what persisted.
**Priority**: Must

### Acceptance Criteria
- **Given** a C-STORE association, **when** instances arrive, **then** each persists and returns a success status within 10s (p95); failures return a NAK with reason.
- **Given** a duplicate SOP UID, **when** stored again, **then** it is idempotently acknowledged without re-persist.
- **Given** storage failure, **when** persistence fails, **then** a NAK returns and the attempt is logged for the AE to retry.

## US-R17-02: Query studies via C-FIND
**Story**: As the external PACS, I want to query studies/series/instances, so that I can locate data.
**Priority**: Must

### Acceptance Criteria
- **Given** a C-FIND query, **when** processed, **then** matches return with the expected keysets within the 30s timeout.
- **Given** no matches, **then** an empty result returns cleanly.

## US-R17-03: Retrieve studies via C-MOVE
**Story**: As the external PACS, I want to C-MOVE studies to my AE, so that I can pull what I need.
**Priority**: Must

### Acceptance Criteria
- **Given** a C-MOVE request, **when** matches are found, **then** instances transfer to the requesting AE with sub-operation status.
- **Given** the requesting AE is unreachable, **when** transfer fails, **then** it retries 2x before failing and logging.

## US-R17-04: Search via DICOMweb QIDO-RS
**Story**: As an external system, I want QIDO-RS search, so that I can query via HTTPS.
**Priority**: Must

### Acceptance Criteria
- **Given** a QIDO-RS request, **when** processed, **then** study/series/instance results return in DICOMweb format.
- **Given** invalid query parameters, **when** requested, **then** a 400 returns with detail.

## US-R17-05: Retrieve via WADO-RS for the viewer
**Story**: As the frontend viewer, I want WADO-RS frames and thumbnails, so that images load progressively.
**Priority**: Must

### Acceptance Criteria
- **Given** a WADO-RS request, **when** processed, **then** pixels/metadata return with correct content type; frame-level requests work.
- **Given** an unauthorized request, **when** made, **then** 401 returns.

## US-R17-06: Route instances after store
**Story**: As an integration admin, I want stored instances routed per rules, so that studies reach the right destinations.
**Priority**: Should

### Acceptance Criteria
- **Given** a stored instance matching a routing rule, **when** persistence completes, **then** the instance routes to the target AE/storage and delivery logs.
- **Given** a delivery failure, **when** routing fails, **then** the failure is logged and retried per routing config.

## US-R17-07: Manage AE nodes
**Story**: As an integration admin, I want to manage AE nodes and test connectivity, so that associations work.
**Priority**: Must

### Acceptance Criteria
- **Given** the AE node config, **when** I add/update a node, **then** it persists and a connectivity test reports status.
- **Given** I remove a node, **when** saved, **then** associations from it are rejected and logged.

## Dependencies
- US-R17-01..03 → DICOM SCP (dcm server)
- US-R17-04..05 → DICOMweb (dicomweb admin)
- US-R17-06 → routing-rules engine
- US-R17-07 → AE/station admin
