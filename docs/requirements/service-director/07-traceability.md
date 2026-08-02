# Traceability Matrix — Service Director (R03)

## FR/NFR → AC Traceability

| FR/NFR ID | Covered by AC | AC IDs | Status |
|-----------|---------------|--------|--------|
| FR-R03-01 | No | — | Gap — no AC yet |
| FR-R03-02 | No | — | Gap — no AC yet |
| FR-R03-03 | No | — | Gap — no AC yet |
| FR-R03-04 | No | — | Gap — no AC yet |
| FR-R03-05 | No | — | Gap — no AC yet |
| FR-R03-06 | No | — | Gap — no AC yet |
| FR-R03-07 | No | — | Gap — no AC yet |
| FR-R03-08 | No | — | Gap — no AC yet |
| FR-R03-09 | No | — | Gap — no AC yet |
| FR-R03-10 | No | — | Gap — no AC yet |
| FR-R03-11 | No | — | Gap — no AC yet |
| FR-R03-12 | No | — | Gap — no AC yet |
| FR-R03-13 | No | — | Gap — no AC yet |
| FR-R03-14 | No | — | Gap — no AC yet |
| FR-R03-15 | No | — | Gap — no AC yet |
| NFR-R03-01 | No | — | Gap — no AC yet |
| NFR-R03-02 | No | — | Gap — no AC yet |
| NFR-R03-03 | No | — | Gap — no AC yet |
| NFR-R03-04 | No | — | Gap — no AC yet |
| NFR-R03-05 | No | — | Gap — no AC yet |
| NFR-R03-06 | No | — | Gap — no AC yet |
| NFR-R03-07 | No | — | Gap — no AC yet |
| NFR-R03-08 | No | — | Gap — no AC yet |
| NFR-R03-09 | No | — | Gap — no AC yet |
| NFR-R03-10 | No | — | Gap — no AC yet |

## GATED Requirements (codebase reality, verified 2026-08-03)

No analytics/reporting routes or endpoints exist in the codebase (only `/metrics` +
`/dashboard/metrics`). All analytics FRs are aspirational v3.0 spec — ACs exist in
artifact 06 but are **GATED** on new backend work (`/analytics/*`, `/reports/*`
endpoints + `ANALYTICS_*`/`REPORT_*` permissions flagged to backend):

| FR/NFR ID | Status | Blocking Dependency |
|-----------|--------|---------------------|
| FR-R03-01..15 (analytics/reporting) | GATED | No analytics or report endpoints |
| NFR-R03-* | GATED | Blocked on the FRs above |

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
| R03 Service Director | Consumes metrics | R01 Super Admin | Infrastructure SLOs from metrics dashboard |
| R03 Service Director | Consumes QA data | R05 QI/QA Team | QA scores → protocol compliance scorecard |
| R03 Service Director | Consumes turnaround data | R12 Staff Radiologist | `report.signed_at` − `study.created` (GATED on reporting) |
| R03 Service Director | Consumes equipment data | R10 Biomedical Engineer | Modality uptime, PM schedule, downtime (GATED) |
| R03 Service Director | Consumes scheduling data | R04 Service Coordinator | Worklist status (scheduled/performed/cancelled) |
