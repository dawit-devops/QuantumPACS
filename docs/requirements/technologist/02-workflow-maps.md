# End-to-End Workflow Maps — Radiology Technologist (R06)

## Workflow W1: Exam Preparation and Patient Positioning (frequency: per exam, criticality: high)

```mermaid
sequenceDiagram
    actor User as R06 Technologist
    participant UI as Worklist + Exam Detail
    participant API as Backend API
    participant DB as PostgreSQL
    participant PACS as PACS Archive
    User->>UI: Open worklist (GET /api/v2/worklists/technologist)
    UI->>API: GET /api/v2/worklists/technologist
    API->>DB: SELECT exams WHERE assigned_to=R06 AND status='pending'
    DB-->>API: pending exams
    API-->>UI: 200 + worklist data
    UI-->>User: Display worklist with STAT highlighted
    User->>UI: Click next STAT exam
    UI->>API: GET /api/v2/exams/{id}
    API->>DB: SELECT exam + patient + protocol
    DB-->>API: exam data
    API-->>UI: 200 + exam detail
    UI-->>User: Display patient demographics + protocol
    User->>UI: Click "Confirm Patient"
    UI->>API: POST /api/v2/exams/{id}/confirm-patient
    API->>DB: UPDATE exam status='in_progress'; INSERT audit log
    DB-->>API: OK
    API-->>UI: 200
    UI-->>User: Exam status changes to in-progress; acquisition UI opens
    User->>UI: Position patient per protocol instructions
    User->>UI: Click "Start Acquisition"
    UI->>API: POST /api/v2/exams/{id}/start-acquisition
    API->>DB: UPDATE exam status='acquiring'
    DB-->>API: OK
    API-->>UI: 200
    UI-->>User: Image preview appears with real-time QA overlay
```

### Friction & Cognitive Load Points
- Patient identity verification requires technologist to manually confirm, adding a step before acquisition
- Protocol parameters may conflict with patient safety (contrast allergy) — requires careful review
- Positioning instructions must be followed precisely; incorrect positioning leads to repeat exams

### Error & Exception Paths
- **Patient mismatch**: If patient initials don't match expected, technologist can "Swap Patient" and re-search
- **Protocol not assigned**: If no protocol is assigned, show "Protocol not assigned" error with CTA to assign
- **PACS unavailable**: Image preview still works from local cache; PACS push queued for retry

---

## Workflow W2: Image Acquisition and Quality Assurance (frequency: per exam, criticality: critical)

```mermaid
sequenceDiagram
    actor User as R06 Technologist
    participant UI as Image Preview + QA Overlay
    participant API as Backend API
    participant DB as PostgreSQL
    participant PACS as PACS Archive
    User->>UI: Start image acquisition
    UI->>API: POST /api/v2/exams/{id}/acquire
    API->>DB: INSERT acquisition record with dose params
    DB-->>API: acquisition record
    API-->>UI: 200 + image preview URL
    UI-->>User: Real-time image preview with QA overlay
    loop For each image acquired
        User->>UI: Review image quality
        alt Image passes QA
            User->>UI: Click "Accept" → next image
            API->>DB: UPDATE image status='accepted'
        else Image fails QA
            User->>UI: Click "Reject" → select reason code
            UI->>API: POST /api/v2/exams/{id}/reject {reason, description}
            API->>DB: UPDATE image status='rejected'; INSERT reject log
            DB-->>API: OK
            API-->>UI: 200
            UI-->>User: Red alert "Image rejected — reason: {reason}"; re-acquire prompt
        end
    end
    User->>UI: Click "Complete Exam"
    UI->>API: POST /api/v2/exams/{id}/complete
    API->>DB: UPDATE exam status='complete'; INSERT dose log
    API->>PACS: Push images to archive
    API-->>UI: 200
    UI-->>User: Exam complete notification; radiologist worklist updated
```

### Friction & Cognitive Load Points
- Real-time QA requires technologist to evaluate image quality while continuing acquisition — split attention
- Reject reason selection requires knowing standardized codes; incorrect codes affect QA metrics
- Cumulative dose tracking requires technologist to monitor running total during exam

### Error & Exception Paths
- **Image preview fails**: Show "Image unavailable" placeholder with retry button; acquisition continues
- **Dose logging failure**: Show warning "Dose not logged — check manually"; exam can still complete
- **PACS push fails**: Queue images for retry; show "Images pending archive" banner; auto-retry every 30s
- **Reject limit exceeded**: If >3 rejects for same acquisition, show "High reject rate — consider repositioning" warning

---

## Workflow W3: Dose Documentation and ALARA Compliance (frequency: per exam, criticality: high)

```mermaid
sequenceDiagram
    actor User as R06 Technologist
    participant UI as Dose Monitor Panel
    participant API as Backend API
    participant DB as PostgreSQL
    User->>UI: Begin exam acquisition
    UI->>API: GET /api/v2/exams/{id}/dose-baseline
    API->>DB: SELECT patient cumulative dose + protocol ACR benchmark
    DB-->>API: dose data
    API-->>UI: 200 + dose baseline
    UI-->>User: Display cumulative dose + protocol benchmark on dose panel
    loop During acquisition
        UI->>UI: Update dose panel with each acquisition (DLP, CTDIvol, kVp, mAs)
        alt Cumulative dose exceeds protocol benchmark
            UI-->>User: Yellow warning banner "Cumulative dose approaching ACR benchmark"
        end
    end
    User->>UI: Complete exam
    UI->>API: POST /api/v2/exams/{id}/complete (includes dose data)
    API->>DB: INSERT dose record; UPDATE cumulative patient dose
    DB-->>API: OK
    API-->>UI: 200
    UI-->>User: Dose panel shows final values; green checkmark if within benchmark
```

### Friction & Cognitive Load Points
- Technologist must monitor cumulative dose in real-time while acquiring images — cognitive load
- ALARA principle requires minimizing dose while maintaining diagnostic quality — trade-off decision
- Protocol ACR benchmarks vary by modality and body part — must be clearly displayed

### Error & Exception Paths
- **Dose data missing from DICOM header**: Show "Dose not recorded" warning; allow manual entry
- **Cumulative dose exceeds benchmark**: Show red alert "Dose limit exceeded — consult R05 QA"; exam can still complete but is flagged for QA review
- **Protocol benchmark not configured**: Show "No ACR benchmark for this protocol" info message; no dose flagging

---

## Workflow W4: Exam Completion and Radiologist Handoff (frequency: per exam, criticality: high)

```mermaid
sequenceDiagram
    actor User as R06 Technologist
    participant UI as Exam Completion Panel
    participant API as Backend API
    participant DB as PostgreSQL
    participant R12 as R12 Radiologist Worklist
    participant PACS as PACS Archive
    User->>UI: Click "Complete Exam"
    UI->>API: POST /api/v2/exams/{id}/complete {dose_data, sequence_compliance, reject_count}
    API->>DB: UPDATE exam status='complete'; INSERT dose log; UPDATE sequence compliance
    DB-->>API: OK
    API->>PACS: Push images to archive (async)
    API->>R12: Notify radiologist via WebSocket (exam complete, study UID)
    API-->>UI: 200
    UI-->>User: "Exam complete" notification; exam moves to completed section
    R12->>R12: Radiologist sees new exam in worklist
    PACS-->>PACS: Images archived and available for viewing
```

### Friction & Cognitive Load Points
- Technologist must ensure all required fields are complete before marking exam done (dose, sequences, rejects)
- Radiologist notification must be timely — delay affects report turnaround
- PACS push is async; images may not be immediately available to radiologist

### Error & Exception Paths
- **Completion blocked by missing data**: If dose or sequence compliance is incomplete, show "Please complete all required fields" and highlight missing fields
- **PACS push fails**: Images queued for retry; radiologist notified that images are pending
- **Radiologist notification fails**: Show "Radiologist notification pending" banner; retry every 30s

---

## Workflow W5: Retake/Incident Logging (frequency: as needed, criticality: medium)

```mermaid
sequenceDiagram
    actor User as R06 Technologist
    participant UI as Incident Log Modal
    participant API as Backend API
    participant DB as PostgreSQL
    participant R05 as R05 QA Team
    participant R12 as R12 Radiologist
    User->>UI: Flag image as rejected or log incident
    UI->>API: POST /api/v2/exams/{id}/reject {reason, description, severity}
    API->>DB: INSERT reject log; UPDATE image status='rejected'
    DB-->>API: OK
    API->>R05: Notify QA team if severity=high
    API->>R12: Notify radiologist if severity=critical
    API-->>UI: 200
    UI-->>User: Rejection recorded; re-acquire prompt shown
    alt Severity is high/critical
        R05->>R05: QA team receives notification
        R12->>R12: Radiologist receives notification
    end
```

### Friction & Cognitive Load Points
- Technologist must select correct reject reason code from standardized list
- Severity assessment (high/critical) requires clinical judgment
- Incident logging adds time to exam workflow; must be streamlined

### Error & Exception Paths
- **Reject reason not selected**: Show "Please select a reject reason" validation error
- **Notification to R05/R12 fails**: Log the failure; retry notification; technologist can manually notify
- **Duplicate reject log**: Prevent duplicate entries for same image rejection