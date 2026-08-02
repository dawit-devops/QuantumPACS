# UI/UX Requirements — Radiology & Imaging Service QI/QA Team (R05)

**Version**: 1.0.0 (v3.0 scope)
**Status**: Final
**Date**: 2026-08-02

---

## Screen Inventory

| Screen | Route | Purpose | Primary Widgets |
|--------|-------|---------|-----------------|
| **S1** | `/qa/queue` | QA review queue | Filterable table (accession, patient initials, modality, protocol, priority, status), pagination, auto-refresh |
| **S2** | `/qa/review/{study_uid}` | QA review form | "Open in Viewer" link + QA form (Pass/Fail, dose fields, sequence checklist, comments) |
| **S3** | `/qa/protocols` | Protocol registry CRUD | CRUD table + Add Protocol modal with dynamic sequence editor + ACR benchmark editor |
| **S4** | `/qa/actions` | Corrective action inbox | Card list (source badge, issue, study UIDs expandable, status, actions) |
| **S5** | `/qa/incidents` | Incident/retake logging | Incident log form + incidents table (filterable by type, resolved status) |
| **S6** | `/qa/peer-review` | Peer review management | Assignment form (study search, radiologist picker, reason) + peer review list table + comparison modal |
| **S7** | `/qa/dashboard` | Personal compliance dashboard | 4 KPI cards (exams reviewed, compliance %, incidents logged, open actions) with trend sparklines |

---

## Navigation & Information Architecture

```
Sidebar (qa_team role)
├── 📋 QA Queue (/qa/queue) ← Default landing
├── 📝 Review (/qa/review/{study_uid})
├── 📋 Protocols (/qa/protocols)
├── 🔧 Incidents (/qa/incidents)
├── 📬 Corrective Actions (/qa/actions)
├── 👥 Peer Review (/qa/peer-review)
├── 📊 Dashboard (/qa/dashboard)
└── 👤 Account (/account)

Breadcrumb Pattern:
QA Queue > [Review Detail] > [Study UID]
Example: "QA Queue > Review > ACC12345"
```

---

## Component State Matrix (Per Widget)

### S1: QA Queue Table

| State | Visual | Behavior | ARIA |
|-------|--------|----------|------|
| **Loading** | Skeleton rows (5) in table body | `aria-busy="true"` on table | — |
| **Empty** | "No exams pending QA review" with checkmark illustration | "Check completed exams" link | — |
| **Error** | Table-level error banner, retry button | Toast + retry | `aria-live="assertive"` |
| **Success (Populated)** | Data rows with status badges (gray=pending, blue=in_review, green=completed, red=skipped) | Pagination at bottom, auto-refresh timer | `role="grid"` |
| **Success (Filtered)** | Filtered rows, active filter indicator | Clear filter button | — |
| **Focused** | Row highlight, focus ring on first interactive cell | Arrow keys navigate rows | `tabindex="0"` on rows |

### S2: QA Review Form

| State | Visual | Behavior | ARIA |
|-------|--------|----------|------|
| **Loading** | Form fields disabled, spinner on "Open in Viewer" | `aria-busy="true"` on form | — |
| **Empty** | N/A (data always available from queue) | — | — |
| **Error** | Inline field errors (red), form-level error banner | Focus first error on submit | `aria-live="assertive"` on banner |
| **Success (Idle)** | Clean form with Pass/Fail radio, dose fields, sequence checklist, comments textarea | — | — |
| **Success (Submitting)** | "Submit" button → spinner + "Submitting...", form disabled | Polling for API response | `aria-busy="true"` on form |
| **Success (Complete)** | Toast "QA score submitted", form resets, returns to queue | Queue refreshes | `aria-live="polite"` on toast |
| **Focused** | Focus trap within form, Escape returns to queue | Focus on first radio button on open | `aria-labelledby="form-title"` |

### S3: Protocol Registry

| State | Visual | Behavior | ARIA |
|-------|--------|----------|------|
| **Loading** | Skeleton rows in table | `aria-busy="true"` | — |
| **Empty** | "No protocols configured" with "Add Protocol" CTA | Button opens modal | — |
| **Error** | Table error banner, retry | — | `aria-live="assertive"` |
| **Success** | Full table with CRUD actions | Click Edit → modal pre-populated; Click Delete → confirmation dialog | `role="grid"` |
| **Modal (Create)** | Form with all fields, validation errors inline | Auto-save draft to localStorage | `aria-modal="true"`, focus trap |
| **Modal (Edit)** | Pre-populated form, same behavior as Create | — | Same as Create |

### S4: Corrective Action Cards

| State | Visual | Behavior | ARIA |
|-------|--------|----------|------|
| **Loading** | Skeleton cards (3) | `aria-busy="true"` | — |
| **Empty** | "No corrective actions assigned" with checkmark | — | — |
| **Error** | Card-level error banner, retry per card | — | — |
| **Success (Open)** | Card with source badge (R03/R05_self/R06), issue, expand button | Click "Review" → card expands | `role="article"`, `aria-expanded="false"` |
| **Success (Expanded)** | Card expands: study UID list (clickable links), findings textarea, actions textarea, Resolve button | Click "Resolve" → confirmation dialog → status changes | `aria-expanded="true"` |
| **Success (Resolved)** | Card with green "Resolved" badge, resolved date, findings visible | Card cannot be re-opened | `aria-label="Corrective action resolved on {date}"` |
| **Focused** | Card border `--color-primary`, button focus ring | Tab to card, Enter to expand | `tabindex="0"` on card |

### S5: Incident Log Form

| State | Visual | Behavior | ARIA |
|-------|--------|----------|------|
| **Loading** | Form fields disabled | `aria-busy="true"` | — |
| **Empty** | N/A (form always available) | — | — |
| **Error** | Inline field errors + study metadata error banner | Focus first error | `aria-live="assertive"` |
| **Success (Filling)** | Clean form with autocomplete, dropdown, textarea | Autocomplete shows metadata on study UID entry | — |
| **Success (Submitting)** | "Submit" button → spinner | — | `aria-busy="true"` |
| **Success (Complete)** | Toast "Incident logged", form clears, table refreshes | — | `aria-live="polite"` on toast |

### S6: Peer Review Comparison Modal

| State | Visual | Behavior | ARIA |
|-------|--------|----------|------|
| **Loading** | Skeleton layout in modal | `aria-busy="true"` | — |
| **Empty** | "No peer review data" (should not occur) | — | — |
| **Error** | Inline error banner, retry button | — | `aria-live="assertive"` |
| **Success (Loaded)** | Side-by-side: original report (left) + peer review findings (right) + discrepancy badge + Escalate button (if major/critical) | Escalate button triggers confirmation dialog | `role="dialog"`, `aria-modal="true"` |
| **Focused** | Focus trapped in modal, Escape closes | Focus on first interactive element | `aria-labelledby="modal-title"` |

### S7: Personal Compliance Dashboard

| State | Visual | Behavior | ARIA |
|-------|--------|----------|------|
| **Loading** | Skeleton KPI cards (4) | `aria-busy="true"` | — |
| **Empty** | "No QA reviews this week" + "Start Reviewing" CTA | Links to QA Queue | — |
| **Error** | Per-card error banner + retry | Other cards remain functional | `aria-live="assertive"` |
| **Success** | 4 KPI cards with values, trend sparklines, date range selector | Auto-refresh at 5min | `role="region"`, `aria-label` per card |

---

## Design System Conformance

### Existing Tokens Referenced (from `design-tokens.json`)

| Semantic Token | Primitive | Usage in R05 Screens |
|----------------|-----------|----------------------|
| `color-primary` | `primitive.color.blue-600` | Primary buttons, focus rings, active states |
| `color-success` | `primitive.color.emerald-500` | Pass badge, resolved status, success toast |
| `color-warning` | `primitive.color.amber-500` | Warning badge, in-progress status |
| `color-error` | `primitive.color.red-500` | Error badge, Fail radio, error states |
| `color-info` | `primitive.color.indigo-500` | Info badge, in_review status |
| `bg-page` | `primitive.color.slate-50` | Page background |
| `bg-surface` | `primitive.color.white` | Card/widget backgrounds, modals |
| `text-primary` | `primitive.color.slate-800` | Body text, KPI values |
| `text-secondary` | `primitive.color.slate-600` | Secondary text, timestamps |
| `text-muted` | `primitive.color.slate-500` | Muted text, empty states |
| `text-inverse` | `primitive.color.white` | Text on dark backgrounds (badges, buttons) |
| `border-color` | `primitive.color.slate-200` | Card borders, table borders |
| `font-family-base` | `primitive.typography.font-sans` | All text |
| `font-size-body` | `primitive.typography.size-base` (14px) | Body text, table cells |
| `font-size-h3` | `primitive.typography.size-xl` (20px) | Widget titles, modal headers |
| `font-weight-semibold` | `primitive.typography.weight-semibold` (600) | KPI values |
| `spacing-4` | `primitive.spacing.4` (16px) | Base padding |
| `spacing-6` | `primitive.spacing.6` (24px) | Section gaps |
| `radius-md` | `primitive.radius.md` (6px) | Card radius, button radius |
| `radius-lg` | `primitive.radius.lg` (8px) | Modal radius |

### Proposed New Semantic Tokens (R05 Specific)

| Token | Primitive Ref / Value | Description | Usage |
|-------|----------------------|-------------|-------|
| `qa-pass-bg` | `#D1FAE5` | Light green background for pass badge/card | Pass badge, success states |
| `qa-fail-bg` | `#FEE2E2` | Light red background for fail badge/card | Fail badge, error states |
| `incident-warning-bg` | `#FEF3C7` | Amber background for incident cards | Incident type badges, warning states |
| `corrective-action-bg` | `#DBEAFE` | Blue background for corrective action cards | Corrective action card backgrounds |

### Component Spec Extensions (Add to `component-specs.md`)

#### QAReviewForm (New Component)
```
┌─────────────────────────────────────────────────────────────┐
│  Open in Viewer [Link → /files/{uid}]                       │
├──────────────────────────────────┬──────────────────────────┤
│                                  │  Pass/Fail               │
│  [Cornerstone3D Viewer]          │  ○ Pass  ○ Fail         │
│  (opens in new tab)              │                          │
│                                  │  Dose                    │
│                                  │  DLP [450] mGy·cm       │
│                                  │  CTDIvol [22] mGy        │
│                                  │  kVp [120]               │
│                                  │  mAs [200]               │
│                                  │                          │
│                                  │  Required Sequences      │
│                                  │  ☑ Venous (contrast)     │
│                                  │  ☑ Arterial (contrast)   │
│                                  │  ☐ Non-contrast          │
│                                  │                          │
│                                  │  Comments                │
│                                  │  [Good quality, dose OK] │
│                                  │  [500/500 chars]         │
│                                  │                          │
│                                  │  [Cancel] [Submit]       │
└──────────────────────────────────┴──────────────────────────┘
```
**States**: idle, validating, submitting, error, success
**Tokens**: `qa-pass-bg`, `qa-fail-bg`, `--color-primary`, `--color-error`, `--bg-surface`, `--radius-lg`
**Accessibility**: All fields labeled, `aria-invalid` on validation errors, `aria-live="assertive"` on error messages, keyboard nav (Tab through fields, Enter to submit)

#### QAQueueTable (Extends Table)
- Filterable columns: modality (dropdown), status (dropdown), priority (radio), date range
- Status badges: pending (gray), in_review (blue), completed (green), skipped (red)
- Priority badges: stat (red), escalated (amber), routine (gray)
- "Review" action button per row (primary style)
- Virtualized rows (react-window) for 50+ rows
**Tokens**: `Table` tokens + `color-primary` for active filter, status badge colors

#### ProtocolCRUDModal (New Component)
- Form modal: code (required, unique), name (required), modality (dropdown), body part (text)
- Dynamic sequence list: add/remove rows, each row has sequence name + phase + contrast boolean
- ACR benchmark key-value editor: add/remove pairs, key=metric name, value=numeric
- Validation: async code uniqueness check (debounced), ≥1 sequence required
**Tokens**: `Card` tokens + `--color-error` for validation errors

#### CorrectiveActionCard (New Component)
```
┌──────────────────────────────────────────────┐
│  [R03] CT Chest Compliance Gap     [Open]   │
│  Issue: Missing arterial phase in 12/50      │
│  Assigned: 2026-08-02  Status: [Open]       │
│                                              │
│  ▼ Expand (click to reveal)                  │
│  ├─ Studies: ACC12345, ACC12346, ... (50)   │
│  ├─ Findings: [textarea]                     │
│  ├─ Actions Taken: [textarea]                │
│  └─ [Resolve]                                │
└──────────────────────────────────────────────┘
```
**States**: collapsed, expanded, resolved
**Tokens**: `corrective-action-bg`, `--color-primary`, `--color-success`, status badge colors
**Accessibility**: `aria-expanded` on expand button, focus trap on Resolve confirmation dialog

#### PeerReviewComparisonModal (New Component)
```
┌──────────────────────────────────────────────────────┐
│  Peer Review Comparison          [Discrepancy: Minor] │
│  ┌────────────────────┬────────────────────────────┐ │
│  │  Original Report   │  Peer Review Findings      │ │
│  │  (from reports     │  "Agree with original.    │ │
│  │   table)           │   Minor: small pleural     │ │
│  │                    │   effusion not mentioned." │ │
│  └────────────────────┴────────────────────────────┘ │
│                                                      │
│  [Escalate to Service Director]  [Close]            │
└──────────────────────────────────────────────────────┘
```
**States**: loading, loaded, error
**Tokens**: `--bg-surface`, `--text-primary`, discrepancy badge colors (green/amber/red/dark-red)
**Accessibility**: Focus trap, Escape closes, screen reader announces comparison summary

---

## Accessibility Requirements (WCAG 2.2 AA)

### Keyboard Navigation
| Requirement | Implementation |
|-------------|----------------|
| **Tab Order** | Logical: Queue → Review form → Protocol registry → Incidents → Corrective actions → Peer review → Dashboard |
| **Focus Indicators** | 2px solid `--color-primary` outline, offset 2px on ALL interactive elements |
| **Focus Trap** | Modals (protocol CRUD, corrective action resolve, peer review comparison) trap focus; Escape closes |
| **Skip Links** | "Skip to main content" link at top of each QA page |
| **Arrow Key Navigation** | Queue table: arrow keys navigate rows; Protocol form: arrow keys in dynamic sequence list; Corrective action cards: arrow keys between cards |

### Screen Reader Support
| Requirement | Implementation |
|-------------|----------------|
| **ARIA Landmarks** | `<nav>` for sidebar, `<main>` for content, `<section>` for each widget with `aria-label` |
| **Live Regions** | Toast notifications use `aria-live="polite"`; error banners use `aria-live="assertive"`; auto-refresh uses `aria-live="polite"` |
| **Widget Labels** | Every KPI card: `aria-label` with full value + trend; Queue rows: `aria-label` with accession + status; Form fields: associated `<label>` elements |
| **Table Semantics** | All tables use `<table>` with `<th scope="col">` and `role="grid"` for virtualized tables |
| **Chart Accessibility** | KPI sparklines: `role="img"` with `aria-label` summarizing trend |

### Color & Contrast
| Requirement | Implementation |
|-------------|----------------|
| **Contrast Ratio** | All text: ≥ 4.5:1; Large text (≥18px): ≥ 3:1; UI components: ≥ 3:1 |
| **Color Independence** | No information conveyed by color alone: Status badges include text label + icon; Priority badges include text + icon; Discrepancy levels include icon + text |
| **Color-Blind Safe** | Pass/Fail uses checkmark/X icons + color; Incident types use distinct icons per type; All charts tested with Coblis simulator |
| **High Contrast Mode** | `prefers-contrast: more` increases border widths, uses system colors |

### Motion & Animation
| Requirement | Implementation |
|-------------|----------------|
| **Reduced Motion** | `prefers-reduced-motion: reduce` disables: card expand/collapse animations, toast slide-in, modal transitions |
| **Auto-refresh Control** | "Pause auto-refresh" toggle in queue header (persists in localStorage); defaults to on |

---

## Responsive Behavior

### Breakpoints (from `UX-Functionality.md`)

| Breakpoint | Width | QA Queue Layout |
|------------|-------|-----------------|
| `xl` | ≥ 1200px | Full table, all columns visible, modal 600px |
| `lg` | 992-1199px | Table horizontal scroll, modal 90% |
| `md` | 768-991px | Card layout per row, modal full-screen |
| `sm` | 576-767px | Card layout, touch targets 44×44px |
| `xs` | < 576px | Single column, simplified filters |

### Component-Specific Responsive Rules

| Component | ≥ 992px | 768-991px | < 768px |
|-----------|---------|-----------|---------|
| **QAQueueTable** | Full table, all columns | Horizontal scroll, sticky first col | Card per row, swipe to dismiss |
| **QAReviewForm** | Side-by-side (viewer link left, form right) | Stacked (viewer link top, form bottom) | Full-width form, viewer link as button |
| **ProtocolCRUDModal** | 600px modal, full form visible | 90% width modal, scrollable form | Full-screen modal, stacked fields |
| **CorrectiveActionCard** | Full-width cards in 2-col grid | Full-width cards in 1-col | Full-width cards, tap to expand |
| **PeerReviewComparisonModal** | Side-by-side 50/50 split | Stacked (original top, findings bottom) | Full-width stacked, scrollable |

---

## UX Principles Applied

| Principle | Application in R05 Screens |
|-----------|----------------------------|
| **Progressive Disclosure** | Queue shows summary → click Review for detail → click study link for viewer; Corrective actions collapsed by default → expand for details |
| **Cognitive Load Reduction** | Consistent form layout across all QA screens; auto-populate from protocol JSONB; inline validation with clear error messages; no manual data entry where auto-fill available |
| **Error Recovery** | Per-widget retry (not page reload); inline form validation with specific messages; export retry with same parameters; audit log for all actions |
| **Trust & Safety (Clinical Data)** | HIPAA min necessary (initials only in queue, full details on drill-through); audit trail immutable; no PHI in URLs/analytics events; color-blind safe for all status indicators |
| **Efficiency for Daily Use** | Bookmarkable URLs for review pages; keyboard-first navigation; auto-refresh configurable; protocol templates save time; "Start Reviewing" CTA for empty state |

---

## Implementation Notes for Frontend Team

### Component Architecture (React + Ant Design v5)
```
src/
├── qa/
│   ├── QALayout.tsx              # Tab navigation, breadcrumb, auto-refresh toggle
│   ├── QAQueueTable.tsx           # Filterable queue table (S1)
│   ├── QAReviewForm.tsx           # Pass/Fail + dose + sequence checklist (S2)
│   ├── ProtocolRegistry.tsx       # CRUD table + modal (S3)
│   ├── CorrectiveActionList.tsx   # Card list + expand/resolve (S4)
│   ├── IncidentLog.tsx            # Incident form + table (S5)
│   ├── PeerReviewManager.tsx      # Assignment form + comparison modal (S6)
│   └── QADashboard.tsx            # Personal KPI cards (S7)
├── components/
│   ├── QAQueueTable.tsx           # Extends Table with QA-specific columns
│   ├── QAReviewForm.tsx           # Pass/Fail radio + dose fields + sequence checklist
│   ├── ProtocolForm.tsx           # Dynamic sequence editor + ACR benchmark editor
│   ├── CorrectiveActionCard.tsx   # Expandable card with resolve flow
│   ├── IncidentForm.tsx           # Incident log form with autocomplete
│   ├── PeerReviewComparison.tsx   # Side-by-side comparison modal
│   └── QAQueueTable.tsx           # Extends Table with status/priority badges
├── hooks/
│   ├── useQAQueue.ts              # TanStack Query hooks for queue
│   ├── useQAReview.ts             # TanStack Query hooks for review form
│   ├── useProtocols.ts            # TanStack Query hooks for protocol CRUD
│   ├── useCorrectiveActions.ts    # TanStack Query hooks for corrective actions
│   ├── useIncidents.ts            # TanStack Query hooks for incidents
│   ├── usePeerReview.ts           # TanStack Query hooks for peer review
│   └── useQADashboard.ts          # TanStack Query hooks for personal dashboard
└── styles/
    ├── qa.module.css              # CSS Modules with token references
    ├── protocol-form.module.css   # Protocol form-specific styles
    └── peer-review.module.css     # Peer review comparison styles
```

### Data Fetching Strategy
- **QA Queue**: `useQuery` with `staleTime: 1min`, `refetchInterval: 1min`
- **QA Review Form**: `useQuery` for initial load + `useMutation` for submit
- **Protocol CRUD**: `useQuery` for list + `useMutation` for create/update/delete
- **Corrective Actions**: `useQuery` with `staleTime: 5min`
- **Incidents**: `useQuery` for list + `useMutation` for log
- **Peer Review**: `useQuery` for list + `useMutation` for assign/submit
- **Dashboard**: `useQuery` with `staleTime: 5min`, `refetchInterval: 5min`
- **All**: Error boundaries per widget; fallback UI per state matrix