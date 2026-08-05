# Traceability Matrix — Super Admin (R01)

## FR/NFR → AC Traceability

| FR/NFR ID | Covered by AC | AC IDs | Status |
|-----------|---------------|--------|--------|
| FR-R01-01 | Yes | AC-R01-01, AC-R01-02, AC-R01-03 | Covered |
| FR-R01-02 | Yes | AC-R01-04 | Covered |
| FR-R01-03 | Yes | AC-R01-05, AC-R01-06 | Covered |
| FR-R01-04 | Yes | AC-R01-07 | Covered |
| FR-R01-05 | Yes | AC-R01-08, AC-R01-09 | Covered |
| FR-R01-06 | Yes | AC-R01-10, AC-R01-11 | Covered |
| FR-R01-07 | Yes | AC-R01-12, AC-R01-13 | Covered |
| FR-R01-08 | Yes | AC-R01-14, AC-R01-15 | Covered |
| FR-R01-09 | Yes | AC-R01-35 | Covered |
| FR-R01-10 | Yes | AC-R01-16, AC-R01-17, AC-R01-18 | Covered |
| FR-R01-11 | Yes | AC-R01-19, AC-R01-20 | Covered |
| FR-R01-12 | Yes | AC-R01-36 | Covered |
| FR-R01-13 | Yes | AC-R01-21, AC-R01-22 | Covered |
| FR-R01-14 | Yes | AC-R01-23, AC-R01-24 | Covered |
| FR-R01-15 | Yes | AC-R01-25, AC-R01-26 | Covered |
| FR-R01-16 | Yes | AC-R01-27 | Covered |
| FR-R01-17 | Yes | AC-R01-37 | Covered — `GET /v2/dashboard/health` (METRICS_READ) implemented; AC-R01-37 Pass |
| FR-R01-18 | Yes | AC-R01-38 | GATED — no implementation exists; backlog |
| FR-R01-19 | Yes | AC-R01-05, AC-R01-28 | Covered |
| FR-R01-20 | Yes | AC-R01-29 | Covered |
| NFR-R01-01 | Yes | AC-R01-30 | Covered |
| NFR-R01-02 | Yes | AC-R01-31 | Covered |
| NFR-R01-03 | Yes | AC-R01-16 | Covered |
| NFR-R01-04 | Yes | AC-R01-39 | Covered |
| NFR-R01-05 | Yes | AC-R01-01, AC-R01-11, AC-R01-28 | Covered |
| NFR-R01-06 | Yes | AC-R01-06, AC-R01-15, AC-R01-26 | Covered |
| NFR-R01-07 | Yes | AC-R01-32 | Covered |
| NFR-R01-08 | Yes | AC-R01-32 | Covered |
| NFR-R01-09 | Yes | AC-R01-04 | Covered |
| NFR-R01-10 | Implicit | AC-R01-35 (≤ 5s target embedded in AC) | Covered |
| NFR-R01-11 | Yes | AC-R01-33 | Covered |
| NFR-R01-12 | Yes | AC-R01-40 | Covered |
| NFR-R01-13 | Yes | AC-R01-34 | Covered |
| NFR-R01-14 | Yes | AC-R01-41 | Covered |

## Cross-Artifact Dependencies

| Source Artifact | Target Artifact | Dependency |
|-----------------|-----------------|------------|
| 01 User Requirements | 03 User Stories | Each US maps to ≥1 FR |
| 01 User Requirements | 06 Acceptance Criteria | Each FR/NFR has ≥1 AC |
| 02 Workflow Maps | 03 User Stories | Each workflow step with user decision → US |
| 03 User Stories | 04 UI/UX Requirements | Each US component → state spec |
| 04 UI/UX Requirements | 06 Acceptance Criteria | Each state → validator gate |
| 05 Metrics & SLAs | 06 Acceptance Criteria | Each metric target → measurable AC |
| 07 Traceability Matrix | 08 Implementation Roadmap | Roadmap derived from traceability gaps |

## Cross-Role Dependencies

| Role | Dependency Type | Target Role | Contract |
|------|----------------|-------------|----------|
| R01 Super Admin | Provisions tenant | R02 Tenant Admin | Tenant config + credentials |
| R01 Super Admin | Configures integrations | R15 External RIS | HL7/FHIR endpoint config |
| R01 Super Admin | Configures integrations | R16 External EMR | HL7/FHIR endpoint config |
| R01 Super Admin | Configures integrations | R17 External PACS | DICOM C-FIND/C-MOVE/C-STORE config |
| R03 Service Director | Consumes metrics | R01 Super Admin | Infrastructure SLOs from metrics dashboard |
| R05 QI/QA | Consumes QA reports | R01 Super Admin | Audit log access, protocol compliance data |
| R12 Staff Radiologist | Depends on storage/replica health | R01 Super Admin | Routing rules, worklist availability |
| R18 Teleradiologist | Depends on storage/replica health | R01 Super Admin | Routing rules, secure remote access config |

## Integration Contracts (R15–R17)

| Integration | Direction | Protocol | Failure Semantics |
|-------------|-----------|----------|-------------------|
| External RIS (R15) | R15 → R01/R02 | HL7 ORM/ORU, FHIR ServiceRequest | Retry 3x → dead-letter → manual reconciliation |
| External EMR (R16) | R16 → R01/R02 | HL7 ADT/ORM/ORU, FHIR Patient | Async backfill, no blocking |
| External PACS (R17) | R17 ↔ R01/R02 | DICOM C-FIND/C-MOVE/C-STORE | Query timeout 30s, retrieve retry 2x |