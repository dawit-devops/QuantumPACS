# User Stories — Front Desk / Receptionist (R08)

## US-R08-01: Search and dedup patients before registering
**Story**: As a front desk receptionist, I want to search for an existing patient before registering, so that I never create a duplicate record.
**Priority**: Must

### Acceptance Criteria
- **Given** I type a partial name or full MRN, **when** I submit the search, **then** matching patients appear with name, MRN, and DOB within 500ms (p95).
- **Given** the search returns ≥1 match, **when** the registration form opens, **then** a dedup warning banner is visible until I confirm a new-patient registration.
- **Given** the search returns no matches, **when** the form submits, **then** a second review step confirms no existing record.
- **Accessibility**: search input has a visible label and keyboard focus ring.
- **Performance**: LCP ≤ 2.5s; search INP ≤ 200ms.

## US-R08-02: Register a new patient with validated demographics
**Story**: As a front desk receptionist, I want to capture full demographics with inline validation, so that downstream departments have accurate data.
**Priority**: Must

### Acceptance Criteria
- **Given** required fields are empty, **when** I submit, **then** inline field errors appear and nothing is sent.
- **Given** all required fields are valid, **when** I submit, **then** the record saves with an optimistic update and a success state within 500ms.
- **Given** the HL7 demographics sync fails, **when** the record is saved, **then** a sync-pending indicator appears on the patient record with automatic retry.
- **Accessibility**: error messages are announced to screen readers.

## US-R08-03: Capture a referring order
**Story**: As a front desk receptionist, I want to capture the ordered procedure, indication, and urgency, so that the exam is scheduled correctly.
**Priority**: Must

### Acceptance Criteria
- **Given** a patient visit is open, **when** I add an order, **then** procedure, indication, referring physician, and urgency are captured and linked to the visit.
- **Given** an order is marked STAT, **when** scheduling opens, **then** STAT styling is applied to the order.
- **Performance**: order save INP ≤ 200ms.

## US-R08-04: Schedule with conflict detection
**Story**: As a front desk receptionist, I want to see scheduling conflicts before confirming, so that double bookings are prevented.
**Priority**: Must

### Acceptance Criteria
- **Given** I pick a modality and date, **when** availability loads, **then** open slots render with modality/room/technologist and existing bookings are shown.
- **Given** a slot becomes occupied while I confirm, **then** the system returns a conflict message with refreshed availability.
- **Accessibility**: slot grid is keyboard-navigable with focus indicators.

## US-R08-05: Check in a patient
**Story**: As a front desk receptionist, I want to check a patient in and verify demographics, so that the clinical team knows the patient has arrived.
**Priority**: Must

### Acceptance Criteria
- **Given** a patient has a scheduled visit, **when** I check them in, **then** the visit status changes to checked-in and is visible to R11/R06/R07.
- **Given** demographics changed at check-in, **when** I save corrections, **then** a demographics-update event is recorded.
- **Accessibility**: all states (loading/empty/error/success) announced.

## US-R08-06: Attach consent and flag missing forms
**Story**: As a front desk receptionist, I want to attach signed consents and see which are missing, so that the exam never proceeds without consent.
**Priority**: Should

### Acceptance Criteria
- **Given** a visit with required consent types, **when** I open the forms list, **then** each required type shows attached or missing.
- **Given** I upload a scan, **then** it attaches within 2s and the form's status updates.
- **Performance**: upload feedback ≤ 500ms for small files.

## US-R08-07: View a privacy-limited waiting queue
**Story**: As a front desk receptionist, I want a queue board that hides full PHI, so that patient privacy is preserved in the waiting area.
**Priority**: Should

### Acceptance Criteria
- **Given** the queue board is displayed in a shared area, **when** it renders, **then** only initials + MRN last 4 are shown.
- **Given** I open a patient's detail, **then** full PHI requires an authenticated action (not the shared view).

## Dependencies
- US-R08-01/02 → patient API + HL7 ADT outbound (R16)
- US-R08-04 → schedule board data model shared with R04
- US-R08-06 → upload + consent storage
