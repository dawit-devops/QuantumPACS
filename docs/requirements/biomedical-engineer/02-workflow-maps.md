# End-to-End Workflow Maps — Biomedical Engineer (R10)

## Workflow W1: Downtime Logging (frequency: as needed, criticality: high)

```mermaid
sequenceDiagram
    actor Engineer as Biomedical Engineer
    participant UI as Equipment UI
    participant API as Backend API
    participant DB as PostgreSQL
    participant R3 as R03 Dashboards
    Engineer->>UI: Open equipment + start downtime
    UI->>API: POST /equipment/{id}/downtime (start)
    API->>DB: create downtime event
    API-->>UI: 201 + active downtime
    Engineer->>UI: Record cause + impact + resolution
    UI->>API: PUT /equipment/{id}/downtime/{id} (end)
    API->>DB: close event + compute duration
    API->>R3: aggregate downtime metric (async)
    API-->>UI: 200 + duration + uptime updated
    UI-->>Engineer: Success + uptime refresh
```

### Friction & Cognitive Load Points
- Starting/stopping downtime must be two quick taps — no multi-step wizards.
- Cause categories must be a managed picklist, not free text.

### Error & Exception Paths
- Forgetting to close a downtime event → open-event list with "still running" reminders.
- Concurrent events on the same equipment → validation warning.

## Workflow W2: PM Completion with QC (frequency: daily/weekly, criticality: high)

```mermaid
sequenceDiagram
    actor Engineer as Biomedical Engineer
    participant UI as PM/QC UI
    participant API as Backend API
    participant DB as PostgreSQL
    Engineer->>UI: Open PM/QC queue (due/overdue)
    UI->>API: GET /equipment/pm (due)
    API->>DB: query due PM + QC schedules
    DB-->>API: due items
    API-->>UI: 200 + due list
    Engineer->>UI: Complete PM, enter QC results
    UI->>API: POST /equipment/{id}/qc
    API->>DB: store QC record + mark PM complete
    API-->>UI: 201 + updated compliance
    UI-->>Engineer: Success + PM compliance updated
```

### Friction & Cognitive Load Points
- QC forms should prefill prior values for comparison.

### Error & Exception Paths
- QC failure → auto-flag equipment status and trigger fault alert (FR-R10-07).
