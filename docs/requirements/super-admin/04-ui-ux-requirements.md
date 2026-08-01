# UI/UX Requirements — Super Admin (R01)

Design-system conformance: all colors, typography, spacing, and radius reference
`docs/design-tokens.json` (Ant Design v6, `frontend/src/common/theme.ts`); components
reference `docs/component-specs.md`. No one-off styling.

## Screens & Navigation

| Screen | Route (existing) | Entry Point | Purpose |
|--------|------------------|-------------|---------|
| Dashboard / Health | `/metrics` | Sidebar "Metrics" | System-wide health + platform metrics |
| Tenants | `/tenants` | Sidebar | Tenant CRUD + provision dialog |
| Users | `/users` | Sidebar | User lifecycle + bulk import |
| Roles | `/roles` | Sidebar | RBAC roles + permission catalog |
| Replicas | `/replicas` | Sidebar | Storage replicas + status |
| Routing Rules | `/routing` | Sidebar | DICOM routing rules |
| Service Keys | `/service-keys` | Sidebar | API keys |
| Integrations | `/integrations` | Sidebar | Webhooks + OAuth providers |
| FHIR Config | `/fhir/config` | Integrations | FHIR server + clients + test |
| FHIR Monitoring | `/fhir/monitoring` | Integrations | FHIR request health |
| HL7 Admin | `/hl7` | Integrations | HL7 status + messages |
| Logs | `/logs` | Sidebar | Audit log investigation |
| DICOMweb Admin | `/dicomweb` | Sidebar | Station AE titles + DICOM metrics |
| Notifications | bell (header) | Header | Admin event notifications |

**IA rules**:
- Sidebar groups: System (Dashboard, Tenants, Users, Roles, Replicas, Routing, Service Keys, Logs), Integrations (Webhooks/OAuth, FHIR, HL7, DICOMweb).
- Navigation persists tenant context; super-admin-only items visible only for `SYSTEM_ADMIN`-capable users (`component-specs.md` admin-item pattern).
- Breadcrumb path from any detail back to its list.

## Component & State Spec (per key screen)

### Tenants List
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| Tenant table | rows: name, slug, domain, quota, status, created | Skeleton rows (`MetricsSkeleton` pattern) | Empty state: "No tenants — create the first" + CTA | Banner + retry | Row highlight after create | Actions disabled while provisioning |
| Provision dialog | form fields prefilled (db host/port from defaults) | Spinner + progress note >30s | n/a | Step-level failure banner | One-time password panel (copy + confirm) | Submit disabled while pending |
| Tenant switcher | current tenant name | n/a | "No tenants" | error + keep previous | checkmark on selected | n/a |

### Users List
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| Users table | username, name, email, role, status, created | Skeleton | "No users — add the first" + CTA | Banner + retry | Row updated | n/a |
| Add user modal | form | spinner on submit | n/a | inline field errors | toast + row appears | submit disabled until valid |
| Bulk import | dropzone | progress bar | n/a | per-row error list | report: created/skipped/failed | commit disabled until validation run |

### Roles + Permission Catalog
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| Roles table | name, users count, permission count | Skeleton | "No roles" | Banner | row highlight | delete disabled while assigned users exist |
| Permission catalog | grouped checkboxes + module select-all | spinner | n/a | inline error | count updates | SYSTEM_ADMIN requires confirm modal |

### Replicas List
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| Replica rows | name, type, status (icon+text), last sync | Skeleton | "No replicas configured" | Banner + retry | status refresh | retry disabled while pending |
| Replica detail | expandable: last error, backend info | spinner | n/a | last-error panel | saved toast | n/a |

### Routing Rules
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| Rule list | priority order, drag handles | Skeleton | "No rules — studies route to default" | Banner | reorder persisted | disabled destination badge |
| Condition builder | AND/OR groups, labelled selects | n/a | n/a | overlap warning modal | saved | n/a |

### Logs
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| Log table | timestamp, actor, event type, resource | Skeleton rows | "No audit events match filters" + clear | timeout prompt (narrow range) | filtered | export disabled while fetching |
| Row detail | pretty JSON + copy | n/a | n/a | parse error | copied toast | n/a |
| Facets | event types, actors, date range | facet skeleton | n/a | retry | counts update | n/a |

### Metrics Dashboards
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| Dashboard panels | per-area cards | panel skeleton | "no data in range" | "metrics unavailable" + retry (isolated panel) | charts + accessible table | n/a |
| Time-range control | 24h default | n/a | n/a | n/a | range applied | n/a |

### Integrations (FHIR / HL7 / OAuth / Webhooks)
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| Config forms | persisted values | spinner | n/a | field errors + detail | saved toast | test button disabled while running |
| Test runner | structured result (status, latency, req/res) | spinner ≤5s | n/a | failure detail | pass state | n/a |
| Message history | table with status column | Skeleton | "no messages" | retry | per-message detail | n/a |
| Secret panel | secret shown once + copy | n/a | n/a | n/a | "I saved the secret" confirm | copy disabled after confirm |

## Design System Conformance

- **Tokens**: `--color-primary` blue-600 `#0077B6`; success emerald-500; warning amber-500; error red-500; backgrounds slate-50/100; borders slate-200/300; text slate-800/600/500 (`docs/design-tokens.json`).
- **Status colors never alone**: always icon + text (validator gate: color-blind-safe).
- **Components**: Ant Design v6 Table, Modal, Form, Select, Drawer, Tag, Badge per `docs/component-specs.md`; new components (condition builder, permission catalog, secret-confirm panel) must be added to the design system before implementation.
- **Typography**: Inter; type scale from tokens; mono font for JSON payloads and secrets.

## Accessibility Requirements

- WCAG 2.1/2.2 AA minimum: keyboard operability, visible focus, contrast ≥ 4.5:1, semantic landmarks per screen, labelled form controls, ARIA for dialogs (focus trap), status announcements (aria-live for badges and progress).
- Screens must pass axe-core with zero serious violations.
- Tables: proper header scope, keyboard navigation, no click-only interactions (row actions must have focusable controls).

## Responsive Behavior

- Desktop-first: primary layout ≥ 1280px; usable ≥ 1024px; below 1024px sidebar collapses to drawer/mobile nav (existing `MobileNav.tsx` pattern).
- Tables degrade to stacked cards below `md` breakpoint; dashboards single-column.
- No mobile requirement for R01, but no data loss at tablet widths.

## UX Principles Applied

- **Progressive disclosure**: overview lists → expandable detail → full JSON; permission catalog grouped to reduce cognitive load; advanced filters behind "More filters".
- **Error recovery**: every error state offers retry or guidance (narrow range, check config); errors never silently swallow.
- **Trust & safety**: destructive actions (delete tenant/replica/key, revoke, disable provider) always require confirmation naming the target; secrets shown once with explicit save confirmation.
- **Batch efficiency**: bulk import, module select-all, drag-to-reorder, CSV export of current filter — reduce clicks for daily admin work.
- **Consistency**: identical table/state patterns across Tenants/Users/Roles/Replicas/Routing/Logs to lower learning cost.
