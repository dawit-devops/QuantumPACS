# UI/UX Requirements — External EMR (R16)

## System Interface Surface (Presentation Layer)

The External EMR is a system-to-system integration: it has **no web UI**. Access is
API-driven via authenticated integration endpoints. Verified against
`backend/api/routes.py`.

### Endpoints Exposed (codebase reality)

| Endpoint | Purpose | Auth |
|----------|---------|------|
| `POST /hl7` | HL7 ADT/ORM/ORU inbound (demographics, orders, results) | HL7 receiver |
| `/hl7/admin/*` | Message history, config, status, metrics | Admin (`HL7_READ`) |
| `/fhir/Patient`, `/fhir/Patient/{id}` | Patient demographics (FHIR R4) | OAuth client |
| `/fhir/ImagingStudy`, `/fhir/DocumentReference` | Study/report read | OAuth client |
| `POST /webhooks` | Result-status push events | Admin (`SYSTEM_ADMIN`) |

### Interface Gating

- **Implemented**: HL7 ADT receiver, FHIR Patient read/search, ImagingStudy and
  DocumentReference scaffolding, webhook delivery.
- **Not implemented** (aspirational FRs marked `GATED` in 01/07/08): report
  backfill job, results-status workflow, async demographics sync with conflict
  resolution.

## Screens & Navigation

The EMR is a system actor with **no end-user UI**. Its surface is the existing
**FHIR admin + HL7 admin** screens used by R01/R02:

| # | Screen | Entry Point | Purpose |
|---|--------|-------------|---------|
| 1 | FHIR Config | Sidebar → FHIR Config | Base URL, auth, client registration |
| 2 | FHIR Clients | Config → Clients | Client CRUD, scopes, test endpoint |
| 3 | FHIR Monitoring | Sidebar → FHIR Monitoring | Request log, volume, latency, errors |
| 4 | FHIR Docs | Sidebar → FHIR Docs | Resource documentation / CapabilityStatement |
| 5 | HL7 Dashboard | Sidebar → HL7 | ADT message log + replay (shared with R15) |

## Component & State Spec

| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| ClientTable | Rows | Skeleton | "No clients" | Retry | — | — |
| ClientForm | Fields | — | — | Inline errors | Registered | During submit |
| RequestTable | Rows | Skeleton | "No requests" | Retry | — | — |
| RequestDetail | Payload | Spinner | — | Retry | Parsed | — |
| TestResult | — | Spinner | — | Failed → retry | Passed | — |

## Design System Conformance

- Tokens: `--color-success`, `--color-danger`, `--color-warning`, `--bg-surface`, mono font for payloads.
- Components: reuse `Table`, `Form`, `Tag`, `Drawer`, `Descriptions`, `Button`; new `ClientForm`, `RequestDetail` specs.

## Accessibility Requirements

- WCAG 2.2 AA for the admin surface: keyboard-navigable tables, focus rings, contrast ≥ 4.5:1, non-color status indicators.

## Responsive Behavior

- Desktop-first admin surface; no mobile requirement (system integration).

## UX Principles Applied

- Client lifecycle visible (active/revoked); request payloads inspectable; test endpoint one-click; no PHI in URLs; status not color-only.
