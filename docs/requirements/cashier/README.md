# Requirements Package — R09 Radiology Service Cashier

| Field | Value |
|-------|-------|
| **Version** | 1.1.2 |
| **Status** | draft |
| **Generated** | 2026-08-03 |
| **Changelog** | [CHANGELOG.md](CHANGELOG.md) |

## Codebase Alignment (verified 2026-08-03; re-verified 2026-08-03 post-merge 4d136e0)

**Presentation layer**: role-based; see artifact 04 — "Role-Based Routing &
Navigation". Cashier accounts today have only the Files/patient read-only views.
`PermissionRoute` now enforces role-based access at the URL boundary — deep links to
routes without the required permission redirect to `/` (Files).

**GATED**: all billing features — payment collection, invoice/payment records,
insurance claim status, receipts, cash reconciliation. No billing routes or endpoints
exist; requires new backend module + permissions flagged to backend.

**Post-merge re-verification (4d136e0)**: merge shipped exams/QA/reports routes and
permissions only; `backend/api/routes.py` still has **no billing endpoints**, and the
frontend has **no billing pages**. Built-in `cashier` role carries only
PATIENT_READ/PATIENT_WRITE. FR-R09-01..08/10 remain GATED; FR-R09-09 partial status
unchanged.

## Role Summary

**Persona**: Cashier handling payment collection, invoices, receipts, insurance
claim status, and end-of-day reconciliation.
**Access tier**: Billing (read-only clinical context — no images, no reports).
**Context**: High-volume counter; PCI scope must stay minimal; every payment
mutation is audited.

## Artifact Index

| # | Artifact | File |
|---|----------|------|
| 01 | User Requirements | `01-user-requirements.md` |
| 02 | End-to-End Workflow Maps | `02-workflow-maps.md` |
| 03 | User Stories | `03-user-stories.md` |
| 04 | UI/UX Requirements | `04-ui-ux-requirements.md` |
| 05 | Metrics & SLAs | `05-metrics-slas.md` |
| 06 | Acceptance Criteria (validator-gated) | `06-acceptance-criteria.md` |
| 07 | Traceability Matrix | `07-traceability.md` |
| 08 | Implementation Roadmap | `08-implementation-roadmap.md` |

## Cross-Role Dependencies

- **R08 Front Desk** — supplies insurance/authorization data.
- **R01/R02 Admin** — refund approval workflow, billing system config.
- **R03/R05** — billing turnaround and quality metrics.
- **External claims feed** (future) — claim status integration.

## Flagged Gaps (backend — must be raised before sprint commitment)

- No billing endpoints exist (invoices, payments, receipts, reconciliation).
- No payment-processor integration (tokenized) — must be scoped with Security.
- No claims-status feed; local manual status fallback required.
- Refund approval workflow needs a task/approval primitive.
