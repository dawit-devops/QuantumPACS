# Acceptance Criteria — Radiology Trainee/Resident (R13)

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R13-01 | FR-R13-01 | Given the resident worklist, when it loads, then assigned studies render with columns Accession, Patient (initials), Modality, Protocol, Priority, Assigned Attending, Status; STAT rows have a red left border; auto-refresh occurs within 30s | Automated E2E + WebSocket probe | Must pass 6.4 |
| AC-R13-02 | FR-R13-02 | Given an assigned study, when the supervised viewer opens, then a split-screen renders (viewer left, attending guidance right) with the attending's preliminary notes and focus areas; guidance toggles with 'G' key; empty state shows a placeholder and still allows interpretation | Automated E2E | Must pass 6.4 |
| AC-R13-03 | FR-R13-03 | Given the draft editor, when I pause typing 10s, then an auto-save indicator transitions Saving → Saved and the draft persists; when I submit, then status becomes Submitted, the draft locks, and the attending receives a notification within 5s | Automated E2E + backend timing | Must pass 6.4 |
| AC-R13-04 | FR-R13-04 | Given an attending review queue, when I open a draft, then side-by-side comparison renders (resident draft left, final report right) with inline comments; on Approve & Co-sign, then status becomes Final with signature appended and the resident is notified; on Return, then the draft unlocks with section feedback | Automated E2E | Must pass 6.4 |
| AC-R13-05 | FR-R13-05 | Given a completed interpretation, when I capture a teaching case, then the editor pre-populates with key images, findings, and feedback; on submit, then status is Pending Approval; on approval, then the case publishes de-identified (no PHI in images or metadata) | Automated E2E + PHI scan | Must pass 6.4 |
| AC-R13-06 | FR-R13-06 | Given the exam list, when it loads, then a filterable, paginated table renders with date, accession, modality, body part, diagnosis, attending, review status, and interpretation time; CSV export completes within 5s for 500 studies | Automated E2E + backend timing | Must pass 6.4 |
| AC-R13-07 | FR-R13-07 | Given the feedback dashboard, when it loads, then charts render (by-modality bar, interpretation-time trend, agreement gauge, feedback themes); private attending feedback entries appear; tablet layout stacks charts readably; R03 sees cohort comparison | Automated E2E + visual evidence | Must pass 6.4 |
| AC-R13-08 | FR-R13-08 | Given an on-call consult request, when submitted, then the on-call attending (R12/R18) receives a priority notification and a consult banner renders with estimated response; a response arrives within 15min | Escalation probe + E2E | Must pass 6.4 |
| AC-R13-09 | FR-R13-09 | Given a protocol panel, when opened, then educational annotations render (indication, key sequences, artifacts, variants, red flags); Mark as Reviewed persists with a timestamp and the learning progress updates | Automated E2E | Must pass 6.4 |
| AC-R13-10 | FR-R13-10 | Given tagged cases, when I generate a presentation, then a de-identified PDF/PowerPoint exports with images, findings, final report, diagnosis, and discussion points; attending approval required before conference inclusion | Automated E2E | Must pass 6.4 |
| AC-R13-11 | NFR-R13-01 | Given the worklist, when measured, then LCP ≤ 2.0s | Lighthouse CI, RUM | Must pass 6.4 |
| AC-R13-12 | NFR-R13-02 | Given a draft auto-save, when measured, then latency ≤ 300ms | Backend timing | Must pass 6.4 |
| AC-R13-13 | NFR-R13-03 | Given a submitted draft, when measured, then the attending notification latency ≤ 5s | WebSocket delta | Must pass 6.4 |
| AC-R13-14 | NFR-R13-04 | Given a teaching file, when measured, then de-identification ≤ 2s per case | Backend timing | Must pass 6.4 |
| AC-R13-15 | NFR-R13-05 | Given an exam-list export, when measured, then CSV completes ≤ 5s for 500 studies | Backend timing | Must pass 6.4 |
| AC-R13-16 | NFR-R13-06 | Given the worklist, when measured, then real-time sync staleness ≤ 30s | WebSocket + DB trigger | Must pass 6.4 |
| AC-R13-17 | NFR-R13-07 | Given the resident UI, when audited, then WCAG 2.2 AA passes (keyboard operability, focus, contrast ≥ 4.5:1, ARIA) | axe-core CI + manual | Must pass 6.4 |
| AC-R13-18 | NFR-R13-08 | Given an image preview, when measured, then latency ≤ 500ms from acquisition | Frontend timing | Must pass 6.4 |
| AC-R13-19 | NFR-R13-09 | Given concurrent residents, when loaded, then ≥ 10 simultaneous sessions operate correctly | k6 WebSocket scenario | Must pass 6.4 |
| AC-R13-20 | NFR-R13-10 | Given draft typing, when measured, then the completeness indicator updates ≤ 200ms | Frontend timing | Must pass 6.4 |

## Excluded Scope / Out of Scope

- Independent (unsupervised) reading and final report sign-off — resident drafts require attending co-sign (FR-R13-04).
- Draft reports visible to referring clinicians (R14) or patients (R19) before attending approval.
- Administrative role management, tenant config, or system administration (R01/R02).
- Modality image acquisition (R06/R07).
- Billing (R09).
- AI/CAD-assisted teaching features (v3.2+).
