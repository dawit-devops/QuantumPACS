# End-to-End Workflow Maps — Radiology Service Cashier (R09)

## Workflow W1: Payment Collection (frequency: daily, criticality: high)

```mermaid
sequenceDiagram
    actor Cashier as Cashier
    participant UI as Billing UI
    participant API as Backend API
    participant DB as PostgreSQL
    participant PS as Payment Processor
    Cashier->>UI: Search patient / open invoice
    UI->>API: GET /billing/invoices?patient=
    API->>DB: query invoices + balance
    DB-->>API: invoices
    API-->>UI: 200 + invoice list + balance
    Cashier->>UI: Enter payment (method, amount, split)
    UI->>API: POST /billing/payments (tokenized card)
    API->>PS: charge (token)
    PS-->>API: result
    API->>DB: record payment + receipt
    API-->>UI: 201 + payment + receipt
    UI-->>Cashier: Success + printable receipt
```

### Friction & Cognitive Load Points
- Partial/split tenders add cognitive load — guided totals with running balance.
- Denied claims need clear "action required" cues.

### Error & Exception Paths
- Card declined → friendly retry with alternative methods; nothing recorded as paid.
- Double-click submit → idempotency key prevents duplicate charges.
- Print fails → reprint from payment history.

## Workflow W2: End-of-Day Reconciliation (frequency: daily, criticality: high)

```mermaid
sequenceDiagram
    actor Cashier as Cashier
    participant UI as Billing UI
    participant API as Backend API
    participant DB as PostgreSQL
    Cashier->>UI: Open shift close
    UI->>API: GET /billing/reconciliation (date, cashier)
    API->>DB: aggregate payments by method
    DB-->>API: totals
    API-->>UI: 200 + expected totals
    Cashier->>UI: Enter counted cash
    UI->>API: POST /billing/reconciliation/close
    API->>DB: store variance + close shift
    API-->>UI: 201 + variance result
    UI-->>Cashier: Summary + variance flag if any
```

### Friction & Cognitive Load Points
- Variance without reason entry forces follow-up — capture reason inline.
