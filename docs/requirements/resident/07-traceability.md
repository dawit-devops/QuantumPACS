# Traceability Matrix — Radiology Trainee/Resident (R13)

## FR/NFR → AC Traceability

| FR/NFR ID | Covered by AC | AC IDs | Status |
|-----------|---------------|--------|--------|
| FR-R13-01 | Yes | AC-R13-01 | Covered |
| FR-R13-02 | Yes | AC-R13-02 | Covered |
| FR-R13-03 | Yes | AC-R13-03 | Covered |
| FR-R13-04 | Yes | AC-R13-04 | Covered |
| FR-R13-05 | Yes | AC-R13-05 | Covered |
| FR-R13-06 | Yes | AC-R13-06 | Covered |
| FR-R13-07 | Yes | AC-R13-07 | Covered |
| FR-R13-08 | Yes | AC-R13-08 | Covered |
| FR-R13-09 | Yes | AC-R13-09 | Covered |
| FR-R13-10 | Yes | AC-R13-10 | Covered |
| NFR-R13-01 | Yes | AC-R13-11 | Covered |
| NFR-R13-02 | Yes | AC-R13-12 | Covered |
| NFR-R13-03 | Yes | AC-R13-13 | Covered |
| NFR-R13-04 | Yes | AC-R13-14 | Covered |
| NFR-R13-05 | Yes | AC-R13-15 | Covered |
| NFR-R13-06 | Yes | AC-R13-16 | Covered |
| NFR-R13-07 | Yes | AC-R13-17 | Covered |
| NFR-R13-08 | Yes | AC-R13-18 | Covered |
| NFR-R13-09 | Yes | AC-R13-19 | Covered |
| NFR-R13-10 | Yes | AC-R13-20 | Covered |

## GATED Requirements (codebase reality, verified 2026-08-03)

No resident-specific functionality exists in the codebase (no role distinction from
R12 today). All supervised-reading FRs are aspirational v3.0 spec — ACs exist in
artifact 06 but are **GATED** on new backend work (supervised worklist, draft report,
attending sign-off, teaching files/de-identification, feedback dashboard — 6+ new
endpoints flagged to backend, depends on R12 reporting):

| FR/NFR ID | Status | Blocking Dependency |
|-----------|--------|---------------------|
| FR-R13-06 (partial) | Partial — study/patient list infrastructure exists (Files browser) | No resident exam-log view |
| FR-R13-01..05, FR-R13-07..10 | GATED | No supervised-reading endpoints or routes |
| NFR-R13-01..10 | GATED | Blocked on the FRs above |

## Cross-Artifact Dependencies

| Source Artifact | Target Artifact | Dependency |
|-----------------|-----------------|------------|
| 01 User Requirements | 03 User Stories | US-R13-01..10 map to FR-R13-01..10 |
| 01 User Requirements | 06 Acceptance Criteria | Every FR/NFR has ≥1 AC (AC-R13-01..20) |
| 02 Workflow Maps | 03 User Stories | Each workflow step with a resident decision → US |
| 03 User Stories | 04 UI/UX Requirements | Split-screen viewer, draft editor, feedback dashboard state specs |
| 04 UI/UX Requirements | 06 Acceptance Criteria | Each state → validator gate |
| 05 Metrics & SLAs | 06 Acceptance Criteria | Each metric target → measurable AC (NFR coverage) |

## Cross-Role Dependencies

| Role | Dependency Type | Target Role | Contract |
|------|----------------|-------------|----------|
| R13 Resident | Supervised by | R12 Staff Radiologist | Attending guidance + review/sign-off (drafts) |
| R13 Resident | On-call consult | R18 Teleradiologist | Priority consult request + response ≤ 15min |
| R13 Resident | Rotation assignment | R04 Service Coordinator | Resident ↔ attending assignment per rotation |
| R13 Resident | Studies to interpret | R06/R07 Technologist/Technician | Completed exams enter resident worklist |
| R13 Resident | Performance visibility | R03 Service Director | Program-director cohort view (with R12) |
| R13 Resident | Feedback data | R05 QI/QA Team | Peer-review/discrepancy data feeds feedback |
| R13 Resident | Draft visibility gate | R14 Referring Clinician | Drafts invisible until attending co-sign |

## Integration Contracts

| Integration | Direction | Protocol | Failure Semantics |
|-------------|-----------|----------|-------------------|
| Attending guidance + review | R13 ↔ R12 | WebSocket (send_state / notifications) | Draft notify ≤ 5s; guidance real-time; draft lock on submit |
| On-call consult | R13 → R12/R18 | Notification + fallback | ≤ 15min response SLA; fallback channel; logged |
| Teaching file de-identification | R13 → Backend | Async de-ident job | ≤ 2s/case; PHI scan failure blocks publish |
| Resident worklist | R13 → Backend | WebSocket + DB trigger | Sync staleness ≤ 30s; assignments from R04 |

## Excluded Scope / Out of Scope

- Independent/final reading (R12/R18 only).
- Draft access by R14/R19 before co-sign.
- System administration (R01/R02), acquisition (R06/R07), billing (R09).
