# User Requirements — Radiology Service Cashier (R09)

**Version**: 1.0.0 (v3.0 scope)
**Status**: Draft
**Date**: 2026-08-02

## Functional Requirements

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-R09-01 | **Invoice & Payment Records**: View a patient's invoices, payments, balances, and payment history. Filter by status (open, partially paid, paid, written off). | Must | Billing records screen |
| FR-R09-02 | **Payment Collection**: Collect payments in cash, card, or check; support partial payments and split tenders. Record method, amount, date, and operator. | Must | PCI scope minimized — no card data stored |
| FR-R09-03 | **Receipts**: Generate a printable/e-mailable receipt on payment; support reprint of prior receipts. | Must | Receipts tied to payment record |
| FR-R09-04 | **Insurance Claim Status**: View claim submissions and their status (submitted, acknowledged, denied, appeal). Flag denials requiring action. | Should | Claims data from billing system |
| FR-R09-05 | **Cash Reconciliation**: End-of-day reconciliation of collected vs. recorded payments; flag variances. | Must | Shift close workflow |
| FR-R09-06 | **Refunds & Adjustments**: Process refunds and balance adjustments with a recorded reason and approval workflow. | Should | Requires approval for above-threshold refunds |
| FR-R09-07 | **Price Quotes & Estimates**: Show procedure pricing and estimated patient responsibility before service; record the quote given. | Should | Uses R08 insurance/authorization data |
| FR-R09-08 | **Payment Plans**: Set up a payment plan with installments and due dates; track status. | Could | Requires billing engine support |
| FR-R09-09 | **Read-Only Clinical Context**: View the scheduled/ordered procedures and visit context needed to bill (no images, no reports). | Must | HIPAA minimum necessary |
| FR-R09-10 | **PHI Minimum Necessary**: Billing screens must never display clinical findings; access to patient demographics is scoped to what billing requires. | Must | HIPAA §164.514(d) |

## Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-R09-01 | Billing screens load time | LCP ≤ 2.5s, INP ≤ 200ms | Lighthouse CI, RUM |
| NFR-R09-02 | Payment recording latency | ≤ 500ms optimistic update | Backend timing |
| NFR-R09-03 | Receipt generation | ≤ 1s from request | Backend timing |
| NFR-R09-04 | PCI scope | No card numbers/PAN stored; tokenized only | Security audit |
| NFR-R09-05 | Reconciliation accuracy | Zero unexplained variance at shift close | E2E + audit |
| NFR-R09-06 | WCAG 2.2 AA compliance | 100% (forms + receipts) | axe-core CI + manual |

## Codebase Status (verified 2026-08-03)

**GATED**: All FR-R09-NN billing requirements are aspirational v3.0 — no billing,
payment, invoice, claim, or reconciliation routes/endpoints exist. Cashier accounts
today have only Files/patient read-only views. Requires new backend billing module +
permissions flagged to backend. See artifacts 04/07/08.

## Assumptions & Constraints

- A1: Card payments are tokenized by an external payment processor; the PACS never stores PAN.
- A2: The cashier has read-only access to scheduled/ordered procedures, never to images or reports.
- A3: Refund approvals above a threshold require an R01/R02 admin sign-off.
- A4: Insurance claim status is sourced from an external billing system (future integration); local fallback is manual status entry.
- A5: All payment mutations are audited (who, what, when).
