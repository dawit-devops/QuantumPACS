# Requirements Package — R13 Radiology Trainee/Resident

| Field | Value |
|-------|-------|
| **Version** | 1.2.0 |
| **Status** | draft |
| **Generated** | 2026-08-03 |
| **Changelog** | [CHANGELOG.md](CHANGELOG.md) |

## Codebase Alignment (verified 2026-08-03)

**Presentation layer**: role-based; see artifact 04 — "Role-Based Routing &
Navigation". **No resident-specific functionality exists** — no `resident` built-in
role; residents use the shared radiologist surfaces.

**Shared R12 stack (merge 4d136e0) now available as the resident foundation**:
reading worklist (`GET /reports/reading-list`), draft report editor with autosave
(`GET/PUT /reports/{exam_id}`, `ReportEditor.tsx`), report templates
(`GET /reports/templates`), peer review (`/peer-reviews*`, `PeerReviewInbox.tsx`),
reading presets (`/reading-presets*`), notifications (`exam.completed` + `/ws`).
**GATED**: attending-assignment data + supervised worklist columns (FR-R13-01),
attending-guidance panel (FR-R13-02), "DRAFT — Awaiting Attending Review"
badge/completeness indicator + submit-to-attending (FR-R13-03 slice),
attending review/co-sign workflow (FR-R13-04 — peer review covers final signed
reports only), teaching files + de-identification (FR-R13-05), exam-log
filters/CSV/metrics (FR-R13-06), feedback dashboard (FR-R13-07), on-call consult
(FR-R13-08), protocol learning (FR-R13-09), case-conference export (FR-R13-10).
5+ new endpoints flagged to backend; no longer blocked on R12 reporting itself.

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

- **Attending review/co-sign endpoints** (submit/approve/return queue) do not exist — shared draft editor shipped via R12 reporting; peer review (`/peer-reviews*`) covers final signed reports only (largest blocker).
- Supervised worklist requires attending-assignment data + supervised-status columns.
- Teaching-file de-identification service does not exist.
- On-call consult routing and feedback-dashboard aggregates are not wired.
- Protocol learning annotations and case-conference export are new.
