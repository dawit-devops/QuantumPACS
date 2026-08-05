# Traceability Matrix — Other Hospital Staff (R19)

## FR/NFR → AC Traceability

| FR/NFR ID | Covered by AC | AC IDs | Status |
|-----------|---------------|--------|--------|
| FR-R19-01 | Yes | AC-R19-01 | Covered |
| FR-R19-02 | Yes | AC-R19-02 | Covered |
| FR-R19-03 | Yes | AC-R19-03 | Covered |
| FR-R19-04 | Yes | AC-R19-04 | Covered |
| FR-R19-05 | Yes | AC-R19-05 | Covered |
| FR-R19-06 | Yes | AC-R19-06 | Covered |
| FR-R19-07 | Yes | AC-R19-07 | Covered |
| FR-R19-08 | Yes | AC-R19-08 | Covered |
| FR-R19-09 | Yes | AC-R19-09 | Covered |
| FR-R19-10 | Yes | AC-R19-10 | Covered |
| NFR-R19-01 | Yes | AC-R19-13 | Covered |
| NFR-R19-02 | Yes | AC-R19-14 | Covered |
| NFR-R19-03 | Yes | AC-R19-15 | Covered |
| NFR-R19-04 | Yes | AC-R19-11 | Covered |
| NFR-R19-05 | Yes | AC-R19-12 | Covered |
| NFR-R19-06 | Yes | AC-R19-16 | Covered |

## GATED Requirements (codebase reality, verified 2026-08-03)

No limited-scope portal routes or endpoints exist in the codebase. Portal FRs are
aspirational v3.0 spec — ACs exist in artifact 06 but are **GATED** on new backend
work (care-team scope model, portal shell, results notification flagged to backend):

| FR/NFR ID | Status | Blocking Dependency |
|-----------|--------|---------------------|
| FR-R19-05 (partial) | Implemented — read-only viewer via share link / Files browser | n/a |
| FR-R19-09 (partial) | Implemented — shared audit infrastructure (`/logs`) | n/a |
| FR-R19-01..04, FR-R19-06..08, FR-R19-10 (portal FRs) | GATED | No portal endpoints or routes |
| NFR-R19-* | GATED | Blocked on the FRs above |

## Cross-Artifact Dependencies

| Source Artifact | Target Artifact | Dependency |
|-----------------|-----------------|------------|
| 01 User Requirements | 03 User Stories | US-R19-01..06 map to FRs |
| 01 User Requirements | 06 Acceptance Criteria | Every FR/NFR has ≥1 AC |
| 02 Workflow Maps | 03 User Stories | W1 results check → US-R19-01/02/03; W2 notification → US-R19-04 |
| 03 User Stories | 04 UI/UX Requirements | Portal/search/read-only viewer state specs |
| 04 UI/UX Requirements | 06 Acceptance Criteria | Each state → validator gate |

## Cross-Role Dependencies

| Role | Dependency Type | Target Role | Contract |
|------|----------------|-------------|----------|
| R19 Hospital Staff | Reads results | R12/R18 Radiologist | Finalized reports only (drafts hidden) |
| R19 Hospital Staff | Order status | R04/R15 | Order status via schedule/worklist |
| R19 Hospital Staff | Notification source | R12/R18 | Report-finalize event → fan-out |
| R19 Hospital Staff | Scope/audit | R01/R02 Admin | Care-team scope model + audit retention |
| R19 Hospital Staff | Read-only viewer | R14 Referring Clinician | Reuses share-link read-only mode |

## Integration Contracts

| Integration | Direction | Protocol | Failure Semantics |
|-------------|-----------|----------|-------------------|
| Report finalize → notify | R12 → R19 | Notification event | ≤ 60s; no PHI in body; retry + audit |
| Scoped read | R19 → API | REST (read-only) | 403 on out-of-scope; logged |

## Excluded Scope / Out of Scope

- Admin (R01/R02); reading/reporting (R12/R18); acquisition (R06/R07); nursing documentation (R11); billing (R09).
