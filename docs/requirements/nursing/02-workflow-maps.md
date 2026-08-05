# End-to-End Workflow Maps — Radiology Service Nursing Team (R11)

## Workflow W1: Pre-Contrast Safety + Contrast Administration (frequency: per contrast exam, criticality: critical)

```mermaid
sequenceDiagram
    actor Nurse as Radiology Nurse
    participant UI as Nursing UI
    participant API as Backend API
    participant DB as PostgreSQL
    participant R12 as On-call Radiologist
    Nurse->>UI: Open patient prep checklist
    UI->>API: GET /nursing/prep/{visit}
    API->>DB: query checklist + allergy flags (HL7)
    DB-->>API: checklist + allergy/pregnancy/renal flags
    API-->>UI: 200 + checklist + safety flags
    Nurse->>UI: Confirm allergy/pregnancy/renal screening
    UI->>API: POST /nursing/safety-confirm
    API->>DB: record confirmation (blocks contrast until true)
    API-->>UI: 201 + confirmed
    Nurse->>UI: Record contrast administration
    UI->>API: POST /nursing/contrast
    API->>DB: record agent/dose/route/time
    API-->>UI: 201 + recorded
    UI-->>Nurse: Success + contrast linked to exam dose
```

### Friction & Cognitive Load Points
- Safety screening must be a hard gate — contrast action disabled until confirmed.
- Allergy flags from HL7 must be visually prominent.

### Error & Exception Paths
- Allergy flag present → warning banner, contrast requires physician override.
- Adverse reaction → escalation flow (W2).

## Workflow W2: Adverse Reaction Escalation (frequency: as needed, criticality: critical)

```mermaid
sequenceDiagram
    actor Nurse as Radiology Nurse
    participant UI as Nursing UI
    participant API as Backend API
    participant DB as PostgreSQL
    participant R12 as On-call Radiologist
    Nurse->>UI: Log adverse reaction (type, severity, onset)
    UI->>API: POST /nursing/reaction
    API->>DB: store reaction record
    API->>R12: escalation notification (≤ 15min SLA)
    R12-->>API: acknowledge
    API-->>UI: 201 + escalation status
    UI-->>Nurse: Escalation sent + ack tracking
```

### Friction & Cognitive Load Points
- Reaction entry must be < 10 taps (type, severity, onset, actions).

### Error & Exception Paths
- Escalation channel down → retry with fallback (SMS/pager); logged.
