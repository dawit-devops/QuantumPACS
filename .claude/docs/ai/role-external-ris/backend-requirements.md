# Backend Requirements: R15 External RIS

## Context

The External RIS is a **system-to-system** integration (no web UI): it exchanges
orders and scheduling via HL7 ORM/ORU and DICOM MWL, receives status updates, and
receives finalized reports. The operational surface in QuantumPACS is the HL7
admin/dashboard + worklist + DICOMweb + FHIR admin screens (used by R01/R02), but
the RIS itself consumes the API directly. Failure semantics are the critical
contract: retry 3x → dead-letter → manual reconciliation.

**Screens (existing)**: HL7 receiver + dashboard (`/hl7`, `/hl7/admin/*`),
worklist CRUD (`/worklist*`), DICOMweb query (`/dicomweb/studies*`), FHIR
DocumentReference scaffolding (`/fhir/DocumentReference`; **no ServiceRequest
endpoint exists**), webhooks — see `hl7-adt-orm/`, `worklist/`, `dicomweb/`,
`fhir-r4-api/`, `phase4-integration/`.

**Personas**: P6 (RIS). **Access tier**: API only (HL7 + DICOM + FHIR + webhooks).

## Interfaces

### Order Exchange (HL7 ORM^O01)

**Purpose**: Receive orders and create/update worklist entries.

**Data I need**: accession, requested procedure, modality, scheduling, referring
physician → mapped to `/worklist` entries. Outbound status (scheduled →
performed/cancelled, study UID, performed time) back to RIS.

**Actions**: inbound create/update/cancel; outbound status updates; ACK/NAK every
message (NAK with error detail on malformed/unprocessable).

**States to handle**: message accepted/queued/processed/failed; dead-letter.

**Business rules affecting UI**: every message logged with direction, type,
control ID, timestamp, processing result; replay + detail inspection; PHI in
payloads logged securely, never in URLs.

### DICOM MWL / MPPS

**Purpose**: Serve Modality Worklist C-FIND queries and receive MPPS.

**Data I need**: MWL fields (accession, patient, procedure, scheduling); MPPS
start/end.

**Actions**: C-FIND MWL (≤1000 results), MPPS updates → worklist status.

**Business rules affecting UI**: full MWL/MPPS lifecycle is **GATED** — the
DICOM MWL SCP (`dicom-mwl-scp/`) exists, but MPPS wiring is not complete.

### Report Delivery (HL7 ORU / FHIR)

**Purpose**: Deliver finalized reports to the RIS.

**Data I need**: report → ORU^R01 or FHIR DocumentReference push.

**Business rules affecting UI**: **GATED on R12 structured reporting** — no
report data exists yet.

## Uncertainties

- [ ] Full MWL/MPPS lifecycle and report delivery push are GATED — raise with
  backend.
- [ ] FHIR order exchange: only `/fhir/DocumentReference` exists — no
  `/fhir/ServiceRequest` endpoint. Is HL7 ORM the canonical order contract?
- [ ] Message retry policies (3x → dead-letter) — is a reconciliation UI planned,
  or is this backend-only for now?
- [ ] Is the outbound status reverse-mapping confirmed against the existing
  worklist status fields (`scheduled`/`performed`/`cancelled`)?

## Questions for Backend

- What is the roadmap for MPPS lifecycle and outbound ORU report delivery?
- Is dead-letter + manual reconciliation an admin UI feature (R01/R02) or an
  external integration concern only?
- Does the FHIR ServiceRequest path fully cover order exchange, or is HL7 ORM
  the canonical contract?

## Discussion Log

_(pending backend review)_
