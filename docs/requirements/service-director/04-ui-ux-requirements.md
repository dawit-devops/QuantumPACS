# UI/UX Requirements — Radiology Service Director (R03)

## Role-Based Routing & Navigation (Presentation Layer)

RBAC drives the presentation layer (`hasPermission()` + `RequirePermission`, gated
`Sidebar.tsx` items). Verified against `frontend/src/`.

### Routes Accessible (codebase reality)

| Route | Screen | Access rule |
|-------|--------|-------------|
| `/` | Files / study search (read) | Any authenticated user |
| `/metrics` | Metrics dashboard | Any authenticated user (sidebar item) |
| `/account` | Account | Any authenticated user |
| `/patients/:id`, `/files/:id` | Patient page, viewer | `PATIENT_READ` / `FILE_READ` |
| `/analytics/*`, `/reports/*` | **Not accessible** | No analytics/report endpoints or routes exist — GATED |

### Navigation Gating (Sidebar.tsx)

| Menu item | Visible when |
|-----------|--------------|
| Files / Metrics / Account / Notifications | Always (authenticated) |
| Admin submenu | Only if granted admin `*_READ` perms (service director typically read-only) |

### Functionality Gating

- Today the service director can only view `GET /metrics` + `/dashboard/metrics`;
  KPI/capacity/protocol-compliance/SLA dashboards, report builder, exports, and
  dashboard-access audit are **not implemented** — aspirational FRs marked `GATED`
  (artifacts 01/07/08) with new endpoints + `ANALYTICS_*` / `REPORT_*` permissions
  flagged to backend.
- Aggregate dashboards must be read-only; no study-level PHI without audit
  justification.

**Version**: 1.0.0 (v3.0 scope)
**Status**: Final
**Date**: 2026-08-02

---

## Screen Inventory

| Screen | Route | Purpose | Primary Widgets |
|--------|-------|---------|-----------------|
| **S1** | `/dashboard` | Daily KPI overview | 4 KPI cards (Volume, Turnaround, Utilization, Staffing), global date range picker, auto-refresh indicator |
| **S2** | `/dashboard/capacity` | Modality capacity heatmap | Heatmap grid (7-day × 24h × 6 modalities), modality tabs, equipment status panel, "Notify Coordinator" modal |
| **S3** | `/dashboard/protocol` | Protocol compliance scorecard | Scorecard table (virtualized), protocol filter chips, gap analysis side panel, corrective action button |
| **S4** | `/dashboard/sla` | SLA tracking & breach alerts | Breach list table (paginated), STAT/Routine toggle, KPI summary cards, escalation status badges |
| **S5** | `/dashboard/reports` | Report Builder | Template gallery (5 cards), parameter modal, generation progress modal, history table (recent reports) |

---

## Navigation & Information Architecture

```
Sidebar (Service Director role)
├── 📊 Dashboard (/dashboard) ← Default landing
│   ├── Overview (S1)
│   ├── Capacity (S2)
│   ├── Protocol (S3)
│   ├── SLA (S4)
│   └── Reports (S5)
└── 👤 Account (/account)

Breadcrumb Pattern:
Dashboard > [Tab Name] > [Drill-through Context]
Example: "Dashboard > Capacity > CT Monday 08:00 (120%)"
```

**Entry Points:**
- Direct: `/dashboard` (bookmarkable)
- From KPI drill-through: `/files?modality=CT&date_range=last_7d` (Files page with context breadcrumb)
- From Report Builder: `/dashboard/reports?template=tpl-01` (deep link to template)

---

## Component State Matrix (Per Widget)

### S1: Dashboard Overview — KPI Card

| State | Visual | Behavior | ARIA |
|-------|--------|----------|------|
| **Loading** | Skeleton card (shimmer) matching final dimensions: 280×140px | `aria-busy="true"`, `aria-label="Study Volume, loading"` | Live region: polite |
| **Empty** | Card with "No data" illustration, "Run first study" CTA button (primary) | Button links to `/files` | `aria-label="No study data available"` |
| **Error** | Card with error banner (red), "Retry" button (secondary), timestamp | Button re-fetches this widget only | `aria-live="assertive"` on error banner |
| **Success** | Value (large), trend icon + %, sparkline (SVG), last-updated timestamp | Hover shows tooltip with 7-day values | `role="region"`, `aria-label="Study Volume: 1,247, up 12% from last week"` |
| **Disabled** | N/A (dashboard always accessible for this role) | — | — |

### S2: Capacity — Heatmap Cell

| State | Visual | Behavior | ARIA |
|-------|--------|----------|------|
| **Loading** | Skeleton grid cell (shimmer) with pattern overlay placeholder | `aria-busy="true"` | — |
| **Empty** | Muted cell with "—" text, pattern overlay for color-blind | `aria-label="No schedule data for CT Monday 08:00"` | — |
| **Error** | Cell with warning icon, tooltip "Failed to load" | Retry button on modality row header | — |
| **Success (Green)** | `--heatmap-low` bg, white text, utilization % | Hover → tooltip with details | `aria-label="CT Monday 08:00: 15 scheduled, 20 capacity, 75% utilization, equipment up"` |
| **Success (Yellow)** | `--heatmap-medium` bg, dark text, utilization % | Same as green | Same as green |
| **Success (Red)** | `--heatmap-high` bg, white text, utilization %, pulsing border | Same + "Notify Coordinator" on click | Same + `aria-pressed="false"` on click |
| **Success (Critical)** | `--heatmap-critical` bg, white text, utilization %, pulsing + crosshatch pattern | Same + escalation badge | Same |
| **Focused** | 2px solid `--color-primary` outline, offset 2px | Keyboard focus trap within modality grid | `tabindex="0"` on each cell |
| **Selected** | Same as focused + `aria-pressed="true"` | Modal open | `aria-modal="true"` on modal |

### S3: Protocol — Scorecard Row

| State | Visual | Behavior | ARIA |
|-------|--------|----------|------|
| **Loading** | Skeleton row (shimmer) across all columns | `aria-busy="true"` on row | — |
| **Empty** | "No protocols configured" message in table body | CTA: "Add Protocol" (admin only) | — |
| **Error** | Row with error cell, retry on row | — | — |
| **Success (Pass)** | Green `--color-success` badge "Pass" with ✓ icon, compliance % | Click → gap panel (empty for pass) | `role="gridcell"`, `aria-label="CT Chest Contrast: 98% compliance, Pass"` |
| **Success (Fail)** | Red `--color-error` badge "Fail" with ✗ icon, compliance % | Click → gap panel with missing sequences | Same + `aria-expanded="true"` when panel open |
| **Focused** | Row highlight (`--table-highlight-bg`), cell focus ring | Arrow keys navigate cells | `role="gridcell"`, `tabindex="0"` |
| **Selected** | Row highlight persists, gap panel open | Escape closes panel, focus returns to row | `aria-controls="gap-panel-{protocol_id}"` |

### S4: SLA — Breach List Row

| State | Visual | Behavior | ARIA |
|-------|--------|----------|------|
| **Loading** | Skeleton rows (5) in table body | `aria-busy="true"` on table | — |
| **Empty** | "No breaches detected" with checkmark illustration | — | — |
| **Error** | Table-level error banner, retry button | — | `aria-live="assertive"` |
| **Success (STAT Breach)** | Red pulsing badge "STAT", minutes overdue in red, radiologist name | Click → study detail modal | `role="row"`, `aria-label="STAT breach: ACC12345, CT Chest, 45 min overdue, Dr. Smith"` |
| **Success (Routine Breach)** | Amber badge "Routine", minutes overdue in amber | Same | Same |
| **Focused** | Row highlight, focus ring on first actionable cell | Arrow keys, Enter opens detail | `tabindex="0"` on row |
| **Escalated** | Badge "Escalated" with ⚠ icon, timestamp | — | `aria-label="Escalated at 2026-08-02 08:15"` |

### S5: Report Builder — Template Card

| State | Visual | Behavior | ARIA |
|-------|--------|----------|------|
| **Loading** | Skeleton card (shimmer) | `aria-busy="true"` | — |
| **Empty** | "No templates available" (should not occur) | — | — |
| **Error** | Card with error, retry | — | — |
| **Success** | Card: icon, name, description, est. time, "Select" button (primary) | Click → parameter modal | `role="button"`, `aria-label="Select Monthly Volume Summary, estimated 30s CSV, 60s PDF"` |
| **Focused** | Card border `--color-primary`, button focus ring | Tab to button, Enter opens modal | — |
| **Selected** | N/A (modal opens) | Modal focus trap | `aria-modal="true"` on modal |

### S5: Report Builder — Parameter Modal

| State | Visual | Behavior | ARIA |
|-------|--------|----------|------|
| **Loading** | Form fields disabled, spinner on "Generate" | `aria-busy="true"` on form | — |
| **Empty** | N/A (defaults pre-filled) | — | — |
| **Error** | Inline field errors (red), form-level error banner | Focus first error on submit | `aria-live="assertive"` on banner |
| **Success (Generating)** | "Generate" button → spinner + "Generating 23%", progress bar, modal dismissible | Polls progress every 5s | `aria-live="polite"` on progress |
| **Success (Complete)** | Toast "Report generated in 42s", file downloads, modal stays open | "Download Another" button | `aria-live="polite"` on toast |
| **Focused** | Focus trap: Tab cycles within modal, Escape closes | Focus returns to template card on close | `aria-labelledby="modal-title"` |

---

## Design System Conformance

### Existing Tokens Referenced (from `design-tokens.json`)

| Semantic Token | Primitive | Usage in R03 Screens |
|----------------|-----------|---------------------|
| `color-primary` | `primitive.color.blue-600` | Primary buttons, focus rings, active states, KPI trend up |
| `color-secondary` | `primitive.color.indigo-500` | Secondary accents, link hover |
| `color-accent` | `primitive.color.cyan-500` | Highlight accents, info badges |
| `color-success` | `primitive.color.emerald-500` | Pass badges, green heatmap, positive trends |
| `color-warning` | `primitive.color.amber-500` | Warning badges, yellow heatmap, routine breaches |
| `color-error` | `primitive.color.red-500` | Error badges, red heatmap, STAT breaches, error states |
| `color-info` | `primitive.color.indigo-500` | Info badges, tooltips |
| `bg-page` | `primitive.color.slate-50` | Dashboard page background |
| `bg-surface` | `primitive.color.white` | Card/widget backgrounds, modals |
| `bg-dark` | `primitive.color.slate-900` | Sidebar, chart tooltip background |
| `text-primary` | `primitive.color.slate-800` | Body text, KPI values |
| `text-secondary` | `primitive.color.slate-600` | Secondary text, timestamps, labels |
| `text-muted` | `primitive.color.slate-500` | Muted text, empty states, placeholders |
| `text-inverse` | `primitive.color.white` | Text on dark backgrounds (sidebar, tooltips) |
| `text-link` | `primitive.color.blue-600` | Links, drill-through breadcrumbs |
| `border-color` | `primitive.color.slate-200` | Card borders, table borders, input borders |
| `font-family-base` | `primitive.typography.font-sans` | All text |
| `font-size-h1` | `primitive.typography.size-3xl` (32px) | Dashboard title |
| `font-size-h2` | `primitive.typography.size-2xl` (24px) | Section headers (Capacity, Protocol, SLA, Reports) |
| `font-size-h3` | `primitive.typography.size-xl` (20px) | Widget titles, modal headers |
| `font-size-body` | `primitive.typography.size-base` (14px) | Body text, table cells, form labels |
| `font-size-sm` | `primitive.typography.size-sm` (13px) | Timestamps, captions, badge text |
| `font-weight-semibold` | `primitive.typography.weight-semibold` (600) | KPI values, headers |
| `font-weight-bold` | `primitive.typography.weight-bold` (700) | Large KPI numbers |
| `spacing-4` | `primitive.spacing.4` (16px) | Base padding, card gaps |
| `spacing-6` | `primitive.spacing.6` (24px) | Section gaps, modal padding |
| `spacing-8` | `primitive.spacing.8` (32px) | Page margins, large gaps |
| `radius-md` | `primitive.radius.md` (6px) | Card radius, button radius |
| `radius-lg` | `primitive.radius.lg` (8px) | Modal radius, table radius |

### Proposed New Semantic Tokens (R03 Specific)

| Token | Primitive Ref / Value | Description | Usage |
|-------|----------------------|-------------|-------|
| `chart-axis-color` | `primitive.color.slate-500` | Chart axis labels, tick marks | All ChartWidget axes |
| `chart-grid-color` | `primitive.color.slate-200` | Chart grid lines | ChartWidget grid |
| `chart-tooltip-bg` | `primitive.color.slate-900` | Chart tooltip background | ChartWidget tooltips |
| `heatmap-low` | `primitive.color.emerald-500` | Under-capacity (<80%) | HeatmapCell green |
| `heatmap-medium` | `primitive.color.amber-500` | Near-capacity (80-95%) | HeatmapCell yellow |
| `heatmap-high` | `primitive.color.red-500` | Over-capacity (95-110%) | HeatmapCell red |
| `heatmap-critical` | `#7F1D1D` | Critical over-capacity (>110%) | HeatmapCell critical (dark red) |
| `kpi-trend-up` | `primitive.color.emerald-500` | Positive trend (volume up, turnaround down) | KPICard trend indicator |
| `kpi-trend-down` | `primitive.color.red-500` | Negative trend (volume down, turnaround up) | KPICard trend indicator |
| `kpi-trend-neutral` | `primitive.color.slate-500` | Neutral trend | KPICard trend indicator |
| `canvas-dropzone-bg` | `primitive.color.slate-50` | Report builder drop zone background | ReportBuilder parameter area |
| `canvas-grid-line` | `primitive.color.slate-200` | Report builder grid lines | ReportBuilder preview grid |

### Component Spec Extensions (Add to `component-specs.md`)

#### KPICard (New Component)
```
┌─────────────────────────────────────┐
│  Study Volume              [⟳] 2m  │
│  ─────────────────────────────────  │
│        1,247        ↑ 12%           │
│  ████▁▂▃▅▂▃▁▂▃▅▂▃▁▂▃▅▂▃▁▂▃▅▂▃▁▂▃▅  │
│  ─────────────────────────────────  │
│  Last updated: 08:15  [Retry]       │
└─────────────────────────────────────┘
```
**States**: loading (skeleton), empty (CTA), error (banner+retry), success (value+trend+sparkline)
**Tokens**: `bg-surface`, `text-primary`, `kpi-trend-*`, `border-color`, `radius-lg`
**Accessibility**: `role="region"`, `aria-label` with full value+trend, focus ring on card

#### HeatmapCell (New Component)
```
┌──────────────┐
│    75%       │  ← green bg, white text
│  ████████    │  ← pattern overlay for color-blind
└──────────────┘
```
**States**: loading, empty, error, success (4 bands), focused, selected
**Tokens**: `heatmap-*`, `text-inverse`, `text-primary`, `radius-sm`
**Accessibility**: `tabindex="0"`, `role="gridcell"`, `aria-label` with full details, arrow key navigation, pattern overlays

#### ScorecardTable (Extends Table)
- Virtualized rows (react-window) for 50+ protocols
- Expandable rows for gap panel (slide-down animation)
- Columns: Code, Name, Modality, Reviewed, Compliance%, Avg Dose, Status, Trend
**Tokens**: `Table` tokens + `color-success/error` for badges

#### ChartWidget (New Component)
- Wrapper for recharts/visx charts with consistent theming
- Responsive SVG (viewBox), legend collapses < 600px
- Tooltip with `chart-tooltip-bg`, `text-inverse`
**Tokens**: `chart-axis-color`, `chart-grid-color`, `chart-tooltip-bg`, `color-primary/secondary/success/warning/error` for series

#### ReportBuilder (New Component)
- Template gallery: 5 cards in responsive grid (2/1 columns)
- Parameter modal: form with date range picker, multi-select, radio group
- Progress modal: determinate progress bar, cancel button
- History table: recent reports with download links
**Tokens**: `Card` tokens + `canvas-dropzone-bg`, `canvas-grid-line`

---

## Accessibility Requirements (WCAG 2.2 AA)

### Keyboard Navigation
| Requirement | Implementation |
|-------------|----------------|
| **Tab Order** | Logical: Dashboard tabs → KPI cards (left-right, top-bottom) → heatmap cells (arrow keys) → scorecard table (arrow keys) → breach list → report builder |
| **Focus Indicators** | 2px solid `--color-primary` outline, offset 2px on ALL interactive elements (cards, cells, buttons, links, form fields) |
| **Focus Trap** | Modals (Report Builder, breach detail, gap panel, notify coordinator) trap focus; Escape closes and returns focus to trigger |
| **Skip Links** | "Skip to main content" link at top of `/dashboard` (hidden until focused) |
| **Arrow Key Navigation** | Heatmap: ←/→ timeslot, ↑/↓ day; Scorecard table: arrow keys between cells; Report parameter modal: arrow keys in multi-select |

### Screen Reader Support
| Requirement | Implementation |
|-------------|----------------|
| **ARIA Landmarks** | `<header>` for dashboard title, `<nav>` for tabs, `<main>` for content, `<aside>` for gap panel, `<section>` for each widget with `aria-label` |
| **Live Regions** | Auto-refresh: `aria-live="polite"` on dashboard root; Breach alerts: `aria-live="assertive"` on breach banner; Progress: `aria-live="polite"` on progress bar |
| **Widget Labels** | Every KPI card: `aria-label="Study Volume: 1,247 studies, up 12% from last week"`; Heatmap cell: `aria-label="CT Monday 08:00: 15 scheduled, 20 capacity, 75% utilization"` |
| **Table Semantics** | Scorecard: `role="grid"` with `role="columnheader"`/`role="rowheader"`; Breach list: standard `<table>` with `<th scope="col">` |
| **Chart Accessibility** | ChartWidget: `role="img"` with `aria-label` summarizing key insight; data table alternative available via "View Data" button |

### Color & Contrast
| Requirement | Implementation |
|-------------|----------------|
| **Contrast Ratio** | All text: ≥ 4.5:1 (WCAG AA); Large text (≥18px): ≥ 3:1; UI components (borders, focus rings): ≥ 3:1 |
| **Color Independence** | No information conveyed by color alone: Trends use icon+color (↑/↓/→); Heatmap uses pattern overlay+color; Status badges use text+icon+color; Breach types use badge text+icon+color |
| **Color-Blind Safe Palettes** | Chart series: Viridis (sequential) or ColorBrewer Set2 (qualitative); Heatmap: pattern overlays per band; All charts tested with Coblis simulator (protanopia, deuteranopia, tritanopia) |
| **High Contrast Mode** | CSS `prefers-contrast: more` increases border widths, removes subtle backgrounds, uses system colors |

### Motion & Animation
| Requirement | Implementation |
|-------------|----------------|
| **Reduced Motion** | `prefers-reduced-motion: reduce` disables: heatmap pulse animation, sparkline transitions, modal slide animations, progress bar animations, auto-refresh transitions |
| **Auto-refresh Control** | "Pause auto-refresh" toggle in dashboard header (persists in localStorage); defaults to on |

---

## Responsive Behavior

### Breakpoints (from `UX-Functionality.md`)

| Breakpoint | Width | Dashboard Layout |
|------------|-------|------------------|
| `xl` | ≥ 1200px | 4-column KPI grid; heatmap full 24h; scorecard full table; breach list full; report gallery 3-col |
| `lg` | 992-1199px | 2-column KPI grid (2×2); heatmap horizontal scroll; scorecard horizontal scroll; breach list full; report gallery 2-col |
| `md` | 768-991px | 1-column KPI stack; heatmap collapsed to modality tabs + horizontal scroll; scorecard card layout; breach list card layout; report gallery 1-col |
| `sm` | 576-767px | Same as md; modal full-screen; touch targets 44×44px minimum |
| `xs` | < 576px | Same as sm; KPI cards full-width; heatmap shows 12h default with "Show 24h" toggle |

### Component-Specific Responsive Rules

| Component | ≥ 992px | 768-991px | < 768px |
|-----------|---------|-----------|---------|
| **KPICard** | 4-col grid, sparkline visible | 2-col grid, sparkline visible | 1-col stack, sparkline hidden (tap to expand) |
| **HeatmapCell** | 24h visible, tooltip hover | 12h default, horizontal scroll, tooltip tap | 6h default, "Show 24h" toggle, modal on tap |
| **ScorecardTable** | Full table, virtualized | Horizontal scroll, sticky first col | Card per protocol, expandable gaps |
| **BreachList** | Full table, pagination | Horizontal scroll, card layout | Card layout, swipe to dismiss (resolved) |
| **ChartWidget** | Full size, legend right | Legend bottom, responsive SVG | Legend collapsible, full-width SVG |
| **ReportBuilder** | 3-col gallery, modal 600px | 2-col gallery, modal 90% | 1-col gallery, modal full-screen |

### Tablet Rounding Mode (768-1024px, touch)
- Simplified KPI view: tap card → full-screen detail with larger touch targets
- Heatmap: swipe between days, pinch to zoom timeslots
- All modals: bottom-sheet style (slide up), 44px minimum touch targets
- Sidebar: collapsible hamburger menu, swipe from left edge

---

## UX Principles Applied

| Principle | Application in R03 Screens |
|-----------|----------------------------|
| **Progressive Disclosure** | Dashboard shows KPI summary; drill-through for detail; heatmap shows utilization %; tap for study list; scorecard shows compliance %; tap for gaps |
| **Cognitive Load Reduction** | Auto-refresh with subtle indicator (no flashing); consistent card layout across tabs; color+icon+text for all status; sparklines for trends without mental math |
| **Error Recovery** | Widget-level retry (not page reload); inline form validation with specific messages; export retry with same parameters; audit log for all actions |
| **Trust & Safety (Clinical Data)** | HIPAA min necessary in aggregates; drill-through requires justification; audit trail immutable; no PHI in URLs/analytics events; color-blind safe for dose maps |
| **Efficiency for Daily Use** | Bookmarkable URLs for drill-through; keyboard-first navigation; 5-min auto-refresh (configurable); template reports with saved parameters; "Last used" template default |

---

## Implementation Notes for Frontend Team

### Component Architecture (React + Ant Design v5)
```
src/
├── dashboard/
│   ├── DashboardLayout.tsx          # Tab navigation, breadcrumb, auto-refresh toggle
│   ├── KPICard.tsx                  # Reusable KPI widget (S1)
│   ├── CapacityHeatmap.tsx          # Heatmap grid + modality tabs (S2)
│   ├── ProtocolScorecard.tsx        # Virtualized table + gap panel (S3)
│   ├── SLATracker.tsx               # Breach list + KPI summary (S4)
│   └── ReportBuilder.tsx            # Template gallery + param modal + progress (S5)
├── components/
│   ├── ChartWidget.tsx              # Themed chart wrapper (recharts/visx)
│   ├── HeatmapCell.tsx              # Individual heatmap cell
│   ├── ScorecardRow.tsx             # Expandable scorecard row
│   ├── BreachRow.tsx                # Breach list row with actions
│   └── TemplateCard.tsx             # Report template selection card
├── hooks/
│   ├── useAnalytics.ts              # TanStack Query hooks for all analytics endpoints
│   ├── useWebSocket.ts              # SSE/WebSocket for capacity real-time
│   └── useReportGeneration.ts       # Polling for report progress
└── styles/
    ├── dashboard.module.css         # CSS Modules with token references
    ├── heatmap.module.css           # Heatmap-specific styles
    └── report-builder.module.css    # Report builder styles
```

### Data Fetching Strategy
- **KPI Dashboard**: `useQuery` with `staleTime: 5min`, `refetchInterval: 5min`, parallel fetch for 4 widgets
- **Capacity Heatmap**: `useQuery` for initial load + `useWebSocket` for real-time updates via `events:ingestion` stream
- **Protocol/SLA**: `useQuery` with `staleTime: 10min`, manual refresh button
- **Report Generation**: `useMutation` for generate, `useQuery` with `refetchInterval: 5s` for progress polling
- **All**: Error boundaries per widget; fallback UI per state matrix

### Performance Optimizations
- **Virtualization**: `react-window` for ScorecardTable (50+ rows), BreachList (100+ rows)
- **Code Splitting**: `React.lazy` for each dashboard tab (loaded on tab click)
- **Memoization**: `React.memo` for KPICard, HeatmapCell, ScorecardRow, BreachRow
- **Chart Rendering**: `recharts` with `ResponsiveContainer`, SVG output for PDF export
- **Bundle**: Dashboard tab chunks < 50KB each gzipped

---

## Design Token Implementation (CSS Custom Properties)

```css
/* In dashboard.module.css */
:root {
  /* Existing semantic tokens (from design-tokens.json) */
  --color-primary: #0077B6;
  --color-success: #10B981;
  --color-warning: #F59E0B;
  --color-error: #EF4444;
  --bg-surface: #FFFFFF;
  --bg-page: #F8FAFC;
  --text-primary: #1E293B;
  --text-secondary: #475569;
  --border-color: #E2E8F0;
  --radius-lg: 8px;
  --spacing-4: 16px;
  --spacing-6: 24px;
  --font-size-body: 14px;
  --font-size-h3: 20px;
  --font-weight-semibold: 600;

  /* R03 Proposed Semantic Tokens */
  --chart-axis-color: #64748B;
  --chart-grid-color: #E2E8F0;
  --chart-tooltip-bg: #0F172A;
  --heatmap-low: #10B981;
  --heatmap-medium: #F59E0B;
  --heatmap-high: #EF4444;
  --heatmap-critical: #7F1D1D;
  --kpi-trend-up: #10B981;
  --kpi-trend-down: #EF4444;
  --kpi-trend-neutral: #64748B;
  --canvas-dropzone-bg: #F8FAFC;
  --canvas-grid-line: #E2E8F0;
}

/* Pattern overlays for color-blind accessibility */
.heatmap-cell--low::before { background-image: none; }
.heatmap-cell--medium::before { background-image: repeating-linear-gradient(45deg, transparent, transparent 4px, rgba(0,0,0,0.1) 4px, rgba(0,0,0,0.1) 8px); }
.heatmap-cell--high::before { background-image: radial-gradient(circle at 2px 2px, rgba(0,0,0,0.15) 1px, transparent 1px); background-size: 8px 8px; }
.heatmap-cell--critical::before { background-image: repeating-linear-gradient(45deg, rgba(0,0,0,0.2), rgba(0,0,0,0.2) 2px, transparent 2px, transparent 4px); }
```

---

## Open Questions for Design Review

1. **Heatmap Timeslot Granularity**: 1-hour slots (24/day) vs 30-min (48/day) — 30-min increases cells 2x, may need virtualization
2. **Sparkline Library**: Use `recharts` AreaChart (adds ~15KB) or custom SVG path (lightweight, less features)?
3. **Report PDF Engine**: Server-side Puppeteer (heavy, full fidelity) vs client-side `jspdf` + `html2canvas` (lighter, pagination issues)?
4. **Auto-refresh Default**: 5min (as specified) or user-configurable (1min/5min/15min/off)?
5. **KPI Card Density**: 4 cards on desktop — should we support customizable dashboard layout (drag-drop) in v3.1?