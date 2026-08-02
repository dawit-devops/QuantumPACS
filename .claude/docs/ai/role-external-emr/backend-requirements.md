# Backend Requirements: R16 External EMR

## Context

The External EMR is a **system-to-system** integration (no web UI): it supplies
patient demographics (HL7 ADT), order context, and receives finalized reports and
results status. The operational surface in QuantumPACS is the FHIR admin +
HL7 admin screens (used by R01/R02), but the EMR consumes the API directly.
Demographics sync is **async and non-blocking** — failures must never block
registration (R08) or clinical flows.

**Screens (existing)**: HL7 receiver (`POST /hl7`), FHIR Patient read/search
(`/fhir/Patient`), ImagingStudy + DocumentReference scaffolding, FHIR admin
config/monitoring/metrics, webhooks — see `fhir-r4-api/`, `hl7-adt-orm/`,
`phase4-integration/`.

**Personas**: P7 (EMR). **Access tier**: API only (HL7 + FHIR + webhooks).

## Interfaces

### Patient Demographics (HL7 ADT + FHIR Patient)

**Purpose**: Upsert patient demographics without blocking clinical flows.

**Data I need**: ADT A01 (admit), A04 (registration), A08 (update) → patient
upsert; FHIR Patient read/search for EMR consumption.

**Actions**: async upsert; FHIR read of the patient resource.

**States to handle**: accepted → upserted; async backfill with conflict
resolution (**GATED** — no conflict-resolution job exists).

**Business rules affecting UI**: allergy/pregnancy flags arrive via ADT for R11
safety screening; demographics sync is non-blocking.

### Order Context / Results (FHIR ServiceRequest, DiagnosticReport, HL7 ORU)

**Purpose**: Link imaging to the clinical record and deliver results.

**Data I need**: EMR ServiceRequest/order reference for cross-linking; finalized
reports delivered as FHIR DiagnosticReport or ORU.

**Actions**: receive order context; deliver report backfill.

**Business rules affecting UI**: **report backfill and results-status workflow
are GATED** (depend on R12 reporting); the report status fields (received /
in-progress / final) need a synchronization contract.

## Uncertainties

- [ ] Report backfill + results-status workflow are GATED — raise with backend.
- [ ] Demographics outbound (QuantumPACS → EMR) — is it ADT or FHIR Patient
  update, and is it in scope for v3?
- [ ] Conflict resolution for async demographics sync — is there a design?
- [ ] Allergy/pregnancy flag extraction from ADT — confirmed mapping?

## Questions for Backend

- What is the roadmap for report backfill (FHIR DiagnosticReport / ORU)?
- Is there a client/scope registration contract beyond the existing FHIR admin
  config for SMART-on-FHIR?
- Should demographics outbound be scheduled, event-driven, or manual?

## Discussion Log

_(pending backend review)_
