# Traceability Matrix — Radiology Technician (R07)

## FR/NFR → AC Traceability

| FR/NFR ID | Covered by AC | AC IDs | Status |
|-----------|---------------|--------|--------|
| FR-R07-01 | Yes | AC-R07-01-01, AC-R07-01-02, AC-R07-01-03, AC-R07-01-04, AC-R07-01-05 | Covered |
| FR-R07-02 | Yes | AC-R07-02-01, AC-R07-02-02, AC-R07-02-03, AC-R07-02-04, AC-R07-02-05 | Covered |
| FR-R07-03 | Yes | AC-R07-03-01, AC-R07-03-02, AC-R07-03-03, AC-R07-03-04 | Covered |
| FR-R07-04 | Yes | AC-R07-04-01, AC-R07-04-02, AC-R07-04-03, AC-R07-04-04, AC-R07-04-05 | Covered |
| FR-R07-05 | Yes | AC-R07-05-01, AC-R07-05-02, AC-R07-05-03, AC-R07-05-04, AC-R07-05-05 | Covered |
| FR-R07-06 | Yes | AC-R07-06-01, AC-R07-06-02, AC-R07-06-03, AC-R07-06-04, AC-R07-06-05 | Covered |
| FR-R07-07 | Yes | AC-R07-07-01, AC-R07-07-02, AC-R07-07-03, AC-R07-07-04 | Covered |
| FR-R07-08 | Yes | AC-R07-08-01, AC-R07-08-02, AC-R07-08-03, AC-R07-08-04 | Covered |
| FR-R07-09 | Yes | AC-R07-09-01, AC-R07-09-02, AC-R07-09-03, AC-R07-09-04, AC-R07-09-05 | Covered |
| FR-R07-10 | Yes | AC-R07-10-01, AC-R07-10-02, AC-R07-10-03, AC-R07-10-04, AC-R07-10-05 | Covered |
| NFR-R07-01 | Yes | AC-R07-01-01, AC-R07-01-05 | Covered |
| NFR-R07-02 | Yes | AC-R07-04-01 | Covered |
| NFR-R07-03 | Yes | AC-R07-07-02 | Covered |
| NFR-R07-04 | Yes | AC-R07-05-01 | Covered |
| NFR-R07-05 | Yes | AC-R07-04-02 | Covered |
| NFR-R07-06 | Yes | AC-R07-01-02, AC-R07-01-05 | Covered |
| NFR-R07-07 | Yes | AC-R07-02-01, AC-R07-03-01, AC-R07-06-01, AC-R07-08-01 | Covered |
| NFR-R07-08 | Yes | AC-R07-04-02, AC-R07-07-04 | Covered |
| NFR-R07-09 | Yes | AC-R07-01-05 | Covered |
| NFR-R07-10 | Yes | AC-R07-03-01 | Covered |

## GATED Requirements (codebase reality, verified 2026-08-03)

Study browser/viewer/worklist are implemented. Acquisition-workflow FRs (incl.
fluoroscopy and mammography) are aspirational v3.0 spec — ACs exist in artifact 06
but are **GATED** on new backend work (`/exams/*` endpoints + `EXAM_*` permissions
flagged to backend):

| FR/NFR ID | Status | Blocking Dependency |
|-----------|--------|---------------------|
| FR-R07-01..10 (acquisition incl. fluoro/mammo) | GATED | No exam/acquisition endpoints or routes |
| NFR-R07-* tied to GATED FRs | GATED | Blocked on the FRs above |

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
| R07 Technician → R12 Radiologist | Exam completion handoff | R12 | `POST /api/v2/exams/{id}/complete` pushes to R12 worklist via WebSocket |
| R07 Technician → R05 QA Team | Incident/retake logging | R05 | R07 logs incidents → R05 QA review queue |
| R07 Technician → R04 Coordinator | Exam status updates | R04 | R07 marks exam complete → R04 worklist updates |
| R07 Technician → R16 EMR | Patient allergy/demographics | R16 | R07 reads allergy data via HL7 ADT feed |
| R07 Technician → R17 PACS | Image archive push | R17 | R07 triggers PACS push on exam completion |
| R07 Technician → R15 RIS | Exam order feed | R15 | R15 sends scheduled orders → R07 worklist auto-populates |

## Integration Contracts (R15–R17)

### R15 → R07: HL7 ORM (Scheduled Exam Feed)
- **Direction**: R15 (External RIS) → R07 (Radiology Technician)
- **Protocol**: HL7 ORM (order message) for new exam orders
- **Mapping**: RIS `Placer Order Number` → `exam_id`; RIS `Filler Order Number` → `study_uid`; RIS `Priority` → `priority` (STAT/urgent/routine); RIS `Modality` → `modality` (DR/CR/Fluoroscopy/Mammography)
- **Failure**: If RIS feed is down, worklist shows stale data; technician can manually refresh
- **Retry**: 3 attempts with exponential backoff (1s, 5s, 15s); dead-letter queue for failed messages

### R16 → R07: HL7 ADT (Patient Demographics)
- **Direction**: R16 (External EMR) → R07 (Radiology Technician)
- **Protocol**: HL7 ADT^A01 (admission), ADT^A04 (registration)
- **Mapping**: EMR `Patient ID` → `patient_id`; EMR `Patient Name` → `patient_name` (initials shown); EMR `Allergy` → `contrast_allergy` flag; EMR `Pregnancy` → `pregnancy_status` flag
- **Failure**: If EMR feed is down, technician manually enters allergy/pregnancy info; scheduling works without EMR feed
- **Async**: No blocking — exam preparation works without EMR feed

### R17 ↔ R07: DICOM C-STORE (Image Archive)
- **Direction**: R07 → R17 (PACS)
- **Protocol**: DICOM C-STORE for image push on exam completion
- **Timeout**: 30s per image push; retry 2x on timeout
- **Failure**: If PACS is unreachable, images are queued for retry; exam is still marked complete; radiologist notified that images are pending