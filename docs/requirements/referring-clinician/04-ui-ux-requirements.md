# UI/UX Requirements — Referring Clinician (R14)

## Role-Based Routing & Navigation (Presentation Layer)

The referring clinician is the only **unauthenticated** persona: access is via a
share link (`/view/:key`, `tempKey` mode). `ProtectedRoute` accepts `tempKey` as an
alternative to `userId`; the sidebar is hidden entirely and only the viewer Image tab
renders. Verified against `frontend/src/`.

### Routes Accessible (codebase reality)

| Route | Screen | Access rule |
|-------|--------|-------------|
| `/view/:key` | Share-link viewer (Image tab only) | `tempKey` share key (no login) |
| `/login` | Redirect target on expired/invalid key | — |
| Portal / report retrieval / order status | **Not accessible** | No portal routes or endpoints exist — GATED |

### Navigation Gating

- No sidebar, no other tabs (Data/Share/Changes/Admin all hidden), no downloads, no
  annotation persistence, no mutations.

### Functionality Gating

- **Implemented**: view images via share link, measure/annotate locally (not
  persisted).
- **Not implemented** (aspirational FRs marked `GATED` in 01/07/08): order
  placement, exam status tracking, report retrieval, results notification,
  follow-up requests, SSO portal.

**Version**: 1.0.0 (v3.0 scope)
**Status**: Final
**Date**: 2026-08-02

---

## Screens & Navigation

| Screen ID | Screen Name | Entry Point | Navigation |
|-----------|-------------|-------------|------------|
| S1 | Share-link viewer | `/share/{key}` | Direct link; no navigation bar |
| S2 | SSO login | `/login/sso` | Redirect from IdP |
| S3 | Study list | `/studies` | Sidebar → Studies |
| S4 | Study detail | `/studies/{study_uid}` | Click row in study list |
| S5 | Notifications | `/notifications` | Sidebar → Bell icon |
| S6 | Follow-up request form | Study detail → "Request Follow-Up" | Modal on S4 |
| S7 | Share links management | `/share/links` | Sidebar → Share Links |

### Navigation Hierarchy

```
SSO Login (S2) → Study List (S3) → Study Detail (S4) → Follow-up Form (S6)
Share Link (S1) → Study Detail (S4)
Notifications (S5) → Study Detail (S4)
Study List (S3) → Share Links (S7)
```

### Entry Points

- **Share link**: Direct URL `/share/{key}` — no sidebar, no navigation, minimal UI
- **SSO login**: `/login/sso` — SSO button, no PACS login form
- **Study list**: `/studies` — main dashboard for referring clinicians
- **Study detail**: `/studies/{study_uid}` — viewer + report + metadata

---

## Component & State Spec

### S1: Share-Link Viewer Page

| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| Viewer | Hidden | Spinner | "No images available" | Error banner + retry | Images rendered | N/A |
| Report panel | Hidden | Spinner | "Report pending" | Error banner | Report text | Read-only |
| Error page | Hidden | — | — | Error message + CTA | — | — |

### S2: SSO Login Page

| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| SSO button | Visible | — | — | — | — | — |
| Loading spinner | Hidden | Visible | — | — | — | — |
| Error message | Hidden | — | — | "Authentication failed" + retry | — | — |
| Access denied | Hidden | — | — | "Access not provisioned" | — | — |

### S3: Study List Page

| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| Study table | Hidden | Spinner | "No referred studies found" + CTA | Error banner | Table with rows | — |
| Search field | Empty | — | — | — | — | — |
| Filter dropdowns | Default (all) | — | — | — | — | — |
| Pagination | Hidden | — | — | — | Page controls | — |
| Status badges | — | — | — | — | Color-coded | — |

### S4: Study Detail Page

| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| Viewer | Hidden | Spinner | "No images available" | Error banner + retry | Images rendered | Read-only |
| Metadata panel | Hidden | Spinner | — | Error banner | All fields displayed | Read-only |
| Report panel | Hidden | Spinner | "Report pending" | Error banner | Report text | Read-only |
| Follow-up button | Visible | — | — | — | — | Disabled if no study |
| Critical alert | Hidden | — | — | — | Prominent banner | — |

### S5: Notifications Page

| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| Notification list | Hidden | Spinner | "No notifications" | Error banner | List of notifications | — |
| Badge count | 0 | — | — | — | Unread count | — |
| Dropdown | Closed | — | — | — | Open with list | — |

### S6: Follow-Up Request Modal

| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| Form | Empty | — | — | Validation errors | Confirmation toast | Submit disabled until valid |
| Clinical indication | Empty | — | — | Required field error | — | — |
| Urgency dropdown | "Routine" | — | — | — | — | — |
| Modality dropdown | Empty | — | — | Required field error | — | — |
| Notes textarea | Empty | — | — | — | — | — |

### S7: Share Links Management Page

| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| Share links table | Hidden | Spinner | "No active share links" | Error banner | Table with links | — |
| Revoke button | Visible | — | — | — | — | Confirmation required |
| Expiry badge | — | — | — | — | Color-coded | — |

---

## Design System Conformance

### Existing Tokens Referenced (from `design-tokens.json`)

| Semantic Token | Primitive | Usage in R14 Screens |
|----------------|-----------|----------------------|
| `--color-primary` | `#1677ff` | SSO button, links, active filter |
| `--color-error` | `#ff4d4f` | Error banners, validation errors |
| `--color-success` | `#52c41a` | Success toast, status badges |
| `--color-warning` | `#faad14` | Expiring-soon badge, critical alert |
| `--color-critical` | `#ff0000` | Critical findings alert banner |
| `--bg-surface` | `#ffffff` | Page backgrounds, card backgrounds |
| `--bg-elevated` | `#f5f5f5` | Table header background, modal overlay |
| `--text-primary` | `#1a1a1a` | Body text, metadata labels |
| `--text-secondary` | `#666666` | Metadata values, placeholder text |
| `--radius-lg` | `8px` | Card border-radius, modal border-radius |
| `--radius-md` | `4px` | Button border-radius, input border-radius |
| `--spacing-xs` | `4px` | Internal padding for compact UI |
| `--spacing-sm` | `8px` | Gap between form fields |
| `--spacing-md` | `16px` | Section padding, card padding |
| `--spacing-lg` | `24px` | Page padding, section margins |
| `--font-family` | `Inter, -apple-system, sans-serif` | All text |
| `--font-size-sm` | `12px` | Metadata labels, badges |
| `--font-size-md` | `14px` | Body text, table cells |
| `--font-size-lg` | `16px` | Headings, alert text |
| `--font-size-xl` | `20px` | Page titles |

### Proposed New Semantic Tokens (R14 Specific)

| Token | Primitive / Value | Description | Usage |
|-------|-------------------|-------------|-------|
| `--share-link-banner-bg` | `#e6f7ff` | Background for share-link access banner | S1: banner indicating view-only access |
| `--view-only-badge-bg` | `#f6ffed` | Background for "View Only" badge | S3, S4: badge on viewer |
| `--critical-alert-bg` | `#fff1f0` | Background for critical findings alert | S4: critical findings banner |
| `--followup-modal-width` | `480px` | Modal width for follow-up request | S6: modal width |

---

## Accessibility Requirements

### WCAG 2.2 AA Compliance

| Requirement | Implementation | Verification |
|-------------|---------------|--------------|
| **Keyboard operability** | All interactive elements reachable via Tab; viewer controls have keyboard shortcuts | Manual + axe-core |
| **Focus management** | Focus moves to viewer on page load; focus trapped in modal (S6); focus returns to trigger on modal close | Manual + axe-core |
| **Focus visible** | All interactive elements have visible focus indicator (2px outline, `--color-primary`) | Manual + axe-core |
| **Color contrast** | All text ≥ 4.5:1 against background; critical alert text ≥ 3:1 | Manual + Coblis |
| **ARIA labels** | All custom widgets have `aria-label`; viewer controls have `aria-label="Zoom in"`, etc. | axe-core |
| **Screen reader** | Study list has `<th scope="col">`; viewer announces image index; alerts use `role="alert"` | Screen reader test |
| **Semantic HTML** | Use `<nav>`, `<main>`, `<table>`, `<dl>`, `<dt>`, `<dd>`, `<button>`; no `<div>` soup | axe-core |
| **Error identification** | Form errors are associated with fields via `aria-describedby`; error messages are specific | Manual + E2E |
| **Responsive** | Layout adapts at 320px, 768px, 1024px, 1440px breakpoints | Manual + E2E |
| **Touch targets** | All interactive elements ≥ 44×44px on mobile | Manual + E2E |

### Color-Blind Safe Palette

- Status badges use both color + icon/text: green checkmark (completed), yellow clock (in-progress), blue info (scheduled), gray (available)
- Critical alert uses red background + warning icon (not color alone)
- Expiring-soon badge uses amber background + clock icon

---

## Responsive Behavior

### Breakpoints

| Breakpoint | Target | Layout Changes |
|------------|--------|----------------|
| **Base (≥1024px)** | Desktop | Side-by-side: metadata panel (30%) + viewer (70%) |
| **Medium (768px–1023px)** | Tablet | Stacked: metadata above viewer; collapsible sidebar |
| **Small (320px–767px)** | Mobile | Single column: viewer full-width; metadata in accordion; touch gestures for viewer |

### Desktop Layout (S4)

```
┌─────────────────────────────────────────────────────┐
│  Metadata Panel (30%)    │  Viewer (70%)           │
│  ┌─────────────────────┐ │  ┌───────────────────┐  │
│  │ Patient: J. Doe     │ │  │                   │  │
│  │ MRN: 123456         │ │  │  Cornerstone3D    │  │
│  │ Modality: CT        │ │  │  Viewer           │  │
│  │ Protocol: Chest CT  │ │  │                   │  │
│  │ Date: 2026-08-02    │ │  │  [scroll][WW/WL]  │  │
│  │ Series: 12          │ │  │  [zoom][pan]      │  │
│  │ Referring: Dr. Smith│ │  │                   │  │
│  │ Performing: Dr. Lee │ │  └───────────────────┘  │
│  └─────────────────────┘ │                          │
│  ┌─────────────────────┐ │  ┌───────────────────┐  │
│  │ Report (read-only)  │ │  │ [View Only Badge] │  │
│  │ Findings: ...       │ │  └───────────────────┘  │
│  │ Impression: ...     │ │                          │
│  └─────────────────────┘ │                          │
└─────────────────────────────────────────────────────┘
```

### Mobile Layout (S4)

```
┌─────────────────────────┐
│  Metadata (accordion)   │
│  ▼ Patient: J. Doe     │
│    MRN: 123456         │
│    Modality: CT        │
│    Protocol: Chest CT  │
│    Date: 2026-08-02    │
│    Series: 12          │
│    Referring: Dr. Smith│
│    Performing: Dr. Lee │
├─────────────────────────┤
│  Viewer (full-width)    │
│  ┌───────────────────┐  │
│  │  Cornerstone3D    │  │
│  │  Viewer           │  │
│  │  [pinch-zoom]     │  │
│  │  [swipe-nav]      │  │
│  └───────────────────┘  │
│  [View Only Badge]      │
├─────────────────────────┤
│  Report (collapsible)   │
│  ▼ Findings: ...       │
│    Impression: ...     │
└─────────────────────────┘
```

---

## UX Principles Applied

1. **Progressive disclosure**: Share-link page (S1) shows only viewer + report — no navigation, no sidebar, no settings. Study list (S3) shows only essential columns. Details expand on click.
2. **Cognitive load reduction**: Pre-filled follow-up form (S6) uses template data from the study. Search filters are debounced to avoid overwhelming the user. Status table defaults to most recent first.
3. **Error recovery**: Expired share links show a clear error with a "Request new link" CTA. SSO failures show specific, actionable messages. Form validation errors are inline and specific.
4. **Trust & safety for clinical data**: Read-only viewer is explicitly labeled "View Only". No annotation tools visible. Report is read-only with no edit capability. PHI is never in URLs.
5. **Consistency with design system**: All components use semantic tokens from `design-tokens.json`. No one-off colors or custom styles. Cornerstone3D viewer follows existing PACS viewer patterns.
6. **Mobile-first for share links**: Share-link page (S1) is optimized for mobile since referring clinicians may access it from their phone. Desktop study list (S3) and detail (S4) are desktop-first with mobile adaptation.