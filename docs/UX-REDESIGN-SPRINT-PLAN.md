# QuantumPACS — UX Redesign Sprint Plan

**Version**: 1.0
**Status**: Draft
**Date**: 2026-07-29
**Author**: UI-UX-Pro-Max Design System

---

## Overview

Per-persona UX redesign plan based on:
- 7 user persona documents (`docs/user-flows/persona-*.md`)
- UX functionality spec (`docs/UX-Functionality.md`)
- Current implementation audit (2026-07-29)
- UI-UX-Pro-Max design system recommendations
- 34 permission slugs across 13 resource domains

---

## Design System Foundation

### Brand Colors (Medical Cyan + Teal)

| Role | Light Hex | Dark Hex | Usage |
|------|-----------|----------|-------|
| Primary | `#0891B2` | `#06B6D4` | Buttons, links, active states, primary actions |
| On Primary | `#FFFFFF` | `#FFFFFF` | Text on primary backgrounds |
| Secondary | `#22D3EE` | `#67E8F9` | Info badges, secondary accents |
| Accent | `#16A34A` | `#4ADE80` | Success states, "go" actions |
| Background | `#F0FDFA` | `#0F172A` | Page background (light) / app surface (dark) |
| Foreground | `#134E4A` | `#ECFEFF` | Body text (light) / body text (dark) |
| Card | `#FFFFFF` | `#1E293B` | Card/surface backgrounds |
| Card Foreground | `#134E4A` | `#F1F5F9` | Text on card surfaces |
| Muted | `#E8F1F6` | `#334155` | Subtle backgrounds, disabled states |
| Muted Foreground | `#64748B` | `#94A3B8` | Secondary/helper text |
| Border | `#CCFBF1` | `#334155` | Dividers, borders |
| Destructive | `#DC2626` | `#EF4444` | Delete, errors, destructive actions |
| Ring | `#0891B2` | `#22D3EE` | Focus rings |

### Typography
- **Headings**: Figtree (300–700 weight)
- **Body**: Noto Sans (300–700 weight)
- **Google Fonts**: `https://fonts.googleapis.com/css2?family=Figtree:wght@300;400;500;600;700&family=Noto+Sans:wght@300;400;500;700&display=swap`

### Effects
- Border radius: 4px (inputs) / 6px (buttons) / 8px (cards) / 12px (modals)
- Shadows: Subtle elevation via box-shadow, 4 levels
- Motion: 200–300ms micro-interactions, `power2.out` easing

---

## Sprint Plan

### Sprint P1: Dark Mode + Theme System (All Personas)

**Goal**: Full light/dark mode with `prefers-color-scheme` detection + manual toggle.

**Affected Personas**: All (Radiologist highest impact — dark reading rooms)

**Files**:
- `frontend/src/common/tokens.css` — Add `[data-theme="dark"]` token overrides for all semantic tokens
- `frontend/src/common/theme.ts` — Dual ThemeConfig (light/dark) with Ant Design `algorithm: theme.darkAlgorithm`
- `frontend/src/common/ThemeProvider.tsx` — NEW: React context for theme toggle, system preference detection, localStorage persistence
- `frontend/src/index.tsx` — Wrap app with ThemeProvider
- `frontend/src/common/base.tsx` — Apply `data-theme` attribute to root
- `frontend/src/login/Login.css` — Define both theme variants for gradient
- `frontend/src/detail/Detail.css` — Dark viewer chrome
- `frontend/src/common/Sidebar.css` — Dark sidebar tokens cleanup
- `frontend/src/metrics/Metrics.tsx` — Chart.js dynamic color adaptation
- `frontend/src/metrics/Metrics.css` — Dark card backgrounds

**Acceptance Criteria**:
- [ ] System preference detected on first load (`prefers-color-scheme`)
- [ ] Manual toggle in sidebar footer or top bar
- [ ] Preference persisted in localStorage
- [ ] All semantic tokens defined for both themes
- [ ] Login page renders both variants
- [ ] Viewer chrome (tabs, breadcrumb, toolbar) renders in dark mode
- [ ] Tables, cards, modals render in both themes
- [ ] Chart.js colors adapt to theme
- [ ] No hardcoded hex values remaining in CSS

**UX Patterns**:
- `<ThemeProvider>` at app root reads system preference → stores in state + localStorage
- `const { theme, toggleTheme } = useTheme()` anywhere in tree
- CSS variable architecture: `:root {}` for light, `[data-theme="dark"] {}` for dark overrides
- Chart.js: `onBeforeInit` callback reads current `data-theme` to set chart colors

---

### Sprint P2: Radiologist Viewer — Keyboard Shortcuts + Viewer UX (Radiologist)

**Goal**: Professional PACS-grade keyboard shortcuts and annotation workflow.

**Affected Personas**: Radiologist (#1 daily power user)

**Files**:
- `frontend/src/detail/CornerstoneElement.tsx` — Keyboard event listeners for tool switching, scroll, zoom, WW/WL
- `frontend/src/detail/Detail.tsx` — Keyboard shortcut help modal (`?` hotkey)
- `frontend/src/detail/Detail.css` — Shortcut reference modal styles
- `frontend/src/detail/KeyboardShortcuts.tsx` — NEW: shortcut mapping + help panel

**Keyboard Shortcut Map**:

| Key | Action |
|-----|--------|
| `1` | Window/Level (default right-click) |
| `2` | Pan (default left-click) |
| `3` | Zoom |
| `4` | Length measurement |
| `5` | Angle measurement |
| `6` | Arrow annotation |
| `7` | Rectangle ROI |
| `8` | Ellipse ROI |
| `E` | Eraser |
| `R` | Rotate 90° CW |
| `H` | Horizontal flip |
| `V` | Vertical flip |
| `I` | Invert colors |
| `S` | Save annotations |
| `C` | Clear all annotations |
| `Scroll Up/Down` | Scroll through series slices |
| `Ctrl+Scroll` | Zoom |
| `Shift+Scroll` | WW/WL adjustment |
| `+` / `-` | Zoom in / Zoom out |
| `?` | Toggle keyboard shortcut reference |
| `F` | Toggle fullscreen |
| `←` / `→` | Previous / Next file in series |
| `↑` / `↓` | Previous / Next series |

**Acceptance Criteria**:
- [ ] All 14+ tool shortcuts work in viewer
- [ ] Shortcuts disabled when input/textarea is focused
- [ ] `?` opens keyboard reference modal with categorized shortcuts
- [ ] Fullscreen mode (F) hides chrome, expands viewport
- [ ] Scroll wheel navigates slices by default
- [ ] Modifier+scroll for zoom and WW/WL

---

### Sprint P3: Annotation Management + Measurement Panel (Radiologist + Clinician)

**Goal**: Persistent annotation lifecycle management with measurement panel.

**Affected Personas**: Radiologist (create), Clinician (view)

**Files**:
- `frontend/src/detail/CornerstoneElement.tsx` — Emit measurement data on annotation creation/update/delete
- `frontend/src/detail/MeasurementPanel.tsx` — NEW: collapsible side panel listing all measurements with values
- `frontend/src/detail/Detail.tsx` — Toggle measurement panel, pass annotation state
- `frontend/src/detail/MeasurementPanel.css` — NEW: panel styles

**Acceptance Criteria**:
- [ ] Measurement panel lists all annotations on current file
- [ ] Each entry shows: type (Length, Angle, ROI, Arrow), value (cm/deg/area), series number
- [ ] Click measurement entry → viewport centers on that annotation
- [ ] Delete measurement from panel → removes annotation
- [ ] Panel collapses/expands (default collapsed on < 1200px)
- [ ] Export measurements as CSV button
- [ ] Panel hidden in share-key mode (view-only)

---

### Sprint P4: Accessibility — WCAG AA Compliance (All Personas)

**Goal**: WCAG 2.1 AA compliance for all non-viewer UI + screen reader support for viewer.

**Affected Personas**: All (HIPAA compliance + inclusive design)

**Files**:
- `frontend/src/index.css` — Focus ring tokens, `:focus-visible` styles
- `frontend/src/detail/CornerstoneElement.tsx` — `aria-label` on all toolbar buttons, `role="application"` on viewport, screen reader announcements on tool switch
- `frontend/src/detail/ThumbnailStrip.tsx` — `aria-label` per thumbnail, `role="listbox"`
- `frontend/src/common/Sidebar.tsx` — `aria-current="page"`, landmark roles, skip-to-content link
- `frontend/src/common/base.tsx` — Skip-link at top of layout, `role="main"` on content
- `frontend/src/files/Files.tsx` — `aria-live="polite"` on loading state, sort button labels
- `frontend/src/files/AdvancedSearch.tsx` — Form field associations, error announcements
- `frontend/src/login/Login.tsx` — Autocomplete attributes, focus management on error, `aria-describedby` on errors
- `frontend/src/worklist/Worklist.tsx` — Modal focus trap, status announcements
- `frontend/src/common/MobileNav.tsx` — `aria-current="page"`, larger touch targets
- `frontend/src/common/tokens.css` — Focus ring CSS variables (`--focus-ring-color`, `--focus-ring-width`)
- `frontend/src/metrics/Metrics.tsx` — Chart data table fallback for screen readers, chart `role="img"` with `aria-label`

**Acceptance Criteria**:
- [ ] All icon-only buttons have `aria-label`
- [ ] Focus ring visible on all interactive elements (`:focus-visible`)
- [ ] Skip-to-content link as first focusable element
- [ ] `aria-live="polite"` on search results, loading states, status changes
- [ ] Viewer viewport has `role="application"` with `aria-label`
- [ ] All form inputs have associated labels
- [ ] Focus management after modal open/close and form submission
- [ ] Touch targets ≥ 44×44px
- [ ] Tab order matches visual order
- [ ] `prefers-reduced-motion` disables ornamental animations
- [ ] Screen reader announces tool changes, annotation save status
- [ ] Chart.js charts have accessible data table fallback

---

### Sprint P5: Consistent Error/Loading/Empty States (All Personas)

**Goal**: Standardized state pattern across all pages — no more bare `message.error()` toasts.

**Affected Personas**: All

**Files**:
- `frontend/src/common/PageState.tsx` — NEW: `<PageState loading={...} error={...} empty={...} />` wrapper component
- `frontend/src/common/ErrorDisplay.tsx` — NEW: contextual error card with retry button and error details
- `frontend/src/common/EmptyState.tsx` — Refactor: accept contextual message prop, optional action CTA
- `frontend/src/files/Files.tsx` — Replace table spinner with PageState, contextual empty ("No studies match your search"), retry on error
- `frontend/src/worklist/Worklist.tsx` — Replace table spinner with PageState
- `frontend/src/patient/Patient.tsx` — Contextual empty ("Patient has no studies")
- `frontend/src/detail/Detail.tsx` — Error state for viewer init failure with retry
- `frontend/src/detail/CornerstoneElement.tsx` — Error overlay on viewport (not toast), loading progress bar
- `frontend/src/metrics/Metrics.tsx` — Skeleton → PageState pattern, error card
- `frontend/src/logs/Logs.tsx` — PageState integration
- `frontend/src/replicas/Replicas.tsx` — PageState integration
- `frontend/src/routing/RoutingRules.tsx` — PageState integration
- `frontend/src/tenants/Tenants.tsx` — PageState integration
- `frontend/src/users/Users.tsx` — PageState integration
- `frontend/src/roles/Roles.tsx` — PageState integration

**PageState Component API**:
```tsx
interface PageStateProps {
  loading?: boolean;
  error?: { message: string; retry?: () => void } | null;
  empty?: { message: string; action?: { label: string; onClick: () => void } } | null;
  children: React.ReactNode;
}
```

**Priority States** (highest displayed): `error > loading > empty > children`

**Acceptance Criteria**:
- [ ] Every data-fetching page uses `PageState` wrapper
- [ ] Loading shows skeleton placeholders (not just Ant Design table spinner)
- [ ] Error shows contextual card with retry button + error description
- [ ] Empty shows contextual message + optional action button
- [ ] Transitions between states are smooth (fade, no layout shift)
- [ ] Standardized timing: loading < 300ms shows nothing, > 300ms shows skeleton

---

### Sprint P6: Search UX Redesign (Radiologist + Technologist + Clinician)

**Goal**: Professional-grade study search with autocomplete, saved searches, and visual previews.

**Affected Personas**: Radiologist, Technologist, Clinician (all search)

**Files**:
- `frontend/src/files/Files.tsx` — Search bar with autocomplete dropdown, debounced query, result count badge
- `frontend/src/files/AdvancedSearch.tsx` — Full redesign: modality picker, date range picker, DICOM tag autocomplete, visual condition builder
- `frontend/src/files/Files.css` — Search bar styles, autocomplete dropdown, study thumbnails
- `frontend/src/files/SavedSearches.tsx` — NEW: saved search presets (sidebar or top bar dropdown)
- `frontend/src/files/SearchAutocomplete.tsx` — NEW: debounced autocomplete component

**Acceptance Criteria**:
- [ ] Global search shows autocomplete suggestions (patient name, ID, accession#) after 2 chars, 300ms debounce
- [ ] Result count displayed: "Showing 1-10 of 143 studies"
- [ ] Advanced search has modality multi-select, date range, structured DICOM tag inputs
- [ ] Saved searches: save current search as named preset, load from dropdown
- [ ] Recent searches: last 5 unique searches shown below search bar on focus
- [ ] Search state in URL is structured (not raw JSON)
- [ ] Advanced search works offline gracefully (cached recent queries)

---

### Sprint P7: Worklist + Technologist Workflow (Technologist)

**Goal**: Complete modality worklist experience with batch operations, upload feedback, and study verification.

**Affected Personas**: Technologist

**Files**:
- `frontend/src/worklist/Worklist.tsx` — Redesign: status tabs (Scheduled/Performed/Cancelled), batch actions, station AE title filter, calendar view toggle
- `frontend/src/worklist/Worklist.css` — NEW: worklist-specific styles
- `frontend/src/worklist/CreateEntry.tsx` — NEW: dedicated create page (vs modal), with modality picker, station AE autocomplete
- `frontend/src/files/Files.tsx` — Upload progress bar component, drag-and-drop zone
- `frontend/src/files/UploadZone.tsx` — NEW: drag-and-drop upload with progress per file

**Acceptance Criteria**:
- [ ] Worklist status tabs filter entries without full page reload
- [ ] Batch operations: select multiple → cancel all / mark performed
- [ ] Station AE Title dropdown filter in worklist
- [ ] Calendar view toggle (day/week view of scheduled procedures)
- [ ] Upload progress bar with per-file status, estimated time
- [ ] Drag-and-drop zone for DICOM files on Files page
- [ ] Study verification: side-by-side worklist + study details after C-STORE
- [ ] "Verify" button: after study arrives, technologist can mark worklist entry as verified

---

### Sprint P8: PACS Admin — Dashboard + Management UX (PACS Admin)

**Goal**: Proactive system management with visual tools, better data displays, and actionable insights.

**Affected Personas**: PACS Admin

**Files**:
- `frontend/src/metrics/Metrics.tsx` — Time range picker (24h, 7d, 30d, 90d), auto-refresh toggle, comparison period selector
- `frontend/src/metrics/Metrics.css` — Chart responsiveness, dark mode adaptation
- `frontend/src/metrics/MetricsSkeleton.tsx` — Match actual layout (6 stat cards, 3 chart areas)
- `frontend/src/routing/RoutingRules.tsx` — Visual condition builder (JSON → form fields), condition preview, test-rule button
- `frontend/src/routing/RoutingRules.css` — NEW: condition builder styles
- `frontend/src/routing/RuleConditionBuilder.tsx` — NEW: visual condition builder component (modality dropdown, operator select, value input, AND/OR groups)
- `frontend/src/logs/Logs.tsx` — Event type filter chips, date range filter, export to CSV, real-time stream toggle
- `frontend/src/logs/Logs.css` — NEW: log-specific styles
- `frontend/src/tenants/Tenants.tsx` — Storage usage bar per tenant (color-coded: green < 50%, orange 50-75%, red > 75%), quick-action buttons
- `frontend/src/tenants/Tenants.css` — NEW: tenant card styles
- `frontend/src/replicas/Replicas.tsx` — Storage tier labels, health indicators, sync progress bar
- `frontend/src/users/Users.tsx` — Bulk user import modal (CSV upload), role comparison tooltip
- `frontend/src/service-keys/ServiceKeys.tsx` — Expiry indicator, last-used column, copy-key button

**Acceptance Criteria**:
- [ ] Metrics dashboard has time range selector + auto-refresh (30s interval)
- [ ] Metrics skeleton matches actual dashboard layout
- [ ] Routing rules have visual condition builder (no raw JSON editing required)
- [ ] Test-rule button: test routing rule against a selected study ID
- [ ] Audit logs: event type filter chips, date range picker, CSV export, real-time stream toggle
- [ ] Tenant list shows storage usage as color-coded progress bars
- [ ] Replica list shows health indicators + sync progress for in-progress syncs
- [ ] Bulk user import via CSV with preview + validation
- [ ] Service keys show expiry warning (yellow < 7 days, red < 1 day)

---

### Sprint P9: Mobile + Clinician Experience (Clinician)

**Goal**: Touch-optimized mobile viewer, share-link experience polish, PWA improvements.

**Affected Personas**: Clinician (mobile review), Technologist (tablet)

**Files**:
- `frontend/src/detail/CornerstoneElement.tsx` — Touch-optimized toolbar (swipe between slices, pinch zoom, tap to toggle toolbar), bottom sheet annotation panel
- `frontend/src/detail/Detail.tsx` — Mobile-specific layout: full-viewport on mobile, bottom action bar, swipe navigation
- `frontend/src/detail/Detail.css` — Mobile breakpoints (375px, 600px, 768px), bottom sheet styles, gesture hints
- `frontend/src/detail/MobileToolbar.tsx` — NEW: floating bottom toolbar for mobile viewer with essential tools only (Pan, Zoom, WW/WL, Length, Scroll)
- `frontend/src/common/MobileNav.tsx` — Admin submenu access on mobile, notification badge slot
- `frontend/src/common/Sidebar.tsx` — Drawer-style on mobile (slide from left)
- `frontend/src/common/base.tsx` — Safe-area-inset support, viewport height fix for mobile browsers
- `frontend/src/detail/Share.tsx` — Share link UX improvements: QR code generation, copy with visual feedback, email/SMS integration via native share API
- `frontend/src/files/Files.tsx` — Card layout on mobile (instead of table), swipe-to-navigate between studies
- `frontend/src/index.css` — Mobile viewport meta, touch-action, overscroll behavior

**Acceptance Criteria**:
- [ ] Mobile viewer: full-screen viewport, floating toolbar with 5 essential tools
- [ ] Swipe gesture navigates between slices
- [ ] Pinch-to-zoom works on viewport
- [ ] Bottom sheet shows annotation list (swipe up)
- [ ] Share link: QR code generation, native share API integration
- [ ] Mobile sidebar: drawer-style with overlay
- [ ] Files page: card layout on mobile (< 768px), table on desktop
- [ ] Safe-area-inset respected for notched devices
- [ ] Touch targets ≥ 44×44px on mobile
- [ ] PWA: install prompt, offline fallback page, proper icons

---

### Sprint P10: Design Token Adoption + Visual Polish (All Personas)

**Goal**: All components consume CSS tokens consistently. Visual polish across the entire app.

**Affected Personas**: All

**Files**:
- `frontend/src/common/tokens.css` — Complete audit: ensure all 60+ tokens are consumed
- `frontend/src/index.css` — Scrollbar styling, selection colors, focus tokens, `prefers-reduced-motion`
- All `*.css` files — Replace hardcoded hex values/raw values with CSS variable references
- `frontend/src/common/Sidebar.css` — Token-based backgrounds, text colors
- `frontend/src/files/Files.css` — Token-based highlight, border, spacing
- `frontend/src/detail/Detail.css` — Token-based chrome, tab styles
- `frontend/src/detail/CornerstoneElement.css` — Token-based overlay, toolbar styles
- `frontend/src/detail/ThumbnailStrip.css` — Token-based selected state
- `frontend/src/login/Login.css` — Token-based gradient
- `frontend/src/metrics/Metrics.css` — Token-based cards, chart containers
- `frontend/src/common/MobileNav.css` — Token-based background, active color

**Spacing Audit**:
- All padding/margin/gap values should use the 4px/8px spacing system
- Section spacing: 16/24/32/48px tiers by hierarchy
- Component spacing: consistent padding per component type

**Acceptance Criteria**:
- [ ] Zero hardcoded hex values in CSS (all via `var(--*)` or Ant Design theme)
- [ ] All spacing values follow 4px/8px rhythm
- [ ] Scrollbar styling matches brand (thin, theme-aware)
- [ ] Selection color matches brand
- [ ] `prefers-reduced-motion` disables all non-essential animations
- [ ] Consistent border-radius per element type
- [ ] Print styles: hide sidebar, nav, non-essential chrome

---

### Sprint P11: Animation + Micro-interactions (All Personas)

**Goal**: Purposeful motion that enhances usability, not decoration.

**Affected Personas**: All

**Files**:
- `frontend/src/common/tokens.css` — Motion tokens: `--duration-fast: 150ms`, `--duration-normal: 250ms`, `--duration-slow: 400ms`, `--easing-standard`, `--easing-enter`, `--easing-exit`
- `frontend/src/common/base.tsx` — Page transition wrapper (fade + translateY, 250ms)
- `frontend/src/files/Files.tsx` — Staggered table row entrance, search results transition
- `frontend/src/common/Sidebar.tsx` — Smooth collapse/expand with width transition
- `frontend/src/detail/Detail.tsx` — Tab content transition, breadcrumb dropdown animation
- `frontend/src/detail/CornerstoneElement.tsx` — Tool activation spring (transform scale), annotation creation pop
- `frontend/src/common/MobileNav.tsx` — Active indicator spring animation
- `frontend/src/login/Login.tsx` — Card entrance animation, form field staggered reveal
- `frontend/src/common/PageState.tsx` — Fade transition between loading/error/content states
- `frontend/src/metrics/Metrics.tsx` — Stat card counter animation (count up), chart entrance stagger

**Animation Principles**:
- Exit animations faster than enter (150ms vs 250ms)
- Spring physics for UI interactions (tool toggle, nav active state)
- Standard easing for page transitions (`power2.out`)
- No animation when `prefers-reduced-motion: reduce`
- No layout-shifting animations

**Acceptance Criteria**:
- [ ] Page transitions: subtle fade + translateY (250ms, power2.out)
- [ ] Sidebar collapse: smooth width transition (200ms)
- [ ] Table rows: staggered entrance on search/filter
- [ ] Tool toggle: spring animation (100ms)
- [ ] Annotation create: brief scale pop (150ms)
- [ ] Stat cards: count-up animation on metrics page
- [ ] All animations respect `prefers-reduced-motion`
- [ ] Motion tokens consumed from CSS variables (not hardcoded)

---

### Sprint P12: Onboarding + Help System (All Personas)

**Goal**: First-run tour, contextual help, keyboard shortcut reference.

**Affected Personas**: Radiologist (high), Clinician (medium), Technologist (low)

**Files**:
- `frontend/src/common/OnboardingTour.tsx` — NEW: first-login tour overlay (3 steps: search, viewer, sharing)
- `frontend/src/common/ContextualHelp.tsx` — NEW: tooltip-based help system for viewer toolbar
- `frontend/src/detail/KeyboardShortcuts.tsx` — Already exists (Sprint P2), integrate with help system
- `frontend/src/common/HelpButton.tsx` — NEW: floating help button (bottom-right, `?` icon)
- `frontend/src/common/QuickReference.tsx` — NEW: keyboard shortcut + gesture reference panel
- `frontend/src/App.tsx` — Check first-login flag, trigger tour

**Tour Steps**:
1. **Search**: "Find studies by patient name, ID, or accession number. Use Advanced Search for DICOM tag filtering." (points to Files search bar)
2. **Viewer**: "Interact with images using your mouse or keyboard. Press `?` for shortcuts." (points to viewer viewport)
3. **Share**: "Share studies securely with referring physicians via expiring links." (points to Share tab)

**Acceptance Criteria**:
- [ ] First-login tour triggers once (checked via localStorage flag)
- [ ] Tour is skippable, dismissable, with progress indicator (Step 1/3)
- [ ] Contextual tooltips on all viewer toolbar buttons (on hover)
- [ ] Help button opens Quick Reference panel with shortcuts + gestures
- [ ] Tour respects `prefers-reduced-motion`
- [ ] Tour doesn't block normal app usage (can interact with page behind overlay)

---

## Dependency Graph

```
P1 (Dark Mode) ──────────┬── P5 (States) ── P10 (Token Adoption) ── P11 (Animation)
                          │
P2 (Keyboard Shortcuts) ──┤
                          │
P3 (Measurement Panel) ───┤
                          │
P4 (Accessibility) ───────┤
                          │
P6 (Search UX) ───────────┤
                          │
P7 (Worklist/Tech) ───────┤
                          │
P8 (Admin Dashboard) ─────┤
                          │
P9 (Mobile/Clinician) ────┘
                          │
                    P12 (Onboarding) ── depends on P2 (shortcuts), P6 (search), P9 (mobile)
```

---

## Per-Persona Value Delivery

| Sprint | Radiologist | Technologist | PACS Admin | Clinician |
|--------|-------------|--------------|------------|-----------|
| P1 | ★★★ Dark reading room | ★★ Dark modality station | ★★ Dark admin | ★★ Dark mobile |
| P2 | ★★★ Keyboard shortcuts | — | — | — |
| P3 | ★★★ Measurement panel | — | — | ★ Annotation viewing |
| P4 | ★★ Tab focus | ★★ Screen reader | ★★ Audit a11y | ★★ Mobile a11y |
| P5 | ★ Error states | ★ Error states | ★ Error states | ★ Error states |
| P6 | ★★★ Better search | ★★ Worklist search | — | ★★ Simple search |
| P7 | — | ★★★ Full workflow | — | — |
| P8 | — | — | ★★★ Dashboard | — |
| P9 | ★ Mobile reads | ★★ Tablet on gantry | — | ★★★ Mobile review |
| P10 | ★ Polish | ★ Polish | ★ Polish | ★ Polish |
| P11 | ★★ Motion cues | ★ Motion cues | ★ Motion cues | ★ Motion cues |
| P12 | ★★ Onboarding | — | — | ★★★ First-run help |

★ = nice-to-have | ★★ = important | ★★★ = critical for this persona

---

## Key UX Metrics (Before/After)

| Metric | Before | After Target | Sprint |
|--------|--------|--------------|--------|
| WCAG AA compliance | ~40% | 100% (non-viewer) | P4 |
| Keyboard-accessible tools | 0% | 100% | P2 |
| Consistent error states | 0 pages | 12 pages | P5 |
| Dark mode support | 0% | 100% | P1 |
| Animation/motion tokens | 0 | 6+ | P11 |
| Design token adoption | ~5% of components | 95%+ | P10 |
| Mobile-optimized viewer | Basic | Full touch | P9 |
| Search autocomplete | No | Yes | P6 |
| First-run onboarding | None | 3-step tour | P12 |
| Measurement panel | None | Full | P3 |
