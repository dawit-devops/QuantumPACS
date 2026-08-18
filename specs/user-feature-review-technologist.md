# Technologist workflow polish — technical design

Phase 3 of `user-feature-review technologist`. Implements `03-handoff.md`
per `04-design.md`. Branch `phase/user-feature-review-technologist`.

## Scope

| Item | Kind | Backend | Frontend |
|---|---|---|---|
| P0-1 | role-grant drift fix | migration 062 + `seed_built_in_roles` reconcile + pytest | drop `seedTechnologist` API stub |
| P1-1 | critical-results flag | `POST /exams/{id}/critical-flag` (CRITICAL_RESULTS_WRITE) + reading-list surfacing | ExamConsole button/modal + ReadingWorklist tag |
| P1-2 | claim unassigned exams | `POST /exams/{id}/claim` (EXAM_WRITE) + `assigned=mine\|pool` | worklist Unassigned tag + Claim button |
| P1-3 | completed read-state + QA-flag bell | exam payload `report_status` + `_notify_user` on QA incident resolve/flag | Completed-tab Read State column |
| P2-1 | next-patient pointer | reuse `GET /exams` (next ready for modality) | console header line |
| P2-2 | incident-resolved bell event | notify incident author on `qa.incident_resolved` | bell event (existing UI) |
| P2-3 | prior safety history | exam payload `prior_safety_checks` | Safety Checks card sub-section |
| P2-4 | worklist summary | none (derive client-side from per_page=500) | summary headline |
| P2-5 | filter a11y | none | aria-labels + aria-pressed |

## Backend

### P0-1 — grants drift
- Migration `062_reconcile_drifted_role_grants.py` re-applies the canonical
  `BUILT_IN_ROLES` grants for `technologist`, `radiologist`, `resident`,
  `cashier` (the four drifted slugs) — same pattern as 048 but with a
  `WHERE` guard so facility-edited built-ins (per `seed_built_in_roles`
  philosophy) aren't force-reset on every boot: only reconcile when the
  stored set **contains the known 92-grant drift marker** (or simpler:
  re-apply canonical for the four slugs once, matching 048's precedent).
- `db/roles.py seed_built_in_roles()`: for editable built-ins, reconcile to
  canonical when the stored set is a **superset** of canonical (drift marker
  — `set(stored) > set(canonical)`); keep `DO NOTHING` when it's a genuine
  facility edit (subset/other). Rationale in code comment.
- New pytest `tests/test_role_grants_matrix.py`: for every built-in slug,
  assert live-DB grants == `BUILT_IN_ROLES[slug]` (guard for CI drift).

### P1-1 — critical flag
- Schema `CriticalFlagRequest { severity: low|medium|high|critical, series_id?, note }`.
- New table column via `db/exams.py` sync (ALTER IF NOT EXISTS):
  `critical_flag TEXT DEFAULT ''` (severity) + `critical_flag_note TEXT`,
  `critical_flagged_at TIMESTAMPTZ`, `critical_flagged_by TEXT`.
  (sync_db pattern matches IncidentsQA; no new migration needed — sync_db
  is the schema path for exam-family tables.)
- `POST /exams/{id}/critical-flag` (CRITICAL_RESULTS_WRITE): upsert the
  columns, audit `exam.critical_flagged`, notify radiologist role
  (`exam.critical_flagged`) via `_notify_role(conn, 'radiologist', ...)`.
- Exam GET payload gains `critical_flag`, `critical_flag_note`,
  `critical_flagged_at`.
- Reading list (`db/reports.py reading_list`) gains `critical_flag` in the
  select; ReadingWorklist flags it.

### P1-2 — claim
- `POST /exams/{id}/claim` (EXAM_WRITE): 409 if `assigned_technologist` is
  non-empty and != caller; else set to caller, audit `exam.claimed`.
- `list_for_technologist` gains `assigned='mine'|'pool'|None` filter;
  rows already carry `assigned_technologist` (SELECT *).

### P1-3 — read state + QA-flag event
- Exam GET payload gains `report_status` (join `reports.status` by
  accession/exam) and `qa_flags` (pending incidents count for the exam).
- `api/qa.py` resolve handler: after `mark_resolved`, notify the incident
  author (`reported_by`) with `incident.resolved` event via new
  `_notify_user(conn, user_id, ...)` helper (mirrors `_notify_role`).

### P2-3 — prior safety
- Exam GET payload gains `prior_safety_checks`: safety records for prior
  exams of the same patient (excluding this exam).

## Frontend

- **ExamConsole**: "Flag Critical" danger button (CRITICAL_RESULTS_WRITE)
  + modal (severity/series/note); header next-patient line (P2-1);
  Safety Checks card "Prior screenings" (P2-3); incidents list resolution
  tag (P2-2 UI half).
- **TechnologistWorklist**: Unassigned tag + Claim button (P1-2); Read
  State column on Completed tab (P1-3); summary headline (P2-4);
  aria-labels + aria-pressed (P2-5).
- **ReadingWorklist**: red CRITICAL tag + sort-above-routine (P1-1).
- **api/exams.ts / types**: extend payload types.
- **e2e/helpers.ts**: `seedTechnologist` uses the real backend (drop the
  `/api/**` route stub) once P0-1 lands.

## Security checkpoint
- All new endpoints `requires_permission` (CRITICAL_RESULTS_WRITE /
  EXAM_WRITE / QA_WRITE) + `parse_body` validation.
- Notifications carry no PHI beyond existing titles; links scoped to exam
  route.
- No new secrets; no write-path widening (claim only on unassigned rows;
  flag only for grant holders).
