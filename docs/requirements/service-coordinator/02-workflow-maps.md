# End-to-End Workflow Maps — Radiology & Service Coordinator (R04)

## Workflow W1: Modality Scheduling (frequency: daily, criticality: high)

```mermaid
sequenceDiagram
    actor User as R04 Coordinator
    participant UI as Schedule Board
    participant API as Backend API
    participant DB as PostgreSQL
    participant WS as WebSocket
    User->>UI: Open schedule board (GET /api/v2/schedule/board)
    UI->>API: GET /api/v2/schedule/board?date=2026-08-02
    API->>DB: SELECT exams, modalities, technologists
    DB-->>API: rows (exams + modality slots + tech assignments)
    API-->>UI: 200 + schedule board data
    UI-->>User: Render board with modality columns, time slots, priority badges
    User->>UI: Drag exam to different time slot
    UI->>API: POST /api/v2/schedule/move {exam_id, new_slot}
    API->>DB: UPDATE exam slot; INSERT audit log
    DB-->>API: updated exam + conflict check result
    API-->>UI: 200 + moved exam data
    alt Conflict detected
        UI-->>User: Show red inline badge with tooltip listing conflicts
    else No conflict
        UI-->>User: Exam moved smoothly; slot updated
        WS->>R06/R07: Push assignment update to technologist worklist
    end
```

### Friction & Cognitive Load Points
- Dragging an exam that causes a double-book requires the coordinator to mentally resolve the conflict (2 conflicting exams to compare)
- Shift handoff report generation requires switching from board view to report view
- Stat auto-promotion changes the board order without explicit coordinator action (surprise reorder)

### Error & Exception Paths
- **API timeout on move**: Show "Saving..." spinner; retry with exponential backoff (max 3 attempts); on failure, revert board position and show error banner
- **WebSocket disconnect**: Board remains functional; polling fallback every 30s; yellow banner "Live updates disconnected"
- **DB conflict on concurrent edit**: Optimistic locking with version check; show "Another coordinator moved this exam" toast with current state
- **Modality offline**: Slot shows "Offline" badge; drag to slot blocked; tooltip explains modality status

---

## Workflow W2: Exam Assignment & Triage (frequency: daily, criticality: high)

```mermaid
sequenceDiagram
    actor User as R04 Coordinator
    participant UI as Schedule Board / Worklist
    participant API as Backend API
    participant DB as PostgreSQL
    participant WS as WebSocket
    User->>UI: Click exam row → "Assign" button
    UI->>API: GET /api/v2/schedule/assign-options?exam_id=X
    API->>DB: SELECT available technologists (R06/R07, status=available)
    DB-->>API: list of technologists with current load
    API-->>UI: 200 + assign options
    UI-->>User: Dropdown with technologist names + current load indicator
    User->>UI: Select technologist → click Assign
    UI->>API: POST /api/v2/schedule/assign {exam_id, technologist_id, priority}
    API->>DB: UPDATE exam assigned_to; INSERT assignment audit log
    DB-->>API: updated exam
    API-->>UI: 200 + assignment confirmation
    WS->>R06/R07: Push new assignment to technologist worklist
    UI-->>User: Exam row moves to "Assigned" section; green checkmark badge
```

### Friction & Cognitive Load Points
- Coordinator must judge which technologist is best fit (skill + modality + current load) — cognitive load for complex assignments
- Bulk reassign (FR-R04-07) requires confirming multiple affected exams at once

### Error & Exception Paths
- **No available technologists**: Show "No available technologists" empty state with CTA "View on-call roster"
- **Technologist already assigned to overlapping exam**: Conflict detection blocks assignment; shows conflicting exam details
- **API error on assign**: Show inline error on exam row; allow retry

---

## Workflow W3: Stat/Priority Triage (frequency: continuous, criticality: critical)

```mermaid
sequenceDiagram
    actor User as R04 Coordinator
    participant UI as Schedule Board
    participant API as Backend API
    participant DB as PostgreSQL
    User->>UI: STAT exam arrives (DB trigger or API)
    DB->>API: NOTIFY new STAT exam
    API->>UI: Push new STAT exam to board top
    UI-->>User: STAT row appears at top with red fade-in animation
    alt STAT backlog > 3 pending
        API->>DB: Auto-promote oldest routine exam to urgent
        DB-->>API: promoted exam IDs
        API->>UI: Push board reorder with promotion notice
        UI-->>User: Board reorders; yellow banner "1 routine exam promoted to urgent due to STAT backlog"
    end
    User->>UI: Drag STAT exam to top of board (manual reorder)
    UI->>API: POST /api/v2/schedule/reorder {exam_ids: [stat_id, ...]}
    API->>DB: UPDATE order
    DB-->>API: OK
    API-->>UI: 200
```

### Friction & Cognitive Load Points
- Auto-promotion threshold (3) may be too aggressive for low-volume periods or too conservative for high-volume periods
- Coordinator must be aware that auto-promotion happened (notification needed)

### Error & Exception Paths
- **STAT exam with no available modality slot**: Show "No slot available" warning; suggest earliest available slot
- **Auto-promotion causes cascade conflict**: Show conflict resolution modal with affected exams

---

## Workflow W4: Staffing Roster Management (frequency: weekly, criticality: medium)

```mermaid
sequenceDiagram
    actor User as R04 Coordinator
    participant UI as Staffing Roster View
    participant API as Backend API
    participant DB as PostgreSQL
    User->>UI: Navigate to Staffing tab
    UI->>API: GET /api/v2/schedule/roster?week=2026-W32
    API->>DB: SELECT users (R06/R07), shift_assignments, availability
    DB-->>API: roster data
    API-->>UI: 200 + roster table
    UI-->>User: Display roster with status badges, hours summary
    User->>UI: Drag technologist to different shift
    UI->>API: PUT /api/v2/schedule/roster {user_id, shift: "morning"}
    API->>DB: UPDATE shift_assignment; INSERT audit log
    DB-->>API: updated assignment
    API-->>UI: 200
    UI-->>User: Roster updated; status badge changes
```

### Friction & Cognitive Load Points
- Shift assignment affects exam coverage — coordinator must mentally model coverage gaps
- Overtime tracking requires comparing scheduled vs. actual hours across the week

### Error & Exception Paths
- **Shift assignment exceeds max hours**: Show warning "This assignment exceeds 8h shift limit"
- **Technologist already assigned to exam during new shift**: Conflict detection shows affected exams

---

## Workflow W5: Shift Handoff Report (frequency: daily, criticality: medium)

```mermaid
sequenceDiagram
    actor User as R04 Coordinator
    participant UI as Handoff Report Modal
    participant API as Backend API
    participant DB as PostgreSQL
    User->>UI: Click "Generate Handoff Report" button
    UI->>API: POST /api/v2/schedule/handoff-report {shift_end: "15:00"}
    API->>DB: SELECT pending exams, STAT exams in progress, conflicts, overrides
    DB-->>API: report data
    API->>API: Format report (PDF or clipboard)
    API-->>UI: 200 + report content
    UI-->>User: Display report preview; Export as PDF / Copy to Clipboard buttons
    User->>UI: Click "Copy to Clipboard"
    UI-->>User: Report copied; green toast "Report copied to clipboard"
```

### Friction & Cognitive Load Points
- Report generation requires querying multiple data sources (exams, conflicts, overrides) — latency concern
- PDF generation is a backend operation; frontend must handle async with progress indicator

### Error & Exception Paths
- **No pending exams**: Show empty state "No pending exams for this shift"
- **PDF generation timeout**: Show "Report generation taking longer than expected" with cancel option; fall back to clipboard format