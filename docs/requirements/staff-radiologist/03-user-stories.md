# User Stories — Staff Radiologist (R12)

Priority: Must | Should | Could | Won't. Acceptance criteria are observable and
performance-budgeted per the frontend-developer lens.

---

## US-R12-01: Priority-Sorted Reading Worklist
**Story**: As a staff radiologist, I want a worklist sorted by priority with STAT first, so that urgent studies are read first.
**Priority**: Must

### Acceptance Criteria
- **Given** I open the worklist, **when** it loads ≤ 2s p90, **then** studies are sorted STAT → routine with modality, patient, exam, and time visible.
- **Given** a new STAT study arrives, **when** the worklist refreshes (≤ 30s staleness), **then** it moves to the top and the read state is unclaimed.
- **Given** a study is claimed by a colleague, **when** I see it, **then** the holder is visible and I can open it read-only.
- **Given** ES is down, **when** the worklist loads, **then** it still works (no dependency on search).
- **Accessibility**: list rows keyboard-navigable; sort not conveyed by color alone.
- **Performance**: NFR-R12-03 ≤ 2s p90.

### Dependencies
- `GET /worklist`, `GET/PUT /worklist/{id}`; notification wiring for STAT arrivals (GAP)

---

## US-R12-02: Open Study in Viewer Fast
**Story**: As a staff radiologist, I want the study to open quickly, so that reading throughput stays high.
**Priority**: Must

### Acceptance Criteria
- **Given** I open a study, **when** I select it, **then** the first instance renders ≤ 2s p90 on LAN and the viewer is ready for input immediately.
- **Given** a large series, **when** it loads, **then** progressive loading renders the first image before the rest, with a loading indicator for remaining frames.
- **Given** an instance fails to fetch, **when** it fails, **then** the viewer skips it with a visible failed-instance badge and continues.
- **Performance**: NFR-R12-01; pan/zoom smooth at 60fps (NFR-R12-05).

### Dependencies
- `GET /dicomweb/studies/{uid}/series`, `.../instances`, `GET /wado`; existing `ProgressiveLoading` pattern

---

## US-R12-03: Keyboard-First Viewer Tools
**Story**: As a staff radiologist, I want full keyboard access to viewer tools, so that I can read without touching the mouse.
**Priority**: Must

### Acceptance Criteria
- **Given** the viewer is open, **when** I press keys 1–7/E, **then** pan, length, rectangle ROI, ellipse ROI, angle, arrow, and eraser select immediately (per `KeyboardShortcuts.tsx`).
- **Given** I use window/level, **when** I adjust, **then** the change applies to the current series and is stable across instances in the series.
- **Given** a tool is active, **when** I use arrow keys / page up-down, **then** series navigation works in parallel (no tool/navigation conflict).
- **Given** a shortcut conflicts, **when** I check the help, **then** a shortcut map is one key away.
- **Accessibility**: all tools have visible focus indicators and screen-reader labels in toolbars.
- **Performance**: tool switch + interaction INP ≤ 200ms p75.

### Dependencies
- `KeyboardShortcuts.tsx`, `viewer/tools.ts`, CornerstoneElement

---

## US-R12-04: Measurements Persist
**Story**: As a staff radiologist, I want my measurements/annotations to persist across sessions, so that follow-up reads keep context.
**Priority**: Should

### Acceptance Criteria
- **Given** I annotate a study, **when** I reopen it later, **then** the annotations load with the same positions and labels.
- **Given** annotations sync client-side, **when** multiple viewers open the study, **then** updates propagate without conflicting duplicates.
- **Given** I delete an annotation, **when** I reopen, **then** it stays deleted.
- **Performance**: annotation load does not delay first image render (parallel fetch).

### Dependencies
- `viewer/useAnnotationSync.ts`; **GAP: confirm persistence endpoint**

---

## US-R12-05: Priors at One Action
**Story**: As a staff radiologist, I want priors one action away, so that I can compare with previous exams efficiently.
**Priority**: Should

### Acceptance Criteria
- **Given** I am reading a study, **when** I invoke priors, **then** a priors list (modality, date, body part) appears without leaving the viewer.
- **Given** the patient has no priors, **when** I invoke it, **then** a clear empty state says "No priors" without erroring.
- **Given** I select a prior, **when** it loads, **then** it opens side-by-side with synced window/level and pan.
- **Given** the priors list times out, **when** it fails, **then** an inline retry appears and the current reading continues.
- **Performance**: priors list ≤ 2s p90.
- **Note**: GAP — confirm priors loading endpoint (search-based today).

### Dependencies
- Study browser/search; viewer layout sync

---

## US-R12-06: Structured Reporting
**Story**: As a staff radiologist, I want structured reporting with templates and autosave, so that reports are fast and consistent.
**Priority**: Must (gated on backend)

### Acceptance Criteria
- **Given** I open the report panel, **when** it loads, **then** findings and impression editors are available with modality templates.
- **Given** I type, **when** autosave runs (≤ 10s cadence), **then** drafts persist and no explicit save is needed.
- **Given** I sign, **when** I confirm, **then** the report becomes final, is audit-logged, and its status shows in the worklist.
- **Given** the connection drops mid-edit, **when** it recovers, **then** the local draft syncs without loss.
- **Given** another radiologist edits concurrently, **when** a conflict occurs, **then** a clear overwrite/merge choice is presented.
- **Accessibility**: editors have labelled fields; status changes announced.
- **Performance**: report panel load ≤ 2s; autosave invisible to interaction.
- **GATED**: no reporting API exists — backend required.

### Dependencies
- **GAP: `GET/PUT /api/v2/reports/{study_uid}`, `POST .../sign`, templates API**

---

## US-R12-07: Critical Findings Escalation
**Story**: As a staff radiologist, I want to escalate critical findings in two keystrokes, so that referring clinicians are alerted immediately.
**Priority**: Should (gated)

### Acceptance Criteria
- **Given** I identify a critical finding, **when** I press the escalate action, **then** a minimal confirm (severity + referring clinician) appears — no long forms.
- **Given** I confirm, **when** it succeeds, **then** the referring clinician is notified (portal/EMR) and the status is tracked until acknowledged.
- **Given** escalation fails, **when** it errors, **then** an explicit error with manual fallback instructions is shown (never silent).
- **Accessibility**: escalation reachable by keyboard.
- **GATED**: notification/escalation endpoint wiring needed.

### Dependencies
- Notifications; R14 clinician portal; EMR/RIS delivery (R16)

---

## US-R12-08: Resident Draft Review
**Story**: As a staff radiologist, I want to review resident drafts with annotations intact, so that supervision is efficient.
**Priority**: Should (gated)

### Acceptance Criteria
- **Given** a resident submits a draft, **when** the worklist refreshes, **then** it shows "awaiting attending review" with the resident's name.
- **Given** I open the draft, **when** I review, **then** the resident's annotations/report are intact and editable.
- **Given** I approve, **when** I sign, **then** the review completes, is audit-logged (draft → reviewed → signed), and status updates.
- **GATED**: reporting API.

### Dependencies
- R13 workflow; reporting API

---

## US-R12-09: Share for Consultation
**Story**: As a staff radiologist, I want to share studies with colleagues, so that consultations are quick.
**Priority**: Should

### Acceptance Criteria
- **Given** I share a study, **when** I choose a permission level, **then** read-only or annotation access is granted and the link works.
- **Given** the share expires or is revoked, **when** the colleague opens it, **then** a clear access-denied state appears.
- **Given** shared annotations are allowed, **when** the colleague adds them, **then** they merge without corrupting mine.
- **Accessibility**: share dialog keyboard-operable.
- **Performance**: share creation ≤ 2s.

### Dependencies
- `POST /files/{id}/share`, `GET /files/{id}/shares`, `Share.tsx`

---

## US-R12-10: Claim and Manage Read States
**Story**: As a staff radiologist, I want to claim studies and see others' claims, so that no study is read twice.
**Priority**: Should

### Acceptance Criteria
- **Given** I claim a study, **when** I do, **then** the state changes to claimed-by-me and other users see the holder.
- **Given** I complete a study, **when** I mark done, **then** the state updates and the report status becomes visible.
- **Given** two users claim simultaneously, **when** a conflict occurs, **then** one gets a conflict prompt and the state reloads.
- **Accessibility**: state changes keyboard-reachable.
- **Performance**: state update ≤ 1s.

### Dependencies
- `GET/PUT /worklist/{id}`; state semantics confirmed with backend

---

## US-R12-11: Study Metadata and Change History
**Story**: As a staff radiologist, I want metadata and change history, so that I can verify study provenance before reading.
**Priority**: Must

### Acceptance Criteria
- **Given** I open a study's detail, **when** it loads, **then** DICOM metadata (patient, study, series, instances) renders in a readable table.
- **Given** metadata changed, **when** I view history, **then** a change log with actor/timestamp is shown.
- **Given** I need to verify provenance, **when** I inspect, **then** key DICOM identifiers (UIDs) are copyable.
- **Accessibility**: key-value table readable by screen readers.
- **Performance**: detail load ≤ 2s p90.

### Dependencies
- `Detail.tsx`, `Changes.tsx`, `GET /files/{id}/changes`

---

## US-R12-12: Reading Presets
**Story**: As a staff radiologist, I want to save window/level and layout presets per modality, so that setup time is minimal.
**Priority**: Could

### Acceptance Criteria
- **Given** I configure window/level for a modality, **when** I save a preset, **then** it applies automatically when opening that modality.
- **Given** presets exist, **when** I open a study, **then** the saved preset applies before I touch controls.
- **Given** I edit a preset, **when** saved, **then** it persists for future sessions.
- **Performance**: preset application adds ≤ 100ms to study open.

### Dependencies
- Viewer state; preset persistence (GAP: endpoint or localStorage — confirm)
