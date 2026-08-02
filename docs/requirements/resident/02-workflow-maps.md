# End-to-End Workflow Maps — Radiology Trainee/Resident (R13)

## Workflow W1: Supervised Study Interpretation (frequency: per study, criticality: high)

```mermaid
sequenceDiagram
    actor User as R13 Resident
    actor Attending as R12 Attending
    participant UI as Supervised Worklist + Viewer
    participant API as Backend API
    participant DB as PostgreSQL
    User->>UI: Open supervised worklist (GET /api/v2/worklists/resident)
    UI->>API: GET /api/v2/worklists/resident
    API->>DB: SELECT studies WHERE resident_id=R13 AND status IN ('pending','in_review')
    DB-->>API: assigned studies
    API-->>UI: 200 + worklist data
    UI-->>User: Display worklist with attending column, STAT highlighted
    User->>UI: Click next study
    UI->>API: GET /api/v2/studies/{id}/supervised
    API->>DB: SELECT study + resident assignment + attending notes
    DB-->>API: study data
    API-->>UI: 200 + supervised study view
    UI-->>User: Split-screen: DICOM viewer + attending guidance panel
    User->>UI: Interpret study; toggle attending guidance as needed
    Attending->>Attending: Adds guidance notes during or before resident read
    UI->>API: POST /api/v2/studies/{id}/attending-guidance (Attending)
    API->>DB: UPDATE attending_notes
    DB-->>API: OK
    API-->>UI: 200 (real-time update to resident)
```

### Friction & Cognitive Load Points
- Split-screen view requires resident to synthesize attending guidance with own findings
- Attending guidance may be added asynchronously — resident must check for updates
- Balancing independent interpretation with attending guidance (educational tension)

### Error & Exception Paths
- **No attending assigned**: Show "No attending assigned for this study — contact coordinator" with CTA
- **Attending guidance unavailable**: Show "Attending guidance not yet available" placeholder; resident can proceed independently
- **PACS unavailable**: Viewer shows cached images; guidance panel still functional

---

## Workflow W2: Draft Report Creation and Attending Review (frequency: per study, criticality: critical)

```mermaid
sequenceDiagram
    actor User as R13 Resident
    actor Attending as R12 Attending
    participant UI as Draft Report Editor
    participant API as Backend API
    participant DB as PostgreSQL
    User->>UI: Click "Create Draft Report" in supervised viewer
    UI->>API: POST /api/v2/reports/draft {study_id, resident_id}
    API->>DB: INSERT draft_report (status='draft')
    DB-->>API: draft report ID
    API-->>UI: 200 + draft report editor
    UI-->>User: Structured report editor with DRAFT badge; auto-save every 10s
    User->>UI: Write findings, impression, recommendations
    UI->>API: PUT /api/v2/reports/draft/{id} (auto-save)
    API->>DB: UPDATE draft_report content
    DB-->>API: OK
    API-->>UI: 200
    User->>UI: Click "Submit for Attending Review"
    UI->>API: POST /api/v2/reports/draft/{id}/submit
    API->>DB: UPDATE status='submitted'; INSERT notification for attending
    DB-->>API: OK
    API->>Attending: Notify attending via WebSocket (draft submitted)
    API-->>UI: 200
    UI-->>User: "Submitted for review" notification; report locked from editing
    Attending->>Attending: Opens resident review queue
    Attending->>UI: Clicks draft → side-by-side comparison view
    Attending->>UI: Adds inline comments/amendments
    Attending->>UI: Clicks "Approve & Co-sign" or "Return for Revision"
    alt Approve
        UI->>API: POST /api/v2/reports/draft/{id}/approve {attending_signature}
        API->>DB: UPDATE report status='final'; INSERT co-signature; DELETE draft
        DB-->>API: OK
        API->>User: Notify resident "Report approved"
    else Return for Revision
        UI->>API: POST /api/v2/reports/draft/{id}/return {feedback}
        API->>DB: UPDATE status='revision'; INSERT feedback
        DB-->>API: OK
        API->>User: Notify resident "Revision requested" with attending feedback
    end
```

### Friction & Cognitive Load Points
- Resident must wait for attending review — creates workflow bottleneck
- Side-by-side comparison requires attending to mentally map changes
- Revision cycle may repeat multiple times for complex cases

### Error & Exception Paths
- **Attending unavailable for >4 hours**: Escalate to R03 service director; show "Review delayed — escalated"
- **Draft auto-save fails**: Show "Auto-save failed — manual save required" banner; manual save button
- **Concurrent edit conflict**: If attending and resident edit simultaneously, show "Attending is reviewing — your changes will be merged" warning
- **Auto-save during attending review**: Attending sees "Resident editing — refresh to see latest" indicator

---

## Workflow W3: Teaching File Capture (frequency: weekly, criticality: medium)

```mermaid
sequenceDiagram
    actor User as R13 Resident
    participant UI as Teaching File Capture
    participant API as Backend API
    participant DB as PostgreSQL
    User->>UI: From study viewer, click "Capture Teaching Case"
    UI->>API: GET /api/v2/studies/{id}/teaching-capture
    API->>DB: SELECT study images + resident draft + attending report
    DB-->>API: study data
    API-->>UI: 200 + teaching file editor
    UI-->>User: Pre-populated: key images (from study), resident findings, attending feedback, diagnosis
    User->>UI: Select key images (multi-select from thumbnail strip)
    User->>UI: Add differential diagnosis, key learning points, tags
    User->>UI: Click "Submit for Attending Approval"
    UI->>API: POST /api/v2/teaching-files {study_id, images, findings, diagnosis, tags}
    API->>DB: INSERT teaching_file (status='pending_approval')
    DB-->>API: OK
    API->>Attending: Notify attending "Teaching file submitted for approval"
    API-->>UI: 200
    Attending->>Attending: Reviews teaching file
    Attending->>UI: Clicks "Approve" or "Request Changes"
    alt Approve
        UI->>API: POST /api/v2/teaching-files/{id}/approve
        API->>DB: UPDATE status='approved'; de-identify images; ADD to teaching library
        DB-->>API: OK
        API->>User: Notify resident "Teaching file approved and published"
    else Request Changes
        UI->>API: POST /api/v2/teaching-files/{id}/request-changes {feedback}
        API->>DB: UPDATE status='revision'; INSERT feedback
        DB-->>API: OK
        API->>User: Notify resident "Changes requested" with attending feedback
    end
```

### Friction & Cognitive Load Points
- De-identification must be thorough (burned-in text, DICOM tags, facial features in some modalities)
- Resident must select truly representative key images — educational judgment required
- Attending approval adds latency to teaching file publication

### Error & Exception Paths
- **De-identification fails**: Show "De-identification incomplete — manual review required"; do not publish
- **Image export fails**: Show "Failed to export images — retry" with retry button
- **Attending rejects teaching file**: Status returns to 'revision'; resident must address feedback

---

## Workflow W4: Exam List Management and Portfolio Export (frequency: monthly, criticality: medium)

```mermaid
sequenceDiagram
    actor User as R13 Resident
    participant UI as Exam List Dashboard
    participant API as Backend API
    participant DB as PostgreSQL
    User->>UI: Navigate to Exam List / Portfolio
    UI->>API: GET /api/v2/resident/{id}/exam-list
    API->>DB: SELECT studies WHERE resident_id=R13
    DB-->>API: resident's interpreted studies
    API-->>UI: 200 + exam list data
    UI-->>User: Filterable table: date, modality, body part, diagnosis, attending, review status
    User->>UI: Apply filters (modality=CT, body_part=chest)
    UI->>API: GET /api/v2/resident/{id}/exam-list?modality=CT&body_part=chest
    API->>DB: SELECT filtered
    DB-->>API: filtered studies
    API-->>UI: 200 + filtered list
    User->>UI: Click "Export CSV"
    UI->>API: POST /api/v2/resident/{id}/exam-list/export {filters}
    API->>DB: SELECT filtered + metrics
    DB-->>API: export data
    API->>API: Generate CSV
    API-->>UI: 200 + CSV download
    UI-->>User: CSV downloaded with columns: date, accession, modality, body_part, diagnosis, attending, interpretation_time, draft_to_final_turnaround, revision_count
```

### Friction & Cognitive Load Points
- Resident must ensure all studies have complete data for accurate portfolio
- Export format must match residency program requirements (varies by program)
- Metrics calculation requires complete data (interpretation time, turnaround)

### Error & Exception Paths
- **Export timeout**: Show "Generating export — please wait" with progress; allow background download
- **Missing data for metrics**: Show "Some studies missing interpretation time — metrics may be incomplete"
- **Large export (>1000 studies)**: Chunk export; show progress bar

---

## Workflow W5: Performance Feedback and On-Call Support (frequency: continuous, criticality: medium)

```mermaid
sequenceDiagram
    actor User as R13 Resident
    actor Attending as R12 Attending
    participant UI as Feedback Dashboard
    participant API as Backend API
    participant DB as PostgreSQL
    User->>UI: Open Feedback Dashboard
    UI->>API: GET /api/v2/resident/{id}/feedback
    API->>DB: SELECT metrics, attending feedback, rotation milestones
    DB-->>API: feedback data
    API-->>UI: 200 + dashboard
    UI-->>User: Charts: studies by modality, interpretation time trend, agreement rate, feedback themes
    Attending->>Attending: Adds private feedback note on study
    Attending->>UI: Clicks "Add Feedback" on resident's study
    UI->>API: POST /api/v2/resident/{id}/feedback {study_id, feedback, category}
    API->>DB: INSERT feedback (private: visible to resident, attending, R03)
    DB-->>API: OK
    API->>User: Notify resident "New feedback from Dr. {attending}"
    User->>UI: Opens Feedback Dashboard → sees new feedback entry
    alt On-Call Support
        User->>UI: Click "Request Attending Consult" (on-call mode)
        UI->>API: POST /api/v2/resident/{id}/consult-request {study_id, urgency}
        API->>DB: INSERT consult_request; FIND on-call attending (R12/R18)
        DB-->>API: on-call attending ID
        API->>Attending: Priority notification "Resident consult request — {study_id}"
        Attending->>UI: Joins screen-share or provides written guidance
        Attending->>UI: Submits guidance
        UI->>API: POST /api/v2/resident/{id}/consult-response {guidance}
        API->>DB: UPDATE consult_request status='completed'
        DB-->>API: OK
        API->>User: Guidance appears in study viewer
    end
```

### Friction & Cognitive Load Points
- Feedback dashboard aggregates multiple data sources — latency concern
- On-call consult requires synchronous attending availability — may have wait time
- Private feedback visibility (resident, attending, R03) requires careful permission model

### Error & Exception Paths
- **No on-call attending available**: Escalate to R03; show "No attending available — escalated to service director"
- **Screen-share fails**: Fall back to written guidance in study viewer
- **Feedback notification fails**: Show in dashboard on next load; retry notification