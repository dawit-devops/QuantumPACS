# Traceability Matrix — Radiology Service Cashier (R09)

## FR/NFR → AC Traceability

| FR/NFR ID | Covered by AC | AC IDs | Status |
|-----------|---------------|--------|--------|
| FR-R09-01 | Yes | AC-R09-01 | Covered |
| FR-R09-02 | Yes | AC-R09-02 | Covered |
| FR-R09-03 | Yes | AC-R09-03 | Covered |
| FR-R09-04 | Yes | AC-R09-04 | Covered |
| FR-R09-05 | Yes | AC-R09-05 | Covered |
| FR-R09-06 | Yes | AC-R09-06 | Covered |
| FR-R09-07 | Yes | AC-R09-07 | Covered |
| FR-R09-08 | Yes | AC-R09-08 | Covered |
| FR-R09-09 | Yes | AC-R09-09 | Covered |
| FR-R09-10 | Yes | AC-R09-10 | Covered |
| NFR-R09-01 | Yes | AC-R09-11 | Covered |
| NFR-R09-02 | Yes | AC-R09-13 | Covered |
| NFR-R09-03 | Yes | AC-R09-14 | Covered |
| NFR-R09-04 | Yes | AC-R09-12 | Covered |
| NFR-R09-05 | Yes | AC-R09-15 | Covered |
| NFR-R09-06 | Yes | AC-R09-16 | Covered |

## GATED Requirements (codebase reality, verified 2026-08-03)

No billing routes or endpoints exist in the codebase. All billing FRs are
aspirational v3.0 spec — ACs exist in artifact 06 but are **GATED** on new backend
work (billing module + payment/claims integrations flagged to backend):

| FR/NFR ID | Status | Blocking Dependency |
|-----------|--------|---------------------|
| FR-R09-09 (partial) | Partial — read-only patient/study context exists (Files/patient page) | No billing context in billing flow |
| FR-R09-01..08, FR-R09-10 (billing FRs) | GATED | No billing endpoints, payment processor, claims feed |
| NFR-R09-* | GATED | Blocked on the FRs above |

## Cross-Artifact Dependencies

| Source Artifact | Target Artifact | Dependency |
|-----------------|-----------------|------------|
| 01 User Requirements | 03 User Stories | US-R09-01..06 map to FRs |
| 01 User Requirements | 06 Acceptance Criteria | Every FR/NFR has ≥1 AC |
| 02 Workflow Maps | 03 User Stories | W1 payment → US-R09-02/03; W2 reconciliation → US-R09-05 |
| 03 User Stories | 04 UI/UX Requirements | Payment form/reconciliation state specs |
| 04 UI/UX Requirements | 06 Acceptance Criteria | Each state → validator gate |

## Cross-Role Dependencies

| Role | Dependency Type | Target Role | Contract |
|------|----------------|-------------|----------|
| R09 Cashier | Consumes insurance data | R08 Front Desk | Insurance/authorization on visit |
| R09 Cashier | Refund approval | R01/R02 Admin | Approval queue + audit |
| R09 Cashier | Read-only clinical context | R04 Service Coordinator | Scheduled/ordered procedures only |
| R09 Cashier | Billing metrics | R03 Service Director | Turnaround + collection KPIs |
| R09 Cashier | Audit | R01/R02 Admin | All payment mutations logged |

## Integration Contracts

| Integration | Direction | Protocol | Failure Semantics |
|-------------|-----------|----------|-------------------|
| Payment processor (tokenized) | R09 → Processor | REST (tokenized card) | Decline → retry with alternatives; idempotency key; no PAN stored |
| Claims status feed (future) | External → R09 | HL7/Bulk FHIR | Async; manual status fallback; denials flagged |

## Excluded Scope / Out of Scope

- Clinical image/report access (R12); insurance authorization creation (R08); merchant account admin (R01).
