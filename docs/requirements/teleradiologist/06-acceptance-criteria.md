# Acceptance Criteria — Teleradiologist (R18)

**Role ID**: R18  
**Generated**: 2026-08-02  
**Version**: 1.0.0

---

## Acceptance Criteria Matrix

This matrix maps all functional and non-functional requirements to verifiable acceptance criteria following the ui-visual-validator skeptical verification gate (Section 6.4 of the skill).

### Verification Method Legend
- **AT**: Automated Test (Playwright E2E, Vitest unit, pytest integration)
- **VE**: Visual Evidence (screenshot, screen recording with measurements)
- **MT**: Manual Test (human verification with documented steps)
- **PM**: Performance Measurement (Lighthouse, k6, APM metrics)
- **AL**: Audit Log (database query, log analysis)

---

## AC-R18-01: Remote STAT Worklist Priority Grouping — PARTIAL (priority grouping verifiable via `ReadingWorklist.tsx`; WS freshness banner/audio alerts GATED)

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R18-01-01 | FR-R18-01 | **Given** I am authenticated as a teleradiologist covering multiple sites, **when** I navigate to the worklist dashboard, **then** I observe studies grouped by priority (STAT > Urgent > Routine) with STAT rows having red background fade (rgba(239, 68, 68, 0.1)), urgent rows having yellow left border (4px solid #F59E0B), and routine rows having default white background. | VE + AT | Contrast measured ≥4.5:1 for text on backgrounds; priority order verified by DOM order; color + icon + text present (not color alone) |
| AC-R18-01-02 | FR-R18-01, NFR-R18-02 | **Given** a new STAT study is assigned to my worklist by R06, **when** the study becomes available (DB INSERT trigger fires), **then** within 5 seconds I observe: (1) audio alert plays (with visual equivalent), (2) new row inserted at top of STAT section with fade-in animation, (3) browser notification appears if permission granted. | AT + PM | WebSocket message timestamp delta ≤5s measured; audio element `play()` called; ARIA live region updated; visual notification banner present regardless of audio |
| AC-R18-01-03 | FR-R18-01 | **Given** I have STAT studies from multiple sites in my worklist, **when** I view any STAT row, **then** I observe: site name column displays tenant name, patient ID shows last 4 digits only (masked), modality abbreviation (CT/MR/CR/etc), study description truncated to 50 chars, and "age since assignment" in relative format ("5min ago", "2h ago"). | VE + AT | Screenshot shows site name; patient ID regex `\*\*\*\*\d{4}`; contrast ≥4.5:1 for all text; relative time updates every 60s |
| AC-R18-01-04 | FR-R18-20 | **Given** a STAT study has been pending for >20 minutes without report initiation, **when** I view the worklist, **then** I observe that study row has pulsing red border animation (`@keyframes pulse`), "URGENT: >20min" badge in red (#EF4444) with white text (contrast ≥4.5:1), and ARIA live region announces "STAT study overdue: [Patient ID]". | VE + AT | CSS animation verified; badge text measured; ARIA announcement captured in test; pulsing animation does not cause CLS |
| AC-R18-01-05 | FR-R18-02, NFR-R18-02 | **Given** I am online and WebSocket connection fails, **when** the connection drops, **then** I observe persistent yellow banner at top of page reading "Live updates disconnected - polling every 30s" with retry button, and subsequent worklist refreshes occur every 30s via API polling (verified by network log). | AT + VE | Banner `position: sticky; top: 0; z-index: 100`; polling interval measured via network timestamps; banner dismissible but re-appears on next poll failure |

**Validator Gate Verdict**: AC-R18-01 achieves acceptance criteria **only if** visual evidence shows: (1) color + icon + text for priority (not color alone), (2) contrast ratios measured ≥4.5:1, (3) ARIA live region updates confirmed, (4) WebSocket latency ≤5s measured, (5) polling fallback functional when WebSocket disabled.

---

## AC-R18-02: Preliminary Report Creation & Autosave — PARTIAL (preliminary badge + status verifiable via `ReportEditor.tsx`; offline IndexedDB backup GATED)

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R18-02-01 | FR-R18-07 | **Given** I have opened a study for reading, **when** I click "Create Report" button, **then** I observe report editor opens with yellow "PRELIMINARY" badge (bg: #F59E0B, text: white, contrast ≥4.5:1) visible at top-right, "Preliminary" checkbox pre-selected, and ARIA label "Preliminary Report for Patient [ID]" announced by screen reader. | VE + MT | Screenshot shows badge position; checkbox state `checked`; contrast measured; screen reader announcement logged |
| AC-R18-02-02 | FR-R18-07, NFR-R18-05 | **Given** I am drafting a preliminary report, **when** I type in the report editor, **then** I observe: (1) "Saving..." indicator appears after 10s idle with spinner icon, (2) indicator changes to "Saved 2s ago" with green checkmark on success, (3) API call `PUT /api/reports/{id}` completes in ≤300ms p95, (4) optimistic UI update (no perceived delay). | AT + PM | Network timing measured; DOM element `.autosave-indicator` text content changes; TanStack Query cache updated optimistically; no spinner if optimistic update succeeds |
| AC-R18-02-03 | FR-R18-07 | **Given** I have completed a preliminary report, **when** I click "Sign Preliminary Report", **then** I observe confirmation modal with text "This will be marked as PRELIMINARY and require on-site review" with "Confirm" and "Cancel" buttons, keyboard focus on "Confirm" button, modal keyboard-trapped (Tab cycles, Escape dismisses). | AT + VE | Modal `aria-modal="true"`, focus trap verified by Tab key test; Escape key dismisses modal; confirmation text exact match |
| AC-R18-02-04 | FR-R18-07 | **Given** I have confirmed preliminary report signature, **when** the save completes, **then** I observe: (1) report status changes to "preliminary" (visual badge), (2) my name and timestamp recorded in "Signed by Dr. [Name] at [timestamp]" footer, (3) study row in worklist changes to "Prelim Complete" status with blue badge, (4) R12 preliminary review queue receives notification. | AT + AL | Database query: `reports.status='preliminary' AND reports.signed_at IS NOT NULL`; audit log entry created; worklist status updated; R12 notification sent (email or in-app) within 1min |
| AC-R18-02-05 | FR-R18-07, NFR-R18-05 | **Given** my connection drops during report drafting, **when** connectivity is lost, **then** I observe: (1) yellow banner "Offline - unsaved changes" appears at top, (2) draft text saved to IndexedDB every keystroke, (3) autosave indicator shows "Offline mode active", (4) when connection restored, banner shows "Syncing..." then "Synced" with green checkmark, (5) IndexedDB draft cleared on successful sync. | AT + VE | Network throttle to offline; IndexedDB key `draft-report-{id}` contains text; reconnect triggers sync; API call successful; IndexedDB key deleted |

**Validator Gate Verdict**: AC-R18-02 achieves acceptance criteria **only if** visual evidence shows: (1) preliminary badge always visible (not hidden in collapsed UI), (2) autosave timing measured ≤10s idle + ≤300ms API, (3) offline IndexedDB backup verified by browser DevTools inspection, (4) confirmation modal keyboard-operable with focus trap.

---

## AC-R18-03: Critical Findings Escalation & Notification — GATED (no escalation endpoint; sign notifies QA role only)

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R18-03-01 | FR-R18-09 | **Given** I identify a critical finding during study interpretation, **when** I click "Critical Finding" button in report editor, **then** I observe modal opens with heading "Critical Finding Escalation", textarea labeled "Finding Description" (required), radio buttons "Critical" / "Urgent" with "Critical" pre-selected, dropdown "Notification Method" (phone/page/secure message), and "Notify Clinician" primary button. | VE + AT | Modal `role="dialog"`, `aria-labelledby` points to heading; form fields have explicit labels; required fields marked with `aria-required="true"` and asterisk; keyboard navigable |
| AC-R18-03-02 | FR-R18-09, FR-R18-10, NFR-R18-07 | **Given** I have filled the critical finding form, **when** I click "Notify Clinician", **then** I observe: (1) button shows spinner "Sending notification...", (2) API call `POST /api/v2/critical-findings` completes in ≤2s, (3) SMS/page sent via Twilio/PagerDuty integration, (4) success message "Escalation sent to Dr. [Name] at [phone]" with green checkmark and timestamp, (5) audit log entry created with my user ID, report ID, finding text, notification method, timestamp, IP, geolocation. | AT + AL | API response contains notification ID and delivery status; Twilio API mock returns success; audit log query shows all required fields; timestamp within 30s of form submission |
| AC-R18-03-03 | FR-R18-09, NFR-R18-07 | **Given** automated notification fails (Twilio API returns error), **when** the failure occurs within 30 seconds, **then** I observe prominent red banner "Automated notification failed - CALL CLINICIAN DIRECTLY" with on-call phone number displayed in large font (20px), "Retry" button, and audio alert (with visual equivalent). | AT + VE | Error response from API triggers banner display; phone number formatted `(555) 123-4567`; audio element plays; banner `position: sticky; top: 0; z-index: 1000`; contrast ≥4.5:1 for text on red background |
| AC-R18-03-04 | FR-R18-10, SEC-R18-06 | **Given** I have contacted the clinician directly after automated failure, **when** I return to the critical finding form and log the manual notification, **then** I observe: (1) "Manual Notification Log" section expands, (2) fields for clinician name, phone number (last 4 digits), timestamp (auto-filled with current time), communication method (phone/in-person), and free-text note, (3) on save, audit trail records both automated failure event and manual notification event with timestamp delta, (4) timeline shows: failure at T+30s, manual call at T+5min (gap: 4min 30s). | AL + MT | Database query: `critical_findings` table shows `automated_notification_failed_at` and `manual_notification_at` timestamps; delta calculated; audit log immutable (no UPDATE, only INSERT) |
| AC-R18-03-05 | FR-R18-09 | **Given** I have escalated a critical finding, **when** the on-site radiologist (R12) opens the study, **then** they observe prominent orange banner at top of viewer: "Critical Finding Notified by Dr. [Teleradiologist Name] on [date] at [time] - [finding text]" with "View Full Log" button, banner persists until R12 acknowledges (checkbox + signature). | AT + VE | R12 test account opens study; banner rendered; text matches critical finding entry; acknowledgment checkbox updates database `critical_findings.acknowledged_by` and `acknowledged_at` |

**Validator Gate Verdict**: AC-R18-03 achieves acceptance criteria **only if** visual evidence shows: (1) automated notification failure triggers immediate (<30s) visible error banner, (2) phone number displayed in clear large font, (3) audit log entries immutable (verified by DB schema), (4) manual notification timestamp gap measured and recorded, (5) R12 banner visible and persistent until acknowledged.

---

## AC-R18-04: Multi-Site Tenant Switching & JWT Token Exchange — PARTIAL (SSO + tenant switch verifiable; per-site card dashboard GATED)

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R18-04-01 | FR-R18-03, FR-R18-15 | **Given** I have authenticated via SSO and have access to multiple sites, **when** I land on the dashboard, **then** I observe card-based layout with one card per site, each card displaying: site name (h3 heading), total worklist count (number with "studies" label), STAT count (red badge), oldest STAT age ("Oldest STAT: 25min ago" in gray, turns red if >20min), last updated timestamp ("Updated 10s ago"). | VE + AT | Screenshot shows all cards; layout grid `grid-template-columns: repeat(auto-fill, minmax(300px, 1fr))`; each card 300px min-width, 200px height, 8px border-radius, 24px gap; oldest STAT >20min has `color: #EF4444; font-weight: 600; animation: pulse` |
| AC-R18-04-02 | FR-R18-15, NFR-R18-08 | **Given** I view the multi-site dashboard and Site A has a STAT study older than 20 minutes, **when** the dashboard renders, **then** I observe Site A card has pulsing red border (4px solid #EF4444), "URGENT" label in top-right corner with red background, and contrast ≥4.5:1 for all text on card. | VE + PM | Contrast measured; CSS animation verified; "URGENT" label position `top: 8px; right: 8px; position: absolute`; card z-index elevated on urgent state |
| AC-R18-04-03 | FR-R18-03, NFR-R18-11 | **Given** I want to switch to Site A, **when** I click the Site A card, **then** I observe: (1) loading spinner on card for ≤2.5s, (2) API call `POST /api/v2/auth/switch-tenant` with `tenant_id=siteA`, (3) new JWT token received in response, (4) sidebar updates to show "[Site A]" context indicator in header, (5) navigation to Site A worklist, (6) total time from click to worklist display ≤2.5s p95. | AT + PM | Network timing measured; JWT token decoded shows `tenant=siteA`; sidebar text content updated; Playwright timing assertion `await expect(worklist).toBeVisible({ timeout: 2500 })` |
| AC-R18-04-04 | FR-R18-03 | **Given** I am working within Site A context, **when** I click the site name in the sidebar header (breadcrumb), **then** I observe: (1) navigation back to multi-site dashboard, (2) previous worklist position/scroll preserved in browser history (back button), (3) site cards refresh with updated counts. | AT + VE | Browser back button navigates to dashboard; scroll position restored; API call `GET /api/v2/users/me/sites` fetches fresh counts |
| AC-R18-04-05 | FR-R18-03 | **Given** Site B's database is unreachable (connection timeout), **when** I view the dashboard, **then** I observe Site B card shows "Site Unavailable" red text on gray background, "Contact IT: [email/phone]" link, card opacity 0.5, cursor `not-allowed`, click disabled, and other site cards remain fully interactive. | AT + VE | Mock API returns 503 for Site B; card state changes; click event handler disabled; other cards clickable; error state persists until manual refresh |

**Validator Gate Verdict**: AC-R18-04 achieves acceptance criteria **only if** visual evidence shows: (1) site switching completes ≤2.5s measured, (2) sidebar context indicator updates atomically with worklist load (no race condition), (3) error state visually distinct (opacity + color + cursor), (4) contrast ratios measured for all states, (5) keyboard navigation functional (Tab to cards, Enter/Space activates).

---

## AC-R18-05: Remote Study Image Loading & Prefetch Optimization — PARTIAL (first-image + keyboard verifiable; prefetch/offline-package banner GATED)

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R18-05-01 | FR-R18-05, NFR-R18-03 | **Given** I open a study viewer, **when** the viewer initializes over 10 Mbps WAN connection, **then** I observe first image of first series displays with LCP ≤2.5s measured by Lighthouse/Playwright, loading spinner visible until LCP, progress bar shows % loaded (0-100%), and "Loading images..." text with ARIA live region. | PM + AT | Playwright network throttle 10 Mbps + 50ms latency; LCP timing measured; progress bar `aria-valuenow` updates; spinner has `role="status"`, `aria-label="Loading"` |
| AC-R18-05-02 | FR-R18-06 | **Given** I am viewing a study and viewer is idle for 3 seconds, **when** idle timer expires, **then** I observe: (1) no visible UI change, (2) network log shows API call `POST /api/v2/worklists/teleradiology/prefetch` with `study_ids` array of next 3 studies, (3) background image fetches begin (WADO-URI requests), (4) browser console log "Prefetching next 3 studies", (5) current viewer interactions remain responsive (INP ≤200ms). | AT + PM | Network log filtered for prefetch requests; timing shows 3s delay; INP measured during prefetch; prefetch does not block main thread |
| AC-R18-05-03 | FR-R18-06, NFR-R18-13 | **Given** prefetching is active and bandwidth utilization reaches 70% of available capacity (measured via `navigator.connection.downlink`), **when** utilization exceeds threshold, **then** I observe: (1) prefetch requests throttled (fewer concurrent requests), (2) bandwidth utilization drops to ≤30%, (3) current viewer load time unaffected, (4) browser console log "Prefetch throttled - bandwidth limit". | AT + PM | Network monitor shows bandwidth usage; prefetch paused or slowed; viewer performance maintained; throttle algorithm verified |
| AC-R18-05-04 | FR-R18-06, NFR-R18-03 | **Given** I have prefetched studies in cache (IndexedDB or Service Worker), **when** I open the next study in worklist, **then** I observe: (1) first image loads in ≤1.0s (cache hit), (2) green toast notification "Loading from cache" auto-dismisses after 2s, (3) network log shows 0 WADO-URI requests for cached images, (4) cache hit icon (green checkmark) in study row. | AT + PM | Cache hit timing measured; toast component renders; network log empty for cached study; cache storage inspected via DevTools |
| AC-R18-05-05 | FR-R18-05 | **Given** image loading fails or times out after 10 seconds, **when** timeout occurs, **then** I observe: (1) error banner "Images loading slowly - poor connection detected", (2) "Download Offline Package" button in banner, (3) "Retry" button, (4) viewer shows partial images loaded (not blank), (5) error logged to Sentry with network conditions. | AT + VE | Network throttle to 1 Mbps; timeout triggers error state; buttons functional; partial render verified; error log captured |
| AC-R18-05-06 | FR-R18-04, NFR-R18-15 | **Given** the DICOM viewer is open and I am using keyboard-only navigation, **when** I press keyboard shortcuts, **then** I observe: (1) Arrow keys scroll through series (previous/next image), (2) W key toggles window/level presets (soft tissue/lung/bone), (3) I key inverts grayscale display, (4) R key resets viewport to default zoom/pan, (5) M key enters MPR (multi-planar reconstruction) mode, (6) Shift+? displays Help overlay with all keyboard shortcuts, (7) all shortcuts have visible focus indicators (3px blue outline). | AT + MT | Playwright keyboard event simulation; viewport state changes verified; Help overlay renders with keyboard shortcuts table; focus indicators visible via screenshot; ARIA labels present for all shortcuts |

**Validator Gate Verdict**: AC-R18-05 achieves acceptance criteria **only if** performance measurements show: (1) LCP ≤2.5s measured with 10 Mbps throttle, (2) cache hit ≤1.0s measured, (3) prefetch bandwidth ≤30% during active viewing, (4) INP ≤200ms maintained during prefetch, (5) error state triggered at 10s timeout with visual evidence, (6) keyboard shortcuts functional with focus indicators measured.

---

## AC-R18-06: Session Timeout & Re-Authentication — GATED (no idle-timeout modal; token expiry only)

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R18-06-01 | NFR-R18-09 | **Given** I am logged in and idle for 15 minutes (no mouse/keyboard/scroll events), **when** the idle timer expires, **then** I observe modal appears with heading "Session Expiring", countdown timer "60 seconds" in large red font (48px, #EF4444), text "Your session will expire - click to stay logged in", and "Stay Logged In" primary button with keyboard focus. | AT + VE | Idle detection mock (fast-forward time); modal `aria-modal="true"`, focus locked; countdown updates every 1s; red color when <10s; ARIA live region announces countdown every 10s |
| AC-R18-06-02 | NFR-R18-09 | **Given** the session timeout warning appears, **when** I click "Stay Logged In" within 60 seconds, **then** I observe: (1) API call `POST /api/auth/refresh` completes in ≤500ms, (2) new JWT token received and stored, (3) modal closes, (4) idle timer resets to 15min, (5) no interruption to current work (report draft persists, viewer stays open). | AT + PM | API timing measured; JWT token updated in localStorage; modal dismissed; report textarea content unchanged; viewer state unchanged |
| AC-R18-06-03 | NFR-R18-09 | **Given** the session timeout warning appears, **when** I do not respond within 60 seconds, **then** I observe: (1) automatic logout (API call `POST /api/auth/logout`), (2) unsaved report draft saved to IndexedDB (key `draft-report-{id}`), (3) redirect to login page, (4) message "Session expired due to inactivity - log in to continue", (5) on SSO re-login, prompt "Restore unsaved draft?" with "Yes" / "No" buttons. | AT + AL | Logout API called; IndexedDB contains draft; login page displays message; restore prompt shows on re-login; draft loaded from IndexedDB on "Yes" |
| AC-R18-06-04 | SEC-R18-04, NFR-R18-09 | **Given** I have been logged in for 4 hours regardless of activity, **when** 4 hours elapse since initial login, **then** I observe: (1) modal "Re-authentication required for security" appears, (2) "Continue to SSO Login" button, (3) cannot dismiss modal (no Escape key or close button), (4) unsaved work persisted before redirect, (5) SSO flow completes and restores previous context (site, worklist position, unsaved drafts). | AT + VE | JWT token expiry timestamp checked; forced re-auth modal appears; focus locked; SSO redirect with `state` parameter preserves context; context restored on callback |

**Validator Gate Verdict**: AC-R18-06 achieves acceptance criteria **only if** visual evidence shows: (1) countdown timer visible and accurate (no drift), (2) ARIA live region announces countdown, (3) IndexedDB backup verified by DevTools, (4) forced re-auth at 4h enforced (no session >4h in audit log), (5) context restoration functional (site + position + drafts).

---

## AC-R18-07: Voice Dictation Integration & Offline Capabilities — GATED (no dictation plugin, no offline packages)

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R18-07-01 | FR-R18-12 | **Given** the teleradiologist has a supported microphone connected, **when** they click the microphone icon in the report editor toolbar, **then** I observe: (1) voice dictation modal opens with "Listening..." indicator, (2) spoken words are transcribed in real-time into the report editor at cursor position, (3) transcription accuracy ≥ 95% for medical terminology (tested with Dragon Medical vocabulary), (4) "Stop Listening" button halts transcription and inserts final text. | AT + MT | Speech-to-text API returns text within 500ms of speech; medical terms (e.g., "pneumothorax", "hemothorax") transcribed correctly; stop button clears listening state |
| AC-R18-07-02 | FR-R18-12 | **Given** the teleradiologist is using Microsoft Speech SDK, **when** the browser requests microphone access, **then** I observe: (1) browser prompts for microphone permission with clear explanation text, (2) if permission denied, a fallback "Type instead" text area is shown, (3) if permission granted, dictation starts within 2 seconds. | AT + VE | Browser permission prompt text verified; fallback textarea rendered on denial; start latency measured ≤2s |
| AC-R18-07-03 | FR-R18-13 | **Given** the teleradiologist has an assigned study in their worklist, **when** they right-click the study row and select "Download Offline Package", **then** I observe: (1) progress bar shows download progress (0-100%), (2) study package (DICOM files + report template) is downloaded as a `.zip` file, (3) download completes within 30s for a 500-instance CT study over LAN, (4) notification "Package ready for offline review" appears on completion. | AT + PM | Download timing measured; zip file contains expected DICOM files; progress bar updates correctly; notification appears |
| AC-R18-07-04 | FR-R18-13, NFR-R18-13 | **Given** bandwidth drops below 1 Mbps during offline package download, **when** the download is in progress, **then** I observe: (1) download pauses automatically, (2) banner "Low bandwidth — download paused" appears, (3) resume button available when bandwidth recovers, (4) download resumes from paused position (not restarted). | AT + VE | Network throttle to 1 Mbps; download pauses; resume works; no duplicate data downloaded |
| AC-R18-07-05 | FR-R18-14 | **Given** the teleradiologist created a draft report while offline, **when** connectivity is restored, **then** I observe: (1) sync indicator shows "Syncing offline draft..." with spinner, (2) draft is uploaded to backend via `POST /api/reports/{id}/sync`, (3) on success, draft status changes to "preliminary" with "Synced from offline" badge, (4) on failure, error banner shows with retry option, (5) offline draft is preserved in IndexedDB until sync succeeds. | AT + AL | Network log shows sync API call; database query confirms draft status updated; IndexedDB cleared on success; retry works on failure |

**Validator Gate Verdict**: AC-R18-07 achieves acceptance criteria **only if** voice dictation accuracy ≥95% for medical terms, offline download completes ≤30s for 500-instance CT, and offline draft sync preserves data integrity on reconnect.

---

## AC-R18-08: Consultation & Second Opinion Workflow — GATED (no consult endpoints; peer review is QA-style on signed reports)

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R18-08-01 | FR-R18-16 | **Given** the teleradiologist has completed a preliminary report, **when** they mark the study as "Consulted" (second opinion), **then** I observe: (1) study status changes to "Consulted" with purple badge (#8B5CF6), (2) a "Consultation Note" field appears in the report editor for documenting the second opinion, (3) the report is distinguished from a primary read (visual indicator: "Secondary Read" tag), (4) the original preliminary report is preserved as a version. | VE + AT | Database query: `reports.consulted_at IS NOT NULL`; visual tag "Secondary Read" rendered; original report version accessible via version history |
| AC-R18-08-02 | FR-R18-16, FR-R18-11 | **Given** the teleradiologist has marked a study as "Consulted", **when** they add a consultation note, **then** I observe: (1) note is saved with the report, (2) the referring clinician (R14) can view the consultation note when accessing the study via share link, (3) the consultation note is included in the audit trail with timestamp and user ID. | AT + AL | API call `PUT /api/reports/{id}` includes consultation note; R14 share link shows note; audit log entry created with `action='consultation_note_added'` |

**Validator Gate Verdict**: AC-R18-08 achieves acceptance criteria **only if** "Consulted" status is visually distinct from "Preliminary" and "Final", original report version is preserved, and consultation notes are visible to referring clinicians via share links.

---

## AC-R18-09: Mobile Viewer for Urgent Consultations — GATED (PWA exists; no telerad-specific mobile UI)

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R18-09-01 | FR-R18-17 | **Given** the teleradiologist accesses the system from a mobile device (viewport ≤768px), **when** they open an urgent STAT study, **then** I observe: (1) mobile-optimized viewer layout loads (single-column, touch-friendly controls), (2) basic diagnostic viewing is available (window/level, zoom, scroll), (3) advanced tools (MPR, 3D reconstruction) are disabled with tooltip "Available on desktop", (4) report creation is limited to structured findings template only. | VE + AT | Browser viewport set to 375×667 (iPhone SE); viewer renders in single-column; advanced tools show tooltip; report editor limited to template |
| AC-R18-09-02 | FR-R18-17, NFR-R18-14 | **Given** the mobile viewer is accessed on iOS Safari 15+ and Android Chrome 90+, **when** the viewer initializes, **then** I observe: (1) first image loads within 5s on mobile network (4G), (2) touch gestures (pinch-zoom, swipe-navigate) work correctly, (3) no console errors related to unsupported features, (4) viewer controls are usable with touch targets ≥44px (Apple HIG). | AT + VE | BrowserStack or device emulation tested on iOS Safari 15+ and Android Chrome 90+; touch targets measured ≥44px; load time ≤5s on 4G |

**Validator Gate Verdict**: AC-R18-09 achieves acceptance criteria **only if** mobile viewer provides functional basic diagnostic viewing on STAT studies, advanced tools are gracefully degraded, and touch targets meet accessibility standards.

---

## AC-R18-10: Prior Studies Comparison & Reading Enhancements — PARTIAL (layout presets verifiable via `/reading-presets*`; priors/allergy/scenario templates GATED)

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R18-10-01 | FR-R18-18 | **Given** the teleradiologist opens a study for reading, **when** they click "Compare with Prior" button in the viewer toolbar, **then** I observe: (1) a side-by-side layout splits the viewer into left (current study) and right (prior study), (2) prior study is auto-selected based on same modality and body region, (3) synchronized scrolling is enabled (scrolling one pane scrolls the other), (4) window/level changes apply to both panes simultaneously, (5) a "Reset Comparison" button restores single-pane view. | VE + AT | DOM shows two viewer instances side-by-side; scroll events synchronized between panes; window/level state shared; reset button restores single pane |
| AC-R18-10-02 | FR-R18-18 | **Given** the teleradiologist is in side-by-side comparison mode, **when** they use keyboard shortcuts, **then** I observe: (1) Arrow keys scroll both panes simultaneously, (2) `C` key toggles comparison mode on/off, (3) `W` key applies window/level to both panes, (4) `R` key resets both panes to default zoom/pan. | AT + MT | Playwright keyboard event simulation; both panes respond to scroll/level/reset; toggle key `C` switches modes |
| AC-R18-10-03 | FR-R18-22 | **Given** the teleradiologist is using a multi-monitor setup, **when** they open the viewer settings, **then** I observe: (1) layout profile selector shows options for "2-monitor", "3-monitor", and "laptop single-screen", (2) selecting a profile reconfigures the viewer layout accordingly, (3) the selected profile is saved per user preference and restored on next login, (4) on laptop single-screen, the viewer auto-detects screen size and suggests the optimal layout. | VE + AT | Layout changes match selected profile; user preference persisted in localStorage/DB; auto-detection logic verified on different viewport sizes |
| AC-R18-10-04 | FR-R18-23 | **Given** the teleradiologist opens a study for a patient with known allergies or contrast reaction history, **when** the viewer loads, **then** I observe: (1) a prominent yellow warning banner appears at the top of the viewer reading "⚠ Patient Alert: [Allergy/Reaction]", (2) the banner is visually distinct from the critical finding red banner, (3) the banner persists across study navigation within the same patient, (4) clicking the banner expands to show full allergy/contrast history from the patient record. | VE + AT | Banner rendered with yellow background (#F59E0B) and dark text; contrast ≥4.5:1; banner persists on study navigation; expand shows full history |
| AC-R18-10-05 | FR-R18-24 | **Given** the teleradiologist opens a new study, **when** they access the hanging protocol selector in the viewer toolbar, **then** I observe: (1) templates are organized by category (Chest CT, Trauma Pan-Scan, Neuro Stroke), (2) selecting a template applies the corresponding window/level presets, viewport layout, and zoom level, (3) custom templates can be saved per user, (4) the most recently used template is pinned at the top of the selector. | VE + AT | Template categories displayed correctly; applying template changes viewport state; custom template save works; MRU template pinned |

**Validator Gate Verdict**: AC-R18-10 achieves acceptance criteria **only if** side-by-side comparison scrolls synchronously, multi-monitor profiles persist across sessions, patient allergy warnings are visually distinct from critical findings, and hanging protocol templates apply correctly.

---

## AC-R18-11: Turnaround Time Tracking & Secure Messaging — GATED (no per-study TAT UI, no clinician messaging)

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R18-11-01 | FR-R18-19 | **Given** a study has been assigned to the teleradiologist, **when** they open the study and begin drafting a report, **then** I observe: (1) a "Turnaround Time" timer starts from assignment timestamp, (2) the elapsed time is displayed in the viewer header (e.g., "Turnaround: 12min 34s"), (3) when the preliminary report is signed, the final turnaround time is recorded and displayed in the worklist, (4) the turnaround time is included in the R05 QA metrics dashboard. | VE + AT + PM | Timer starts on study open; elapsed time displayed in header; database records `turnaround_time` on report sign; QA dashboard shows the metric |
| AC-R18-11-02 | FR-R18-19, NFR-R18-05 | **Given** the teleradiologist is viewing the turnaround time tracker, **when** the report autosave fires, **then** I observe: (1) turnaround timer continues running without interruption, (2) autosave does not reset or pause the timer, (3) timer display updates smoothly (no flicker) during autosave. | AT | Timer state persists across autosave events; no timer reset on autosave; display updates smoothly |
| AC-R18-11-03 | FR-R18-21 | **Given** the teleradiologist has completed a report, **when** they click "Notify Referring Clinician", **then** I observe: (1) a secure messaging modal opens with recipient selector (showing referring clinicians for the patient), (2) message composer supports text formatting (bold, italic) and attachment of report PDF, (3) on send, the message is delivered via the secure messaging endpoint (`POST /api/v2/messages`), (4) the referring clinician receives a notification in their worklist. | AT + VE | Modal opens with recipient list; message API call succeeds; notification appears in R14 worklist; message content encrypted in transit |
| AC-R18-11-04 | FR-R18-21, SEC-R18-05 | **Given** the teleradiologist sends a secure message to a referring clinician, **when** the message is delivered, **then** I observe: (1) message content is encrypted (TLS 1.3), (2) PHI is not exposed in URL query parameters, (3) audit log records the message send event with sender ID, recipient ID, timestamp, and message metadata (not content), (4) the referring clinician can reply via the same secure channel. | AL + VE | Audit log entry created; no PHI in URLs; TLS confirmed via SSL Labs scan; reply thread visible in both R18 and R14 worklists |

**Validator Gate Verdict**: AC-R18-11 achieves acceptance criteria **only if** turnaround time tracking is accurate and non-disruptive during autosave, and secure messaging delivers encrypted messages with full audit logging.

---

## Excluded Scope / Out of Scope

The following are explicitly **NOT** covered by these acceptance criteria and are out of scope for R18 teleradiologist requirements:

### Out of Scope — Technical
1. **Built-in RIS functionality** — No scheduling, billing, or EMR integration beyond HL7/FHIR endpoints (v3.1 roadmap)
2. **AI/ML inference** — No automated preliminary reports, CAD, or segmentation (v3.2 roadmap)
3. **Native mobile apps** — No iOS/Android builds, PWA only
4. **Blockchain audit trail** — Audit logs in PostgreSQL only
5. **DICOM Print Management** — Not included
6. **VNA / XDS-I registry** — Not included

### Out of Scope — Clinical
1. **State medical license verification** — Policy enforcement outside PACS scope
2. **Teleradiology contract management** — Business operations outside PACS
3. **Peer review workflow** — Separate from preliminary review (shipped 2026-08-03 as QA-style review of final signed reports via `/peer-reviews*`, shared with R05)
4. **Teaching file capture** — R13 resident feature, not R18 teleradiologist priority

### Out of Scope — Operational
1. **Automated report signing** — All reports require explicit radiologist sign-off (no AI auto-sign)
2. **Direct modality control** — Read-only access, no MPPS control from remote
3. **Video conferencing** — Use Zoom/Teams separately, no built-in tele-consultation video
4. **Automated paging system integration** — Twilio/PagerDuty plugin architecture, not core feature in v1

### Out of Scope — Compliance (delegated to policy)
1. **Prior authorization** — RIS function, not PACS
2. **Billing code assignment** — RIS function
3. **Credentialing** — Hospital HR function, PACS stores credential verification flag only

---

## Quality Gate Summary

| Artifact | Completeness | Feasibility | Usability | Validator |
|----------|--------------|-------------|-----------|-----------|
| 01-user-requirements.md | ✅ All FR/NFR with IDs | ✅ Performance quantified | ✅ Error/empty states specified | ✅ APIs mapped to shipped v2 endpoints vs 7 flagged |
| 02-workflow-maps.md | ✅ 5 workflows with Mermaid | ✅ All states (loading/error/success) | ✅ Friction points flagged | ✅ Integration touchpoints mapped |
| 03-user-stories.md | ✅ 12 stories with Given/When/Then | ✅ Dependencies listed | ✅ A11y + performance ACs | ✅ 4-phase priority order |
| 04-ui-ux-requirements.md | ✅ 10 screens, all 6 states per component | ✅ Tokens referenced | ✅ Keyboard nav specified | ✅ Contrast ratios measured |
| 05-metrics-slas.md | ✅ 70 metrics, 10 SLAs | ✅ Measurement method specified | ✅ Dashboards assigned | ✅ 3-tier SLA definitions |
| 06-acceptance-criteria.md | ✅ 11 AC groups, FR/NFR mapping | ✅ Verification methods (AT/VE/PM/AL) | ✅ Observable outcomes | ✅ Validator gate per AC group |

**Overall Verdict**: From the visual evidence, structured requirements, and measurable acceptance criteria, I observe the R18 Teleradiologist requirements package — **Goal ACHIEVED** with the following conditions:

1. **Shipped (2026-08-03, merge 4d136e0)**: SSO/OAuth/OIDC + tenant switching, preliminary→final reporting (draft → preliminary → final + sign), reading worklist, peer review, reading presets, viewer parity — the formerly-flagged reporting/SSO API work now exists.
2. **7 new API endpoints still required** (flagged in FR-R18 requirements): teleradiology worklist (site/assignment filters), critical-findings escalation, offline packages, consultations, prefetch, multi-site dashboard aggregates — must be designed and implemented before the telerad-specific workflows are functional.
3. **WebSocket real-time sync** — `/ws` endpoint shipped; teleradiology-specific worklist channels require LISTEN/NOTIFY extension.
4. **Offline package generation** — requires background job queue (Celery/Redis) and encryption key management.
5. **Critical finding escalation** — requires third-party integration (Twilio/PagerDuty) plugin architecture.

**Next Steps**:
1. Delegate API contract design to `frontend-to-backend-requirements` skill (escalation, offline packages, consultations, prefetch)
2. Delegate RESTful resource design to `rest-api-design` skill
3. Schedule stakeholder review of open questions (4 still open in README.md; 3 resolved 2026-08-03)
4. Prioritize Phase 1 user stories (US-R18-01, 02, 03, 04, 05, 08) — reporting/SSO slices now unblocked
5. Conduct usability testing with 2-3 teleradiologists before full implementation
