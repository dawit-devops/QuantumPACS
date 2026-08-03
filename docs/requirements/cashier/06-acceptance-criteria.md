# Acceptance Criteria — Radiology Service Cashier (R09)

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R09-01 | FR-R09-01 | Given a patient, when billing opens, then invoices render with status and balance; empty state when none exist | Automated E2E | Must pass 6.4 |
| AC-R09-02 | FR-R09-02 | Given an open invoice, when a partial/split payment is entered, then balance updates optimistically and the payment persists within 500ms | Automated E2E + backend timing | Must pass 6.4 |
| AC-R09-03 | FR-R09-03 | Given a completed payment, when a receipt is requested, then it generates within 1s and is printable/e-mailable and reprintable | Automated E2E | Must pass 6.4 |
| AC-R09-04 | FR-R09-04 | Given claims exist, when the claim list renders, then each shows status and denials are flagged | Automated E2E | Must pass 6.4 |
| AC-R09-05 | FR-R09-05 | Given shift close, when counted cash is entered, then totals and variance render and a non-zero variance requires a reason | Automated E2E | Must pass 6.4 |
| AC-R09-06 | FR-R09-06 | Given an above-threshold refund, when submitted, then it enters an approval queue and is not applied until approved | Automated E2E | Must pass 6.4 |
| AC-R09-07 | FR-R09-07 | Given a procedure, when a quote is requested, then pricing and estimated responsibility render and the quote is recorded | Automated E2E | Must pass 6.4 |
| AC-R09-08 | FR-R09-08 | Given a payment plan request, when configured, then installments and due dates persist and status tracks | Automated E2E | Must pass 6.4 |
| AC-R09-09 | FR-R09-09 | Given billing context, when opened, then only scheduled/ordered procedures render; no images or reports are accessible | Automated E2E + visual evidence | Must pass 6.4 |
| AC-R09-10 | FR-R09-10 | Given a billing screen, when audited, then no clinical findings render and demographics access is scoped | Security audit + visual evidence | Must pass 6.4 |
| AC-R09-11 | NFR-R09-01 | Given billing screens, when measured, then LCP ≤ 2.5s and INP ≤ 200ms | Lighthouse CI, RUM | Must pass 6.4 |
| AC-R09-12 | NFR-R09-04 | Given a card payment, when processed, then no PAN is stored in PACS; only a processor token persists | Security audit | Must pass 6.4 |
| AC-R09-13 | NFR-R09-02 | Given a payment submit, when measured, then optimistic update completes ≤ 500ms | Backend timing | Must pass 6.4 |
| AC-R09-14 | NFR-R09-03 | Given a receipt request, when measured, then generation completes ≤ 1s | Backend timing | Must pass 6.4 |
| AC-R09-15 | NFR-R09-05 | Given a shift close, when measured, then reconciliation completes with zero unexplained variance | E2E + audit | Must pass 6.4 |
| AC-R09-16 | NFR-R09-06 | Given billing screens, when audited, then WCAG 2.2 AA passes (keyboard, focus, contrast ≥ 4.5:1) | axe-core CI + manual | Must pass 6.4 |

## Excluded Scope / Out of Scope

- Clinical image viewing, reports, or interpretation (R12).
- Insurance authorization capture (R08) — cashier reads it, does not create it.
- Denial appeal submission (external billing system, future).
- Payment processor administration and merchant account management (R01).
