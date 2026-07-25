# ADR-019: FHIR R4 + HL7 v2.x Integration in v3

## Status
Accepted

## Date
2026-07-25

## Context

QuantumPACS v2.0 has no healthcare interoperability protocols beyond DICOM. Hospitals and imaging centers use two primary standards for non-image data exchange:

1. **HL7 v2.x** — The dominant standard for patient demographics (ADT), orders (ORM), and results (ORU). Most modalities and RIS applications output HL7 v2.x messages over MLLP (Minimal Lower Layer Protocol). QuantumPACS needs to ingest ADT messages to auto-register patients and ORM messages to create modality worklist entries.

2. **FHIR R4** — The emerging standard for RESTful healthcare APIs. EHRs use FHIR to query patient data, imaging studies, and reports. QuantumPACS needs to expose patient and imaging study data as FHIR resources for EHR integration.

The PRD decision was "RIS integration, not built-in RIS" — QuantumPACS provides the endpoints that external RIS/EHR applications use to exchange data, without becoming a RIS itself.

## Decision

Implement both HL7 v2.x ingestion and FHIR R4 API in v3.0.

### HL7 v2.x Ingestion

**Scope**: ADT (Admission/Discharge/Transfer) and ORM (Order) message types only.

**Architecture**:
- Runs in the **ingestion service** (separate process, extracted in Phase 1)
- MLLP listener on configurable port (default 12579)
- TLS support (configurable cert)
- Messages parsed using `hl7` (or `python-hl7`) library
- Unknown segments logged and skipped (non-fatal)
- Malformed messages rejected with MLLP NACK
- Every message logged with SHA-256 hash for non-repudiation audit trail

**ADT Message Mapping**:

| HL7 Field | DICOM/PACS Field | Table |
|-----------|------------------|-------|
| PID-3 (Patient ID) | `patient_id` | `patients` |
| PID-5 (Patient Name) | `name` | `patients` |
| PID-7 (DOB) | `birth_date` | `patients` |
| PID-8 (Sex) | `sex` | `patients` |
| PID-11 (Address) | `meta` JSONB | `patients` |

**ORM Message Mapping**:

| HL7 Field | DICOM MWL Field | Table |
|-----------|------------------|-------|
| ORC-2 (Placer Order Number) | `accession_number` | `worklist_entries` |
| OBR-3 (Filler Order Number) | `requested_procedure_id` | `worklist_entries` |
| OBR-4 (Universal Service ID) | `requested_procedure_description` | `worklist_entries` |
| OBR-7 (Start Date/Time) | `scheduled_procedure_step_start_date` + `_time` | `worklist_entries` |
| OBR-15 (Order Effective Date) | `scheduled_procedure_step_end_date` | `worklist_entries` |
| PID-3 → Patient ID | `patient_id` | `worklist_entries` (FK to patients) |

### FHIR R4 API

**Scope**: `Patient`, `ImagingStudy`, and `DocumentReference` resources only.

**Architecture**:
- Runs in the main monolith under `/api/v2/fhir/`
- Uses minimal FHIR resource serializers (no full FHIR server library — `fhir.resources` for validation)
- Returns `application/fhir+json` content type
- CapabilityStatement at `GET /api/v2/fhir/metadata`

**Resource Mapping**:

| FHIR Resource | Source Table | Key Maps |
|---------------|-------------|----------|
| `Patient` | `patients` | `Patient.identifier` ← `patients.patient_id`, `Patient.name` ← `patients.name` |
| `ImagingStudy` | `studies` + `series` + `files` | `ImagingStudy.identifier` ← `studies.study_id`, `ImagingStudy.series` ← nested series/instances |
| `DocumentReference` | `shared_files` + `file_changes` | `DocumentReference.content.attachment.url` ← share link URL |

**Search Parameters**:

| Resource | Search Parameters |
|----------|------------------|
| `Patient` | `identifier`, `name`, `birthdate`, `_lastUpdated` |
| `ImagingStudy` | `patient`, `accession`, `modality`, `started`, `_lastUpdated` |
| `DocumentReference` | `patient`, `type`, `period`, `_lastUpdated` |

### Coexistence Strategy

- HL7 and FHIR coexist with existing v2 REST endpoints. The v2 `POST /api/files/upload` and the new STOW-RS (`/api/v2/dicomweb/studies`) write to the same tables.
- HL7 ADT messages create patients that are immediately visible via FHIR `Patient` search and via v2 `GET /api/patients/{id}`.
- HL7 ORM messages create MWL entries that are immediately visible via DICOM MWL C-FIND.
- No data duplication — all write paths converge on the same database tables.

## Consequences

### Positive

- **Interoperability**: Hospitals using Epic, Cerner, or Meditech can send ADT/ORM messages to QuantumPACS and query imaging studies via FHIR.
- **No vendor lock-in**: HL7 v2.x and FHIR R4 are open standards. Any RIS/EHR that supports them can integrate.
- **RIS-ready**: External RIS applications use these endpoints to exchange data with QuantumPACS, satisfying the "RIS integration, not built-in RIS" requirement.

### Negative

- **HL7 variant complexity**: HL7 v2.x has hundreds of variants (different field positions, custom Z-segments, different encoding characters). The parser must be tolerant. Mitigation: fuzz test with 100+ real HL7 samples from different hospital systems before GA.
- **FHIR R4 scope**: Only `Patient` + `ImagingStudy` + `DocumentReference` are implemented in v3.0. `DiagnosticReport`, `Encounter`, `ServiceRequest` are deferred to v3.1 (RIS bundle). Some EHRs may require these for full integration.
- **MLLP operational burden**: MLLP is a TCP-based protocol with minimal framing. TLS adds complexity. The ingestion service must handle connection management, keepalive, and reconnection. Mitigation: use an async TCP server (asyncio) with connection pooling.

## References

- ADR-012: HL7 ADT/ORM Ingestion
- PRD-v3.md §3.2 — Integration Points
- IMPLEMENTATION_PLAN-v3.md Phase 4 — Integration
- HL7 v2.5.1 Implementation Guide
- FHIR R4 (http://hl7.org/fhir/R4/)