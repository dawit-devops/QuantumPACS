# Traceability Matrix — Tenant Admin (R02)

## FR/NFR → AC Traceability

| FR/NFR ID | Covered by AC | AC IDs | Status |
|-----------|---------------|--------|--------|
| FR-R02-01 | Yes | AC-R02-01, AC-R02-02 | Covered |
| FR-R02-02 | Yes | AC-R02-03, AC-R02-04 | Covered |
| FR-R02-03 | Yes | AC-R02-05 | Covered |
| FR-R02-04 | Yes | AC-R02-06, AC-R02-07, AC-R02-08 | Covered |
| FR-R02-05 | Yes | AC-R02-29 | Covered |
| FR-R02-06 | Yes | AC-R02-09, AC-R02-10 | Covered |
| FR-R02-07 | Yes | AC-R02-11 | Covered |
| FR-R02-08 | No | — | Gap — no AC yet |
| FR-R02-09 | Yes | AC-R02-12, AC-R02-13 | Covered |
| FR-R02-10 | Yes | AC-R02-14, AC-R02-15 | Covered |
| FR-R02-11 | Yes | AC-R02-16, AC-R02-17 | Covered |
| FR-R02-12 | Yes | AC-R02-18 | Covered |
| FR-R02-13 | Yes | AC-R02-21 | Covered |
| FR-R02-14 | Yes | AC-R02-19 | Covered |
| FR-R02-15 | Yes | AC-R02-20 | Covered |
| FR-R02-16 | Yes | AC-R02-03, AC-R02-11, AC-R02-22 | Covered |
| NFR-R02-01 | No | — | Gap — no AC yet |
| NFR-R02-02 | No | — | Gap — no AC yet |
| NFR-R02-03 | Yes | AC-R02-01 | Covered |
| NFR-R02-04 | No | — | Gap — no AC yet |
| NFR-R02-05 | No | — | Gap — no AC yet |
| NFR-R02-06 | Yes | AC-R02-15 | Covered |
| NFR-R02-07 | No | — | Gap — no AC yet |
| NFR-R02-08 | No | — | Gap — no AC yet |
| NFR-R02-09 | No | — | Gap — no AC yet |
| NFR-R02-10 | No | — | Gap — no AC yet |

## GATED Requirements (codebase reality, verified 2026-08-03)

Most R02 admin FRs are implemented (tenant-scoped CRUD via the shared R01 screens).
GATED items are aspirational v3.0 — ACs exist in artifact 06 but are **GATED** on new
backend work flagged to backend:

| FR/NFR ID | Status | Blocking Dependency |
|-----------|--------|---------------------|
| FR-R02-15 (partial) | Partial — `GET /tenants/{id}/stats` exists (storage + quota); usage/quota dashboard UI GATED | Usage dashboard endpoint/UI needed |
| (not an FR yet) Department/modality registry | GATED | No department CRUD endpoint; modalities implied by station AEs — raise as new FR |
| (not an FR yet) Backup/restore (tenant scope) | GATED | No backup UI (shared R01 roadmap item) — raise as new FR |

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
| R01 Super Admin | Provisions tenant | R02 Tenant Admin | Tenant DB, quota, admin user; R02 operates inside it |
| R04 Service Coordinator | Consumes worklist config | R02 Tenant Admin | Worklist/station configuration managed by R02 |
| R06/R07 Technologist/Technician | Uses worklists | R02 Tenant Admin | Modality worklists configured by R02 |
| R15/R16/R17 External RIS/EMR/PACS | Tenant-scoped integrations | R02 Tenant Admin | Integration endpoints managed by R02 |
| R05 QI/QA | Reads tenant audit | R02 Tenant Admin | R02 ensures audit capture |
| R03 Service Director | Consumes tenant metrics | R02 Tenant Admin | Tenant infra SLOs |
