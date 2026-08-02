# Traceability Matrix — Front Desk / Receptionist (R08)

## FR/NFR → AC Traceability

| FR/NFR ID | Covered by AC | AC IDs | Status |
|-----------|---------------|--------|--------|
| FR-R08-01 | Yes | AC-R08-01 | Covered |
| FR-R08-02 | Yes | AC-R08-02 | Covered |
| FR-R08-03 | Yes | AC-R08-03 | Covered |
| FR-R08-04 | Yes | AC-R08-04 | Covered |
| FR-R08-05 | Yes | AC-R08-05 | Covered |
| FR-R08-06 | Yes | AC-R08-06 | Covered |
| FR-R08-07 | Yes | AC-R08-07 | Covered |
| FR-R08-08 | Yes | AC-R08-08 | Covered |
| FR-R08-09 | Yes | AC-R08-09 | Covered |
| FR-R08-10 | Yes | AC-R08-10 | Covered |
| NFR-R08-01 | Yes | AC-R08-11 | Covered |
| NFR-R08-02 | Yes | AC-R08-13 | Covered |
| NFR-R08-03 | Yes | AC-R08-14 | Covered |
| NFR-R08-04 | Yes | AC-R08-15 | Covered |
| NFR-R08-05 | Yes | AC-R08-16 | Covered |
| NFR-R08-06 | Yes | AC-R08-12 | Covered |

## GATED Requirements (codebase reality, verified 2026-08-03)

No registration/scheduling routes or endpoints exist in the codebase. All FRs below
are aspirational v3.0 spec — ACs exist in artifact 06 but are **GATED** on new
backend work (registration module + permissions flagged to backend):

| FR/NFR ID | Status | Blocking Dependency |
|-----------|--------|---------------------|
| FR-R08-01 (partial) | Partial — patient lookup via Files browser/patient page; dedup + registration flow GATED | No registration endpoints or routes |
| FR-R08-02..10 | GATED | No registration/scheduling endpoints or routes |
| NFR-R08-01..06 | GATED | Blocked on the FRs above |

## Cross-Artifact Dependencies

| Source Artifact | Target Artifact | Dependency |
|-----------------|-----------------|------------|
| 01 User Requirements | 03 User Stories | Each US maps to ≥1 FR (US-R08-01..07) |
| 01 User Requirements | 06 Acceptance Criteria | Every FR/NFR has ≥1 AC |
| 02 Workflow Maps | 03 User Stories | W1 registration → US-R08-01/02/03; W2 scheduling → US-R08-04 |
| 03 User Stories | 04 UI/UX Requirements | Registration form/slot picker state specs |
| 04 UI/UX Requirements | 06 Acceptance Criteria | Each state → validator gate |

## Cross-Role Dependencies

| Role | Dependency Type | Target Role | Contract |
|------|----------------|-------------|----------|
| R08 Front Desk | Registers patient | R04 Service Coordinator | Patient/order visible on schedule board |
| R08 Front Desk | Schedules exam | R06/R07 Technologist/Technician | Exam appears in modality worklist |
| R08 Front Desk | Registers patient | R11 Nursing | Check-in status feeds nursing worklist |
| R08 Front Desk | Syncs demographics | R16 External EMR | HL7 ADT A01 outbound (async) |
| R08 Front Desk | Captures insurance | R09 Cashier | Insurance/authorization data for billing |
| R08 Front Desk | Orders reference | R15 External RIS | Order context via HL7 ORM inbound |
| R08 Front Desk | Consent handling | R01/R02 Admin | Consent forms retained + audited |

## Integration Contracts

| Integration | Direction | Protocol | Failure Semantics |
|-------------|-----------|----------|-------------------|
| Patient demographics sync (R16) | R08 → R16 | HL7 ADT A01/A04/A08 | Async retry → dead-letter → manual reconciliation |
| Order context (R15) | R15 → R08 | HL7 ORM^O01 | Retry 3x → dead-letter → manual reconcile |

## Excluded Scope / Out of Scope

- Payment and claims processing (R09); schedule administration (R04); clinical care during exam (R11); image interpretation (R12).
