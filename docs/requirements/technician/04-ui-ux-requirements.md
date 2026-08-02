# UI/UX Requirements — Radiology Technician (R07)

## Role-Based Routing & Navigation (Presentation Layer)

RBAC drives the presentation layer (`hasPermission()` + `RequirePermission`, gated
`Sidebar.tsx` items). Verified against `frontend/src/`.

### Routes Accessible (codebase reality)

| Route | Screen | Access rule |
|-------|--------|-------------|
| `/` | Files / study search | Any authenticated user |
| `/worklist` | Modality worklist | `WORKLIST_READ` (admin submenu item) |
| `/metrics` | Metrics dashboard | Any authenticated user (sidebar item) |
| `/account` | Account | Any authenticated user |
| `/files/:id`, `/patients/:id` | Viewer (acquisition QA via viewer), patient page | `FILE_READ` / `PATIENT_READ` |
| `/acquisition/*`, `/exams/*`, fluoroscopy/mammo flows | **Not accessible** | No exam routes/endpoints exist — GATED |

### Navigation Gating (Sidebar.tsx)

| Menu item | Visible when |
|-----------|--------------|
| Files / Metrics / Account / Notifications | Always (authenticated) |
| Worklist (under Admin) | `WORKLIST_READ` |

### Functionality Gating

- Existing: study browser, viewer, worklist (same as R06).
- **Not implemented** (aspirational FRs marked `GATED` in 01/07/08): DR/CR
  acquisition, fluoroscopy (live/spot/cine/DAP), mammography (CC/MLO, compression,
  AGD), retakes, exam completion. Requires `EXAM_*` permissions + endpoints flagged
  to backend.

## Screens & Navigation

### Screen Inventory
| Screen | ID | Entry Point | Navigation |
|--------|----|-------------|------------|
| Worklist | S-R07-01 | Sidebar → "Worklist" | Primary view; auto-refreshing table |
| Exam Detail | S-R07-02 | Click exam row in worklist | Slide-out panel or full-screen |
| Acquisition View | S-R07-03 | Exam detail → "Start Protocol" | Full-screen image preview + QA overlay |
| Dose Monitor | S-R07-04 | Acquisition view sidebar | Persistent dose panel |
| Safety Check | S-R07-05 | Before contrast administration (fluoroscopy) | Modal overlay |
| Incident Log | S-R07-06 | From QA panel or worklist | Modal overlay |
| Fluoroscopy Workflow | S-R07-07 | Modality-specific acquisition view | Live fluoroscopy mode + spot capture + cine |
| Mammography Workflow | S-R07-08 | Modality-specific acquisition view | CC/MLO view selection + compression monitoring |

### Navigation Hierarchy
```
Sidebar
├── Worklist (S-R07-01) ──── Primary view
├── Exam Detail (S-R07-02) ──── From worklist click
│   ├── Acquisition View (S-R07-03) ──── From exam detail
│   │   ├── Dose Monitor (S-R07-04) ──── Sidebar
│   │   ├── Safety Check (S-R07-05) ──── Modal before contrast
│   │   ├── Incident Log (S-R07-06) ──── From QA panel
│   │   ├── Fluoroscopy Workflow (S-R07-07) ──── Modality-specific
│   │   └── Mammography Workflow (S-R07-08) ──── Modality-specific
│   └── Protocol Override (not in R07 scope)
└── Completed Exams ──── History view
```

### Entry Points
- **Primary**: Sidebar navigation → Worklist
- **Secondary**: Keyboard shortcut `Ctrl+Shift+W` opens worklist
- **Context**: STAT exam notification opens exam detail directly

### Breadcrumbs/Back Paths
- Worklist → no parent (top-level view)
- Exam Detail → back to Worklist (preserves scroll position and filter state)
- Acquisition View → back to Exam Detail
- Safety Check → back to Exam Detail
- Incident Log → back to Exam Detail

---

## Component & State Spec (per screen)

### Worklist (S-R07-01)
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| Worklist | Empty state: "No exams assigned" with refresh button | Skeleton table rows with pulse animation | Same as default (no exams assigned) | Red banner "Failed to load worklist" + Retry button | Full table with auto-refresh, STAT highlighting, pagination | Table frozen during auto-refresh |

### ExamDetail (S-R07-02)
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| ExamDetail | Closed (not rendered) | Spinner inside panel | "No exam selected" message | Red inline error "Failed to load exam details" | Full exam info + Confirm Patient button + protocol panel | Confirm button disabled during API call |

### AcquisitionView (S-R07-03)
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| AcquisitionView | Closed (not rendered) | Spinner in viewer area | "No images acquired yet" message | Red inline error "Image preview unavailable" | Full Cornerstone3D viewer with QA overlay + dose panel | Reject/Accept buttons disabled during image load |

### DoseMonitor (S-R07-04)
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| DoseMonitor | Closed (sidebar) | Skeleton placeholder | "No dose data yet" message | Red inline error "Dose tracking unavailable" | Live dose panel with cumulative total and benchmark comparison | Dose panel read-only during acquisition |

### SafetyCheck (S-R07-05)
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| SafetyCheck | Modal (opens before contrast) | Spinner in modal body | "No allergy data available" message | Red inline error "Failed to load safety data" | Full safety check form with allergy info + confirmation | "Proceed" button disabled until checkbox confirmed |

### IncidentLog (S-R07-06)
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| IncidentLog | Modal (opens from QA panel) | Spinner in modal body | "No incidents logged" message | Red inline error "Failed to log incident" | Incident recorded with confirmation toast | Submit button disabled until required fields filled |

### FluoroscopyWorkflow (S-R07-07)
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| FluoroscopyWorkflow | Closed (modality-specific view) | Spinner in viewer area | "No fluoroscopy data" message | Red inline error | Live fluoroscopy feed + spot capture + cine recording + DAP tracker | Spot/cine buttons disabled during live mode |

### MammographyWorkflow (S-R07-08)
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| MammographyWorkflow | Closed (modality-specific view) | Spinner in viewer area | "No mammography data" message | Red inline error | CC/MLO view selection + compression monitor + AGD tracker | Acquisition disabled until view selected |

---

## Design System Conformance

### Tokens Referenced
- **Color**: `--color-primary` (blue #3B82F6), `--color-danger` (red #EF4444), `--color-warning` (yellow #F59E0B), `--color-success` (green #10B981)
- **Typography**: `--font-sans` (Inter), `--text-sm` (14px), `--text-base` (16px), `--text-lg` (18px), `--font-bold` (600)
- **Spacing**: `--space-2` (8px), `--space-3` (12px), `--space-4` (16px), `--space-6` (24px)
- **Radius**: `--radius-md` (8px), `--radius-lg` (12px)
- **Shadow**: `--shadow-sm` (0 1px 2px rgba(0,0,0,0.05)), `--shadow-md` (0 4px 6px rgba(0,0,0,0.07))

### New Semantic Tokens Required
| Semantic Token | Primitive Ref / Value | Description |
|----------------|----------------------|-------------|
| `acquisition-stat-bg` | `rgba(239, 68, 68, 0.1)` | Background for STAT exam blocks on worklist |
| `acquisition-reject-bg` | `#FEE2E2` | Background for rejected image indicators |
| `acquisition-accept-bg` | `#D1FAE5` | Background for accepted image indicators |
| `dose-warning-bg` | `#FEF3C7` | Background for dose warning banner |
| `dose-danger-bg` | `#FEE2E2` | Background for dose limit exceeded banner |
| `safety-alert-bg` | `#FEF2F2` | Background for safety warning banners |
| `fluoro-live-bg` | `rgba(239, 68, 68, 0.05)` | Background for live fluoroscopy mode indicator |
| `mammo-compression-bg` | `#FEF3C7` | Background for compression pressure warning |

### Components Referenced
- `Table` (existing) — used for worklist
- `Cornerstone3D` (existing) — image viewer with QA overlay
- `Modal` (existing) — used for safety check, incident log
- `Badge` (existing) — priority badges (STAT=red, urgent=yellow, routine=gray)
- `Toast` (existing) — operation confirmation and error notifications
- `Banner` (existing) — used for dose warnings, safety alerts, reject notifications
- `Skeleton` (existing) — loading states for worklist and exam detail

---

## Accessibility Requirements
- WCAG 2.2 AA compliance for all screens
- Keyboard operability: Tab through worklist rows, Enter to open exam detail, Escape to close modals
- Focus indicators: 3px blue outline (`--color-focus: #3B82F6`) on all interactive elements
- ARIA labels: `aria-label="Worklist for {technician_name}"`, `aria-label="Exam {accession} - {modality} - {priority}"`
- Screen reader announcements: "Exam {accession} assigned" on new exam; "Image {n} accepted/rejected" on QA action
- Color not used alone: priority indicators use color + icon + text (STAT=🔴 red circle + "STAT"); reject reasons use icons + text
- Touch targets: all interactive elements ≥ 44×44px on touch devices
- Contrast ratios: all text on backgrounds ≥ 4.5:1; dose warning banners ≥ 4.5:1

## Responsive Behavior
- **Desktop (≥1024px)**: Full worklist table; acquisition view with image preview + QA overlay + dose panel side-by-side
- **Tablet (768–1023px)**: Condensed worklist; acquisition view with image preview + dose panel stacked
- **Mobile (<768px)**: List view for worklist; acquisition view with image preview full-screen; dose panel as collapsible bottom sheet

## UX Principles Applied
- **Progressive disclosure**: Exam details shown on click, not inline; advanced options (incident log) in expandable panels
- **Cognitive load reduction**: Auto-refreshing worklist reduces manual checking; real-time QA overlay reduces split attention
- **Error recovery**: Reject images can be re-acquired; dose logging failures allow manual entry; PACS push retries automatically
- **Trust & safety**: Patient safety checks are mandatory gates before contrast; dose limits are prominently displayed; audit trail for all actions