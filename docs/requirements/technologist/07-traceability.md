# Traceability Matrix — Radiology Technologist (R06)

## FR/NFR → AC Traceability

| FR/NFR ID | Covered by AC | AC IDs | Status |
|-----------|---------------|--------|--------|
| FR-R06-01 | Yes | AC-R06-01-01, AC-R06-01-02, AC-R06-01-03, AC-R06-01-04, AC-R06-01-05 | Covered |
| FR-R06-02 | Yes | AC-R06-02-01, AC-R06-02-02, AC-R06-02-03, AC-R06-02-04, AC-R06-02-05 | Covered |
| FR-R06-03 | Yes | AC-R06-03-01, AC-R06-03-02, AC-R06-03-03, AC-R06-03-04 | Covered |
| FR-R06-04 | Yes | AC-R06-04-01, AC-R06-04-02, AC-R06-04-03, AC-R06-04-04, AC-R06-04-05 | Covered |
| FR-R06-05 | Yes | AC-R06-05-01, AC-R06-05-02, AC-R06-05-03, AC-R06-05-04, AC-R06-05-05 | Covered |
| FR-R06-06 | Yes | AC-R06-06-01, AC-R06-06-02, AC-R06-06-03, AC-R06-06-04, AC-R06-06-05 | Covered |
| FR-R06-07 | Yes | AC-R06-07-01, AC-R06-07-02, AC-R06-07-03, AC-R06-07-04 | Covered |
| FR-R06-08 | Yes | AC-R06-08-01, AC-R06-08-02, AC-R06-08-03, AC-R06-08-04 | Covered |
| FR-R06-09 | Yes | AC-R06-09-01, AC-R06-09-02, AC-R06-09-03, AC-R06-09-04 | Covered |
| FR-R06-10 | Yes | AC-R06-10-01, AC-R06-10-02, AC-R06-10-03, AC-R06-10-04, AC-R06-10-05, AC-R06-10-06 | Covered |
| NFR-R06-01 | Yes | AC-R06-01-01, AC-R06-01-05 | Covered |
| NFR-R06-02 | Yes | AC-R06-04-01 | Covered |
| NFR-R06-03 | Yes | AC-R06-07-02 | Covered |
| NFR-R06-04 | Yes | AC-R06-05-01 | Covered |
| NFR-R06-05 | Yes | AC-R06-04-02 | Covered |
| NFR-R06-06 | Yes | AC-R06-01-02, AC-R06-01-05 | Covered |
| NFR-R06-07 | Yes | AC-R06-02-01, AC-R06-03-01, AC-R06-06-01, AC-R06-08-01 | Covered |
| NFR-R06-08 | Yes | AC-R06-04-02, AC-R06-07-04 | Covered |
| NFR-R06-09 | Yes | AC-R06-01-05 | Covered |
| NFR-R06-10 | Yes | AC-R06-03-01 | Covered |

## GATED Requirements (codebase reality, verified 2026-08-03)

Study browser/viewer/worklist are implemented. Acquisition-workflow FRs are
aspirational v3.0 spec — ACs exist in artifact 06 but are **GATED** on new backend
work (`/exams/*` endpoints + `EXAM_*` permissions flagged to backend):

| FR/NFR ID | Status | Blocking Dependency |
|-----------|--------|---------------------|
| FR-R06-01..10 (acquisition workflow) | GATED | No exam/acquisition endpoints or routes |
| NFR-R06-* tied to GATED FRs | GATED | Blocked on the FRs above |

## Cross-Artifact Dependencies

| Source Artifact | Target Artifact | Dependency |
|-----------------|-----------------|------------|
| 01 User Requirements | 03 User Stories | Each US maps to ≥1 FR |
| 01 User Requirements | 06 Acceptance Criteria | Each FR/NFR has ≥1 AC |
| 02 Workflow Maps | 03 User Stories | Each workflow step with user decision → US |
| 03 User Stories | 04 UI/UX Requirements | Each US component → state spec |
| 04 UI/UX Requirements | 06 Acceptance Criteria | Each state → validator gate |
| 05 Metrics & SLAs | 06 Acceptance Criteria | Each metric target → measurable AC |
| 01 User Requirements | 07 Traceability | This matrix |
| 01 User Requirements | 08 Implementation Roadmap | FR ordering by dependency |

## Cross-Role Dependencies

| Role | Dependency Type | Target Role | Contract |
|------|----------------|-------------|----------|
| R06 Technologist → R12 Radiologist | Exam completion handoff | R12 | `POST /api/v2/exams/{id}/complete` pushes to R12 worklist via WebSocket |
| R06 Technologist → R05 QA Team | Incident/retake logging | R05 | R06 logs incidents → R05 QA review queue |
| R06 Technologist → R04 Coordinator | Exam status updates | R04 | R06 marks exam complete → R04 worklist updates |
| R06 Technologist → R16 EMR | Patient allergy/demographics | R16 | R06 reads allergy data via HL7 ADT feed |
| R06 Technologist → R17 PACS | Image archive push | R17 | R06 triggers PACS push on exam completion |
| R06 Technologist → R15 RIS | Exam order feed | R15 | R15 sends scheduled orders → R06 worklist auto-populates |

## Integration Contracts (R15–R17)

### R15 → R06: HL7 ORM (Scheduled Exam Feed)
- **Direction**: R15 (External RIS) → R06 (Radiology Technologist)
- **Protocol**: HL7 ORM (order message) for new exam orders
- **Mapping**: RIS `Placer Order Number` → `exam_id`; RIS `Filler Order Number` → `study_uid`; RIS `Priority` → `priority` (STAT/urgent/routine); RIS `Modality` → `modality`
- **Failure**: If RIS feed is down, worklist shows stale data; technologist can manually refresh
- **Retry**: 3 attempts with exponential backoff (1s, 5s, 15s); dead-letter queue for failed messages

### R16 → R06: HL7 ADT (Patient Demographics)
- **Direction**: R16 (External EMR) → R06 (Radiology Technologist)
- **Protocol**: HL7 ADT^A01 (admission), ADT^A04 (registration)
- **Mapping**: EMR `Patient ID` → `patient_id`; EMR `Patient Name` → `patient_name` (initials shown); EMR `Allergy` → `contrast_allergy` flag; EMR `Pregnancy` → `pregnancy_status` flag
- **Failure**: If EMR feed is down, technologist manually enters allergy/pregnancy info; scheduling works without EMR feed
- **Async**: No blocking — exam preparation works without EMR feed

### R17 ↔ R06: DICOM C-STORE (Image Archive)
- **Direction**: R06 → R17 (PACS)
- **Protocol**: DICOM C-STORE for image push on exam completion
- **Timeout**: 30s per image push; retry 2x on timeout
- **Failure**: If PACS is unreachable, images are queued for retry; exam is still marked complete; radiologist notified that images are pending