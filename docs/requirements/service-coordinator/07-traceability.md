# Traceability Matrix — Radiology & Service Coordinator (R04)

## FR/NFR → AC Traceability

| FR/NFR ID | Covered by AC | AC IDs | Status |
|-----------|---------------|--------|--------|
| FR-R04-01 | Yes | AC-R04-01-01, AC-R04-01-02, AC-R04-01-03, AC-R04-01-04, AC-R04-01-05 | Covered |
| FR-R04-02 | Yes | AC-R04-02-01, AC-R04-02-02, AC-R04-02-03, AC-R04-02-04 | Covered |
| FR-R04-03 | Yes | AC-R04-03-01, AC-R04-03-02, AC-R04-03-03 | Covered |
| FR-R04-04 | Yes | AC-R04-04-01, AC-R04-04-02, AC-R04-04-03, AC-R04-04-04, AC-R04-04-05 | Covered |
| FR-R04-05 | Yes | AC-R04-05-01, AC-R04-05-02, AC-R04-05-03, AC-R04-05-04 | Covered |
| FR-R04-06 | Yes | AC-R04-06-01, AC-R04-06-02, AC-R04-06-03, AC-R04-06-04, AC-R04-06-05 | Covered |
| FR-R04-07 | Yes | AC-R04-07-01, AC-R04-07-02, AC-R04-07-03, AC-R04-07-04 | Covered |
| FR-R04-08 | Yes | AC-R04-08-01, AC-R04-08-02, AC-R04-08-03, AC-R04-08-04 | Covered |
| FR-R04-09 | Yes | AC-R04-09-01, AC-R04-09-02, AC-R04-09-03, AC-R04-09-04 | Covered |
| FR-R04-10 | Yes | AC-R04-10-01, AC-R04-10-02, AC-R04-10-03, AC-R04-10-04 | Covered |
| NFR-R04-01 | Yes | AC-R04-01-04, AC-R04-04-04, AC-R04-06-05 | Covered |
| NFR-R04-02 | Yes | AC-R04-02-02 | Covered |
| NFR-R04-03 | Yes | AC-R04-02-02 | Covered |
| NFR-R04-04 | Yes | AC-R04-08-04 | Covered |
| NFR-R04-05 | Yes | AC-R04-01-04, AC-R04-06-05 | Covered |
| NFR-R04-06 | Yes | AC-R04-01-05, AC-R04-05-04, AC-R04-06-05 | Covered |
| NFR-R04-07 | Yes | AC-R04-01-05 | Covered |
| NFR-R04-08 | Yes | AC-R04-06-05 | Covered |
| NFR-R04-09 | Yes | AC-R04-09-01, AC-R04-09-02 | Covered |
| NFR-R04-10 | Yes | AC-R04-05-04 | Covered |

## GATED Requirements (codebase reality, verified 2026-08-03)

Worklist CRUD/calendar/batch is implemented (`/worklist*`). Schedule board, exam
assignment, staffing rosters, utilization, and shift-handoff report FRs are
aspirational v3.0 spec — ACs exist in artifact 06 but are **GATED** on new backend
work (scheduling endpoints flagged to backend):

| FR/NFR ID | Status | Blocking Dependency |
|-----------|--------|---------------------|
| FR-R04-01..05, FR-R04-07..10 (scheduling/staffing) | GATED | No scheduling-board endpoints or routes |
| FR-R04-06 (worklist) | Implemented | `/worklist*` exists |
| NFR-R04-* tied to GATED FRs | GATED | Blocked on the FRs above |

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
| R04 Coordinator → R06 Technologist | Exam assignment | R06 | `POST /api/v2/schedule/assign` pushes to R06 worklist via WebSocket |
| R04 Coordinator → R07 Technologist | Exam assignment | R07 | Same as R06; R07 is the DR/CR technologist |
| R04 Coordinator → R05 QA Team | Incident/retake data | R05 | R04 logs incidents → R05 QA review queue |
| R04 Coordinator → R03 Service Director | Utilization data | R03 | R04 dashboard provides utilization metrics → R03 reads for capacity planning |
| R04 Coordinator → R01 Super Admin | System health | R01 | R04 reports modality downtime → R01 manages DICOM AE nodes |

## Integration Contracts (R15–R17)

| Integration | Direction | Protocol | Failure Semantics |
|-------------|-----------|----------|-------------------|
| External RIS (R15) | R15 → R04 | HL7 ORM/ORU (scheduled exam feed) | Retry 3x → dead-letter → manual reconciliation |
| External EMR (R16) | R16 → R04 | HL7 ADT (patient demographics) | Async backfill, no blocking |
| External PACS (R17) | R17 ↔ R04 | DICOM C-FIND (study lookup for scheduling) | Query timeout 30s, retrieve retry 2x |

## Integration Contract Details

### R15 → R04: HL7 ORM/ORU (Scheduled Exam Feed)
- **Direction**: R15 (External RIS) → R04 (Service Coordinator)
- **Protocol**: HL7 ORM (order message) for new exam orders; HL7 ORU (result message) for exam completion
- **Mapping**: RIS `Placer Order Number` → `exam_id`; RIS `Filler Order Number` → `study_uid`; RIS `Priority` → `priority` (STAT/urgent/routine)
- **Failure**: If RIS feed is down, coordinator manually schedules exams; RIS feed resumes with backfill of missed orders
- **Retry**: 3 attempts with exponential backoff (1s, 5s, 15s); dead-letter queue for failed messages

### R16 → R04: HL7 ADT (Patient Demographics)
- **Direction**: R16 (External EMR) → R04 (Service Coordinator)
- **Protocol**: HL7 ADT^A01 (admission), ADT^A04 (registration)
- **Mapping**: EMR `Patient ID` → `patient_id`; EMR `Patient Name` → `patient_name` (initials shown on board)
- **Failure**: If EMR feed is down, coordinator can still schedule exams with manual patient entry; demographics populate when feed resumes
- **Async**: No blocking — scheduling works without EMR feed

### R17 ↔ R04: DICOM C-FIND (Study Lookup)
- **Direction**: Bidirectional — R04 queries R17 for study details when scheduling
- **Protocol**: DICOM C-FIND with query keys (Study Date, Modality, Patient ID)
- **Timeout**: 30s query timeout; retry 2x on timeout
- **Failure**: If R17 is unreachable, coordinator can schedule exams without study details; study details populate when R17 recovers