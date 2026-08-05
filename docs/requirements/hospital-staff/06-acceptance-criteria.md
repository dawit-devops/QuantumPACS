# Acceptance Criteria — Other Hospital Staff (R19)

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R19-01 | FR-R19-01 | Given a scoped search, when I query by MRN/name, then permitted patients return within 500ms; out-of-scope queries return nothing and log the attempt | Automated E2E + audit scan | Must pass 6.4 |
| AC-R19-02 | FR-R19-02 | Given a finalized report, when opened, then it renders read-only with no edit/annotation controls; drafts are never visible | Automated E2E | Must pass 6.4 |
| AC-R19-03 | FR-R19-03 | Given orders exist, when the order tab opens, then each shows scheduled/in-progress/complete; empty state when none | Automated E2E | Must pass 6.4 |
| AC-R19-04 | FR-R19-04 | Given a permitted patient's report finalizes, when the event fires, then an in-app notification arrives within 60s with no PHI in the body | Notification probe | Must pass 6.4 |
| AC-R19-05 | FR-R19-05 | Given a study, when the viewer opens, then it renders read-only with all tools disabled; write actions blocked in UI and API | Automated E2E + API test | Must pass 6.4 |
| AC-R19-06 | FR-R19-06 | Given this role, when any mutation is attempted, then it is rejected with 403 and logged (0 mutations allowed) | Pen test + E2E | Must pass 6.4 |
| AC-R19-07 | FR-R19-07 | Given the portal on a mid-tier phone, when measured, then LCP ≤ 2.5s | Lighthouse CI, RUM | Must pass 6.4 |
| AC-R19-08 | FR-R19-08 | Given the scope model, when audited, then zero unrelated-patient reads occur | Audit scan | Must pass 6.4 |
| AC-R19-09 | FR-R19-09 | Given any patient access, when it occurs, then who/what/when is recorded | Audit log scan | Must pass 6.4 |
| AC-R19-10 | FR-R19-10 | Given a follow-up request, when submitted, then it routes to the radiology team and confirmation renders within 500ms | Automated E2E | Must pass 6.4 |
| AC-R19-11 | NFR-R19-04 | Given the portal, when audited, then WCAG 2.2 AA passes (keyboard, focus, contrast ≥ 4.5:1) | axe-core CI + manual | Must pass 6.4 |
| AC-R19-12 | NFR-R19-05 | Given all reads, when scanned, then no unauthorized patient data is returned | Pen test + audit scan | Must pass 6.4 |
| AC-R19-13 | NFR-R19-01 | Given the portal on a mid-tier phone, when measured, then LCP ≤ 2.5s | Lighthouse CI, RUM | Must pass 6.4 |
| AC-R19-14 | NFR-R19-02 | Given a patient lookup, when measured, then latency ≤ 500ms p95 | Synthetic probe | Must pass 6.4 |
| AC-R19-15 | NFR-R19-03 | Given a report finalize, when measured, then notification latency ≤ 60s | Notification probe | Must pass 6.4 |
| AC-R19-16 | NFR-R19-06 | Given this role, when any mutation is attempted, then 0 are possible via UI or API | Pen test + E2E | Must pass 6.4 |

## Excluded Scope / Out of Scope

- Full PACS administration (R01/R02).
- Diagnostic reading or reporting (R12/R18) — view-only results.
- Image acquisition (R06/R07), patient care documentation (R11), billing (R09).
- Any write, annotation, share creation, download, or report editing.
