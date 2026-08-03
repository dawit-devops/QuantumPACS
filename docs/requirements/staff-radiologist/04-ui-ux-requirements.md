# UI/UX Requirements — Staff Radiologist (R12)

## Role-Based Routing & Navigation (Presentation Layer)

RBAC drives the presentation layer (`hasPermission()` + `RequirePermission`, gated
`Sidebar.tsx` items). Verified against `frontend/src/`.

### Routes Accessible (codebase reality)

| Route | Screen | Access rule |
|-------|--------|-------------|
| `/` | Files / study search | Any authenticated user |
| `/files/:id` | Viewer (Detail) — Image/Data/Share/Changes/Admin tabs | `FILE_READ`; Admin tab only with `USER_ADMIN` |
| `/patients/:id` | Patient page | `PATIENT_READ` |
| `/metrics` | Metrics dashboard | Any authenticated user (sidebar item) |
| `/account` | Account | Any authenticated user |
| `/view/:key` | Share-link viewer (read-only, Image tab only) | `tempKey` (no auth) |
| `/reporting/*`, resident-review, peer-review | **Not accessible** | No reporting/review routes or endpoints exist — GATED |

### Navigation Gating (Sidebar.tsx)

| Menu item | Visible when |
|-----------|--------------|
| Files / Metrics / Account / Notifications | Always (authenticated) |
| Worklist (under Admin) | `WORKLIST_READ` |

### Functionality Gating

- **Implemented**: viewer + tools, multi-series navigation, annotations (client
  sync; persistence endpoint to confirm), study metadata + change history, patient
  context, share links, audit.
- **Not implemented** (aspirational FRs marked `GATED` in 01/07/08): structured
  reporting (create/sign), critical-findings escalation, resident attending-review
  queue, peer-review inbox, dedicated priors endpoint.

Design-system conformance: tokens from `docs/design-tokens.json`; components from
`docs/component-specs.md`. The viewer is a specialized surface (Cornerstone3D) —
apply design-system tokens to chrome (toolbars, panels, worklist), and clinical
best practices to the canvas (contrast, color-blind-safe overlays, non-distracting
dark theme).

## Screens & Navigation

| Screen | Route (existing) | Entry Point | Notes |
|--------|------------------|-------------|-------|
| Reading Worklist | `/worklist` | Sidebar / login default | Priority-sorted; STAT first |
| Study Browser | `/dicomweb` | Worklist → Browse | Search + series/instance drill-down |
| Viewer | `/view/:key` | Worklist/Study Browser | Detail + Cornerstone3D |
| Detail view | `/files/:id` (via viewer) | Viewer | Metadata, management, changes |
| Patient context | `/patients/:id` | Viewer/Detail | Demographics + exam history |
| Report panel | (in viewer) | Viewer | GATED on backend |
| Notifications | bell (header) | Header | STAT arrivals (GAP: wiring) |

**IA rules**:
- Worklist is the home screen; everything else is reachable in ≤ 2 steps.
- Viewer chrome is minimal: tools left/right rails, thumbnail strip bottom, status
  top — maximized canvas (clinical priority).
- Report panel docks right, collapsible, never covers the image by default.

## Component & State Spec (per key screen)

### Reading Worklist
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| Study rows | priority, modality, patient, exam, time, priors indicator, read state, holder | Skeleton rows | "No studies awaiting interpretation" | Banner + retry | state transitions | open disabled for studies held by others (read-only instead) |
| STAT banner | top row highlighted (icon+text) | n/a | n/a | n/a | re-sort on arrival | n/a |
| Filters | modality, priority, date, claim state | n/a | "no matches" + clear | retry | filtered list | n/a |

### Viewer
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| Canvas | first instance rendered | progressive-load indicator | "no images" state | failed-instance badge (skip-and-continue) | interactive | n/a |
| Tool rails | active tool highlighted (icon + label) | n/a | n/a | n/a | tool active | tools disabled while no series loaded |
| Thumbnail strip | series thumbnails | skeleton thumbs | "no series" | per-thumb error badge | navigation | n/a |
| Measurement panel | list of measurements with values | n/a | "no measurements" | sync error with retry | synced | n/a |
| Priors drawer | priors list (right drawer) | skeleton | "No priors for this patient" | inline retry | side-by-side view | n/a |
| Report panel (GATED) | findings + impression editors | skeleton | n/a | autosave error banner | autosaved indicator | sign disabled while invalid |

### Study Browser
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| Study results | paginated table (DICOMweb pagination) | skeleton | "No studies match" | retry (incl. ES-down graceful) | drill-down | n/a |
| Series/instance drill-down | nested expand | skeleton | n/a | per-series error | selected series loads | n/a |

## Design System Conformance

- **Chrome tokens**: primary blue-600 `#0077B6`; success emerald-500; warning
  amber-500; error red-500; **viewer uses dark surface** (slate-900 `#0F172A`)
  with slate-100 text — clinical dark theme; contrast ≥ 4.5:1 for all chrome text.
- **Status never color alone**: STAT, failed instances, read states use icon + text.
- **Components**: Ant Design v6 Table/Drawer/Dropdown/Tag/Badge/Skeleton per
  `component-specs.md`; Cornerstone3D canvas is not an Ant component — keep tool
  chrome consistent with the design system.
- **Typography**: Inter for chrome; numeric/measurement values use tabular figures;
  DICOM payloads monospace.

## Accessibility Requirements

- WCAG 2.1/2.2 AA for all chrome UI (worklist, toolbars, drawers, panels): keyboard
  operability, visible focus, contrast, ARIA labels for icon-only tools, aria-live
  for status changes (STAT arrival, autosave).
- The canvas itself is a medical imaging surface: provide keyboard equivalents for
  all tools (already required), screen-reader descriptions of series content, and
  announce measurement additions.
- Color-blind-safe overlays: annotations must not rely on hue alone (stroke style +
  label).

## Responsive Behavior

- **Viewer is desktop-only**: min 1280×800; no mobile rendering.
- Worklist usable on tablet (≥ 768px): table → stacked cards below `md`.
- No resizing below 1024 for the viewer (show "desktop required" state).

## UX Principles Applied

- **Speed and throughput**: keyboard-first, progressive loading, presets, autosave —
  every interaction budgeted (NFR-R12-01/02/05).
- **Trust & safety**: read-state claims prevent double reads; escalation is minimal-
  form; report conflicts explicit; PHI never in URLs (share keys, not raw paths).
- **Progressive disclosure**: viewer chrome collapses (auto-hide rails) to maximize
  canvas; details on demand.
- **Error recovery**: skip-and-continue for failed instances; autosave resilience;
  explicit escalation failures with fallback.
- **Dark clinical theme**: reduce visual fatigue; preserve annotation contrast.
