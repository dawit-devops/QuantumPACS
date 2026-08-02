# Traceability Matrix — Teleradiologist (R18)

## FR/NFR → AC Traceability

| FR/NFR ID | Covered by AC | AC IDs | Status |
|-----------|---------------|--------|--------|
| FR-R18-01 | No | — | Gap — no AC yet |
| FR-R18-02 | No | — | Gap — no AC yet |
| FR-R18-03 | No | — | Gap — no AC yet |
| FR-R18-04 | No | — | Gap — no AC yet |
| FR-R18-05 | No | — | Gap — no AC yet |
| FR-R18-06 | No | — | Gap — no AC yet |
| FR-R18-07 | No | — | Gap — no AC yet |
| FR-R18-08 | No | — | Gap — no AC yet |
| FR-R18-09 | No | — | Gap — no AC yet |
| FR-R18-10 | No | — | Gap — no AC yet |
| FR-R18-11 | No | — | Gap — no AC yet |
| FR-R18-12 | No | — | Gap — no AC yet |
| FR-R18-13 | No | — | Gap — no AC yet |
| FR-R18-14 | No | — | Gap — no AC yet |
| FR-R18-15 | No | — | Gap — no AC yet |
| FR-R18-16 | No | — | Gap — no AC yet |
| FR-R18-17 | No | — | Gap — no AC yet |
| FR-R18-18 | No | — | Gap — no AC yet |
| FR-R18-19 | No | — | Gap — no AC yet |
| FR-R18-20 | No | — | Gap — no AC yet |
| FR-R18-21 | No | — | Gap — no AC yet |
| FR-R18-22 | No | — | Gap — no AC yet |
| FR-R18-23 | No | — | Gap — no AC yet |
| FR-R18-24 | No | — | Gap — no AC yet |
| NFR-R18-01 | No | — | Gap — no AC yet |
| NFR-R18-02 | No | — | Gap — no AC yet |
| NFR-R18-03 | No | — | Gap — no AC yet |
| NFR-R18-04 | No | — | Gap — no AC yet |
| NFR-R18-05 | No | — | Gap — no AC yet |
| NFR-R18-06 | No | — | Gap — no AC yet |
| NFR-R18-07 | No | — | Gap — no AC yet |
| NFR-R18-08 | No | — | Gap — no AC yet |
| NFR-R18-09 | No | — | Gap — no AC yet |
| NFR-R18-10 | No | — | Gap — no AC yet |
| NFR-R18-11 | No | — | Gap — no AC yet |
| NFR-R18-12 | No | — | Gap — no AC yet |
| NFR-R18-13 | No | — | Gap — no AC yet |
| NFR-R18-14 | No | — | Gap — no AC yet |
| NFR-R18-15 | No | — | Gap — no AC yet |
| NFR-R18-16 | No | — | Gap — no AC yet |
| NFR-R18-17 | No | — | Gap — no AC yet |
| NFR-R18-18 | No | — | Gap — no AC yet |

## GATED Requirements (codebase reality, verified 2026-08-03)

Remote viewer/annotation/share features are implemented (same as R12). Telerad-
specific FRs are aspirational v3.0 spec — ACs exist in artifact 06 but are **GATED**
on new backend work (offline packages, prelim→final routing, consult queue, secure
remote config; reporting shared with R12):

| FR/NFR ID | Status | Blocking Dependency |
|-----------|--------|---------------------|
| FR-R18 offline/edge packages | GATED | No offline-package endpoints |
| FR-R18 prelim→final routing | GATED | No reporting/sign-off backend |
| FR-R18 consultations / multi-site | GATED | No consult-queue endpoints |

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
| R06/R07 Technologist/Technician | Exam completion → worklist assignment | R18 Teleradiologist | MPPS completion → remote worklist |
| R04 Service Coordinator | Stat/priority triage | R18 Teleradiologist | Worklist ordering |
| R02 Tenant Admin | Remote access config | R18 Teleradiologist | VPN/SSO setup |
| R15 External RIS | Order context | R18 Teleradiologist | HL7/FHIR scheduling data |
| R16 External EMR | Patient demographics | R18 Teleradiologist | Clinical context |
| **R14 (Referring Clinician)**: Report delivery, critical findings notification | | | |
| **R12 (Staff Radiologist)**: Preliminary report review and finalization | | | |
| **R03 (Service Director)**: Turnaround time metrics, coverage analytics | | | |
| **R12 (Staff Radiologist)**: Shared viewer/reporting tools, consultation workflow | | | |
| **R13 (Resident)**: Teaching case access, supervision workflow (teleradiologist may supervise remotely) | | | |
