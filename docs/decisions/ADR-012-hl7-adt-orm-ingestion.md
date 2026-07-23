# ADR-012: HL7 v2.x ADT/ORM Ingestion

## Status
Accepted

## Date
2026-07-23

## Context
Hospital EHRs and HIS systems send patient demographic updates (ADT — Admission/Discharge/Transfer) and procedure orders (ORM — Order Entry) via HL7 v2.x over MLLP. QuantumPACS needs to ingest these messages to:
- Auto-create and update patient records from ADT events (A01, A04, A08, etc.)
- Create worklist entries from ORM orders (O01)
- Maintain an audit trail of all received messages
- Provide admin visibility into connection health and message throughput

Currently, all patient data enters the system via DICOM C-STORE or manual entry. There is no mechanism to receive unsolicited HL7 feeds from hospital systems.

## Decision
Implement an MLLP listener with a custom HL7 parser, storing messages in PostgreSQL and triggering patient/study updates.

Key design choices:

1. **MLLP listener**: A standalone async TCP server using the Minimal Lower Layer Protocol (MLLP — 0x0B message 0x1C 0x0D framing). Listens on a configurable port (default 2575). Runs as a background task within the Starlette application lifespan or as a separate process.

2. **Custom HL7 parser**: Uses the `hl7` Python library for message structure parsing. Maps ADT segments (MSH, PID, PD1, PV1, etc.) to patient fields and ORM segments (ORC, OBR, etc.) to order/study fields. Stores raw message text for audit purposes.

3. **Message storage**: A new `hl7_messages` table stores every received message with metadata (message type, event type, sending facility, patient ID, parse status, raw content, parsed fields as JSONB). A `hl7_parse_errors` table captures per-field parsing failures.

4. **Patient sync**: ADT message processing creates or updates entries in the `patients` table. A `sync_source` field (or extension of the `meta` JSONB column) tags patients as HL7-sourced, DICOM-sourced, or manual. Conflict detection flags patients updated by both HL7 and DICOM with different field values.

5. **Order-to-worklist bridge**: ORM messages auto-create entries in the `worklist_entries` table (see ADR-011), linking the HL7 message to the resulting worklist entry for full traceability.

6. **Admin UI**: Dashboard with listener status, throughput metrics, and alerting. Message log with search/filter/pagination and raw message display. Connection configuration screen (port, facility ID, IP whitelist).

7. **Security**: The listener binds only to configured network interfaces. An IP whitelist restricts which sender addresses are accepted. Listener start/stop is admin-only via API.

## Alternatives Considered

### FHIR-only integration
- Pros: Modern protocol, JSON payloads, simpler parsing
- Cons: Most hospitals' EHRs still send HL7 v2.x over MLLP; FHIR would require an integration engine or vendor support
- Rejected: HL7 v2.x is the de-facto standard for ADT/ORM in production hospital environments

### External integration engine (Mirth Connect / NextGen Connect)
- Pros: Mature HL7 parsing, channel-based routing, built-in MLLP support
- Cons: Adds Java dependency, separate deployment and monitoring surface, licensing complexity, deployment overhead for a single-PACS setup
- Rejected: In-house implementation is simpler for the subset of messages (ADT + ORM) that QuantumPACS needs

### Manual patient entry only
- Pros: No HL7 development
- Cons: Unsustainable at scale; duplicates and data entry errors; no real-time patient synchronization
- Rejected: Manual entry cannot meet production hospital requirements

## Consequences
- New MLLP network listener on a configurable port (default 2575)
- New `hl7_messages`, `hl7_parse_errors` database tables
- Patient table extended with sync source metadata
- HL7 parsing dependency (`hl7` Python library)
- Admin UI for HL7 dashboard, message log, patient sync status, and connection configuration
- Auto-creation of worklist entries from ORM orders (bridges ADR-011)
- IP whitelisting and interface binding for security
- Audit trail of all received HL7 messages with raw content retention
