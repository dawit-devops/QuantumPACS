# User Stories — Referring Clinician (R14)

**Version**: 1.0.0 (v3.0 scope)
**Status**: Final
**Date**: 2026-08-02

---

## US-R14-01: Open shared study via link

**Story**: As a referring clinician, I want to open a shared study link and view the images and report without logging in, so that I can quickly review the study without needing a PACS account.

**Priority**: Must

### Acceptance Criteria

- **Given** I have a share link URL, **when** I open it in a browser, **then** the study images and report are displayed without requiring login.
- **Given** the share link has expired, **when** I open it, **then** I see a friendly error page with a "Request new link" button.
- **Given** the share key is invalid, **when** I open it, **then** I see the same error page as for expired links (no information leakage).
- **Given** the study has no report yet, **when** I open the share link, **then** the viewer loads but the report panel shows "Report pending radiologist review".
- **Accessibility**: The share link page has a descriptive `<title>` and ARIA landmarks; the error page has a heading and a visible "Request new link" button.
- **Performance**: Share link page LCP ≤ 2.5s; viewer first image load ≤ 2s.
- **Security**: The share key is a 32-char cryptographically random string; no PHI in the URL.

### Dependencies
- R08/R12 share link creation (existing `ShareFilesHandler`)
- `shared_files` DB table

---

## US-R14-02: Login via SSO

**Story**: As a referring clinician with an enterprise identity, I want to log in via SSO (Azure AD / Okta) so that I can access my referred studies without a separate PACS password.

**Priority**: Must

### Acceptance Criteria

- **Given** I click the SSO login button, **when** I complete the IdP authentication, **then** I am redirected to the PACS study list with `referring_physician` role.
- **Given** my SSO assertion is invalid or expired, **when** I attempt login, **then** I see "Authentication failed" with a retry option.
- **Given** my SSO identity is not provisioned in PACS, **when** I attempt login, **then** I see "Access not provisioned. Contact your PACS administrator."
- **Given** I am already logged in, **when** I navigate to /login/sso, **then** I am redirected to my study list (no re-login).
- **Accessibility**: The SSO login page has a descriptive heading, ARIA labels on the login button, and keyboard-operable redirect flow.
- **Performance**: SSO redirect completes within 3s from IdP.
- **Security**: JWT is validated against the IdP's public key; token expiry is handled gracefully (401 → redirect to login).

### Dependencies
- Tenant-level IdP configuration (R01/R02)
- Existing auth infrastructure (`backend/api/auth.py`)

---

## US-R14-03: View study images in read-only viewer

**Story**: As a referring clinician, I want to view DICOM images in a basic viewer with scroll, WW/WL, zoom, and pan, so that I can assess image quality and findings.

**Priority**: Must

### Acceptance Criteria

- **Given** I am on a study detail page, **when** the viewer loads, **then** the first series is displayed with scroll, WW/WL, zoom, and pan controls.
- **Given** I am on a study detail page, **when** I try to annotate or measure, **then** no annotation tools are available and the viewer is explicitly marked "View Only".
- **Given** I navigate between series, **when** I click a series thumbnail, **then** the viewer loads that series within 2s.
- **Given** I use pinch-zoom on mobile, **when** I pinch, **then** the image zooms in/out smoothly.
- **Given** I use swipe on mobile, **when** I swipe, **then** the image navigates to the next/previous slice.
- **Accessibility**: The viewer has ARIA labels for all controls; keyboard shortcuts are documented; focus is managed so screen reader can announce the current image index.
- **Performance**: First series loads within 2s; series switch within 2s.
- **Design**: Viewer uses semantic tokens; no one-off colors; responsive layout.

### Dependencies
- Cornerstone3D viewer (read-only mode)
- Study metadata API (`GET /api/v2/studies/{study_uid}`)

---

## US-R14-04: View radiology report

**Story**: As a referring clinician, I want to view the radiology report for a study, so that I can understand the radiologist's findings and recommendations.

**Priority**: Must

### Acceptance Criteria

- **Given** I am viewing a completed study, **when** the report panel renders, **then** the structured report (findings, impression) and narrative text are displayed.
- **Given** the report has critical/urgent findings, **when** it renders, **then** a prominent alert banner is shown at the top of the report.
- **Given** I try to edit the report, **when** I click on any field, **then** no edit capability is available (all fields are read-only).
- **Given** the report is not yet signed, **when** I view the study, **then** the report panel shows "Report pending radiologist review".
- **Accessibility**: Report text has sufficient contrast (≥ 4.5:1); critical alert uses both color and icon (not color alone); report sections have ARIA headings.
- **Performance**: Report renders within 1s of study detail page load.

### Dependencies
- Report API (`GET /api/v2/studies/{study_uid}` returns report)
- R12 radiologist report signing workflow

---

## US-R14-05: Check study status

**Story**: As a referring clinician, I want to see the status of my referred studies (scheduled, in-progress, completed, available), so that I know which results are ready to review.

**Priority**: Must

### Acceptance Criteria

- **Given** I navigate to my study list, **when** the page loads, **then** I see a table of my referred studies with status column.
- **Given** a study is completed and report is available, **when** I view the study list, **then** the status shows "Available" and the row is clickable to open the viewer.
- **Given** I filter by status, **when** I select a filter, **then** the table updates to show only studies with that status.
- **Given** I sort by date, **when** I click the date column header, **then** the table sorts by study date (newest first).
- **Given** I have no referred studies, **when** I view the study list, **then** I see an empty state with "No referred studies found" message.
- **Accessibility**: Table has `<th scope="col">` headers; rows are keyboard-navigable; status badges have ARIA labels.
- **Performance**: Study list loads within 2s; pagination (25/page) works without full page reload.

### Dependencies
- Study status API (`GET /api/v2/studies?role=referring_physician`)
- R06/R07 exam completion events

---

## US-R14-06: Receive results notification

**Story**: As a referring clinician, I want to be notified when a study I referred has been completed and a report is available, so that I can review the results promptly.

**Priority**: Must

### Acceptance Criteria

- **Given** a report is signed for a study I referred, **when** the notification is generated, **then** I receive an email notification (if email is enabled) and an in-app notification.
- **Given** I have unread notifications, **when** I view the notification bell icon, **then** the badge count reflects the number of unread notifications.
- **Given** I click a notification, **when** I open the study, **then** the study viewer and report are displayed.
- **Given** I mark a notification as read, **when** I click the notification, **then** the badge count decrements and the notification is marked read.
- **Given** the notification includes a report summary, **when** I view it, **then** the summary is truncated to 200 characters with a "View full report" link.
- **Accessibility**: Notifications are announced by screen reader; notification bell has ARIA label; dropdown is keyboard-navigable.
- **Performance**: Notification badge updates within 5s of report sign-off.

### Dependencies
- Existing notification infrastructure (`events:notify` Redis Stream)
- Email delivery service

---

## US-R14-07: Search and filter referred studies

**Story**: As a referring clinician, I want to search and filter my referred studies by patient name, MRN, date range, modality, and status, so that I can quickly find the study I need.

**Priority**: Must

### Acceptance Criteria

- **Given** I am on the study list page, **when** I enter a patient name in the search field, **then** the table filters to show only matching studies.
- **Given** I select a modality filter, **when** I apply the filter, **then** the table shows only studies of that modality.
- **Given** I select a date range, **when** I apply the filter, **then** the table shows only studies within that range (capped at 90 days).
- **Given** I combine multiple filters, **when** I apply them, **then** the table shows only studies matching all filters.
- **Given** no studies match the filters, **when** I apply them, **then** I see an empty state with "No studies match your filters" message.
- **Given** the date range exceeds 90 days, **when** I apply the filter, **then** I see a warning and the range is capped at 90 days.
- **Accessibility**: Search field has ARIA label; filter dropdowns have ARIA labels; results table has proper `<th scope="col">` headers.
- **Performance**: Filtering responds within 500ms; debounced search input (300ms delay).

### Dependencies
- Study search API (`GET /api/v2/studies?role=referring_physician&search=...&modality=...&date_from=...&date_to=...`)

---

## US-R14-08: View study detail with metadata

**Story**: As a referring clinician, I want to view the study detail page with all relevant metadata (patient demographics, modality, protocol, referring physician, performing physician, study date, series count), so that I have full context for the images and report.

**Priority**: Must

### Acceptance Criteria

- **Given** I open a study from my list, **when** the study detail page loads, **then** I see the metadata panel on the left and the viewer + report on the right.
- **Given** I view the metadata panel, **when** I check the fields, **then** all metadata fields are read-only and cannot be edited.
- **Given** the study has multiple series, **when** I view the detail page, **then** the series count is displayed in the metadata panel.
- **Given** the study has a referring physician and performing physician, **when** I view the detail page, **then** both are displayed in the metadata panel.
- **Accessibility**: Metadata panel uses semantic HTML (`<dl>`, `<dt>`, `<dd>`); all fields have ARIA labels; keyboard-navigable.
- **Performance**: Metadata panel renders within 1s of page load.

### Dependencies
- Study detail API (`GET /api/v2/studies/{study_uid}`)

---

## US-R14-09: Request follow-up imaging

**Story**: As a referring clinician, I want to request a follow-up study or additional imaging from the reading radiologist, so that I can get the appropriate next-step imaging for my patient.

**Priority**: Could

### Acceptance Criteria

- **Given** I am viewing a study, **when** I click "Request Follow-Up", **then** a follow-up request form is displayed.
- **Given** the form is displayed, **when** I fill in clinical indication, urgency, and requested modality, **when** I submit, **then** the request is created and I see a confirmation toast.
- **Given** the form is submitted, **when** the radiologist reviews it, **then** the radiologist sees the request in their follow-up queue.
- **Given** the radiologist approves the request, **when** I receive the notification, **then** I see "Follow-up approved" with any radiologist notes.
- **Given** the radiologist rejects the request, **when** I receive the notification, **then** I see "Follow-up rejected" with the rejection reason and can revise and resubmit.
- **Accessibility**: Form fields have ARIA labels; validation errors are announced by screen reader; submit button has descriptive text.
- **Performance**: Form submission response within 1s; notification delivery within 5min.

### Dependencies
- Follow-up request API (`POST /api/v2/studies/{study_uid}/followup-request`)
- R12 radiologist follow-up queue
- Notification infrastructure

---

## US-R14-10: View active share links

**Story**: As a referring clinician, I want to view my active share links and their expiry status, so that I know which links are still valid.

**Priority**: Could

### Acceptance Criteria

- **Given** I navigate to my share links page, **when** the page loads, **then** I see a list of my active share links with study description, creation date, and expiry date.
- **Given** a share link is about to expire (within 24h), **when** I view the list, **then** the link is marked with an "Expiring soon" badge.
- **Given** I want to revoke a share link, **when** I click "Revoke", **then** the link is deactivated and I can no longer access the study via that link.
- **Given** I try to access a revoked share link, **when** I open it, **then** I see "This link has been revoked" error page.
- **Accessibility**: Share link list has ARIA labels; revoke button has confirmation dialog; expiry badges use both color and text.
- **Performance**: Share link list loads within 2s.

### Dependencies
- Share link management API (`GET /api/v2/share/links`, `DELETE /api/v2/share/links/{id}`)
- `shared_files` DB table

---

## US-R14-11: View critical findings alert

**Story**: As a referring clinician, I want to see a prominent alert when a study I referred has a critical or urgent finding, so that I can act on the finding promptly.

**Priority**: Should

### Acceptance Criteria

- **Given** a study has a critical/urgent finding flagged by the radiologist, **when** I view the study or study list, **then** a prominent alert banner is displayed at the top of the report.
- **Given** the alert is displayed, **when** I click "View Details", **then** I am taken to the full report with the critical finding highlighted.
- **Given** the alert is displayed, **when** I dismiss it, **when** I refresh the page, **then** the alert reappears (not dismissible permanently until the finding is resolved).
- **Accessibility**: The alert uses both color and an icon (not color alone); has ARIA role="alert"; is announced by screen reader; is keyboard-dismissable.
- **Performance**: Alert appears within 1s of report load.

### Dependencies
- R12 critical findings escalation workflow
- Report API returns `critical_finding` flag