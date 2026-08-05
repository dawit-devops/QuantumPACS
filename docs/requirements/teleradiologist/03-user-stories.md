# User Stories — Teleradiologist (R18)

**Role ID**: R18  
**Generated**: 2026-08-02  
**Version**: 1.0.0

---

## US-R18-01: Remote STAT Worklist Access
**Story**: As a teleradiologist, I want to access a prioritized STAT worklist filtered by urgency and site, so that I can immediately identify and read the most critical studies first during off-hours coverage.

**Priority**: Must

### Acceptance Criteria
- **Given** I am authenticated as a teleradiologist covering multiple sites, **when** I navigate to the worklist dashboard, **then** I see studies grouped by priority (STAT > Urgent > Routine) with color-coded visual indicators (red for STAT, yellow for urgent, white for routine).
- **Given** a new STAT study is assigned to my worklist, **when** the study becomes available, **then** I receive an audio alert and visual notification within 5 seconds via WebSocket live update.
- **Given** I have STAT studies from multiple sites, **when** I view the worklist, **then** each study row displays site name, patient ID (last 4 digits only), modality, study description, and age since assignment with contrast ≥ 4.5:1.
- **Given** a STAT study has been pending for >20 minutes without report initiation, **when** I view the worklist, **then** that study is highlighted in pulsing red with "URGENT: >20min" badge.
- **Given** I am offline or WebSocket connection fails, **when** the connection drops, **then** I see a persistent "Live updates disconnected" warning banner and the system falls back to polling every 30 seconds.
- **Accessibility**: Worklist table is fully keyboard-navigable with arrow keys; STAT alerts have ARIA live region announcements; audio alerts have visual equivalent.
- **Performance**: Worklist initial load LCP ≤ 2.0s over 10 Mbps WAN connection; INP ≤ 200ms for filter/sort interactions.

### Dependencies
- API: `GET /api/v2/worklists/teleradiology` (new endpoint required)
- WebSocket: `/ws/worklists/teleradiology` for live updates
- Backend: PostgreSQL `notify_event()` trigger on study status changes
- Frontend: Audio notification API, Ant Design Table with custom row styling

---

## US-R18-02: Preliminary Report Creation
**Story**: As a teleradiologist, I want to create and sign preliminary reports that are clearly distinguished from final reports, so that on-site radiologists know these require review and finalization.

**Priority**: Must

### Acceptance Criteria
- **Given** I have opened a study for reading, **when** I click "Create Report", **then** the report editor opens with "Preliminary Report" badge visible at the top and "Preliminary" checkbox pre-selected.
- **Given** I am drafting a preliminary report, **when** I type in the report editor, **then** the system autosaves every 10 seconds with optimistic UI update and "Saving..." indicator that disappears on success.
- **Given** I have completed a preliminary report, **when** I click "Sign Preliminary Report", **then** the system prompts for final confirmation with "This will be marked as PRELIMINARY and require on-site review" message.
- **Given** I have signed a preliminary report, **when** the signature is saved, **then** the report status changes to "preliminary", timestamp and my name are recorded, and the study moves to the "Preliminary Review Queue" for R12.
- **Given** my connection drops during report drafting, **when** connectivity is lost, **then** the draft is saved to browser IndexedDB with "Offline - unsaved changes" warning, and syncs automatically when connection is restored.
- **Accessibility**: Report editor supports screen reader with ARIA labels; preliminary status announced as "Preliminary Report for [Patient ID]"; keyboard shortcut Ctrl+S for manual save.
- **Performance**: Autosave API call ≤ 300ms p95; optimistic UI update instant; sign action ≤ 500ms.

### Dependencies
- API: `POST /api/reports` with `preliminary=true` flag
- API: `PUT /api/reports/{id}` for autosave
- Frontend: TanStack Query mutation with optimistic updates, IndexedDB for offline drafts
- Database: `reports` table with `type` ENUM ('preliminary', 'final', 'addendum')

---

## US-R18-03: Critical Findings Escalation
**Story**: As a teleradiologist, I want to document and escalate critical findings with automated clinician notification, so that urgent results reach the care team within 15 minutes per ACR guidelines.

**Priority**: Must

### Acceptance Criteria
- **Given** I identify a critical finding during study interpretation, **when** I click "Critical Finding" button in the report editor, **then** a modal opens with fields for finding description, urgency level, and clinician notification method.
- **Given** I have filled the critical finding form, **when** I click "Notify Clinician", **then** the system logs the finding timestamp, triggers automated notification (SMS/page) to the on-call clinician, and displays confirmation.
- **Given** automated notification fails, **when** the failure occurs within 30 seconds, **then** I see prominent error banner "Automated notification failed - CALL CLINICIAN DIRECTLY" with on-call phone number displayed.
- **Given** I have contacted the clinician directly, **when** I return to the critical finding form, **then** I log the communication timestamp, method, and clinician name.
- **Given** critical finding is documented, **when** the report is signed, **then** the critical finding log entry is immutably recorded in audit trail with 7-year retention.
- **Accessibility**: Critical finding modal keyboard-operable; urgency communicated with icon + text (not color alone); error banners announced via ARIA live region.
- **Performance**: Notification API call ≤ 2s; escalation log save ≤ 500ms.

### Dependencies
- API: `POST /api/v2/critical-findings` (new endpoint required)
- Backend: Integration with Twilio API (SMS) or PagerDuty API (paging)
- Database: `critical_findings` table with audit fields
- Compliance: HIPAA audit trail with 7-year retention

---

## US-R18-04: Multi-Site Tenant Switching
**Story**: As a teleradiologist covering 3-5 hospital sites simultaneously, I want to quickly switch between site contexts from a unified dashboard, so that I can monitor and respond to urgent studies across all my assigned sites.

**Priority**: Must

### Acceptance Criteria
- **Given** I have authenticated via SSO and have access to multiple sites, **when** I land on the dashboard, **then** I see a card-based layout with one card per site showing site name, worklist count, STAT count, and oldest STAT age.
- **Given** a site has a STAT study older than 20 minutes, **when** I view the dashboard, **then** that site card is highlighted with pulsing red border and "URGENT" label.
- **Given** I want to switch to a specific site, **when** I click a site card, **then** the system exchanges my JWT token for a site-scoped token and navigates to that site's worklist within 2 seconds.
- **Given** one site's database is unreachable, **when** I view the dashboard, **then** that site card shows "Site Unavailable - Contact IT" error state, and other sites remain accessible.
- **Accessibility**: Site cards keyboard-navigable with Tab; card activation with Enter/Space; site context announced when switching.
- **Performance**: Dashboard load LCP ≤ 2.0s; site switching ≤ 2.5s; worklist count updates ≤ 5s staleness.

### Dependencies
- API: `GET /api/v2/users/me/sites` (new endpoint required)
- API: `POST /api/v2/auth/switch-tenant` for JWT token exchange (new endpoint required)
- Frontend: Multi-tenant context state management
- Backend: Per-tenant database connection pooling

---

## US-R18-05: Remote Study Image Loading Optimization
**Story**: As a teleradiologist reading over WAN from home, I want studies to load quickly with aggressive prefetching, so that I don't waste time waiting for images between cases.

**Priority**: Must

### Acceptance Criteria
- **Given** I open a study viewer, **when** the viewer initializes, **then** the first image displays within 2.5 seconds over a 10 Mbps connection.
- **Given** I am viewing a study, **when** the viewer is idle for 3 seconds, **then** the system begins prefetching the next 3 studies in my worklist in the background.
- **Given** prefetching is active, **when** bandwidth utilization reaches 70%, **then** prefetch throttles to 30% to preserve current viewer responsiveness.
- **Given** I have prefetched studies in cache, **when** I open the next study, **then** first image loads in ≤ 1.0s with "Loading from cache" indicator.
- **Accessibility**: Loading indicators are ARIA live regions; cache status announced for screen readers.
- **Performance**: First image LCP ≤ 2.5s (WAN), ≤ 1.0s (cache hit); prefetch uses ≤ 30% bandwidth.

### Dependencies
- API: `POST /api/v2/worklists/teleradiology/prefetch` (new endpoint required)
- Frontend: Cornerstone3D image loader with cache, network speed detection API
- Backend: WADO-URI with CDN caching, HTTP/2 server push
- Infrastructure: CDN or edge cache deployment for WAN optimization

---

## US-R18-06: Offline Study Package Download
**Story**: As a teleradiologist anticipating VPN instability during travel, I want to download complete study packages for offline reading, so that I can continue working without connectivity.

**Priority**: Should

### Acceptance Criteria
- **Given** I am viewing a study, **when** I right-click the study row and select "Download Offline Package", **then** a background job is queued and I see "Preparing offline package - estimated 30s" progress indicator.
- **Given** the offline package is ready, **when** I click the download link, **then** I receive an encrypted ZIP file containing DICOM files, standalone HTML viewer, and metadata JSON.
- **Given** I have downloaded the offline package, **when** I unzip and open viewer.html, **then** the standalone viewer loads without internet connection and displays all study images.
- **Given** I draft a report offline, **when** I regain connectivity and log back in, **then** I see a "Sync Offline Report" button to paste draft text.
- **Accessibility**: Download progress announced via ARIA live region; offline viewer meets WCAG 2.1 AA.
- **Performance**: Package generation ≤ 30s for 500-instance study; ZIP file size ≤ 2GB; viewer load time (offline) ≤ 3s.

### Dependencies
- API: `POST /api/v2/studies/{id}/offline-package` (new endpoint required)
- API: `GET /api/v2/jobs/{id}` for job status polling
- Backend: Background job queue, DICOM decompression, ZIP encryption
- Frontend: Standalone Cornerstone3D viewer bundle

---

## US-R18-07: Preliminary Report Finalization by On-Site Radiologist
**Story**: As a staff radiologist (R12), I want to review and finalize teleradiologist preliminary reports, so that the final report reflects on-site oversight per regulatory requirements.

**Priority**: Must

### Acceptance Criteria
- **Given** I am a staff radiologist, **when** I navigate to "Preliminary Reports" queue, **then** I see a list of all preliminary reports from teleradiologists sorted by oldest first.
- **Given** I click a preliminary report row, **when** the report opens, **then** I see the report text with "Preliminary Report by Dr. [Name]" badge and side-by-side viewer layout.
- **Given** I have reviewed the images and agree with the findings, **when** I click "Finalize Report", **then** the system prompts for confirmation and changes report status to "final".
- **Given** I disagree with preliminary findings, **when** I click "Add Addendum", **then** a text editor opens for documenting discrepancies.
- **Accessibility**: Preliminary report queue keyboard-navigable; side-by-side layout resizable with keyboard.
- **Performance**: Preliminary queue load LCP ≤ 2.0s; report finalization API call ≤ 500ms.

### Dependencies
- API: `GET /api/reports?status=preliminary`
- API: `POST /api/v2/reports/{id}/finalize` (new endpoint required)
- API: `PUT /api/reports/{id}/addendum` (new endpoint required)
- Notification: Email service for alerts

---

## US-R18-08: Session Timeout and Re-Authentication
**Story**: As a teleradiologist working remotely with sensitive PHI, I want automatic session timeout after inactivity, so that my home workstation is not left with open PHI access if I step away.

**Priority**: Must

### Acceptance Criteria
- **Given** I am logged in and idle for 15 minutes, **when** the idle timer expires, **then** I see a modal warning "Session expiring in 60 seconds - click to stay logged in".
- **Given** the session timeout warning appears, **when** I click "Stay Logged In" within 60 seconds, **then** my session is refreshed and I continue working.
- **Given** the session timeout warning appears, **when** I do not respond within 60 seconds, **then** I am automatically logged out and any unsaved report drafts are saved to IndexedDB.
- **Given** I am required to re-authenticate every 4 hours regardless of activity, **when** 4 hours elapse, **then** I see "Re-authentication required for security" modal.
- **Accessibility**: Session timeout modal is keyboard-trapped; countdown announced every 10 seconds via ARIA live region.
- **Performance**: Idle detection polling ≤ 1s interval; token refresh ≤ 500ms; logout action ≤ 200ms.

### Dependencies
- Frontend: Idle timer, localStorage for cross-tab session sync, IndexedDB for draft persistence
- API: `POST /api/auth/refresh` for token renewal
- Security: JWT token expiry aligned with idle timeout

---

## Implementation Priority Order (Recommended)

1. **Phase 1 (Must-Have Foundation)**:
   - US-R18-08 (Session timeout) — security baseline
   - US-R18-04 (Multi-site switching) — core multi-tenant access
   - US-R18-01 (Worklist) — core workflow
   - US-R18-05 (Image loading) — performance critical path

2. **Phase 2 (Core Clinical Workflow)**:
   - US-R18-02 (Preliminary reports)
   - US-R18-03 (Critical findings)
   - US-R18-07 (Report finalization by R12)

3. **Phase 3 (Enhanced Reliability)**:
   - US-R18-06 (Offline packages)
   - US-R18-11 (Mobile fallback)

---

## US-R18-11: Mobile Fallback for Urgent Consultations
**Story**: As a teleradiologist on-call, I want limited mobile viewer access for urgent consultations when away from my workstation, so that I can provide preliminary guidance without delaying critical care.

**Priority**: Could

### Acceptance Criteria
- **Given** I access QuantumPACS from a mobile device (iOS Safari 15+ or Android Chrome 90+), **when** I log in, **then** I see a mobile-optimized interface with "Mobile View - Limited Diagnostic Capability" disclaimer banner (yellow bg, black text, contrast ≥4.5:1, dismissible).
- **Given** I am in mobile view at breakpoint <768px, **when** I open the worklist, **then** I see a card-based layout (not table) with patient ID, modality, priority badge, and age since assignment, with touch targets ≥44x44px (iOS HIG, WCAG 2.1 AAA).
- **Given** I open a study on mobile, **when** the viewer loads, **then** I see a touch-optimized viewer with pinch-to-zoom (2-finger gesture), swipe-to-navigate (1-finger horizontal swipe for series), basic window/level controls (slider), but no MPR/3D/measurement tools, and first-image load ≤5.0s over 4G connection.
- **Given** I am drafting a report on mobile, **when** I open the report editor, **then** I see a warning "Mobile report entry is for urgent consultations only - full review required on workstation" with acknowledgment checkbox, and report is automatically flagged with "Mobile Entry" badge when saved.
- **Given** I create a mobile report, **when** I save it, **then** the report status is set to "preliminary" (cannot sign as final from mobile), R12 review queue shows "Mobile Entry - Desktop Review Required" flag, and audit log records device type (iOS/Android) and screen size.
- **Given** a study requires full diagnostic reading (>300 instances or 3D reconstruction), **when** I attempt to open it on mobile, **then** I see "Complex study - desktop workstation recommended" modal with options: "Proceed with limited view" or "Defer to desktop".
- **Given** I am using mobile with poor network (<5 Mbps), **when** images load, **then** viewer automatically switches to low-resolution preview mode (256px viewport) with "Limited bandwidth - preview mode active" notification.
- **Accessibility**: Mobile UI meets WCAG 2.1 AA for touch targets (≥44x44px), contrast (≥4.5:1), and screen reader support (iOS VoiceOver, Android TalkBack); gestures have button equivalents (zoom buttons, next/prev buttons).
- **Performance**: Mobile worklist load LCP ≤3.0s over 4G (3 Mbps); mobile viewer first-image load ≤5.0s over 4G; mobile report save ≤500ms.
- **Responsive Breakpoints**:
  - **base** (≥1920px): Desktop full-featured view
  - **lg** (1280-1919px): Desktop compact view
  - **md** (768-1279px): Tablet landscape (limited viewer, full report editor)
  - **sm** (<768px): Mobile (card layout, touch viewer, mobile report entry with disclaimer)

### Dependencies
- Frontend: Responsive mobile UI (media queries < 768px), touch event handling (Hammer.js or native), mobile-optimized Cornerstone3D configuration
- API: Mobile client detection (User-Agent), mobile-specific image resolution (WADO-URI with viewport=256)
- Security: Mobile device fingerprinting, geofencing restrictions (optional per tenant policy)
- Clinical policy: Mobile reading disclaimer, R12 desktop review requirement, medico-legal guidance

### Clinical Safety Considerations
- Mobile reports are **consultative only**, not full diagnostic reads
- R12 must review all mobile reports on desktop workstation before finalization
- Mobile viewer limited to 2D viewing (no 3D, MPR, or complex measurements)
- Disclaimer banner required on all mobile screens
- Audit trail captures device type, screen size, network speed for medico-legal defense
