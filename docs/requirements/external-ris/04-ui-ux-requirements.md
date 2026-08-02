# UI/UX Requirements — External RIS (R15)

## System Interface Surface (Presentation Layer)

The External RIS is a system-to-system integration: it has **no web UI**. Access is
entirely API-driven via authenticated integration endpoints (`X-Auth-Pacs` service
key or OAuth client). Verified against `backend/api/routes.py`.

### Endpoints Exposed (codebase reality)

| Endpoint | Purpose | Auth |
|----------|---------|------|
| `GET/POST /worklist`, `GET/PUT /worklist/{id}`, `GET /worklist/station-aes` | Order exchange, scheduling sync, status updates | API key / user token |
| `POST /hl7` | HL7 ORM/ORU inbound (orders + results) | HL7 receiver |
| `/hl7/admin/*` | Message history, config, status, metrics | Admin (`HL7_READ`) |
| `GET /dicomweb/studies*`, `/wado` | DICOM MWL/MPPS / query | API key |
| `/fhir/ServiceRequest` (search/create) | FHIR order exchange | OAuth client |
| `/fhir/DocumentReference` | Report delivery | OAuth client |
| `POST /webhooks`, `/webhooks/test` | Event delivery (push) | Admin (`SYSTEM_ADMIN`) |

### Interface Gating

- **Implemented**: HL7 receiver (`POST /hl7`), worklist CRUD, DICOMweb query,
  FHIR ServiceRequest/DocumentReference scaffolding, webhook delivery.
- **Not implemented** (aspirational FRs marked `GATED` in 01/07/08): full MWL/MPPS
  lifecycle, report delivery push, dead-letter + manual reconciliation UI, message
  retry policies.

## Screens & Navigation

The RIS is a system actor with **no end-user UI**. Its surface is the existing
**HL7 admin/dashboard** used by R01/R02 to operate the integration:

| # | Screen | Entry Point | Purpose |
|---|--------|-------------|---------|
| 1 | HL7 Messages Dashboard | Sidebar → HL7 | Direction/type/status filter, payload inspect |
| 2 | Message Detail | Dashboard → row | Full HL7 payload, control ID, processing result |
| 3 | HL7 Config | Sidebar → HL7 Config | Endpoints, credentials, message-type mapping |
| 4 | HL7 Status/Metrics | Config → Status | Connection health, ack latency, error rates |
| 5 | Reconciliation Queue | Dashboard → Dead-letter | Manual reprocess/resend of failed messages |

## Component & State Spec

| Component | Default | Loading | Empty | Error | Success | Disabled |
|-----------|---------|---------|-------|-------|---------|----------|
| MessageTable | Rows | Skeleton | "No messages" | Retry | — | — |
| MessageDetail | Payload | Spinner | — | Retry | Parsed payload | — |
| ConnectionBadge | Status | Spinner | — | Down → retry | Up | — |
| ReconcilePanel | Queue rows | Spinner | "No failures" | Retry | Reprocessed | During replay |

## Design System Conformance

- Tokens: `--color-success` (acked/up), `--color-danger` (NAK/down), `--color-warning` (dead-letter), `--bg-surface`, mono font for payloads.
- Components: reuse `Table`, `Tag`, `Drawer`, `Descriptions`, `Switch`; new `MessageDetail`, `ReconcilePanel` specs.

## Accessibility Requirements

- WCAG 2.2 AA for the admin surface: keyboard-navigable tables, focus rings, contrast ≥ 4.5:1, screen-reader labels on connection/status badges, no reliance on color alone.

## Responsive Behavior

- Desktop-first admin surface; no mobile requirement (system integration).

## UX Principles Applied

- Payloads readable (monospace, collapsible); status at a glance (badges + counts); dead-letter actions one click; no PHI in UI URLs; retry semantics visible.
