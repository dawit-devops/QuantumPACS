# End-to-End Workflow Maps — External RIS (R15)

## Workflow W1: Order Inbound (HL7 ORM^O01) (frequency: continuous, criticality: critical)

```mermaid
sequenceDiagram
    participant RIS as External RIS
    participant MLLP as HL7 Listener
    participant API as Backend API
    participant DB as PostgreSQL
    RIS->>MLLP: ORM^O01 (new order)
    MLLP->>API: parse + validate + persist raw
    API->>DB: log message (received)
    API->>API: map accession/procedure/modality
    API->>DB: upsert order + worklist entry
    API-->>MLLP: ACK (MSA-1 = AA)
    MLLP-->>RIS: ACK
    Note over API,DB: failure → retry 3x → dead-letter → manual reconcile
```

### Friction & Cognitive Load Points
- Duplicate orders (same accession) must merge, not duplicate.
- Unknown modality/AE → quarantine with reason for admin review.

### Error & Exception Paths
- Unparseable message → NAK with error detail; message retained.
- Mapping failure (missing required fields) → dead-letter with reconciliation UI.

## Workflow W2: Status Update Outbound (ORM/ORU) (frequency: continuous, criticality: high)

```mermaid
sequenceDiagram
    participant API as Backend API
    participant DB as PostgreSQL
    participant MLLP as HL7 Sender
    participant RIS as External RIS
    API->>DB: exam status changes (performed/cancelled)
    DB-->>API: event
    API->>MLLP: build ORM/ORU (accession + study UID + status)
    MLLP->>RIS: send message
    RIS-->>MLLP: ACK
    MLLP->>DB: mark delivered / record ack
    Note over MLLP,DB: no ACK → retry 3x → dead-letter → manual resend
```

### Friction & Cognitive Load Points
- Outbound queue must be idempotent (same status event not sent twice).

### Error & Exception Paths
- RIS unavailable → outbound queue backs up; alert when > threshold.
