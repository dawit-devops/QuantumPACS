# UI/UX Requirements — Radiology Service Cashier (R09)

## Role-Based Routing & Navigation (Presentation Layer)

RBAC drives the presentation layer (`hasPermission()` + `RequirePermission`, gated
`Sidebar.tsx` items). Verified against `frontend/src/`.

### Routes Accessible (codebase reality)

| Route | Screen | Access rule |
|-------|--------|-------------|
| `/` | Files / study search (read) | Any authenticated user |
| `/account` | Account | Any authenticated user |
| Billing / payments / receipts / claims | **Not accessible** | No billing routes or endpoints exist — GATED |

### Navigation Gating (Sidebar.tsx)

| Menu item | Visible when |
|-----------|--------------|
| Files / Account / Notifications | Always (authenticated) |
| Admin submenu | Only if granted admin `*_READ` perms (cashier typically none) |

### Functionality Gating

- **None of the cashier screens exist**: payment collection, invoice/payment
  records, insurance claim status, receipts, cash reconciliation. All aspirational
  FRs marked `GATED` (artifacts 01/07/08) — new endpoints + permissions flagged to
  backend.
- Today a cashier account can only browse files/patients read-only.

## Screens & Navigation

| # | Screen | Entry Point | Purpose |
|---|--------|-------------|---------|
| 1 | Invoice Search | Sidebar / Home | Find patient + invoice |
| 2 | Invoice Detail | Search → invoice | Balance, payment history, claims |
| 3 | Payment Entry | Invoice → "Collect Payment" | Method, amount, split tender |
| 4 | Receipt | Payment success | Print / email / reprint |
| 5 | Claims | Invoice → Claims | Claim status list + denials |
| 6 | Reconciliation | Sidebar → Shift Close | End-of-day totals + variance |

Navigation: search-first; invoice → payment → receipt as a linear flow.

## Component & State Spec

| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| InvoiceTable | Rows | Skeleton | "No invoices" | Retry | — | — |
| BalanceCard | Balance | Spinner | "No balance" | Retry | Updated balance | — |
| PaymentForm | Method + amount | Spinner | — | Decline/retry message | Payment recorded | During processing |
| ReceiptModal | Receipt | Spinner | — | Retry print | Printed/emailed | — |
| ClaimTable | Rows | Skeleton | "No claims" | Retry | — | — |
| ReconciliationPanel | Totals | Spinner | "No payments" | Retry | Variance result | On close |

## Design System Conformance

- Tokens: `--color-success` (paid), `--color-danger` (denied/variance), `--color-warning` (partially paid), `--bg-surface`, `--radius-sm`.
- Components: reuse `Table`, `Form`, `Modal`, `Statistic`, `Tag`, `Popconfirm`; new `PaymentForm` and `ReconciliationPanel` specs.

## Accessibility Requirements

- WCAG 2.2 AA: keyboard-only payment flow, focus management on modal open/close, contrast ≥ 4.5:1, screen-reader announcements for payment success/decline, no time-limited actions without warning.

## Responsive Behavior

- Desktop-first for cashier stations; receipt view print-optimized (A6/A5) with `@media print` styles.
- Tablet allowed for bedside payment collection.

## UX Principles Applied

- Idempotent payment actions with visible "processing" state; running balance feedback; explicit decline recovery; variance reason capture at close; PCI-aware UX (no PAN entry fields in PACS).
