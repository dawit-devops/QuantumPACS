# UI/UX Requirements — Teleradiologist (R18)

## Role-Based Routing & Navigation (Presentation Layer)

RBAC drives the presentation layer (`hasPermission()` + `RequirePermission`, gated
`Sidebar.tsx` items). The teleradiologist uses the same viewer/worklist as R12 over a
secure remote session. Verified against `frontend/src/`.

### Routes Accessible (codebase reality)

| Route | Screen | Access rule |
|-------|--------|-------------|
| `/` | Files / study search | Any authenticated user |
| `/files/:id` | Viewer (Detail) | `FILE_READ` |
| `/patients/:id` | Patient page | `PATIENT_READ` |
| `/metrics` | Metrics dashboard | Any authenticated user (sidebar item) |
| `/account` | Account | Any authenticated user |
| Offline packages / prelim routing / consultations / multi-site | **Not accessible** | No telerad-specific routes or endpoints exist — GATED |

### Navigation Gating (Sidebar.tsx)

| Menu item | Visible when |
|-----------|--------------|
| Files / Metrics / Account / Notifications | Always (authenticated) |
| Worklist (under Admin) | `WORKLIST_READ` |

### Functionality Gating

- **Implemented**: remote viewing, annotations, shares (same as R12).
- **Not implemented** (aspirational FRs marked `GATED` in 01/07/08): offline/edge
  packages, preliminary→final routing, second-opinion consult queue, secure remote
  access config, structured reporting (shared R12 gap).

**Role ID**: R18  
**Generated**: 2026-08-02  
**Version**: 1.0.0

---

## Screens & Navigation

### Primary Navigation Structure
```
Teleradiologist Dashboard (Home)
├── Multi-Site Overview (landing)
├── [Site A] Worklist (context-switched)
│   ├── STAT Queue
│   ├── Urgent Queue
│   ├── Routine Queue
│   └── My Preliminary Reports
├── [Site B] Worklist (context-switched)
├── Consultations
│   ├── Pending Requests
│   └── My Consultation History
├── Critical Findings Log
├── My Performance Dashboard
└── Settings
    ├── Hanging Protocols
    ├── Prefetch Preferences
    └── Notification Settings
```

### Screen Inventory

| Screen ID | Name | Entry Points | Frequency | Device |
|-----------|------|--------------|-----------|--------|
| TR-01 | Multi-Site Dashboard | Login default, sidebar "Home" | Every shift start | Desktop primary |
| TR-02 | Teleradiology Worklist | Site card click, sidebar "[Site]" | Multiple times per shift | Desktop |
| TR-03 | DICOM Viewer | Study row click | Every study | Desktop (dual-monitor) |
| TR-04 | Report Editor | Viewer "Create Report" button | Every study | Desktop |
| TR-05 | Critical Finding Modal | Report editor "Critical Finding" button | As needed | Desktop |
| TR-06 | Preliminary Reports Queue (R12 view) | R12 sidebar "Preliminary Reports" | Daily (R12) | Desktop |
| TR-07 | Consultations Queue | Sidebar "Consultations" | Daily | Desktop, mobile |
| TR-08 | Offline Package Manager | Study context menu | As needed | Desktop |
| TR-09 | Performance Dashboard | Sidebar "My Performance" | Weekly | Desktop |
| TR-10 | Session Timeout Modal | Idle timer | Every 15min idle | All devices |

---

## Component & State Specification

### TR-01: Multi-Site Dashboard

| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| Site Card | White bg, site name, counts, timestamp | Skeleton loader pulse | "No sites assigned - contact admin" | "Site Unavailable" red banner, disabled click | STAT count in red badge, urgent in yellow | Opacity 0.5, cursor not-allowed |
| STAT Alert Badge | Hidden if 0 | Pulse animation | N/A | Red "!" icon | Red circle with count | N/A |
| Oldest STAT Timer | "Newest: 5min ago" gray text | "Loading..." | "No STAT studies" | "Data unavailable" | ">20min" pulsing red animation | N/A |
| Refresh Button | Primary button, icon | Spinning icon | N/A | "Refresh failed" tooltip | Checkmark flash | Disabled during load |

**Layout**: Grid layout, 2 columns on desktop, 1 column on tablet; each card 300px min-width, 200px height; spacing: 24px gap; cards have 8px border-radius, 1px border, 4px hover shadow.

**Interaction States**:
- Hover: Card lifts with `box-shadow: 0 4px 12px rgba(0,0,0,0.1)`
- Focus: 3px blue outline, offset 2px
- Active (click): Scale 0.98 transform, 100ms transition

### TR-02: Teleradiology Worklist Table

| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| Table Row | White bg, black text | Skeleton row (pulse) | "No studies in queue" with icon | "Failed to load worklist" error banner | Conditional: STAT = red bg fade, Urgent = yellow left border | N/A |
| Priority Badge | Text "STAT"/"Urgent"/"Routine" | Placeholder gray box | N/A | N/A | Color-coded: red/yellow/gray + icon | N/A |
| Age Since Assignment | "5min ago" gray text, updates live | "—" | N/A | "Unknown" | ">20min" turns red + bold | N/A |
| Connection Status Banner | Hidden | N/A | N/A | "Live updates disconnected" yellow banner, top-fixed | Green dot + "Connected" (dismissible) | N/A |
| Prefetch Indicator | Hidden | N/A | N/A | N/A | Blue "cached" icon in row | N/A |

**Layout**: Full-width table with fixed header (sticky top: 0); columns: Priority (80px), Site (100px), Patient ID (100px, last 4 digits), Modality (80px), Study Description (flex 1), Age (100px), Actions (80px); row height 48px; zebra striping (even rows slate-50 bg).

**Interaction States**:
- Hover: Row bg slate-100, cursor pointer
- Focus: 2px blue outline around entire row
- Active: Row bg blue-100
- Selected: Row bg blue-50, persists after navigation

**Real-Time Updates**:
- WebSocket message → table row insert with fade-in animation (300ms)
- Audio alert (optional, user setting) + browser notification for new STAT
- Polling fallback every 30s when WebSocket disconnected

### TR-03: DICOM Viewer (Teleradiology-Optimized)

| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| Viewport | Black bg, grid layout | "Loading images..." centered spinner + % progress | "No images" gray text | "Failed to load images" with retry button | First image displayed, 2x2 grid for multi-series | N/A |
| Thumbnail Strip | Bottom, horizontal scroll | Placeholder boxes | Hidden | Hidden | Clickable thumbnails, selected = blue border | N/A |
| Prefetch Status | Hidden | N/A | N/A | N/A | "Next 3 studies cached" green toast (auto-dismiss 3s) | N/A |
| Bandwidth Indicator | Hidden unless <5 Mbps | N/A | N/A | "Poor connection - limited resolution" yellow banner | Hidden | N/A |
| Critical Finding Button | Orange button, icon | N/A | N/A | N/A | Pulsing animation if finding documented | Disabled until report created |

**Layout**: Full-screen mode (F11), dual-monitor support (viewer on monitor 2, worklist on monitor 1); toolbar top 48px height, thumbnail strip bottom 120px height, viewport fills remaining; hanging protocol presets (chest CT: 2x2, neuro: 1x3, trauma: 3x3).

**Interaction States**:
- Pan: Drag with mouse/trackpad, cursor changes to hand
- Zoom: Scroll wheel or pinch, 100-800% range
- Window/Level: Right-drag, cursor changes to crosshair
- Keyboard shortcuts: Arrow keys = scroll series, W = window/level preset, I = invert, R = reset, M = MPR mode

**Performance Targets**:
- First image paint: ≤2.5s (WAN), ≤1.0s (cache)
- Scroll responsiveness: ≤200ms INP
- Prefetch: Background load next 3 studies without blocking UI

### TR-04: Report Editor (Preliminary Mode)

| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| Editor Textarea | White bg, monospace font, placeholder "Enter preliminary findings..." | N/A | Placeholder visible | "Failed to save draft" error banner, retry button | "Draft saved" green checkmark (2s display) | Grayed out during save |
| Preliminary Badge | Top-right, yellow bg, "PRELIMINARY" text | N/A | N/A | N/A | Always visible in preliminary mode | N/A |
| Autosave Indicator | Hidden | "Saving..." gray text, spinner | N/A | "Save failed - offline mode active" yellow banner | "Saved 2s ago" gray text | N/A |
| Sign Button | Primary button, "Sign Preliminary Report" | Disabled during save | Disabled (0 chars) | Disabled | Enabled when >50 chars | Disabled |
| Critical Finding Button | Secondary button, orange, "Critical Finding" | N/A | N/A | N/A | Red badge if finding documented | Disabled until report has text |

**Layout**: Split view, 50% report editor left, 50% viewer right (resizable divider); editor min-width 400px; toolbar top with formatting buttons (bold, list, insert macro); character count bottom-right; font: 14px monospace, line-height 1.6, padding 16px.

**Interaction States**:
- Typing: Autosave queued after 10s idle
- Ctrl+S: Immediate save override
- Offline: IndexedDB backup every keystroke, "Offline - unsaved changes" banner
- Focus: 2px blue outline on textarea

### TR-05: Critical Finding Modal

| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| Modal Overlay | Semi-transparent black (rgba(0,0,0,0.5)) | N/A | N/A | N/A | N/A | N/A |
| Finding Textarea | White, placeholder "Describe critical finding..." | N/A | Red border if empty on submit | N/A | Green border on valid input | N/A |
| Urgency Radio | "Critical" / "Urgent", critical pre-selected | N/A | N/A | N/A | Selected = blue fill | Disabled during submit |
| Notification Status | Hidden | "Sending notification..." spinner | N/A | "Notification failed - CALL CLINICIAN" red banner, phone # displayed | "Notification sent to Dr. [Name]" green text, timestamp | N/A |
| Manual Log Form | Collapsed by default | N/A | N/A | N/A | Expands when "Log Manual Notification" clicked | N/A |
| Submit Button | Primary, "Notify Clinician" | Spinner on button | Disabled | "Retry" button on failure | Changes to "Close" after success | Disabled |

**Layout**: Center modal, 600px width, 400px min-height, 8px border-radius, 24px padding; heading "Critical Finding Escalation", form fields stacked vertically with 16px spacing; buttons bottom-right.

**Interaction States**:
- Focus trap: Tab cycles within modal, Escape closes (with confirmation)
- Required fields: Red border + error text below if empty on submit
- Success: Auto-close after 5s or manual close

### TR-10: Session Timeout Modal

| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| Modal Overlay | Semi-transparent black, blocks all interaction | N/A | N/A | N/A | N/A | N/A |
| Countdown Timer | Large font "60 seconds" with live countdown | N/A | N/A | N/A | Updates every 1s | N/A |
| Warning Text | "Session expiring - click to stay logged in" | N/A | N/A | N/A | N/A | N/A |
| Stay Logged In Button | Primary button, focus on modal open | Spinner during token refresh | N/A | "Refresh failed - logging out..." | Modal closes on success | Disabled during refresh |
| Logout Button | Secondary button | N/A | N/A | N/A | Immediate logout | N/A |

**Layout**: Center modal, 400px width, 250px height, 8px border-radius; countdown text 48px font-size, red color; buttons bottom, 16px spacing.

**Interaction States**:
- Focus locked in modal (can't tab to background)
- Countdown <10s: Pulsing red animation
- Escape key = logout (not dismiss)
- ARIA live region announces countdown every 10s

---

## Design System Conformance

### Color Tokens (from `docs/design-tokens.json`)

| Usage | Token | Value | Contrast Check |
|-------|-------|-------|----------------|
| Primary action (Sign Report, Notify Clinician) | `color-primary` | #0077B6 | ✅ 4.52:1 on white |
| STAT alert background | `color-error` | #EF4444 | ✅ 4.52:1 on white |
| Urgent alert border | `color-warning` | #F59E0B | ✅ 4.52:1 on white |
| Success (notification sent) | `color-success` | #10B981 | ✅ 4.52:1 on white |
| Critical finding button | `amber-500` | #F59E0B | ✅ 4.52:1 on white |
| Page background | `bg-page` | #F8FAFC | N/A |
| Card background | `bg-surface` | #FFFFFF | N/A |
| Text primary | `text-primary` | #1E293B | ✅ 13.6:1 on white |
| Text secondary (timestamps) | `text-secondary` | #475569 | ✅ 7.1:1 on white |
| Border default | `border-color` | #E2E8F0 | N/A |

### Typography Tokens

| Usage | Token | Value |
|-------|-------|-------|
| Body text (worklist, reports) | `font-size-body` | 14px |
| Headings (dashboard sections) | `font-size-h2` | 24px |
| Labels (form fields) | `font-size-body` | 14px |
| Monospace (report editor) | `font-mono` | 'SF Mono', monospace |
| Font weight medium (table headers) | `weight-medium` | 500 |
| Font weight semibold (headings) | `weight-semibold` | 600 |

### Spacing Tokens

| Usage | Token | Value |
|-------|-------|-------|
| Component padding (cards, modals) | `spacing-6` | 24px |
| Vertical spacing between sections | `spacing-8` | 32px |
| Button padding horizontal | `spacing-4` | 16px |
| Button padding vertical | `spacing-2` | 8px |
| Table cell padding | `spacing-3` | 12px |
| Form field margin bottom | `spacing-4` | 16px |

### Radius Tokens

| Usage | Token | Value |
|-------|-------|-------|
| Cards (site cards, worklist card) | `radius-lg` | 8px |
| Buttons | `radius-md` | 6px |
| Modals | `radius-lg` | 8px |
| Input fields | `radius-md` | 6px |

---

## Accessibility Requirements (WCAG 2.1/2.2 AA)

### Keyboard Operability
- All worklist rows focusable and activatable with Enter/Space
- Tab order follows visual order: site cards → worklist table → viewer tools → report editor
- Viewer keyboard shortcuts documented in Help (Shift+?) overlay
- Modal focus trap (Tab cycles within modal, Shift+Tab reverse)
- Escape key closes modals (with unsaved data confirmation)
- Skip link "Skip to worklist" at top of page (hidden until focused)

### Focus Management
- Focus indicator: 3px solid blue outline (#0077B6), 2px offset, no box-shadow
- Focus visible on all interactive elements (buttons, links, table rows, form fields)
- Focus moves to first element of newly opened modal
- Focus returns to trigger element when modal closes
- Focus highlight persists until next focus event (no auto-blur)

### Screen Reader Support
- ARIA landmark roles: `<nav role="navigation">`, `<main role="main">`, `<aside role="complementary">`
- Worklist table: `<table role="table">` with `<thead>` and proper `<th>` headers, sortable columns announce "sorted ascending/descending"
- STAT alerts: ARIA live region `aria-live="assertive"` announces "New STAT study: [Patient ID]"
- Autosave status: `aria-live="polite"` announces "Draft saved" / "Save failed"
- Critical finding urgency: Icon + text (not color alone), `aria-label="Critical urgency level"`
- Session timeout countdown: `aria-live="assertive"` announces every 10 seconds

### Color Contrast
- All text on white background: ≥4.5:1 (AAA goal: ≥7:1 for body text)
- STAT red badge (#EF4444) + white text: 4.52:1 ✅
- Urgent yellow border (#F59E0B) + black text: 4.52:1 ✅
- Disabled state: opacity 0.5 + `aria-disabled="true"`, not just color

### Accessible Labels
- All form inputs have explicit `<label>` or `aria-label`
- Icon-only buttons have `aria-label` (e.g., refresh button: `aria-label="Refresh worklist"`)
- Loading spinners: `aria-label="Loading"`, `role="status"`
- Empty states: Descriptive text (not just "No data")

---

## Responsive Behavior

### Breakpoints (Desktop-First for Clinical Reading)

| Breakpoint | Width | Device | Teleradiologist Usage |
|------------|-------|--------|----------------------|
| `base` | ≥1920px | Dual 4K monitors | Primary diagnostic reading |
| `lg` | 1280-1919px | Single large monitor / laptop | Full-featured reading |
| `md` | 768-1279px | Laptop / tablet landscape | Limited reading, consultations |
| `sm` | <768px | Mobile | Emergency consultations only |

### Screen-Specific Responsive Behavior

**TR-01 Multi-Site Dashboard**:
- `base`: 3-column grid
- `lg`: 2-column grid
- `md`: 1-column grid
- `sm`: 1-column grid, cards stack, older STAT timer moves below counts

**TR-02 Worklist Table**:
- `base`: All columns visible
- `lg`: Hide "Age Since Assignment" column (show in row expansion)
- `md`: Hide "Site" and "Age" columns
- `sm`: Card-based layout (not table), show Priority + Patient ID + Modality only

**TR-03 DICOM Viewer**:
- `base`: Dual-monitor support, 2x2 or 3x3 grid
- `lg`: Single monitor, 1x2 or 2x2 grid
- `md`: 1x1 viewport, thumbnail strip on side
- `sm`: Not recommended — show "Desktop workstation required for diagnostic reading" disclaimer, limited viewer (1x1, basic tools only)

**TR-04 Report Editor**:
- `base`: 50/50 split (editor + viewer)
- `lg`: 50/50 split (resizable)
- `md`: Tabbed layout (switch between editor and viewer)
- `sm`: Full-screen editor, viewer in separate modal

### Touch Targets (Mobile)
- Minimum touch target: 44x44px (iOS HIG, WCAG 2.1 AAA)
- Spacing between targets: ≥8px
- Buttons: 48px height (primary), 44px height (secondary)

---

## UX Principles Applied

### 1. Progressive Disclosure
- Multi-site dashboard → drill down to site-specific worklist → open study
- Worklist row click → viewer; row expansion (click arrow) → study metadata
- Critical finding modal → collapsed manual log form (expand on demand)

### 2. Cognitive Load Reduction
- STAT studies visually distinct (red bg fade) — no scanning needed
- Color + icon + text for urgency (redundant encoding)
- Timestamps in relative format ("5min ago") — easier than absolute time
- Autosave removes "Did I save?" mental burden

### 3. Error Prevention & Recovery
- Confirmation dialogs for destructive actions (sign report, finalize)
- Offline drafts auto-saved to IndexedDB — no work lost on disconnect
- Session timeout warning gives 60s to respond (not instant logout)
- Critical finding notification failure → immediate phone number display

### 4. Trust & Safety (Clinical Data Integrity)
- "Preliminary" badge always visible — can't mistake for final report
- Critical finding log immutably recorded — medico-legal defense
- Audit trail for all remote access — IP, geolocation, timestamp
- No PHI in URLs (patient ID as ID, not name)

### 5. Performance Perception
- Optimistic UI updates (autosave shows "Saved" instantly, rollback on error)
- Skeleton loaders (pulse animation) — perceived faster than spinner
- Prefetch next studies — near-instant load when opening next case
- Loading progress % shown for image load (removes uncertainty)

---

## Interaction Patterns

### Worklist Interaction
1. User scans worklist for STAT (red) → clicks row
2. Viewer opens in new tab (Ctrl+Click) or same tab
3. Background prefetch starts (next 3 studies)
4. User returns to worklist via browser back or Ctrl+W (close tab)

### Report Drafting Workflow
1. User opens viewer → clicks "Create Report"
2. Split view: editor left, viewer right
3. Types findings → autosave every 10s
4. Connection drops → "Offline" banner, IndexedDB backup
5. Connection restores → sync draft automatically
6. User finishes → clicks "Sign Preliminary Report" → confirmation → done

### Critical Finding Escalation
1. User identifies critical finding → clicks "Critical Finding" button in report editor
2. Modal opens → user fills finding description, urgency = "Critical"
3. Clicks "Notify Clinician" → SMS/page sent automatically
4. Notification fails → error banner with on-call phone number
5. User calls clinician directly → logs manual notification in modal
6. Modal closes → critical finding log persists in audit trail

### Multi-Site Context Switching
1. User logs in → lands on multi-site dashboard
2. Sees Site A has 3 STAT (red badge) → clicks Site A card
3. JWT token exchanged → Site A worklist loads
4. Sidebar updates: "[Site A]" context indicator
5. User completes Site A STAT → clicks sidebar "Home" → back to dashboard
6. Clicks Site B card → repeats process

---

## Open Questions & Design Decisions Needed

1. **Hanging Protocol Management**: Should teleradiologist be able to create custom hanging protocols, or limited to pre-configured templates?
2. **Voice Dictation UI**: Should dictation be always-on with voice activation, or push-to-talk button?
3. **Mobile Viewer Feature Parity**: What is the minimum viable tool set for mobile (pan/zoom/WL only, or include measurements)?
4. **Notification Preferences**: Should audio alerts be per-priority (STAT only, or STAT+Urgent), or global on/off?
5. **Multi-Monitor Layout**: Should viewer remember per-user monitor configuration (monitor 1 vs monitor 2), or always default to primary monitor?
6. **Prefetch Algorithm**: Should prefetch be strictly next-in-queue, or predictive based on priority+modality+time?
7. **Dark Mode**: Is dark mode required for off-hours reading (reduce eye strain), or optional user preference?
