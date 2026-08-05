# Acceptance Criteria — Front Desk / Receptionist (R08)

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R08-01 | FR-R08-01 | Given ≥2 search characters, when I submit a search, then matches render with name/MRN/DOB within 500ms and a dedup warning appears if any match exists | Automated E2E + synthetic probe | Must pass 6.4 |
| AC-R08-02 | FR-R08-02 | Given a valid new patient form, when I submit, then a patient record is created, a success state renders within 500ms, and an ADT sync-pending indicator appears | Automated E2E | Must pass 6.4 |
| AC-R08-03 | FR-R08-03 | Given an open visit, when I add an order, then procedure, indication, referring physician, and urgency persist and link to the visit | Automated E2E | Must pass 6.4 |
| AC-R08-04 | FR-R08-04 | Given a modality/date selection, when availability loads, then open slots show modality/room/technologist and conflicts are flagged; a taken slot at confirm returns a conflict with refreshed availability | Automated E2E | Must pass 6.4 |
| AC-R08-05 | FR-R08-05 | Given a scheduled visit, when I check the patient in, then status becomes checked-in and is visible to clinical roles within 5s | Automated E2E + WebSocket probe | Must pass 6.4 |
| AC-R08-06 | FR-R08-06 | Given required consent types, when I open the forms list, then each shows attached/missing; uploading a scan attaches within 2s | Automated E2E | Must pass 6.4 |
| AC-R08-07 | FR-R08-07 | Given insurance fields, when I save, then policy/guarantor/authorization data persists and missing authorization is flagged on the visit | Automated E2E | Must pass 6.4 |
| AC-R08-08 | FR-R08-08 | Given a registered patient, when I print labels, then armband/requisition documents render with name, MRN, DOB, accession | Manual verification | Must pass 6.4 |
| AC-R08-09 | FR-R08-09 | Given patients in the queue, when the board renders, then statuses and destinations update within 5s and the board shows initials only | Automated E2E | Must pass 6.4 |
| AC-R08-10 | FR-R08-10 | Given the shared waiting-area view, when it renders, then no full PHI appears; full identifiers require an authenticated detail action | Visual evidence | Must pass 6.4 |
| AC-R08-11 | NFR-R08-01 | Given the registration screen, when measured, then LCP ≤ 2.5s and INP ≤ 200ms on a mid-tier device | Lighthouse CI, RUM | Must pass 6.4 |
| AC-R08-12 | NFR-R08-06 | Given every form control, when audited, then keyboard operability, focus rings, and contrast ≥ 4.5:1 pass WCAG 2.2 AA | axe-core CI + manual | Must pass 6.4 |
| AC-R08-13 | NFR-R08-02 | Given a patient search, when measured, then server round-trip ≤ 500ms p95 | Synthetic probe | Must pass 6.4 |
| AC-R08-14 | NFR-R08-03 | Given a registration submit, when measured, then optimistic save completes ≤ 500ms | Backend timing | Must pass 6.4 |
| AC-R08-15 | NFR-R08-04 | Given offline entry, when connectivity returns, then queued submissions sync within 2min | Synthetic offline test | Must pass 6.4 |
| AC-R08-16 | NFR-R08-05 | Given a form submit, when it completes, then explicit success or inline error feedback renders | Automated E2E | Must pass 6.4 |

## Excluded Scope / Out of Scope

- Billing / payment collection (R09) — receptionist captures insurance only.
- Scheduling board administration, staffing, and conflicts across modalities (R04).
- Any clinical reading, image interpretation, or report access (R12).
- Patient care during the exam — prep, vitals, contrast (R11).
- Insurance claim submission and payment reconciliation (R09).
