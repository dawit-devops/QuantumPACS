# Traceability Matrix — External EMR (R16)

## FR/NFR → AC Traceability

| FR/NFR ID | Covered by AC | AC IDs | Status |
|-----------|---------------|--------|--------|
| FR-R16-01 | Yes | AC-R16-01 | Covered |
| FR-R16-02 | Yes | AC-R16-02 | Covered |
| FR-R16-03 | Yes | AC-R16-03 | Covered |
| FR-R16-04 | Yes | AC-R16-04 | Covered |
| FR-R16-05 | Yes | AC-R16-05 | Covered |
| FR-R16-06 | Yes | AC-R16-06 | Covered |
| FR-R16-07 | Yes | AC-R16-07 | Covered |
| FR-R16-08 | Yes | AC-R16-08 | Covered |
| FR-R16-09 | Yes | AC-R16-09 | Covered |
| FR-R16-10 | Yes | AC-R16-10 | Covered |
| NFR-R16-01 | Yes | AC-R16-11 | Covered |
| NFR-R16-02 | Yes | AC-R16-14 | Covered |
| NFR-R16-03 | Yes | AC-R16-15 | Covered |
| NFR-R16-04 | Yes | AC-R16-16 | Covered |
| NFR-R16-05 | Yes | AC-R16-12 | Covered |
| NFR-R16-06 | Yes | AC-R16-17 | Covered |
| NFR-R16-07 | Yes | AC-R16-13 | Covered |

## GATED Requirements (codebase reality, verified 2026-08-03)

HL7 ADT receiver, FHIR Patient read/search, ImagingStudy + DocumentReference
scaffolding, and webhooks are implemented. Report backfill job, results-status
workflow, and async demographics sync with conflict resolution are **GATED** (new
backend work flagged to backend):

| FR/NFR ID | Status | Blocking Dependency |
|-----------|--------|---------------------|
| FR-R16 report backfill | GATED | Depends on R12 reporting |
| FR-R16 results-status workflow | GATED | No status workflow endpoints |
| FR-R16 async demographics sync | GATED | No conflict-resolution job |

## Cross-Artifact Dependencies

| Source Artifact | Target Artifact | Dependency |
|-----------------|-----------------|------------|
| 01 User Requirements | 03 User Stories | US-R16-01..06 map to FRs |
| 01 User Requirements | 06 Acceptance Criteria | Every FR/NFR has ≥1 AC |
| 02 Workflow Maps | 03 User Stories | W1 ADT → US-R16-01; W2 report → US-R16-03 |
| 03 User Stories | 04 UI/UX Requirements | FHIR admin/client state specs |
| 04 UI/UX Requirements | 06 Acceptance Criteria | Each state → validator gate |

## Cross-Role Dependencies

| Role | Dependency Type | Target Role | Contract |
|------|----------------|-------------|----------|
| R16 External EMR | Provides demographics | R08 Front Desk | ADT inbound → patient upsert |
| R16 External EMR | Provides allergy flags | R11 Nursing | ADT allergy/pregnancy/renal |
| R16 External EMR | Receives reports | R12/R18 Radiologist | DiagnosticReport/ORU on finalize |
| R16 External EMR | Operated by | R01/R02 Admin | FHIR/HL7 config + monitoring |
| R16 External EMR | Shares identities | R15/R17 | Patient/order/study cross-references |

## Integration Contracts

| Integration | Direction | Protocol | Failure Semantics |
|-------------|-----------|----------|-------------------|
| Demographics inbound | R16 → PACS | HL7 ADT (MLLP) | ACK/NAK; async retry 3x → dead-letter |
| Demographics outbound | PACS → R16 | FHIR Patient / ADT | Retry 3x → dead-letter → manual reconcile |
| Report delivery | PACS → R16 | FHIR DiagnosticReport / ORU | ≤ 5min from finalize; dead-letter on failure |
| FHIR reads | R16 → PACS | FHIR R4 (HTTPS) | ≤ 200ms p95; 401 on unauthorized (logged) |

## Excluded Scope / Out of Scope

- Order scheduling (R15); DICOM image transfer (R17); clinical reading (R12/R18); billing (R09).
