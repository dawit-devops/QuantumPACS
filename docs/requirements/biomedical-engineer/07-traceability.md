# Traceability Matrix — Biomedical Engineer (R10)

## FR/NFR → AC Traceability

| FR/NFR ID | Covered by AC | AC IDs | Status |
|-----------|---------------|--------|--------|
| FR-R10-01 | Yes | AC-R10-01 | Covered |
| FR-R10-02 | Yes | AC-R10-02 | Covered |
| FR-R10-03 | Yes | AC-R10-03 | Covered |
| FR-R10-04 | Yes | AC-R10-04 | Covered |
| FR-R10-05 | Yes | AC-R10-05 | Covered |
| FR-R10-06 | Yes | AC-R10-06 | Covered |
| FR-R10-07 | Yes | AC-R10-07 | Covered |
| FR-R10-08 | Yes | AC-R10-08 | Covered |
| FR-R10-09 | Yes | AC-R10-09 | Covered |
| FR-R10-10 | Yes | AC-R10-10 | Covered |
| NFR-R10-01 | Yes | AC-R10-11 | Covered |
| NFR-R10-02 | Yes | AC-R10-13 | Covered |
| NFR-R10-03 | Yes | AC-R10-14 | Covered |
| NFR-R10-04 | Yes | AC-R10-15 | Covered |
| NFR-R10-05 | Yes | AC-R10-16 | Covered |
| NFR-R10-06 | Yes | AC-R10-12 | Covered |

## GATED Requirements (codebase reality, verified 2026-08-03)

No equipment routes or endpoints exist in the codebase. All equipment FRs are
aspirational v3.0 spec — ACs exist in artifact 06 but are **GATED** on new backend
work (equipment registry, PM/QC, downtime, tickets, alerts flagged to backend):

| FR/NFR ID | Status | Blocking Dependency |
|-----------|--------|---------------------|
| FR-R10-10 (partial) | Partial — audit-log infrastructure exists (shared `/logs`) | No equipment-specific audit view |
| FR-R10-01..09 (equipment FRs) | GATED | No equipment endpoints or routes |
| NFR-R10-* | GATED | Blocked on the FRs above |

## Cross-Artifact Dependencies

| Source Artifact | Target Artifact | Dependency |
|-----------------|-----------------|------------|
| 01 User Requirements | 03 User Stories | US-R10-01..06 map to FRs |
| 01 User Requirements | 06 Acceptance Criteria | Every FR/NFR has ≥1 AC |
| 02 Workflow Maps | 03 User Stories | W1 downtime → US-R10-04; W2 PM/QC → US-R10-02/03 |
| 03 User Stories | 04 UI/UX Requirements | Downtime console/PM queue state specs |
| 04 UI/UX Requirements | 06 Acceptance Criteria | Each state → validator gate |

## Cross-Role Dependencies

| Role | Dependency Type | Target Role | Contract |
|------|----------------|-------------|----------|
| R10 Biomedical Engineer | Provides uptime/PM metrics | R03 Service Director | Uptime, PM compliance, downtime impact aggregates |
| R10 Biomedical Engineer | Blocks modality on downtime | R04 Service Coordinator | Downtime event prevents exam scheduling |
| R10 Biomedical Engineer | Status visible to operators | R06/R07 Technologist/Technician | Equipment status badge on worklists |
| R10 Biomedical Engineer | Registry administration | R01/R02 Admin | Equipment registry CRUD + audit retention |

## Integration Contracts

| Integration | Direction | Protocol | Failure Semantics |
|-------------|-----------|----------|-------------------|
| Fault alerts | R10 → Notification service | WebSocket / in-app | ≤ 30s delivery; retry on connect; audit of deliveries |
| R03 metrics feed | R10 → R03 | Aggregate API (read) | Async refresh ≤ 5min; stale-data indicator |

## Excluded Scope / Out of Scope

- Patient data access (none required); vendor remote diagnostics; clinical workflows.
