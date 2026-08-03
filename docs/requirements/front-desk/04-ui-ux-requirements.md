# UI/UX Requirements — Front Desk / Receptionist (R08)

## Role-Based Routing & Navigation (Presentation Layer)

RBAC drives the presentation layer (`hasPermission()` + `RequirePermission`, gated
`Sidebar.tsx` items). Verified against `frontend/src/`.

### Routes Accessible (codebase reality)

| Route | Screen | Access rule |
|-------|--------|-------------|
| `/` | Files / study search (read) | Any authenticated user |
| `/account` | Account | Any authenticated user |
| `/patients/:id`, `/files/:id` | Patient page, viewer | `PATIENT_READ` / `FILE_READ` |
| Registration / scheduler / check-in / queue | **Not accessible** | No registration/scheduling routes or endpoints exist — GATED |

### Navigation Gating (Sidebar.tsx)

| Menu item | Visible when |
|-----------|--------------|
| Files / Account / Notifications | Always (authenticated) |
| Admin submenu | Only if granted admin `*_READ` perms (receptionist typically none) |

### Functionality Gating

- **None of the front-desk screens exist**: patient registration, duplicate
  detection, order intake, appointment scheduling, check-in, consent capture,
  insurance/guarantor capture, label printing, queue board. All aspirational FRs
  marked `GATED` (artifacts 01/07/08) — new endpoints + permissions flagged to
  backend.
- Today a receptionist account can only browse files/patients read-only.

## Screens & Navigation

| # | Screen | Entry Point | Purpose |
|---|--------|-------------|---------|
| 1 | Registration Search | Sidebar / Home | Find or confirm a patient before registration |
| 2 | Registration Form | Search → "New Patient" | Capture demographics, insurance, order |
| 3 | Scheduler | Registration → "Schedule" | Book modality time slot |
| 4 | Check-In | Today's list | Mark arrival, verify demographics |
| 5 | Forms & Consent | Visit detail | Attach signed forms, view missing consents |
| 6 | Waiting Queue | Sidebar | Privacy-limited status board |

Navigation: search-first flow; breadcrumb Patient → Visit → Order; back paths preserved.

## Component & State Spec

| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| PatientSearch | Input + hint | Skeleton rows | "No matches — register new" | Retry + message | Result rows | During submit |
| RegistrationForm | Fields | — | — | Inline errors | Success banner + label print | On save |
| SlotPicker | Grid of slots | Spinner | "No availability" + waitlist CTA | Retry | Selected slot | Booked slots |
| CheckInButton | "Check In" | Spinner | — | Retry | "Checked in" | Already checked in |
| ConsentList | Form types | Skeleton | "No forms required" | Retry | Attached badges | — |
| QueueBoard | Rows | Skeleton | "No patients in queue" | Retry | Live rows | — |

## Design System Conformance

- Tokens: `--color-primary`, `--color-success`, `--color-danger`, `--color-warning`, `--bg-surface`, `--text-secondary`, `--radius-sm` (docs/design-tokens.json)
- Components: reuse `Table`, `Form`, `Input.Search`, `DatePicker`, `Tag`, `Upload` (docs/component-specs.md)
- New components to spec: `PatientSearchResults` (dedup banner state), `QueueBoard` (privacy mode)

## Accessibility Requirements

- WCAG 2.2 AA: keyboard operability for search and slot grid, visible focus rings, contrast ≥ 4.5:1, screen-reader announcements for validation errors and state changes, no auto-dismissing toasts without a non-visual alternative.

## Responsive Behavior

- Desktop-first for registration workstations (base ≥ 1280px recommended).
- Tablet/mobile: read-only queue view and check-in action; full registration form remains desktop.

## UX Principles Applied

- Progressive disclosure on insurance fields; dedup confirmation before creation; explicit success/error for every submit; privacy-first queue rendering; optimistic saves with clear sync status for HL7 backfill.
