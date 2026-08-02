# User Requirements — Radiology Trainee/Resident (R13)

**Version**: 1.0.0 (v3.0 scope)
**Status**: Draft
**Date**: 2026-08-02

---

## Functional Requirements

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-R13-01 | **Supervised Reading Worklist**: Display a filtered, paginated worklist of studies assigned to the resident for supervised reading. Columns: Accession, Patient (initials), Modality, Protocol, Priority, Assigned Attending, Status (pending/in_review/completed). Auto-refresh every 30s via WebSocket. STAT studies highlighted with red left border. | Must | Extends existing worklist with attending assignment and supervision status |
| FR-R13-02 | **Study Interpretation with Attending Guidance**: Allow the resident to open a study for interpretation with the assigned attending's preliminary notes and suggested areas of focus displayed. Provide a split-screen view: resident's findings panel on left, attending guidance on right. Resident can toggle attending guidance visibility. | Must | New `SupervisedViewer` component; attending guidance from R12 |
| FR-R13-03 | **Draft Report Creation**: Enable resident to create a draft report with structured findings, impression, and recommendations sections. Draft report is marked with "DRAFT — Awaiting Attending Review" badge. Auto-save every 10s (optimistic update). Word count and completeness indicator for each section. | Must | New `DraftReportEditor` component; feeds attending review queue |
| FR-R13-04 | **Attending Review and Sign-Off Workflow**: When resident submits draft report, assigned attending (R12) receives notification and can: (1) review findings side-by-side with resident's draft, (2) add comments/amendments inline, (3) approve and co-sign, (4) return for revision with specific feedback. Resident receives notification with attending feedback. | Must | Cross-role R13↔R12; notification via WebSocket |
| FR-R13-05 | **Teaching File Capture**: Allow resident to capture a teaching case from any study they've interpreted. Teaching file entry includes: de-identified images (selected key images), resident's findings, attending's feedback, diagnosis, differential diagnosis, key learning points, and tags (anatomy, pathology, modality). Resident can submit for attending approval before adding to teaching library. | Must | New `TeachingFileCapture` component; de-identification required |
| FR-R13-06 | **Exam List Management**: Display a personal exam log for the resident showing all studies interpreted, with filters: date range, modality, body part, diagnosis, attending, and review status. Export to CSV for portfolio/educational requirements. Include metrics: interpretation time, draft-to-final turnaround, attending revision rate. | Must | Personal portfolio; exports for residency program requirements |
| FR-R13-07 | **Performance Feedback Dashboard**: Display resident-specific metrics: number of studies interpreted by modality/body part, average interpretation time, attending agreement rate (percentage of drafts approved without major changes), common feedback themes, and progress toward rotation milestones. Attending can add private notes/feedback per study. | Should | Educational analytics; feeds residency program evaluation |
| FR-R13-08 | **On-Call Support Mode**: When resident is on call without immediate attending availability, provide a "Request Attending Consult" button that routes to the on-call attending (R12/R18). Attending receives priority notification and can join a synchronous screen-sharing session or provide written guidance within 15 minutes. | Should | Emergency fallback; integrates with R18 teleradiologist on-call |
| FR-R13-09 | **Protocol Learning Mode**: Display protocol details with educational annotations: why this protocol for this indication, key sequences and their purpose, common artifacts, normal variants, and red flags. Resident can mark protocols as "reviewed" and track learning progress. | Should | Educational content integrated into protocol selection |
| FR-R13-10 | **Case Conference Preparation**: Allow resident to tag studies for departmental case conferences. Tagged cases are compiled into a presentation-ready format with de-identified images, resident's draft findings, attending's final report, and discussion points. Export to PDF/PowerPoint. | Could | Teaching conference preparation; integrates with R03/R12 |

## Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-R13-01 | Worklist load time (LCP) | ≤ 2.0s | Lighthouse CI, RUM |
| NFR-R13-02 | Draft report auto-save latency | ≤ 300ms | Backend timing |
| NFR-R13-03 | Attending review notification latency | ≤ 5s | WebSocket message timestamp delta |
| NFR-R13-04 | Teaching file de-identification | ≤ 2s per case | Backend timing |
| NFR-R13-05 | Exam list export (CSV) | ≤ 5s for 500 studies | Backend timing |
| NFR-R13-06 | Worklist real-time sync staleness | ≤ 30s | WebSocket + DB trigger |
| NFR-R13-07 | WCAG 2.2 AA compliance | 100% (keyboard-intensive workflow) | axe-core CI + manual |
| NFR-R13-08 | Image preview latency | ≤ 500ms from acquisition | Frontend timing |
| NFR-R13-09 | Concurrent resident sessions | ≥ 10 simultaneous residents | k6 WebSocket scenario |
| NFR-R13-10 | Draft report completeness indicator | Real-time (≤200ms update) | Frontend timing |

## Codebase Status (verified 2026-08-03)

**GATED**: All FR-R13-NN resident/supervised-reading requirements are aspirational
v3.0 — no resident-specific functionality exists (no role distinction from R12
today); no supervised worklist, draft-report, attending-sign-off, teaching-file,
feedback, consult, or case-conference endpoints exist. Requires 6+ new endpoints
flagged to backend; depends on R12 reporting. See artifacts 04/07/08.

## Assumptions & Constraints

| # | Assumption / Constraint | Impact |
|---|-------------------------|--------|
| A1 | PHI: Patient initials and MRN last 4 digits shown on worklist; full PHI in study detail per HIPAA minimum necessary; teaching files MUST be fully de-identified | FR-R13-01, FR-R13-05 |
| A2 | 6 new API endpoints required (flagged for `frontend-to-backend-requirements`) | FR-R13-02, FR-R13-04, FR-R13-05, FR-R13-07 |
| A3 | Attending review workflow requires R12 to have a dedicated "Resident Review Queue" in their worklist | FR-R13-04, cross-role R12 |
| A4 | Teaching file de-identification must strip all PHI from images (burned-in annotations, DICOM tags) and metadata | FR-R13-05 |
| A5 | Resident-attending assignment is configured per rotation by R04 coordinator; many-to-one (multiple residents per attending) | FR-R13-01, FR-R13-04 |
| A6 | Draft reports are not visible to referring clinicians (R14) or patients (R19) until attending co-sign | FR-R13-03, FR-R13-04 |
| A7 | Resident performance data is visible to resident, their attending, and program director (R03); not visible to other residents | FR-R13-07 |
| A8 | On-call support mode integrates with R18 teleradiologist for after-hours coverage | FR-R13-08 |
| A9 | Protocol learning content is maintained by R12/R03; resident sees read-only educational annotations | FR-R13-09 |
| A10 | Case conference tagged studies require attending approval before inclusion | FR-R13-10 |