# Traceability Matrix — Radiology Service Nursing Team (R11)

## FR/NFR → AC Traceability

| FR/NFR ID | Covered by AC | AC IDs | Status |
|-----------|---------------|--------|--------|
| FR-R11-01 | Yes | AC-R11-01 | Covered |
| FR-R11-02 | Yes | AC-R11-02 | Covered |
| FR-R11-03 | Yes | AC-R11-03 | Covered |
| FR-R11-04 | Yes | AC-R11-04 | Covered |
| FR-R11-05 | Yes | AC-R11-05 | Covered |
| FR-R11-06 | Yes | AC-R11-06 | Covered |
| FR-R11-07 | Yes | AC-R11-07 | Covered |
| FR-R11-08 | Yes | AC-R11-08 | Covered |
| FR-R11-09 | Yes | AC-R11-09 | Covered |
| FR-R11-10 | Yes | AC-R11-10 | Covered |
| NFR-R11-01 | Yes | AC-R11-11 | Covered |
| NFR-R11-02 | Yes | AC-R11-13 | Covered |
| NFR-R11-03 | Yes | AC-R11-14 | Covered |
| NFR-R11-04 | Yes | AC-R11-15 | Covered |
| NFR-R11-05 | Yes | AC-R11-16 | Covered |
| NFR-R11-06 | Yes | AC-R11-12 | Covered |

## GATED Requirements (codebase reality, verified 2026-08-03)

No nursing routes or endpoints exist in the codebase. All nursing FRs are
aspirational v3.0 spec — ACs exist in artifact 06 but are **GATED** on new backend
work (nursing worklist, prep/vitals/contrast endpoints flagged to backend):

| FR/NFR ID | Status | Blocking Dependency |
|-----------|--------|---------------------|
| FR-R11-09 (partial) | Partial — patient/medication context exists in patient page | No nursing-specific MAR workflow |
| FR-R11-01..08, FR-R11-10 (nursing FRs) | GATED | No nursing endpoints or routes |
| NFR-R11-* | GATED | Blocked on the FRs above |

## Cross-Artifact Dependencies

| Source Artifact | Target Artifact | Dependency |
|-----------------|-----------------|------------|
| 01 User Requirements | 03 User Stories | US-R11-01..07 map to FRs |
| 01 User Requirements | 06 Acceptance Criteria | Every FR/NFR has ≥1 AC |
| 02 Workflow Maps | 03 User Stories | W1 safety+contrast → US-R11-04/05/06; W2 reaction → US-R11-05 |
| 03 User Stories | 04 UI/UX Requirements | Safety gate/reaction form state specs |
| 04 UI/UX Requirements | 06 Acceptance Criteria | Each state → validator gate |

## Cross-Role Dependencies

| Role | Dependency Type | Target Role | Contract |
|------|----------------|-------------|----------|
| R11 Nursing | Consumes check-in status | R08 Front Desk | Visit status → nursing worklist |
| R11 Nursing | Links contrast to exam | R06/R07 Technologist/Technician | Contrast record joins exam dose record |
| R11 Nursing | Escalates reactions | R12/R18 Radiologist | Escalation notification + ack ≤ 15min |
| R11 Nursing | Consumes allergy flags | R16 External EMR | HL7 ADT allergy/pregnancy/renal |
| R11 Nursing | Audited documentation | R01/R02 Admin | MAR + vitals audit retention |

## Integration Contracts

| Integration | Direction | Protocol | Failure Semantics |
|-------------|-----------|----------|-------------------|
| Allergy flags | R16 → R11 | HL7 ADT (allergy segments) | Async; missing flag → nurse manual confirm; audit |
| Escalation | R11 → R12/R18 | Notification + fallback SMS/pager | 15min ack SLA; retry fallback; logged |
| Offline sync | R11 ↔ Backend | Queued mutations | Sync ≤ 2min on reconnect; conflict resolution last-write-wins with audit |

## Excluded Scope / Out of Scope

- Image interpretation (R12/R18); modality acquisition (R06/R07); registration/scheduling (R08/R04); billing (R09).
