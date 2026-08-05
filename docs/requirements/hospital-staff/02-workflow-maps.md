# End-to-End Workflow Maps — Other Hospital Staff (R19)

## Workflow W1: Results Check on Mobile (frequency: daily, criticality: high)

```mermaid
sequenceDiagram
    actor Staff as Hospital Staff (nurse/lab/pharmacy)
    participant UI as Portal (mobile)
    participant API as Backend API
    participant DB as PostgreSQL
    Staff->>UI: Open portal, search patient (MRN)
    UI->>API: GET /patients?q=... (scoped)
    API->>DB: scope check + search
    DB-->>API: permitted matches
    API-->>UI: 200 + results (scope-filtered)
    Staff->>UI: Open patient → order status
    UI->>API: GET /patients/{id}/orders
    API->>DB: query scoped orders
    DB-->>API: statuses
    API-->>UI: 200 + order status list
    Staff->>UI: Open finalized report
    UI->>API: GET /reports/{id} (read-only)
    API->>DB: fetch report (draft filtered out)
    DB-->>API: report
    API-->>UI: 200 + read-only report
    UI-->>Staff: Rendered read-only + audit logged
```

### Friction & Cognitive Load Points
- Scope filtering must be transparent — out-of-scope results simply don't appear.
- Mobile-first layout with readable report rendering.

### Error & Exception Paths
- Out-of-scope access attempt → no data + audit entry.
- Draft-only report → hidden with "not available" messaging.

## Workflow W2: Report Finalize → Notification (frequency: continuous, criticality: high)

```mermaid
sequenceDiagram
    participant API as Backend API
    participant DB as PostgreSQL
    participant NOTIF as Notification Service
    participant UI as Portal
    API->>DB: report finalized (R12/R18)
    DB-->>API: event
    API->>NOTIF: fan-out to permitted staff (patient-link)
    NOTIF->>UI: in-app notification (≤ 60s, no PHI in body)
    UI-->>Staff: badge + list entry
```

### Friction & Cognitive Load Points
- Notification bodies must not contain PHI.

### Error & Exception Paths
- Notification delivery failure → retry; audit of deliveries.
