# Backend Requirements: R09 Radiology Service Cashier

## Context

The Cashier collects payments, records invoices and receipts, tracks insurance
claim status, performs cash reconciliation, and processes refunds/adjustments.
Read-only clinical context (scheduled/ordered procedures) is required to bill,
but **never images or reports** (HIPAA minimum necessary). No billing module
exists in the codebase — this role is fully GATED.

**Screens (existing)**: none — cashier accounts currently have only the Files
study browser + patient page in read-only mode.

**Screens (new/planned — all GATED on a billing backend)**: Invoice & Payment
Records, Payment Collection, Receipts, Insurance Claim Status, Cash
Reconciliation, Refunds & Adjustments, Price Quotes, Payment Plans.

**Personas**: P9 (Cashier). **Access tier**: billing
read/write + read-only clinical context (`PATIENT_READ`, proposed `BILL_*`).

## Screens/Components

### Invoice & Payment Records

**Purpose**: View a patient's invoices, payments, balances, and history.

**Data I need to display**: invoices (status: open / partially paid / paid /
written off), payment history, remaining balance.

**Actions**: filter by status, open a record, drill into payment detail.

**States to handle**: loading, empty, error with retry, zero-balance state.

### Payment Collection

**Purpose**: Record payments in cash, card, or check.

**Data I need**: payment method, amount, date, operator; split/partial payment
support.

**Actions**: record payment (optimistic ≤500ms), print/e-mail receipt.

**Business rules affecting UI**: **PCI scope minimized** — no card number/PAN is
stored or transmitted through the PACS; payments are tokenized by an external
processor (the UI references a token, never raw card data).

### Receipts / Claims / Reconciliation / Refunds

**Purpose**: Post-payment operations and end-of-day controls.

**Data I need**: receipt reprints, claim submissions and status (submitted /
acknowledged / denied / appeal), end-of-day collected-vs-recorded variance,
refund approval workflow (above-threshold requires R01/R02 sign-off).

**Actions**: reprint receipt, flag denied claims, close shift with variance
report, process refund with reason + approval.

### Read-Only Clinical Context

**Purpose**: The minimum procedure/order context needed to bill.

**Data I need**: scheduled/ordered procedures, patient demographics scoped to
billing. **No images, no reports, no clinical findings.**

**Business rules affecting UI**: FR-R09-09/10 enforce minimum necessary; all
payment mutations are audited (who, what, when).

## Uncertainties

- [ ] **Entire billing module is GATED** — no billing, payment, invoice, claim,
  or reconciliation endpoints exist. Must be raised with backend.
- [ ] Insurance claim status is assumed to come from an external billing system
  — is there a local fallback (manual status entry)?
- [ ] Payment processor integration (tokenization) — has a vendor been selected?
- [ ] Refund approval threshold — is the workflow backend-enforced or
  UI-informational?
- [ ] Which permission slugs are proposed (`BILL_READ`/`BILL_WRITE`/`REFUND_*`)?

## Questions for Backend

- What is the roadmap for billing endpoints (invoices, payments, receipts,
  claims, reconciliation)?
- Is claim status a local table or a proxy to an external system?
- Does the UI need a "quote / estimated responsibility" endpoint, or is pricing
  configuration data available?

## Discussion Log

_(pending backend review)_
