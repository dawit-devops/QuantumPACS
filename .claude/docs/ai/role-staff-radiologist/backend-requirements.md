# Backend Requirements: R12 Staff Radiologist

## Context

The Staff Radiologist is the primary diagnostic reader: high-volume reading
sessions, keyboard-heavy, relies on priors, measurements, and reporting. Uses the
existing clinical viewer (Detail page, Cornerstone3D), study browser, worklist,
patient page, share links, audit history, and measurement panel — all built. The
**largest gap is structured reporting**: no report create/render/sign endpoints
exist yet. Annotation persistence and critical-findings escalation are also
open.

**Screens (existing)**: Detail/Viewer (Image, Data, Share, Changes, Admin tabs),
Study Browser (DICOMweb), Worklist, Patient page, Measurement panel.
**Screens (new/planned)**: Report Editor + sign-off, Resident Review Queue,
Peer Review inbox (with R05).

**Personas**: P1 (Radiologist). **Access tier**: clinical reading
(`STUDY_READ`, `WORKLIST_READ`, `PATIENT_READ`, `FILE_READ`).

## Screens/Components

### Viewer / Detail (existing — see the `viewer/` feature doc)

**Data I need**: full patient → study → series → file hierarchy for breadcrumb
navigation; pixel data (WADO-RS + wadouri); per-file thumbnails; DICOM metadata
(key/value); annotations persisted per file (`tools_state`); share links; audit
changes.

**Actions**: open study, switch series/files, annotate (Length/Angle/Arrow/ROI),
export measurements CSV, create/revoke share links, view audit trail.

**Business rules affecting UI**:
- Annotation state is synchronized across open viewers via WebSocket
  (`send_state`) and persisted to the file record.
- Share tab hidden for anonymous share-link viewers.
- Admin tab only for `USER_ADMIN`.

### Worklist / Study Browser

**Data I need**: reading worklist (priority, modality, status), DICOMweb study
search (patient ID) with study → series → instance drill-down.

**Actions**: filter, open study, search.

### Reporting (GAP — new)

**Purpose**: Create, edit, and sign structured reports.

**Data I need (not yet available)**: report templates/impressions, report
create/draft/prelim/final state machine, sign-off, report retrieval for priors
and share views.

**Actions**: create draft report, edit structured sections (findings, impression,
recommendations), sign final, review resident drafts.

**States to handle**: draft / preliminary / final; report versions; sign-off
validation (missing impression blocks sign).

**Business rules affecting UI**: preliminary vs final states must be clearly
distinguished; co-sign workflows (with R13) need an attending review queue.

### Resident Review Queue (with R13)

**Data I need**: resident-submitted draft reports awaiting review, attending
guidance/feedback records.

**Actions**: open side-by-side, add comments/amendments, approve+co-sign, return
for revision.

### Peer Review Inbox (with R05)

**Data I need**: peer review assignments, original report + findings comparison.

**Actions**: perform QA read, submit findings with discrepancy level.

## Uncertainties
- [ ] **Structured reporting is the biggest gap** — no reporting endpoints exist.
  The entire report workflow is pending backend.
- [ ] Priors comparison: no explicit "load priors for patient" endpoint; currently
  depends on study search. Confirm intended behavior.
- [ ] Critical findings escalation: no escalation endpoint (stat alert to
  referring clinician) — likely notifications wiring needed.
- [ ] Annotation persistence: sync exists client-side; confirm the persistence
  endpoint and versioning semantics.
- [ ] Peer review: no review/quality workflow endpoints (R05-related).

## Questions for Backend
- What is the roadmap for report endpoints (create/sign/templates)? Everything
  clinical reporting depends on it.
- Should "load priors" be a dedicated endpoint or is study search + browser the
  intended path?
- Does saving annotations overwrite the whole tool state per file, and is there a
  conflict policy when two viewers edit simultaneously?

## Discussion Log

_(pending backend review)_
