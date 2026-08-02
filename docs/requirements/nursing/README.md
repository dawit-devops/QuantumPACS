# Requirements Package — R11 Radiology Service Nursing Team

| Field | Value |
|-------|-------|
| **Version** | 1.1.1 |
| **Status** | draft |
| **Generated** | 2026-08-03 |
| **Changelog** | [CHANGELOG.md](CHANGELOG.md) |

## Codebase Alignment (verified 2026-08-03)

**Presentation layer**: role-based; see artifact 04 — "Role-Based Routing &
Navigation". Nursing accounts today have only Files/patient read-only views.

**GATED**: all nursing features — patient prep, IV/contrast administration,
monitoring during exam, adverse-reaction response, vitals documentation. No nursing
routes or endpoints exist; requires new backend module + permissions flagged to
backend.

## Role Summary

**Persona**: Radiology nurses providing patient care around the exam — prep,
vitals, contrast administration, safety verification, adverse reaction response,
sedation monitoring, recovery, and discharge.
**Access tier**: Patient care (during exam) — nursing documentation.
**Context**: Bedside tablet-first documentation with hard safety gates (contrast)
and an adverse-reaction escalation SLA of 15 minutes.

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

- **R08 Front Desk** — check-in status feeds the nursing worklist.
- **R06/R07 Technologist/Technician** — exam status; contrast/dose record linkage.
- **R12/R18 Radiologist** — adverse-reaction escalation recipient; sedation oversight.
- **R16 External EMR** — allergy/pregnancy flags via HL7 ADT.
- **R01/R02 Admin** — audit retention, MAR records.

## Flagged Gaps (backend — must be raised before sprint commitment)

- No nursing endpoints exist (worklist, prep, vitals, safety, contrast, reaction, MAR, recovery).
- No adverse-reaction escalation wiring (on-call routing + ack).
- No offline sync queue for bedside documentation.
- Allergy/pregnancy flag ingestion from HL7 is not confirmed end-to-end.
