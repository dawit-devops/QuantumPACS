# Requirements Package — R13 Radiology Trainee/Resident

| Field | Value |
|-------|-------|
| **Version** | 1.1.1 |
| **Status** | draft |
| **Generated** | 2026-08-03 |
| **Changelog** | [CHANGELOG.md](CHANGELOG.md) |

## Codebase Alignment (verified 2026-08-03)

**Presentation layer**: role-based; see artifact 04 — "Role-Based Routing &
Navigation". **No resident-specific functionality exists** — no role distinction
between resident and staff radiologist today; residents use the shared Files/Viewer.

**GATED**: all supervised-reading features — FR-R13-01..10 (supervised worklist,
draft reports, attending review/sign-off, teaching files + de-identification, exam
log, feedback dashboard, on-call consult, protocol learning, case-conference export).
6+ new endpoints flagged to backend; depends on R12 reporting.

## Role Summary

**Persona**: Radiology trainee/resident performing supervised reading — study
interpretation with attending guidance, structured draft reports, attending
review/sign-off, teaching-file capture (de-identified), personal exam log, and a
performance feedback dashboard.
**Access tier**: Clinical reading (supervised) — drafts require attending co-sign.
**Context**: Educational workflow; hard visibility gate (drafts invisible to
R14/R19 until co-sign); de-identification mandatory for teaching files.

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

- **R12 Staff Radiologist** — attending supervision, guidance, review and co-sign.
- **R18 Teleradiologist** — on-call consult fallback.
- **R04 Service Coordinator** — resident ↔ attending rotation assignment.
- **R06/R07 Technologist/Technician** — completed exams feed the resident worklist.
- **R03 Service Director** — program-director cohort view of resident metrics.
- **R05 QI/QA Team** — feedback/peer-review data.
- **R14 Referring Clinician** — drafts invisible until co-sign.

## Flagged Gaps (backend — must be raised before sprint commitment)

- Draft report + attending review/sign-off endpoints do not exist (shared R12 reporting gap — largest blocker).
- Resident worklist requires attending-assignment data + WebSocket push.
- Teaching-file de-identification service does not exist.
- On-call consult routing and feedback-dashboard aggregates are not wired.
- Protocol learning annotations and case-conference export are new.
