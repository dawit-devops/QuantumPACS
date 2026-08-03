# End-to-End Workflow Maps — Front Desk / Receptionist (R08)

## Workflow W1: Patient Registration with Duplicate Check (frequency: daily, criticality: high)

```mermaid
sequenceDiagram
    actor Receptionist as Front Desk
    participant UI as Registration UI
    participant API as Backend API
    participant DB as PostgreSQL
    participant EMR as External EMR (R16)
    Receptionist->>UI: Search patient (name / MRN / DOB)
    UI->>API: GET /patients?q=...
    API->>DB: search + dedup candidates
    DB-->>API: candidate rows
    API-->>UI: 200 + candidates (dedup warning if matches)
    Receptionist->>UI: Confirm "new patient" or select match
    Receptionist->>UI: Enter demographics + insurance + order
    UI->>API: POST /patients (or /visits)
    API->>DB: upsert patient + visit + order
    API->>EMR: HL7 ADT A01 (async)
    API-->>UI: 201 + created record
    UI-->>Receptionist: Success state + printable label
```

### Friction & Cognitive Load Points
- Duplicate search requires ≥2 fields before results render — add fuzzy/quick search.
- Insurance entry is form-heavy — progressive disclosure of optional fields.

### Error & Exception Paths
- Search returns no results → allow new registration with a review step.
- ADT sync fails → registration still succeeds; sync retries; queue indicator on patient record.
- Validation error → inline field errors, nothing lost.

## Workflow W2: Appointment Scheduling with Conflict Detection (frequency: daily, criticality: high)

```mermaid
sequenceDiagram
    actor Receptionist as Front Desk
    participant UI as Scheduler UI
    participant API as Backend API
    participant DB as PostgreSQL
    Receptionist->>UI: Select patient + requested procedure
    UI->>API: GET /schedule/availability (modality, date)
    API->>DB: query slots + existing bookings
    DB-->>API: slots + conflicts
    API-->>UI: 200 + available slots (conflicts flagged)
    Receptionist->>UI: Choose slot, confirm
    UI->>API: POST /schedule/exam
    API->>DB: create exam booking
    API-->>UI: 201 + booking (conflict-free)
    UI-->>Receptionist: Success + adds to R04 schedule board
```

### Friction & Cognitive Load Points
- Slot pickers must show modality + room + technologist, not just time.
- STAT/urgent orders should be visually distinct in the picker.

### Error & Exception Paths
- Slot taken between load and confirm → 409 with refreshed availability.
- No availability → show waitlist option and notify coordinator (R04).
