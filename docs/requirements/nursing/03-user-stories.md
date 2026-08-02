# User Stories — Radiology Service Nursing Team (R11)

## US-R11-01: See patients needing nursing care
**Story**: As a radiology nurse, I want a live nursing worklist, so that I know which patients need prep, contrast, monitoring, or recovery.
**Priority**: Must

### Acceptance Criteria
- **Given** patients in the department, **when** the worklist opens, **then** it renders with status and destination within 2.5s LCP and refreshes within 5s.
- **Given** a patient status changes, **when** the list refreshes, **then** the row updates without a full reload.
- **Accessibility**: keyboard-navigable list with screen-reader status announcements.

## US-R11-02: Complete the prep checklist
**Story**: As a radiology nurse, I want a per-item prep checklist, so that nothing is missed before the exam.
**Priority**: Must

### Acceptance Criteria
- **Given** a checklist, **when** I confirm each item, **then** progress renders and all items must be complete before prep is marked done.
- **Given** a required item is unchecked, **when** I try to complete prep, **then** inline validation blocks submission.
- **Performance**: save INP ≤ 200ms.

## US-R11-03: Capture and review vitals
**Story**: As a radiology nurse, I want to capture vitals repeatedly, so that I can monitor the patient during the procedure.
**Priority**: Must

### Acceptance Criteria
- **Given** a monitoring session, **when** I enter vitals, **then** each reading records with timestamp and operator within 500ms.
- **Given** the device is offline, **when** I enter vitals, **then** they queue and sync within 2min of reconnect.

## US-R11-04: Verify safety before contrast
**Story**: As a radiology nurse, I want a hard safety gate before contrast, so that allergic/pregnant/renal-risk patients are protected.
**Priority**: Must

### Acceptance Criteria
- **Given** allergy/pregnancy/renal flags are present, **when** the contrast action is attempted, **then** it is disabled until screening is confirmed.
- **Given** a positive allergy flag, **then** a warning banner renders and contrast requires a physician override with justification.

## US-R11-05: Log an adverse reaction with escalation
**Story**: As a radiology nurse, I want to log adverse reactions and escalate, so that the on-call radiologist responds within the SLA.
**Priority**: Must

### Acceptance Criteria
- **Given** a reaction, **when** I log type/severity/onset/actions, **then** the record persists and escalation to the on-call radiologist fires within 15min SLA.
- **Given** the escalation channel is down, **then** a fallback channel is attempted and the attempt is logged.

## US-R11-06: Record contrast administration
**Story**: As a radiology nurse, I want to record contrast agent/dose/route/time, so that the exam dose record is complete.
**Priority**: Must

### Acceptance Criteria
- **Given** safety confirmation, **when** I record contrast, **then** agent, dose, route, rate, and time persist and link to the exam.
- **Given** no safety confirmation, **when** I try to record contrast, **then** the action is blocked.

## US-R11-07: Manage recovery and discharge
**Story**: As a radiology nurse, I want to track recovery and discharge criteria, so that patients leave safely.
**Priority**: Must

### Acceptance Criteria
- **Given** a patient in recovery, **when** I record observations, **then** they persist with timestamps.
- **Given** discharge criteria are met, **when** I discharge, **then** the visit status updates and discharge instructions are printable.

## Dependencies
- US-R11-01 → worklist status events (R08/R06/R07)
- US-R11-04/05 → HL7 allergy flags (R16) + escalation wiring
- US-R11-06 → exam dose record (R06/R07)
