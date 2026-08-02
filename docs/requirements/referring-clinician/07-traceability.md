# Traceability Matrix — Referring Clinician (R14)

## FR/NFR → AC Traceability

| FR/NFR ID | Covered by AC | AC IDs | Status |
|-----------|---------------|--------|--------|
| FR-R14-01 | Yes | AC-R14-01, AC-R14-02, AC-R14-03, AC-R14-04, AC-R14-05, AC-R14-06, AC-R14-07, AC-R14-08 | Covered |
| FR-R14-02 | Yes | AC-R14-09, AC-R14-10, AC-R14-11, AC-R14-12, AC-R14-13, AC-R14-14 | Covered |
| FR-R14-03 | Yes | AC-R14-15, AC-R14-16, AC-R14-17, AC-R14-18, AC-R14-19, AC-R14-20, AC-R14-21 | Covered |
| FR-R14-04 | Yes | AC-R14-22, AC-R14-23, AC-R14-24, AC-R14-25, AC-R14-26, AC-R14-27 | Covered |
| FR-R14-05 | Yes | AC-R14-28, AC-R14-29, AC-R14-30, AC-R14-31, AC-R14-32, AC-R14-33, AC-R14-34 | Covered |
| FR-R14-06 | Yes | AC-R14-35, AC-R14-36, AC-R14-37, AC-R14-38, AC-R14-39, AC-R14-40, AC-R14-41 | Covered |
| FR-R14-07 | Yes | AC-R14-42, AC-R14-43, AC-R14-44, AC-R14-45, AC-R14-46, AC-R14-47, AC-R14-48, AC-R14-49 | Covered |
| FR-R14-08 | Yes | AC-R14-50, AC-R14-51, AC-R14-52, AC-R14-53, AC-R14-54, AC-R14-55 | Covered |
| FR-R14-09 | Yes | AC-R14-56, AC-R14-57, AC-R14-58, AC-R14-59, AC-R14-60, AC-R14-61, AC-R14-62 | Covered |
| FR-R14-10 | Yes | AC-R14-63, AC-R14-64, AC-R14-65, AC-R14-66, AC-R14-67, AC-R14-68 | Covered |
| FR-R14-11 | Yes | AC-R14-69, AC-R14-70, AC-R14-71, AC-R14-72, AC-R14-73 | Covered |
| FR-R14-12 | No | — | Gap — no AC yet |
| NFR-R14-01 | No | — | Gap — no AC yet |
| NFR-R14-02 | No | — | Gap — no AC yet |
| NFR-R14-03 | No | — | Gap — no AC yet |
| NFR-R14-04 | No | — | Gap — no AC yet |
| NFR-R14-05 | No | — | Gap — no AC yet |
| NFR-R14-06 | No | — | Gap — no AC yet |
| NFR-R14-07 | No | — | Gap — no AC yet |
| NFR-R14-08 | No | — | Gap — no AC yet |
| NFR-R14-09 | No | — | Gap — no AC yet |
| NFR-R14-10 | No | — | Gap — no AC yet |
| NFR-R14-11 | No | — | Gap — no AC yet |
| NFR-R14-12 | No | — | Gap — no AC yet |

## GATED Requirements (codebase reality, verified 2026-08-03)

Share-link viewer (`/view/:key`) and OAuth-provider admin are implemented. Portal
FRs are aspirational v3.0 spec — ACs exist in artifact 06 but are **GATED** on new
backend work (report retrieval depends on R12 reporting; status tracking,
notifications, patient selector, follow-up, share self-service flagged to backend):

| FR/NFR ID | Status | Blocking Dependency |
|-----------|--------|---------------------|
| FR-R14-04 (report retrieval) | GATED | No reporting endpoints (R12 gap) |
| FR-R14-05 (study status) | GATED | No clinician status API |
| FR-R14-06 (results notification) | GATED | No email/notification routing |
| FR-R14-07..12 (selector, detail, mobile portal, follow-up, share mgmt, alerts) | GATED | No clinician portal shell |

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
| R14 Referring Clinician | Consumes reports | R12 Staff Radiologist | Signed report → share-link display (GATED on reporting) |
| R14 Referring Clinician | Receives results | R01/R02 Admin | Results notification routing (GATED) |
| R14 Referring Clinician | Views imaging | R12/R01 share workflow | `/files/{id}/share` → `/view/:key` viewer |
| R14 Referring Clinician | Places orders | R08 Front Desk / R15 RIS | Order intake → exam scheduling |
