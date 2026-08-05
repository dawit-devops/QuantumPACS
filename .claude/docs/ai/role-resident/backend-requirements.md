# Backend Requirements: R13 Radiology Trainee/Resident

## Context

The Resident performs supervised reading: studies are assigned to them (with an
attending), they interpret with attending guidance, draft reports, and get
sign-off. Also manages a personal exam log/portfolio, teaching-file capture
(must be de-identified), and a performance feedback dashboard. Draft reports are
**not visible** to referring clinicians (R14) or patients until attending
co-sign — a hard visibility rule the frontend and backend must enforce together.

**Screens (new)**: Supervised Reading Worklist, Split-screen Interpretation
Viewer, Draft Report Editor, Attending Review workflow, Teaching File Capture,
Exam Log / Portfolio, Performance Feedback Dashboard, On-Call Consult, Protocol
Learning.

**Personas**: P1 (trainee). **Access tier**: supervised read/write
(worklist + draft reports + teaching files).

## Screens/Components

### Supervised Reading Worklist

**Purpose**: Filtered, paginated list of studies assigned to the resident.

**Data I need to display**: accession, patient initials, modality, protocol,
priority, assigned attending, supervision status
(pending/in_review/completed); auto-refresh (30 s / WebSocket); STAT highlight.

**Actions**: filter/sort, open study for interpretation.

**Business rules affecting UI**: per-rotation assignment (many residents per
attending) is configured by R04 — the worklist reflects it.

### Split-screen Interpretation Viewer

**Purpose**: Resident findings panel + attending guidance side-by-side.

**Data I need**: the study in the existing viewer, plus the assigned attending's
preliminary notes and suggested areas of focus.

**Actions**: toggle guidance visibility; capture findings.

### Draft Report Editor

**Purpose**: Structured draft report with auto-save.

**Data I need**: structured sections (findings, impression, recommendations),
draft state badge ("DRAFT — Awaiting Attending Review"), auto-save state
(10 s, optimistic), word-count/completeness indicator per section.

**Actions**: edit sections, submit for attending review.

**States to handle**: auto-save in-flight/saved/error; submit with missing
sections warning.

**Business rules affecting UI**: drafts are invisible to R14/R19 until co-sign.

### Attending Review Workflow

**Purpose**: Receiving attendings (R12) review and sign off.

**Data I need**: review status, attending comments/amendments, approval/revision
decision; notification when the attending acts.

**Actions**: view feedback, revise and resubmit.

### Teaching File Capture

**Purpose**: Build de-identified teaching cases.

**Data I need**: selected key images, resident findings, attending feedback,
diagnosis, differential, learning points, tags; **de-identified output** (burned-
in annotations + DICOM tags stripped).

**Actions**: capture case, submit for attending approval.

**States to handle**: de-identification in progress (≤2 s/case); PHI-scan warning.

### Exam Log / Portfolio

**Purpose**: Personal log with export for residency requirements.

**Data I need**: all interpreted studies with filters (date, modality, body part,
diagnosis, attending, review status) and metrics (interpretation time,
draft-to-final turnaround, revision rate).

**Actions**: filter, export CSV (≤5 s / 500 studies).

### Performance Feedback Dashboard

**Purpose**: Educational metrics visible to the resident, their attending, and
program director only.

**Data I need**: counts by modality/body part, average interpretation time,
attending agreement rate, common feedback themes, rotation milestones; private
attending notes per study.

### On-Call Consult / Protocol Learning / Case Conference

**Data I need**: on-call attending routing (R12/R18) with 15-min response SLA;
protocol learning annotations (read-only, maintained by R12/R03); case-conference
tags with de-identified export (PDF/PowerPoint).

## Uncertainties
- [ ] Draft report auto-save: is there a versioned draft resource, or a single
  overwritable draft per study?
- [ ] De-identification: what endpoint/service strips PHI (burned-in + tags), and
  is it async?
- [ ] Feedback dashboard visibility scope: how does the backend scope resident
  performance data to resident + attending + program director?
- [ ] On-call consult: is this a notification/routing flow, or does it need a
  synchronous session capability?
- [ ] Six new API endpoints were flagged by the package; none confirmed to exist.

## Questions for Backend
- What is the draft-report lifecycle relative to the (missing) R12 reporting
  endpoints — same resource, different state?
- For teaching files, is the de-identified copy a new study, or a separate
  artifact linked to the original?
- Should the resident worklist reuse the existing worklist contract with an
  added "assigned attending" + "supervision status", or is a dedicated endpoint
  cleaner?

## Discussion Log

_(pending backend review)_
