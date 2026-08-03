# Traceability Matrix — External RIS (R15)

## FR/NFR → AC Traceability

| FR/NFR ID | Covered by AC | AC IDs | Status |
|-----------|---------------|--------|--------|
| FR-R15-01 | Yes | AC-R15-01 | Covered |
| FR-R15-02 | Yes | AC-R15-02 | Covered |
| FR-R15-03 | Yes | AC-R15-03 | Covered |
| FR-R15-04 | Yes | AC-R15-04 | Covered |
| FR-R15-05 | Yes | AC-R15-05 | Covered |
| FR-R15-06 | Yes | AC-R15-06 | Covered |
| FR-R15-07 | Yes | AC-R15-07 | Covered |
| FR-R15-08 | Yes | AC-R15-08 | Covered |
| FR-R15-09 | Yes | AC-R15-09 | Covered |
| FR-R15-10 | Yes | AC-R15-10 | Covered |
| NFR-R15-01 | Yes | AC-R15-11 | Covered |
| NFR-R15-02 | Yes | AC-R15-14 | Covered |
| NFR-R15-03 | Yes | AC-R15-15 | Covered |
| NFR-R15-04 | Yes | AC-R15-16 | Covered |
| NFR-R15-05 | Yes | AC-R15-17 | Covered |
| NFR-R15-06 | Yes | AC-R15-12 | Covered |
| NFR-R15-07 | Yes | AC-R15-13 | Covered |

## GATED Requirements (codebase reality, verified 2026-08-03)

HL7 receiver (`POST /hl7`), worklist CRUD, DICOMweb query, FHIR ServiceRequest/
DocumentReference scaffolding, and webhooks are implemented. Full MWL/MPPS
lifecycle, report delivery push, dead-letter + manual reconciliation UI, and
message-retry policies are **GATED** (new backend work flagged to backend):

| FR/NFR ID | Status | Blocking Dependency |
|-----------|--------|---------------------|
| FR-R15 MWL/MPPS lifecycle | GATED | Full MPPS workflow not wired; MWL C-FIND SCP exists (dicom-mwl-scp) |
| FR-R15-03 (outbound status) | GATED | `/exams/{id}/complete` updates internal status + worklist `performed` (post-merge 4d136e0) but sends no outbound HL7 ORM/ORU to the RIS |
| FR-R15 report delivery push | GATED | Depends on R12 reporting |
| FR-R15 reconciliation/retry | GATED | No dead-letter/retry policy UI |

## Cross-Artifact Dependencies

| Source Artifact | Target Artifact | Dependency |
|-----------------|-----------------|------------|
| 01 User Requirements | 03 User Stories | US-R15-01..06 map to FRs |
| 01 User Requirements | 06 Acceptance Criteria | Every FR/NFR has ≥1 AC |
| 02 Workflow Maps | 03 User Stories | W1 inbound → US-R15-01/02; W2 outbound → US-R15-03/04 |
| 03 User Stories | 04 UI/UX Requirements | Message dashboard/reconcile state specs |
| 04 UI/UX Requirements | 06 Acceptance Criteria | Each state → validator gate |

## Cross-Role Dependencies

| Role | Dependency Type | Target Role | Contract |
|------|----------------|-------------|----------|
| R15 External RIS | Sends orders | R04 Service Coordinator | HL7 ORM^O01 → schedule board |
| R15 External RIS | Populates worklist | R06/R07 Technologist/Technician | Orders → modality worklist |
| R15 External RIS | Receives status | R06/R07/R04 | ORM/ORU reverse status updates |
| R15 External RIS | Receives reports | R12/R18 Radiologist | ORU^R01 on finalization |
| R15 External RIS | Operated by | R01/R02 Admin | HL7 config + message dashboard |

## Integration Contracts

| Integration | Direction | Protocol | Failure Semantics |
|-------------|-----------|----------|-------------------|
| Order exchange | R15 → PACS | HL7 ORM^O01 (MLLP) | ACK/NAK; retry 3x → dead-letter → manual reconcile |
| Status updates | PACS → R15 | HL7 ORM/ORU | Idempotent outbound queue; retry 3x → dead-letter |
| Report delivery | PACS → R15 | HL7 ORU^R01 | ≤ 5min from finalize; dead-letter on failure |
| MWL query | R15 → PACS | DICOM C-FIND MWL | ≤ 1000 results; empty set clean |

## Excluded Scope / Out of Scope

- FHIR exchange (R16); DICOM image transfer (R17); clinical reading (R12); billing (R09).
