# Traceability Matrix — Teleradiologist (R18)

## FR/NFR → AC Traceability

| FR/NFR ID | Covered by AC | AC IDs | Status |
|-----------|---------------|--------|--------|
| FR-R18-01 | Yes | AC-R18-01-01, AC-R18-01-02, AC-R18-01-03 | Covered |
| FR-R18-02 | Yes | AC-R18-01-02, AC-R18-01-05 | Covered |
| FR-R18-03 | Yes | AC-R18-04-01, AC-R18-04-03, AC-R18-04-04, AC-R18-04-05 | Covered |
| FR-R18-04 | Yes | AC-R18-05-06 | Covered |
| FR-R18-05 | Yes | AC-R18-05-01, AC-R18-05-05 | Covered |
| FR-R18-06 | Yes | AC-R18-05-02, AC-R18-05-03, AC-R18-05-04 | Covered |
| FR-R18-07 | Yes | AC-R18-02-01, AC-R18-02-02, AC-R18-02-03, AC-R18-02-04, AC-R18-02-05 | Covered |
| FR-R18-08 | No | — | Gap — no AC yet |
| FR-R18-09 | Yes | AC-R18-03-01, AC-R18-03-02, AC-R18-03-03, AC-R18-03-05 | Covered |
| FR-R18-10 | Yes | AC-R18-03-02, AC-R18-03-04 | Covered |
| FR-R18-11 | Yes | AC-R18-08-02 | Covered |
| FR-R18-12 | Yes | AC-R18-07-01, AC-R18-07-02 | Covered |
| FR-R18-13 | Yes | AC-R18-07-03, AC-R18-07-04 | Covered |
| FR-R18-14 | Yes | AC-R18-07-05 | Covered |
| FR-R18-15 | Yes | AC-R18-04-01, AC-R18-04-02 | Covered |
| FR-R18-16 | Yes | AC-R18-08-01, AC-R18-08-02 | Covered |
| FR-R18-17 | Yes | AC-R18-09-01, AC-R18-09-02 | Covered |
| FR-R18-18 | Yes | AC-R18-10-01, AC-R18-10-02 | Covered |
| FR-R18-19 | Yes | AC-R18-11-01, AC-R18-11-02 | Covered |
| FR-R18-20 | Yes | AC-R18-01-04 | Covered |
| FR-R18-21 | Yes | AC-R18-11-03, AC-R18-11-04 | Covered |
| FR-R18-22 | Yes | AC-R18-10-03 | Covered |
| FR-R18-23 | Yes | AC-R18-10-04 | Covered |
| FR-R18-24 | Yes | AC-R18-10-05 | Covered |
| NFR-R18-01 | Yes | AC-R18-05-01 | Covered |
| NFR-R18-02 | Yes | AC-R18-01-02, AC-R18-01-05 | Covered |
| NFR-R18-03 | Yes | AC-R18-05-01 | Covered |
| NFR-R18-04 | Yes | AC-R18-05-06 | Covered |
| NFR-R18-05 | Yes | AC-R18-02-02 | Covered |
| NFR-R18-06 | Yes | AC-R18-07-03 | Covered |
| NFR-R18-07 | Yes | AC-R18-03-02, AC-R18-03-03 | Covered |
| NFR-R18-08 | Yes | AC-R18-04-02 | Covered |
| NFR-R18-09 | Yes | AC-R18-06-01, AC-R18-06-02, AC-R18-06-03 | Covered |
| NFR-R18-10 | No | — | Gap — no AC yet |
| NFR-R18-11 | Yes | AC-R18-04-03 | Covered |
| NFR-R18-12 | No | — | Gap — no AC yet |
| NFR-R18-13 | Yes | AC-R18-05-03 | Covered |
| NFR-R18-14 | Yes | AC-R18-09-02 | Covered |
| NFR-R18-15 | Yes | AC-R18-05-06 | Covered |
| NFR-R18-16 | No | — | Gap — no AC yet |
| NFR-R18-17 | No | — | Gap — no AC yet |
| NFR-R18-18 | No | — | Gap — no AC yet |

## GATED Requirements (codebase reality, verified 2026-08-03)

Merge 4d136e0 implemented the R12 reading/reporting stack shared by R18 plus
SSO/OAuth/OIDC and tenant switching. See artifact 08 for per-FR status:

| FR/NFR ID | Status | Blocking Dependency |
|-----------|--------|---------------------|
| FR-R18-01 (remote worklist) | Partial | Reading worklist shipped (`/reports/reading-list`, priority-sorted); site filter + assignment filter GATED |
| FR-R18-03 (SSO + multi-site) | Implemented | OAuth/OIDC flow + tenant switching shipped |
| FR-R18-04 (viewer parity) | Implemented | Same viewer as R12; MPR/MIP/3D absent for both roles |
| FR-R18-07/08 (preliminary → final) | Implemented | `GET/PUT /reports/{exam_id}` (draft → preliminary → final) + `POST /reports/{exam_id}/sign` |
| FR-R18-22/24 (layout + hanging presets) | Partial | `/reading-presets*` (window_level + layout 1x1/1x2/2x2 per modality); 3-monitor profiles + scenario templates GATED |
| FR-R18-02 (freshness indicator) | GATED | No freshness banner/polling UI |
| FR-R18-06 (prefetch next 3) | GATED | No prefetch endpoint/algorithm |
| FR-R18-09/10 (critical findings) | GATED | No escalation endpoint (report sign notifies QA role only) |
| FR-R18-11/16 (consult queue) | GATED | No consultation endpoints (peer review is QA-style, not consult) |
| FR-R18-12 (voice dictation) | GATED | No dictation integration |
| FR-R18-13/14 (offline packages) | GATED | No offline-package endpoints |
| FR-R18-15 (multi-site dashboard) | GATED | No per-site worklist-count dashboard |
| FR-R18-17 (mobile viewer) | GATED | PWA exists; no telerad-specific mobile UI |
| FR-R18-18 (priors comparison) | GATED | No priors endpoint (same gap as R12 FR-R12-06) |
| FR-R18-19 (turnaround display) | GATED | No per-study turnaround metric in worklist UI |
| FR-R18-20 (STAT >20min alert) | GATED | No overdue-STUDY alert |
| FR-R18-21 (secure messaging) | GATED | Notifications exist; no clinician messaging |
| FR-R18-23 (allergy warnings) | GATED | No allergy/contrast data pipeline |
| NFR-R18-03/04/05/11 | Covered | Viewers/editor/OAuth shipped — budgets verifiable (WAN tests pending) |
| NFR-R18-01/02/06/07/08/09/10/12/13/14/15/16/17/18 | GATED | Blocked on the FRs above or not yet scoped |

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
