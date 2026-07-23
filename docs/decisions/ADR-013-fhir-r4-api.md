# ADR-013: FHIR R4 API for EHR Integration

## Status
Accepted

## Date
2026-07-23

## Context
Modern EHR systems (Epic, Cerner, etc.) increasingly prefer FHIR R4 as their interoperability standard. QuantumPACS needs to expose FHIR endpoints so that:
- EHRs can query patient demographics and imaging study metadata
- Referring physicians can access imaging reports as DocumentReference resources
- EHRs can discover server capabilities via CapabilityStatement
- External systems can authenticate via SMART-on-FHIR backend services

Currently, all data access requires the QuantumPACS web UI or direct DICOM queries. There is no standards-based REST API that EHRs can integrate with.

## Decision
Implement FHIR R4 endpoints for Patient, ImagingStudy, DocumentReference, Endpoint, and CapabilityStatement resources.

Key design choices:

1. **Resource scope — read-only for EHRs**: Patient (read, search), ImagingStudy (read, search), DocumentReference (read, search), Endpoint (read), CapabilityStatement (read). These cover the primary EHR use cases (patient lookup, study retrieval, report access). Mutating operations (create, update, delete) are deferred until a concrete write use case emerges.

2. **SMART-on-FHIR backend services**: EHR systems authenticate via the client credentials grant (system-to-system). Internal PACS users can also access FHIR endpoints using their existing `X-Auth-Pacs` JWT tokens for testing via the internal docs explorer.

3. **JSON + XML content negotiation**: JSON primary, XML supported via `_format=xml` or `Accept: application/fhir+xml` header. Content type negotiation follows the FHIR R4 specification.

4. **CapabilityStatement**: Dynamically generated from registered resource types and search parameters, served at `[base]/metadata`. Includes server name, supported interactions, search params, and security scheme description.

5. **Endpoint routing**: FHIR endpoints live at `/api/fhir/` sub-path under the existing Starlette application, sharing the same port (8080). The published base URL is configurable for reverse-proxy scenarios.

6. **Patient identity mapping**: The `patients` table's `patient_id` (DICOM tag 0010,0020) is exposed as a FHIR identifier with the assigning authority configurable. An MRN mapping table (`patient_identifiers`) can be added for sites that need separate MRN-to-internal-ID mapping.

7. **Request logging**: All FHIR requests logged to a `fhir_audit` table for the admin monitoring dashboard (request count, latency, status codes, client ID).

## Alternatives Considered

### DICOMweb only
- Pros: Native to DICOM ecosystem, WADO-RS/QIDO-RS/STOW-RS are standard
- Cons: Not all EHRs support DICOMweb; FHIR is more widely adopted for EHR integration; DICOMweb lacks DocumentReference and structured CapabilityStatement
- Rejected: FHIR + DICOMweb are complementary; DICOMweb can be added later for modality-to-PACS web workflows

### Proprietary REST API
- Pros: Full control over schema, simpler implementation
- Cons: No interoperability; every EHR integration requires custom adapters; defeats the purpose of a standard
- Rejected: Standards-based FHIR is required for EHR interoperability

### GraphQL API
- Pros: Flexible queries, over-fetching prevention, single endpoint
- Cons: Not a healthcare standard; EHRs do not natively consume GraphQL; would require custom integration on both sides
- Rejected: FHIR is the mandated standard for healthcare interoperability

## Consequences
- New FHIR endpoints at `/api/fhir/` (non-breaking — existing API routes unchanged)
- New `fhir_audit` database table for request logging
- SMART-on-FHIR backend services authentication module
- CapabilityStatement must be maintained as resources and search parameters evolve
- FHIR-specific response formatting (JSON/XML with OperationOutcome errors)
- Admin configuration UI for FHIR enable/disable, base URL, client registrations
- Admin monitoring UI for request volume, error rate, latency
- Internal FHIR API explorer for testing
