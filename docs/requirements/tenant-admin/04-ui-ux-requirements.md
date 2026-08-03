# UI/UX Requirements — Hospital IT / Tenant Admin (R02)

## Role-Based Routing & Navigation (Presentation Layer)

RBAC drives the presentation layer: `hasPermission()` + `RequirePermission` gate UI
elements; `Sidebar.tsx` renders items only when the tenant admin holds the matching
permission; the backend rejects cross-tenant access with 403. The tenant admin is a
**tenant-scoped subset of R01**: global items (provision tenant, global config) never
render and are rejected server-side. Verified against `frontend/src/`.

### Routes Accessible (codebase reality)

| Route | Screen | Access rule |
|-------|--------|-------------|
| `/` | Files / study search | Any authenticated user |
| `/metrics` | Metrics dashboard | Any authenticated user (sidebar item) |
| `/account` | Account | Any authenticated user |
| `/users`, `/roles`, `/replicas`, `/routing`, `/service-keys`, `/logs`, `/worklist`, `/hl7`, `/dicomweb` | Tenant-scoped admin | Matching `*_READ` permission (no `TENANT_ADMIN` provisioning) |
| `/fhir/*`, `/integrations` | Integration admin | `SYSTEM_ADMIN` (tenant-scoped) |
| `/files/:id`, `/patients/:id` | Viewer, patient page | `FILE_READ` / `PATIENT_READ` |
| `/tenants` | **Not accessible** | R01-only (provisioning) — item not rendered |

### Navigation Gating (Sidebar.tsx)

Same gating table as R01 but the **Tenants** item is hidden for this role (no
`TENANT_ADMIN`), and tenant-scoped rows must never leak other tenants' data.

| Menu item | Visible when |
|-----------|--------------|
| Admin submenu | `user.admin` OR any admin `*_READ` permission |
| Users / Roles / Replicas / Routing / Service Keys / Logs / Worklist / HL7 / DICOMweb | Matching `*_READ` |
| FHIR / Integrations | `SYSTEM_ADMIN` |

### Functionality Gating

- Cross-tenant actions must be impossible in the UI **and** rejected by backend (403).
- Aspirational v3.0 FRs with no backend yet are kept but marked `GATED` (see
  artifacts 01/07/08): tenant-scoped quota/usage dashboard, department/modality
  registry, backup/restore.

Design-system conformance: tokens from `docs/design-tokens.json` (Ant Design v6,
`frontend/src/common/theme.ts`); components from `docs/component-specs.md`. R02 shares
screens/patterns with R01 (same component families) but with tenant-scoped content and
a reduced navigation tree. No one-off styling.

## Screens & Navigation

| Screen | Route (existing) | Entry Point | R02 Visibility |
|--------|------------------|-------------|----------------|
| Dashboard / Metrics | `/metrics` | Sidebar "Metrics" | Yes — tenant-scoped |
| Users | `/users` | Sidebar | Yes — tenant-scoped |
| Worklist | `/worklist` | Sidebar | Yes — tenant worklist + station AEs |
| Routing Rules | `/routing` | Sidebar | Yes — tenant rules |
| Replicas | `/replicas` | Sidebar | Yes — tenant replicas |
| Service Keys | `/service-keys` | Sidebar | Yes — tenant keys |
| Integrations (webhooks/OAuth) | `/integrations` | Sidebar | Yes — tenant-scoped |
| FHIR Config | `/fhir/config` | Integrations | Yes |
| FHIR Monitoring | `/fhir/monitoring` | Integrations | Yes |
| HL7 Admin | `/hl7` | Integrations | Yes |
| Logs | `/logs` | Sidebar | Yes — tenant events |
| DICOMweb Admin | `/dicomweb` | Sidebar | Yes — station AEs |
| Notifications | bell (header) | Header | Yes — tenant events |
| **Tenants** | `/tenants` | Sidebar | **NO — R01 only, hidden** |
| **Roles (global)** | `/roles` | Sidebar | **NO — R01 only unless tenant roles exist (confirm)** |

**IA rules**:
- Navigation is permission-driven: R02 sees the same screen set as R01 minus
  global-only items (Tenants, global roles).
- Tenant context indicator always visible in the header (tenant name) so scoping is
  never ambiguous — critical for the tenant-boundary requirement.
- If the tenant switcher is present (multi-tenant admins), it lists only accessible
  tenants (R01 boundary enforced).

## Component & State Spec (per key screen)

### Users List
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| Users table | tenant rows: username, name, email, role, status | Skeleton | "No users in this tenant" + CTA | Banner + retry | row updated | n/a |
| Add user modal | form + role picker (tenant roles only) | spinner | n/a | inline errors (incl. 403 role) | toast + row | submit disabled until valid |
| Bulk import | dropzone | progress | n/a | per-row error list | report counts | commit disabled pre-validation |

### Worklist / Station AEs
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| Station AE table | AE title, modality tag, status | Skeleton | "No stations — register the first" | Banner + retry | row added | delete disabled while referenced by rules |
| Station form | AE title + modality select (controlled vocab) | spinner | n/a | duplicate-AE inline error | saved toast | submit disabled until valid |

### Routing Rules
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| Rule list | priority order, drag handles | Skeleton | "No rules — default routing applies" | Banner | reorder persisted | disabled-destination badge |
| Condition builder | AND/OR groups, labelled selects | n/a | n/a | overlap warning modal | saved | n/a |

### HL7 / FHIR / Integrations
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| Status header | listening state (icon + text) | skeleton | n/a | "not listening" + retry | state updates | n/a |
| Message history | table with parse/ACK status | Skeleton | "no messages" | retry | detail panel | n/a |
| Test runner | structured result | spinner ≤5s | n/a | failure detail | pass state | test disabled while running |
| Secret panel | secret once + copy | n/a | n/a | n/a | "I saved the secret" confirm | copy disabled after confirm |

### Logs / Dashboard
| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| Log table | tenant events + facets | Skeleton | "No audit events match" + clear | timeout prompt (narrow range) | filtered | export disabled while fetching |
| Usage panel | usage vs quota progress | skeleton | n/a | "usage unavailable" + retry | value + % | n/a (GAP: endpoint) |

## Design System Conformance

- **Tokens**: primary blue-600 `#0077B6`; success emerald-500; warning amber-500;
  error red-500; surfaces slate-50/100; borders slate-200/300; text slate-800/600/500.
- **Status colors never alone**: icon + text (validator gate).
- **Components**: Ant Design v6 Table/Modal/Form/Select/Drawer/Tag/Badge per
  `component-specs.md`; condition builder and secret-confirm panel are shared
  components with R01 — implement once in the design system.
- **Typography**: Inter; mono for JSON payloads, AE titles, and secrets.

## Accessibility Requirements

- WCAG 2.1/2.2 AA minimum: keyboard operability, visible focus, contrast ≥ 4.5:1,
  landmarks, labelled controls, focus-trapped dialogs, aria-live for badge/progress.
- Zero serious axe-core violations on all screens.
- Tables: header scope, keyboard navigation; no click-only actions.

## Responsive Behavior

- Desktop-first ≥ 1280px; usable ≥ 1024px; sidebar collapses below `md`
  (existing `MobileNav.tsx` pattern); tables stack to cards on small screens.
- No mobile requirement, but no data loss at tablet widths.

## UX Principles Applied

- **Trust & safety**: tenant boundary is the prime directive — persistent tenant
  indicator, permission-driven nav, no cross-tenant exposure. Destructive actions
  confirm with target names; secrets shown once.
- **Progressive disclosure**: lists → expandable detail → full payload; grouped
  filters; advanced filters behind "More filters".
- **Error recovery**: every error state offers retry or guidance; 403 responses map
  to actionable inline messages.
- **Consistency**: identical screen/state patterns across R01 and R02 surfaces to
  lower learning cost for admins who operate both levels.
