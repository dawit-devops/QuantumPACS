# UI/UX Requirements — Radiology & Service Coordinator (R04)

## Role-Based Routing & Navigation (Presentation Layer)

RBAC drives the presentation layer (`hasPermission()` + `RequirePermission`, gated
`Sidebar.tsx` items). Verified against `frontend/src/`.

### Routes Accessible (codebase reality)

| Route | Screen | Access rule |
|-------|--------|-------------|
| `/` | Files / study search | Any authenticated user |
| `/worklist` | Modality worklist (CRUD, calendar, batch ops) | `WORKLIST_READ` (admin submenu item) |
| `/metrics` | Metrics dashboard | Any authenticated user (sidebar item) |
| `/account` | Account | Any authenticated user |
| `/schedule-board`, `/staffing`, `/utilization` | **Not accessible** | No routes/endpoints exist — GATED |

### Navigation Gating (Sidebar.tsx)

| Menu item | Visible when |
|-----------|--------------|
| Files / Metrics / Account / Notifications | Always (authenticated) |
| Worklist (under Admin) | `WORKLIST_READ` |

### Functionality Gating

- The existing `Worklist.tsx` covers entries, calendar view, batch mark-performed/
  cancel, search, date-range + station filters — **implemented**.
- Schedule board, exam assignment, staffing rosters, utilization, shift handoff
  report are **not implemented** — aspirational FRs marked `GATED` (artifacts
  01/07/08).

## Screens & Navigation

### Screen Inventory
| Screen | ID | Entry Point | Navigation |
|--------|----|-------------|------------|
| Schedule Board | S-R04-01 | Sidebar → "Schedule" | Primary view; tabs for Board/Calendar/Worklist |
| Utilization Dashboard | S-R04-02 | Sidebar → "Utilization" | Filter bar at top; charts below |
| Staffing Roster | S-R04-03 | Sidebar → "Staffing" | Table view with shift columns |
| Exam Detail Panel | S-R04-04 | Click exam block on board | Slide-out panel from right; closes on Escape |
| Handoff Report Modal | S-R04-05 | Button on Schedule Board header | Modal overlay; PDF export or clipboard copy |
| Override/Mass Reassign Modal | S-R04-06 | Button on Schedule Board toolbar | Modal with confirmation list |

### Navigation Hierarchy
```
Sidebar
├── Schedule (S-R04-01) ──── Board / Calendar / Worklist tabs
├── Utilization (S-R04-02)
├── Staffing (S-R04-03)
└── Reports (S-R04-05)
```

### Entry Points
- **Primary**: Sidebar navigation → Schedule Board
- **Secondary**: Keyboard shortcut `Ctrl+Shift+S` opens schedule board
- **Context**: Clicking a STAT exam in the worklist highlights it on the schedule board

### Breadcrumbs/Back Paths
- Schedule Board → no parent (top-level view)
- Exam Detail → back to Schedule Board (preserves scroll position and filter state)
- Handoff Report → back to Schedule Board

---

## Component & State Spec (per screen)

### ScheduleBoard (S-R04-01)
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| ScheduleBoard | Empty state: "No exams scheduled for this date" with "Schedule Exam" CTA | Skeleton rows with pulse animation | Same as default (no exams) | Red banner "Failed to load schedule" + Retry button | Full board with modality columns, time slots, exam blocks | Board disabled during bulk operations |

### ExamDetailPanel (S-R04-04)
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| ExamDetailPanel | Closed (not rendered) | Spinner inside panel | "No exam selected" message | Red inline error "Failed to load exam details" | Full exam info + Assign button + conflict warnings | Assign button disabled during API call |

### UtilizationDashboard (S-R04-02)
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| UtilizationDashboard | Empty state: "Select a date range to view utilization" | Skeleton chart placeholders | Same as default (no data for selected range) | Red banner "Failed to load utilization data" + Retry | Bar chart + line chart with filter controls | Filter inputs disabled during load |

### StaffingRoster (S-R04-03)
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| StaffingRoster | Table with all R06/R07 technologists | Skeleton table rows | "No technologists found" message | Red banner "Failed to load roster" + Retry | Full roster table with status badges, shift assignments | Drag-and-drop disabled during save |

### HandoffReportModal (S-R04-05)
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| HandoffReportModal | Closed | Spinner in modal body | "No pending exams for this shift" | Red inline error "Failed to generate report" | Report preview with Export PDF / Copy buttons | Export buttons disabled during generation |

### OverrideModal (S-R04-06)
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| OverrideModal | Closed | — | "No exams to reassign" | Red inline error | Confirmation list with affected exams + Confirm/Cancel | Confirm button disabled until selection made |

---

## Design System Conformance

### Tokens Referenced
- **Color**: `--color-primary` (blue #3B82F6), `--color-danger` (red #EF4444), `--color-warning` (yellow #F59E0B), `--color-success` (green #10B981)
- **Typography**: `--font-sans` (Inter), `--text-sm` (14px), `--text-base` (16px), `--text-lg` (18px), `--font-bold` (600)
- **Spacing**: `--space-2` (8px), `--space-3` (12px), `--space-4` (16px), `--space-6` (24px)
- **Radius**: `--radius-md` (8px), `--radius-lg` (12px)
- **Shadow**: `--shadow-sm` (0 1px 2px rgba(0,0,0,0.05)), `--shadow-md` (0 4px 6px rgba(0,0,0,0.07))

### New Semantic Tokens Required
| Token | Value | Description |
|-------|-------|-------------|
| `scheduler-stat-bg` | `rgba(239, 68, 68, 0.1)` | Background for STAT exam blocks on schedule board |
| `scheduler-urgent-bg` | `rgba(245, 158, 11, 0.1)` | Background for urgent exam blocks |
| `scheduler-routine-bg` | `rgba(209, 213, 219, 0.1)` | Background for routine exam blocks |
| `scheduler-conflict-border` | `#EF4444` | Border color for conflict indicators |
| `scheduler-assigned-bg` | `#D1FAE5` | Background for assigned exam blocks |

### Components Referenced
- `KanbanBoard` (existing) — extended for modality columns and time slots
- `Table` (existing) — used for worklist and staffing roster
- `Modal` (existing) — used for scheduling form, override confirmation, handoff report
- `Badge` (existing) — priority badges (STAT=red, urgent=yellow, routine=gray)
- `Tooltip` (existing) — conflict details, exam details on hover
- `Dropdown` (existing) — technologist selector, bulk action selector
- `Toast` (existing) — operation confirmation and error notifications
- `Skeleton` (existing) — loading states for board, dashboard, roster

---

## Accessibility Requirements
- WCAG 2.2 AA compliance for all screens
- Keyboard operability: Tab through board cells, Enter to open exam detail, Escape to close panels
- Focus indicators: 3px blue outline (`--color-focus: #3B82F6`) on all interactive elements
- ARIA labels: `aria-label="Schedule board for {date}"`, `aria-label="Exam {patient_initials} - {modality} - {priority}"`
- Screen reader announcements: "Exam {patient_initials} assigned to {technologist_name}" on assignment
- Color not used alone: priority indicators use color + icon + text (STAT=🔴 red circle + "STAT", urgent=🟡 yellow triangle + "Urgent")
- Touch targets: all interactive elements ≥ 44×44px on touch devices
- Contrast ratios: all text on backgrounds ≥ 4.5:1; priority badges ≥ 4.5:1

## Responsive Behavior
- **Desktop (≥1024px)**: Full schedule board with all modality columns visible; side-by-side charts on dashboard
- **Tablet (768–1023px)**: Condensed board (fewer modality columns visible); stacked charts on dashboard; roster as condensed table
- **Mobile (<768px)**: List view for schedule board (one exam per row); dashboard charts stacked vertically; roster as card list; exam detail panel as full-screen overlay

## UX Principles Applied
- **Progressive disclosure**: Exam details shown on click, not inline; advanced options (override, bulk actions) in expandable toolbar
- **Cognitive load reduction**: Priority-based auto-sorting reduces manual reordering; conflict detection prevents errors before they happen
- **Error recovery**: All operations have undo (board position revert on conflict); bulk operations have confirmation modals listing affected items
- **Trust & safety**: STAT exams visually distinct with red indicators; audit trail for all assignments and overrides; PHI minimized (initials only on board)