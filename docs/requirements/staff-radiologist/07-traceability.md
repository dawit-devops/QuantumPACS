# Traceability Matrix — Staff Radiologist (R12)

## FR/NFR → AC Traceability

| FR/NFR ID | Covered by AC | AC IDs | Status |
|-----------|---------------|--------|--------|
| FR-R12-01 | Yes | AC-R12-01, AC-R12-02 | Covered |
| FR-R12-02 | Yes | AC-R12-03, AC-R12-04, AC-R12-05 | Covered |
| FR-R12-03 | Yes | AC-R12-06, AC-R12-07, AC-R12-08 | Covered |
| FR-R12-04 | Yes | AC-R12-09 | Covered |
| FR-R12-05 | Yes | AC-R12-10, AC-R12-11 | Covered |
| FR-R12-06 | Yes | AC-R12-12, AC-R12-13 | Covered |
| FR-R12-07 | Yes | AC-R12-14 | Covered |
| FR-R12-08 | No | — | Gap — no AC yet |
| FR-R12-09 | Yes | AC-R12-15, AC-R12-20, AC-R12-21, AC-R12-30 | Covered |
| FR-R12-10 | Yes | AC-R12-16, AC-R12-17 | Covered |
| FR-R12-11 | Yes | AC-R12-18 | Covered |
| FR-R12-12 | Yes | AC-R12-22, AC-R12-31 | Covered |
| FR-R12-13 | Yes | AC-R12-19 | Covered |
| FR-R12-14 | Yes | AC-R12-27 | Covered |
| FR-R12-15 | Yes | AC-R12-26 | Covered |
| NFR-R12-01 | Yes | AC-R12-03 | Covered |
| NFR-R12-02 | No | — | Gap — no AC yet |
| NFR-R12-03 | Yes | AC-R12-01 | Covered |
| NFR-R12-04 | Yes | AC-R12-02 | Covered |
| NFR-R12-05 | Yes | AC-R12-08 | Covered |
| NFR-R12-06 | Yes | AC-R12-14 | Covered |
| NFR-R12-07 | No | — | Gap — no AC yet |
| NFR-R12-08 | No | — | Gap — no AC yet |
| NFR-R12-09 | No | — | Gap — no AC yet |
| NFR-R12-10 | No | — | Gap — no AC yet |

## GATED Requirements (codebase reality, verified 2026-08-03)

Viewer/annotation/share/audit/patient features, the reading worklist, structured
reporting (draft → preliminary → final + sign + templates), peer review, reading
presets, and study-arrival notifications are implemented (merge 4d136e0). The
remaining FRs below are **GATED** on new backend work:

| FR/NFR ID | Status | Blocking Dependency |
|-----------|--------|---------------------|
| FR-R12-10 (critical findings escalation) | GATED | No escalation endpoint (report sign currently notifies QA role only) |
| FR-R12-12 (attending review) | Partial | `/peer-reviews*` covers final signed reports; resident-draft attending-review queue not built |
| FR-R12-06 (priors endpoint) | GATED | Confirm priors API (currently study search + browser) |

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
| R04 Service Coordinator | Assigns studies | R12 Staff Radiologist | Prioritized reading worklist |
| R06/R07 Technologist/Technician | Completes exams | R12 Staff Radiologist | MPPS completion → reading queue |
| R13 Resident | Drafts under supervision | R12 Staff Radiologist | Attending review workflow |
| R18 Teleradiologist | Shares worklist | R12 Staff Radiologist | Off-hours preliminary/final reads |
| R03 Service Director | Consumes reading KPIs | R12 Staff Radiologist | Turnaround, quality scores |
| R05 QI/QA | Consumes reading KPIs | R12 Staff Radiologist | QA/quality scores |
| R14 Referring Clinician | Receives reports | R12 Staff Radiologist | Signed report delivery |
| R15/R16 RIS/EMR | Report delivery channels | R12 Staff Radiologist | HL7/FHIR report delivery |
