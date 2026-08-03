# UI/UX Requirements — Radiology Trainee/Resident (R13)

## Role-Based Routing & Navigation (Presentation Layer)

RBAC drives the presentation layer (`hasPermission()` + `RequirePermission`, gated
`Sidebar.tsx` items). Verified against `frontend/src/`.

### Routes Accessible (codebase reality)

| Route | Screen | Access rule |
|-------|--------|-------------|
| `/` | Files / study search | Any authenticated user |
| `/files/:id` | Viewer (Detail) | `FILE_READ` |
| `/patients/:id` | Patient page | `PATIENT_READ` |
| `/account` | Account | Any authenticated user |
| Supervised worklist / draft report / teaching files / exam log / feedback | **Not accessible** | No routes or endpoints exist — GATED |

### Navigation Gating (Sidebar.tsx)

| Menu item | Visible when |
|-----------|--------------|
| Files / Account / Notifications | Always (authenticated) |
| Admin submenu | Only if granted admin `*_READ` perms |

### Functionality Gating

- **No resident-specific functionality exists** in the codebase — no role distinction
  between resident and staff radiologist today. Supervised reading worklist, draft
  reports, attending review/sign-off, teaching-file capture (de-identification),
  exam log, feedback dashboard, on-call consult, protocol learning, case-conference
  export are all aspirational FRs marked `GATED` (artifacts 01/07/08) — 6+ new
  endpoints flagged to backend.

## Screens & Navigation

### Screen Inventory
| Screen | ID | Entry Point | Navigation |
|--------|----|-------------|------------|
| Supervised Worklist | S-R13-01 | Sidebar → "Supervised Worklist" | Primary view; auto-refreshing table |
| Supervised Study View | S-R13-02 | Click study in worklist | Split-screen: viewer + attending guidance |
| Draft Report Editor | S-R13-03 | Supervised view → "Create Draft" | Full-screen structured editor with DRAFT badge |
| Attending Review Queue (R12) | S-R13-04 | R12 Sidebar → "Resident Review" | R12 view; side-by-side comparison |
| Teaching File Capture | S-R13-05 | Supervised view → "Capture Teaching Case" | Modal with image selector + educational fields |
| Exam List / Portfolio | S-R13-06 | Sidebar → "My Exam List" | Filterable table with export |
| Feedback Dashboard | S-R13-07 | Sidebar → "Feedback & Progress" | Charts + feedback feed |
| On-Call Consult | S-R13-08 | Supervised view → "Request Attending Consult" | Modal + screen-share/guidance panel |
| Protocol Learning | S-R13-09 | Protocol panel → "Educational Annotations" | Side panel with progress tracker |
| Case Conference Prep | S-R13-10 | Supervised view → "Tag for Conference" | List view + export |

### Navigation Hierarchy
```
Sidebar
├── Supervised Worklist (S-R13-01) ──── Primary view
├── Supervised Study View (S-R13-02) ──── From worklist
│   ├── Draft Report Editor (S-R13-03) ──── From study view
│   ├── Attending Guidance Panel ──── Right sidebar
│   ├── Teaching File Capture (S-R13-05) ──── Modal
│   ├── On-Call Consult (S-R13-08) ──── Modal
│   ├── Protocol Learning (S-R13-09) ──── Side panel
│   └── Case Conference Tag ──── Toolbar button
├── My Exam List / Portfolio (S-R13-06)
├── Feedback & Progress (S-R13-07)
└── Case Conference Prep (S-R13-10)
```

### Entry Points
- **Primary**: Sidebar navigation → Supervised Worklist
- **Secondary**: Keyboard shortcut `Ctrl+Shift+R` opens supervised worklist
- **Context**: STAT study notification opens supervised study view directly

### Breadcrumbs/Back Paths
- Supervised Worklist → no parent (top-level view)
- Supervised Study View → back to Worklist (preserves scroll position and filter state)
- Draft Report Editor → back to Supervised Study View
- Teaching File Capture → back to Supervised Study View
- Exam List → back to Supervised Worklist
- Feedback Dashboard → back to Supervised Worklist

---

## Component & State Spec (per screen)

### SupervisedWorklist (S-R13-01)
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| SupervisedWorklist | Empty state: "No studies assigned" with refresh button | Skeleton table rows with pulse animation | Same as default | Red banner "Failed to load worklist" + Retry | Full table with auto-refresh, STAT highlighting, attending column | Table frozen during auto-refresh |

### SupervisedStudyView (S-R13-02)
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| SupervisedStudyView | Closed (not rendered) | Spinner in viewer + guidance panel | "No study selected" message | Red inline error "Failed to load study" | Split-screen: Cornerstone3D viewer + attending guidance panel | Guidance toggle disabled during load |

### DraftReportEditor (S-R13-03)
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| DraftReportEditor | Closed (not rendered) | Spinner in editor | "No draft report" message | Red inline error "Failed to load draft" | Full structured editor with DRAFT badge, auto-save indicator, word counts | Submit button disabled until all sections have content |

### AttendingReviewQueue (S-R13-04) — R12 View
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| AttendingReviewQueue | Empty state: "No drafts pending review" | Skeleton table rows | Same as default | Red banner "Failed to load queue" + Retry | Table with drafts + "Review" action buttons | Review button disabled during API call |

### TeachingFileCapture (S-R13-05)
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| TeachingFileCapture | Modal (opens from study view) | Spinner in modal | "No images selected" message | Red inline error "Failed to load teaching editor" | Image selector + findings + diagnosis + tags + submit | Submit disabled until images + diagnosis filled |

### ExamListPortfolio (S-R13-06)
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| ExamListPortfolio | Empty state: "No studies interpreted yet" | Skeleton table rows | Same as default | Red banner "Failed to load exam list" + Retry | Filterable table with metrics summary + export CSV | Export disabled during generation |

### FeedbackDashboard (S-R13-07)
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| FeedbackDashboard | Empty state: "No feedback yet" | Skeleton chart placeholders | Same as default | Red banner "Failed to load feedback" + Retry | Charts + feedback feed with categories | Filters disabled during load |

### OnCallConsult (S-R13-08)
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| OnCallConsult | Modal (opens from study view) | Spinner in modal | "No on-call attending available" | Red inline error "Failed to request consult" | Study selector + urgency + description + submit | Submit disabled if consult already pending for study |

### ProtocolLearning (S-R13-09)
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| ProtocolLearning | Side panel (opens from protocol panel) | Spinner in panel | "No educational content for this protocol" | Red inline error | Annotations + progress tracker + "Mark Reviewed" | "Mark Reviewed" disabled if already reviewed |

### CaseConferencePrep (S-R13-10)
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| CaseConferencePrep | Empty state: "No cases tagged for conference" | Spinner in list | Same as default | Red banner "Failed to load cases" + Retry | Tagged cases list + "Generate Presentation" | Generate disabled until cases tagged |

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
| `resident-draft-bg` | `rgba(59, 130, 246, 0.05)` | Background for DRAFT badge and draft report editor |
| `resident-guidance-bg` | `rgba(16, 185, 129, 0.05)` | Background for attending guidance panel |
| `resident-teaching-bg` | `rgba(168, 85, 247, 0.05)` | Background for teaching file components |
| `resident-feedback-bg` | `rgba(245, 158, 11, 0.05)` | Background for feedback items |
| `resident-consult-bg` | `rgba(239, 68, 68, 0.05)` | Background for on-call consult banner |
| `resident-progress-bg` | `rgba(59, 130, 246, 0.1)` | Background for progress trackers |

### Components Referenced
- `Table` (existing) — used for worklist, exam list, review queue
- `Cornerstone3D` (existing) — DICOM viewer for study interpretation
- `Modal` (existing) — used for teaching capture, consult request, draft submission
- `Badge` (existing) — priority badges (STAT=red, draft=blue, review=yellow)
- `Toast` (existing) — operation confirmation and error notifications
- `Banner` (existing) — used for auto-save status, consult status, feedback notifications
- `Skeleton` (existing) — loading states for all list/table views
- `Progress` (existing) — protocol learning progress, protocol review progress

---

## Accessibility Requirements
- WCAG 2.2 AA compliance for all screens
- Keyboard operability: Tab through worklist rows, Enter to open study view, Escape to close modals
- Focus indicators: 3px blue outline (`--color-focus: #3B82F6`) on all interactive elements
- ARIA labels: `aria-label="Supervised worklist for {resident_name}"`, `aria-label="Draft report for study {accession}"`
- Screen reader announcements: "Study {accession} assigned — attending: Dr. {name}" on new study; "Draft auto-saved" on auto-save
- Color not used alone: priority indicators use color + icon + text (STAT=🔴 red circle + "STAT"); draft status uses badge + text
- Touch targets: all interactive elements ≥ 44×44px on touch devices
- Contrast ratios: all text on backgrounds ≥ 4.5:1; draft badge ≥ 4.5:1

## Responsive Behavior
- **Desktop (≥1024px)**: Full split-screen supervised view (viewer 70% / guidance 30%); side-by-side review queue for attendings
- **Tablet (768–1023px)**: Supervised view with collapsible guidance panel; stacked charts on feedback dashboard
- **Mobile (<768px)**: Supervised view with bottom-sheet guidance panel; exam list as card list; draft report editor full-screen

## UX Principles Applied
- **Progressive disclosure**: Attending guidance is toggleable; educational annotations are in a side panel; teaching capture is a modal
- **Cognitive load reduction**: Auto-save removes save anxiety; split-screen review reduces context switching for attendings; structured draft editor guides resident
- **Error recovery**: Draft auto-save prevents data loss; consult fallback to written guidance; teaching file revision cycle
- **Trust & safety**: DRAFT badge always visible; attending co-sign required for final reports; teaching files de-identified before publication; PHI minimized on worklist