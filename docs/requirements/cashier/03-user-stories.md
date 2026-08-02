# User Stories — Radiology Service Cashier (R09)

## US-R09-01: View invoices and balance
**Story**: As a cashier, I want to see a patient's invoices and running balance, so that I can collect the correct amount.
**Priority**: Must

### Acceptance Criteria
- **Given** a patient, **when** I open billing, **then** invoices render with status and balance within 2.5s LCP.
- **Given** no invoices exist, **when** the screen opens, **then** a meaningful empty state appears.
- **Accessibility**: keyboard-navigable table with focus indicators.

## US-R09-02: Collect a partial or split payment
**Story**: As a cashier, I want to record partial/split payments, so that patients can pay what they can today.
**Priority**: Must

### Acceptance Criteria
- **Given** an open invoice, **when** I enter a partial payment with method and amount, **then** the balance updates optimistically and the payment records within 500ms.
- **Given** a card payment is declined, **when** the processor returns an error, **then** nothing is recorded as paid and a retry with alternative methods appears.
- **Given** I double-submit, **then** an idempotency key prevents a duplicate charge.

## US-R09-03: Generate and reprint receipts
**Story**: As a cashier, I want to print a receipt and reprint past receipts, so that patients always have proof of payment.
**Priority**: Must

### Acceptance Criteria
- **Given** a completed payment, **when** I request a receipt, **then** it generates within 1s and prints/e-mails.
- **Given** a past payment, **when** I reprint, **then** the identical receipt renders.

## US-R09-04: Track insurance claim status
**Story**: As a cashier, I want to see claim status and denials, so that I can flag actions needed.
**Priority**: Should

### Acceptance Criteria
- **Given** claims exist, **when** I view the claim list, **then** each shows status and denials are flagged.
- **Given** a claim is denied, **when** I open it, **then** an "action required" indicator appears.

## US-R09-05: Close the shift with variance handling
**Story**: As a cashier, I want to reconcile collected vs recorded payments, so that my shift closes without discrepancy.
**Priority**: Must

### Acceptance Criteria
- **Given** I close my shift, **when** I enter counted cash, **then** expected totals render and a variance is computed.
- **Given** a non-zero variance, **when** I close, **then** a reason field is required before close completes.
- **Performance**: reconciliation renders ≤ 2s.

## US-R09-06: Process a refund with approval
**Story**: As a cashier, I want to process refunds with recorded reason and approval, so that adjustments are controlled.
**Priority**: Should

### Acceptance Criteria
- **Given** an above-threshold refund, **when** I submit it, **then** it enters an approval queue (R01/R02) and is not applied until approved.
- **Given** an approved refund, **when** processed, **then** the balance and payment history update.

## Dependencies
- US-R09-01..06 → billing endpoints (new)
- US-R09-04 → external claims feed (future) with manual fallback
- US-R09-02 → tokenized payment processor integration
