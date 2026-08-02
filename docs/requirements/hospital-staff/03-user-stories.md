# User Stories — Other Hospital Staff (R19)

## US-R19-01: Look up a permitted patient
**Story**: As a ward nurse, I want to look up my patient by MRN, so that I can check their imaging status.
**Priority**: Must

### Acceptance Criteria
- **Given** I search within my permitted scope, **when** I query by MRN/name, **then** matching patients return within 500ms.
- **Given** a patient is outside my scope, **when** I search, **then** no result appears and the access attempt is logged.
- **Given** no results, **when** the search completes, **then** a meaningful empty state shows.
- **Accessibility**: keyboard-navigable search with focus ring.

## US-R19-02: View results read-only
**Story**: As a ward nurse, I want to view my patient's finalized reports, so that I can support their care.
**Priority**: Must

### Acceptance Criteria
- **Given** a finalized report exists, **when** I open it, **then** it renders read-only with no edit/annotation controls.
- **Given** only a draft exists, **when** I open the patient, **then** the draft is not visible (R13/R12 rule).
- **Performance**: report view LCP ≤ 2.5s on mobile.

## US-R19-03: Track order status
**Story**: As a ward nurse, I want to see order status, so that I know when imaging is scheduled or done.
**Priority**: Must

### Acceptance Criteria
- **Given** orders exist for the patient, **when** I view them, **then** each shows scheduled/in-progress/complete status.
- **Given** no orders, **when** I open the tab, **then** an empty state shows.

## US-R19-04: Receive results notifications
**Story**: As a ward nurse, I want a notification when a report is finalized, so that I can act promptly.
**Priority**: Should

### Acceptance Criteria
- **Given** a permitted patient's report finalizes, **when** the event fires, **then** an in-app notification arrives within 60s (no PHI in the notification body).
- **Given** notifications are disabled, **when** the report finalizes, **then** no notification is sent.

## US-R19-05: Open images read-only
**Story**: As a ward nurse, I want to open images read-only, so that I can see what was done.
**Priority**: Should

### Acceptance Criteria
- **Given** I open a study, **when** the viewer loads, **then** it renders in read-only mode with tools disabled.
- **Given** I attempt a write action, **when** triggered, **then** it is blocked both in UI and API.

## US-R19-06: Request a follow-up
**Story**: As a ward nurse, I want to request a follow-up read, so that questions about results can be escalated.
**Priority**: Could

### Acceptance Criteria
- **Given** a permitted patient, **when** I submit a follow-up request, **then** it routes to the radiology team and I see a confirmation.
- **Performance**: submit feedback ≤ 500ms.

## Dependencies
- US-R19-01/02/03 → patient/study/report read endpoints (scoped)
- US-R19-04 → notification event on report finalize (R12)
- US-R19-05 → read-only viewer mode (exists for share links — reuse)
- US-R19-06 → request primitive (new)
