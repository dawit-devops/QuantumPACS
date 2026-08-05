# Traceability Matrix — External PACS (R17)

## FR/NFR → AC Traceability

| FR/NFR ID | Covered by AC | AC IDs | Status |
|-----------|---------------|--------|--------|
| FR-R17-01 | Yes | AC-R17-01 | Covered |
| FR-R17-02 | Yes | AC-R17-02 | Covered |
| FR-R17-03 | Yes | AC-R17-03 | Covered |
| FR-R17-04 | Yes | AC-R17-04 | Covered |
| FR-R17-05 | Yes | AC-R17-05 | Covered |
| FR-R17-06 | Yes | AC-R17-06 | Covered |
| FR-R17-07 | Yes | AC-R17-07 | Covered |
| FR-R17-08 | Yes | AC-R17-08 | Covered |
| FR-R17-09 | Yes | AC-R17-09 | Covered |
| FR-R17-10 | Yes | AC-R17-10 | Covered |
| NFR-R17-01 | Yes | AC-R17-11 | Covered |
| NFR-R17-02 | Yes | AC-R17-14 | Covered |
| NFR-R17-03 | Yes | AC-R17-15 | Covered |
| NFR-R17-04 | Yes | AC-R17-16 | Covered |
| NFR-R17-05 | Yes | AC-R17-17 | Covered |
| NFR-R17-06 | Yes | AC-R17-12 | Covered |
| NFR-R17-07 | Yes | AC-R17-13 | Covered |

## GATED Requirements (codebase reality, verified 2026-08-03)

QIDO-RS/WADO-RS, WADO-URI, file upload (C-STORE-equivalent), bulk download, and
routing rules are implemented. C-MOVE retrieve workflow, archive synchronization
UI, and migration/backfill tooling are **GATED** (new backend work flagged to
backend):

| FR/NFR ID | Status | Blocking Dependency |
|-----------|--------|---------------------|
| FR-R17 C-MOVE retrieve | GATED | No C-MOVE workflow endpoint |
| FR-R17 archive sync | GATED | No archive-sync UI |
| FR-R17 migration/backfill | GATED | No migration tooling |

## Cross-Artifact Dependencies

| Source Artifact | Target Artifact | Dependency |
|-----------------|-----------------|------------|
| 01 User Requirements | 03 User Stories | US-R17-01..07 map to FRs |
| 01 User Requirements | 06 Acceptance Criteria | Every FR/NFR has ≥1 AC |
| 02 Workflow Maps | 03 User Stories | W1 C-STORE → US-R17-01/06; W2 C-MOVE → US-R17-03 |
| 03 User Stories | 04 UI/UX Requirements | AE/replica/routing admin state specs |
| 04 UI/UX Requirements | 06 Acceptance Criteria | Each state → validator gate |

## Cross-Role Dependencies

| Role | Dependency Type | Target Role | Contract |
|------|----------------|-------------|----------|
| R17 External PACS | Receives stores | R06/R07 Technologist/Technician | Exam completion → C-STORE push |
| R17 External PACS | Serves viewer | R12/R18 Radiologist | WADO-RS frames/thumbnails |
| R17 External PACS | Study lookup | R04 Service Coordinator | C-FIND when scheduling |
| R17 External PACS | Operated by | R01/R02 Admin | AE config, routing, replicas, metrics |
| R17 External PACS | Shares identities | R15/R16 | Patient/order/study cross-references |

## Integration Contracts

| Integration | Direction | Protocol | Failure Semantics |
|-------------|-----------|----------|-------------------|
| Image store | R17 → PACS | DICOM C-STORE | Ack ≤ 10s; NAK with reason; AE retry |
| Query | R17 → PACS | DICOM C-FIND / QIDO-RS | Timeout 30s; invalid params 400 |
| Retrieve | R17 → PACS | DICOM C-MOVE / WADO-RS | Retry 2x; unauthorized 401 |
| Store web | R17 → PACS | DICOMweb STOW-RS | Store response per instance |
| Routing | PACS → targets | DICOM send | After persistence; delivery log; retry per config |

## Excluded Scope / Out of Scope

- HL7 order/report exchange (R15/R16); clinical reading (R12/R18); registration/scheduling (R08/R04); billing (R09).
