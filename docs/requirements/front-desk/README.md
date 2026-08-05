# Requirements Package — R08 Front Desk (Receptionist)

| Field | Value |
|-------|-------|
| **Version** | 1.1.2 |
| **Status** | draft |
| **Generated** | 2026-08-03 |
| **Changelog** | [CHANGELOG.md](CHANGELOG.md) |

## Codebase Alignment (verified 2026-08-03; re-verified 2026-08-03 post-merge 4d136e0)

**Presentation layer**: role-based; see artifact 04 — "Role-Based Routing &
Navigation". Front-desk accounts today have only the Files/patient read-only views.
`PermissionRoute` now enforces role-based access at the URL boundary — deep links to
routes without the required permission redirect to `/` (Files).

**GATED**: all registration/scheduling features — FR-R08-01..10 (patient
registration, duplicate detection, order intake, appointment scheduling, check-in,
consent, insurance, label printing, queue board). No registration/scheduling routes
or endpoints exist; requires new backend module + permissions flagged to backend.

**Post-merge re-verification (4d136e0)**: worklist CRUD/calendar/create-entry
frontends exist (`/worklist`, `/schedule-board`, `CalendarView`, `CreateEntry`), but
`/schedule-board` is an R04 worklist-derived read view (WORKLIST_READ) — not an
appointment-scheduling API; no registration, check-in, consent, or insurance
endpoints exist. HL7 `POST /hl7` remains **inbound-only** — no outbound ADT sender,
so FR-R08-02's demographics-sync trigger stays GATED. FR-R08-01/02 remain
Partial/GATED as recorded in artifacts 07/08.

## Role Summary

**Persona**: Front desk receptionist handling patient registration, order intake,
scheduling, check-in, consent capture, and insurance data collection.
**Access tier**: Registration + scheduling (no billing, no clinical reading).
**Context**: High-traffic lobby environment; must be fast and accurate; waiting-area
displays must preserve patient privacy (initials only).

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

- **R04 Service Coordinator** — scheduling shares the schedule board data model.
- **R06/R07 Technologist/Technician** — scheduled exams appear in modality worklists.
- **R11 Nursing** — check-in status feeds the nursing worklist.
- **R09 Cashier** — insurance/authorization data captured here feeds billing.
- **R16 External EMR** — outbound HL7 ADT on registration.
- **R15 External RIS** — inbound order context (HL7 ORM).

## Flagged Gaps (backend — must be raised before sprint commitment)

- Order intake endpoint (beyond worklist create) does not exist.
- Consent/forms storage endpoint does not exist.
- Check-in status event propagation to clinical roles is not wired.
- Schedule board API is an R04 dependency, not yet implemented.
