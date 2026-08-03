# UI/UX Requirements — Other Hospital Staff (R19)

## Role-Based Routing & Navigation (Presentation Layer)

RBAC drives the presentation layer (`hasPermission()` + `RequirePermission`, gated
`Sidebar.tsx` items). Verified against `frontend/src/`.

### Routes Accessible (codebase reality)

| Route | Screen | Access rule |
|-------|--------|-------------|
| `/` | Files / study search (read) | Any authenticated user |
| `/account` | Account | Any authenticated user |
| `/patients/:id`, `/files/:id` | Patient page, viewer | `PATIENT_READ` / `FILE_READ` |
| `/view/:key` | Share-link viewer | `tempKey` (no auth) |
| Limited-scope portal / results notification | **Not accessible** | No portal routes or endpoints exist — GATED |

### Navigation Gating (Sidebar.tsx)

| Menu item | Visible when |
|-----------|--------------|
| Files / Account / Notifications | Always (authenticated) |
| Admin submenu | Only if granted admin `*_READ` perms |

### Functionality Gating

- **Implemented**: view own-patient imaging/results via study browser or share link.
- **Not implemented** (aspirational FRs marked `GATED` in 01/07/08): limited-scope
  portal with order awareness, results notification.

## Screens & Navigation

| # | Screen | Entry Point | Purpose |
|---|--------|-------------|---------|
| 1 | Portal Home | App root | Scoped patient search + recent notifications |
| 2 | Patient View | Search → patient | Demographics (minimal), order status, results |
| 3 | Report View | Patient → report | Read-only finalized report |
| 4 | Read-Only Viewer | Patient → study | Read-only image view (share-link mode reuse) |
| 5 | Notifications | Bell | Finalized-report alerts, no PHI in bodies |
| 6 | Follow-Up Modal | Report → request | Submit follow-up request |

Navigation: search-first portal; patient → orders/results/imaging tabs; back paths preserved.

## Component & State Spec

| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| PatientSearch | Input | Skeleton rows | "No results" | Retry | Rows | — |
| OrderStatusList | Rows | Skeleton | "No orders" | Retry | — | — |
| ReportView | Read-only | Spinner | "No report" | Retry | Rendered | — |
| ReadOnlyViewer | Image | Spinner | "No images" | Error overlay | Rendered | All tools |
| NotificationBell | Badge | — | "No notifications" | Retry | Entries | — |
| FollowUpForm | Fields | — | — | Inline errors | Submitted | During submit |

## Design System Conformance

- Tokens: `--color-primary`, `--color-success`, `--color-warning`, `--bg-surface`, `--radius-sm`.
- Components: reuse `Table`, `Form`, `Tag`, `Badge`, `Empty`, viewer read-only mode; new `PortalHome`, `FollowUpForm` specs.

## Accessibility Requirements

- WCAG 2.2 AA: mobile touch targets ≥ 44px, keyboard fallback, focus rings, contrast ≥ 4.5:1, screen-reader announcements for notifications and scope-denied states.

## Responsive Behavior

- Mobile-first (base 360px); tablet/desktop progressive enhancement; read-only viewer responsive.

## UX Principles Applied

- Transparent scoping (out-of-scope data simply absent); read-only enforcement visible (disabled tools); notification bodies PHI-free; explicit empty states; minimal navigation depth.
