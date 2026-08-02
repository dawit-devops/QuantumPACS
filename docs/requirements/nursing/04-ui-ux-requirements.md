# UI/UX Requirements — Radiology Service Nursing Team (R11)

## Role-Based Routing & Navigation (Presentation Layer)

RBAC drives the presentation layer (`hasPermission()` + `RequirePermission`, gated
`Sidebar.tsx` items). Verified against `frontend/src/`.

### Routes Accessible (codebase reality)

| Route | Screen | Access rule |
|-------|--------|-------------|
| `/` | Files / study search (read) | Any authenticated user |
| `/account` | Account | Any authenticated user |
| `/patients/:id`, `/files/:id` | Patient page, viewer | `PATIENT_READ` / `FILE_READ` |
| Nursing worklist / prep / vitals / contrast | **Not accessible** | No nursing routes or endpoints exist — GATED |

### Navigation Gating (Sidebar.tsx)

| Menu item | Visible when |
|-----------|--------------|
| Files / Account / Notifications | Always (authenticated) |
| Admin submenu | Only if granted admin `*_READ` perms |

### Functionality Gating

- **None of the nursing screens exist**: patient prep, IV/contrast administration,
  monitoring during exam, adverse-reaction response, pre/post exam care, vitals
  documentation. All aspirational FRs marked `GATED` (artifacts 01/07/08) — new
  endpoints + permissions flagged to backend.
- Today a nursing account can only browse files/patients read-only.

## Screens & Navigation

| # | Screen | Entry Point | Purpose |
|---|--------|-------------|---------|
| 1 | Nursing Worklist | Sidebar / Home | Patients needing nursing care |
| 2 | Patient Care View | Worklist → row | Prep checklist, vitals, safety, contrast |
| 3 | Vitals Panel | Care view | Repeated vitals capture + log |
| 4 | Safety Gate | Care view | Allergy/pregnancy/renal confirmation |
| 5 | Reaction Modal | Care view | Adverse reaction entry + escalation |
| 6 | Recovery View | Care view | Post-procedure observations + discharge |

Navigation: worklist-first; care view is a tabbed panel (prep / vitals / contrast / recovery).

## Component & State Spec

| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| NursingWorklist | Rows | Skeleton | "No patients in queue" | Retry | Live updates | — |
| Checklist | Items | Skeleton | "No prep required" | Retry | All confirmed | On submit |
| VitalsForm | Fields | — | — | Inline errors | Reading saved | During save |
| SafetyGate | Flags | Spinner | "No flags" | Retry | Confirmed badge | Contrast without confirm |
| ReactionForm | Fields | — | — | Retry | Escalation sent | During submit |
| DischargePanel | Criteria | Spinner | — | Retry | Discharged | Until criteria met |

## Design System Conformance

- Tokens: `--color-danger` (allergy/reaction), `--color-warning` (sedation), `--color-success` (confirmed), `--bg-surface`, `--radius-sm`.
- Components: reuse `Table`, `Form`, `Checkbox`, `Statistic`, `Tag`, `Modal`, `Popconfirm`; new `NursingWorklist`, `SafetyGate`, `ReactionForm` specs.

## Accessibility Requirements

- WCAG 2.2 AA: bedside tablet touch targets ≥ 44px, keyboard fallback, focus rings, contrast ≥ 4.5:1, screen-reader announcements for safety confirmations and escalations.

## Responsive Behavior

- Tablet-first for bedside documentation (vitals, checklist, reactions).
- Desktop for the worklist and monitoring views; offline-tolerant forms on tablet.

## UX Principles Applied

- Hard safety gates with explicit disable/override semantics; minimal taps for reaction entry; visible escalation state; offline queue with sync status; recovery discharge criteria as a checklist.
