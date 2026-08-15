# 03 — Hand-off to the Dev Team (technologist)

Prioritized improvement list from the Phase 1 review of the technologist
experience. Every item has a user story, numbered acceptance criteria,
affected areas, and a priority.

---

## P0-1 — Fix role-grant drift: built-in roles must match the canonical matrix

**User story:** As a technologist (or any role), when I log in with a
seeded test account I want the app to behave exactly as my role defines, so
that manual QA and role-scoped E2E test the real persona — not a super-user.

**Why:** the dev DB's `technologist` (92 vs 15), `radiologist` (92 vs 23),
`resident` (27 vs 18) and `cashier` (8 vs 7) role rows carry stale grants;
login tokens are minted from the DB row (`db/users.get_user_role`), so the
app grants far more than `BUILT_IN_ROLES`. Migration 048's trim was
overwritten after it ran. `e2e/helpers.ts seedTechnologist` fakes grants and
stubs the API — hiding the drift instead of fixing it.

**Acceptance criteria**
1. After the fix, `SELECT permissions FROM roles WHERE slug='technologist'`
   equals `BUILT_IN_ROLES['technologist']` (15 grants); the same holds for
   every built-in slug in a migrated DB.
2. The drift is prevented from recurring: either `seed_built_in_roles()`
   reconciles editable built-ins to the canonical set when they differ, or a
   new Alembic migration re-applies migration 048's grants (and a follow-up
   guard — e.g. CI asserts DB grants == BUILT_IN_ROLES after migration).
3. `test.technologist` can no longer open `/reading`, `/qa/queue`, `/admin`,
   `/frontdesk/*` or `/portal` (all bounce to `/exams`).
4. `e2e/helpers.ts` no longer needs to stub `/api/**` for the technologist
   (the real backend role is trustworthy again).
5. A test asserts the live DB role grants match `BUILT_IN_ROLES` for every
   built-in slug.

**Affected areas:** `backend/db/roles.py` (`seed_built_in_roles`),
`backend/migrations/versions/048_*.py` (re-apply / supersede), a new
migration, `frontend/e2e/helpers.ts` (remove the stub), a DB-assert test.

---

## P1-1 — "Flag critical result" needs a real workflow (dead grant → live)

**User story:** As a technologist, I want to flag an alarming finding on the
image during acquisition, so that the radiologist reads it immediately
instead of in queue order.

**Acceptance criteria**
1. The Exam Console shows a "Flag critical" action for roles holding
   `CRITICAL_RESULTS_WRITE` (technologist/radiologist/pacs_admin), with
   severity + optional series reference.
2. A permission-gated `CRITICAL_RESULTS_WRITE` endpoint persists the flag
   and links it to the exam.
3. The radiologist Reading Worklist surfaces flagged exams above
   routine work (priority or badge), so the flag changes read order.
4. The tech sees confirmation ("Flagged for immediate read") and the flag
   state on the exam console.
5. Backend + frontend tests cover the write path and the worklist surfacing.

**Affected areas:** new handler in `backend/api/exams.py` (or a
`critical_results` module), schema in `backend/api/schemas/`, Exam Console
UI in `frontend/src/technologist/ExamConsole.tsx`, Reading Worklist
surfacing in `frontend/src/radiologist/ReadingWorklist.tsx`.

---

## P1-2 — "My Exams" must be mine: distinguish assigned vs unassigned pool + claim

**User story:** As a technologist, I want "My Exams" to show my assigned work
and let me claim unassigned exams explicitly, so that I never guess whether a
STAT is mine and ownership is auditable.

**Acceptance criteria**
1. The worklist marks rows with `assigned_technologist = ''` distinctly
   (e.g. an "Unassigned" tag) instead of blending them with my assignments.
2. A claim action (`EXAM_WRITE`) assigns the exam to me with an audit entry;
   after claiming, the row becomes mine and disappears from the unassigned
   pool for others.
3. A reassign action (P2) is out of scope here but the claim endpoint must
   not conflict with the R04 assignment flow (`assigned_technologist` set
   from the worklist).
4. The "Your assigned exams" subtitle stays truthful (no unassigned rows in
   the assigned-only view; the pool is a separate filter or column).
5. Tests cover claim, double-claim conflict, and the audit row.

**Affected areas:** `backend/db/exams.py` (`list_for_technologist` —
surface `assigned_technologist` and support `assigned=mine|pool`),
`backend/api/exams.py` (claim endpoint), `frontend/src/technologist/
TechnologistWorklist.tsx`.

---

## P1-3 — Completed-exam feedback loop (read-status for the technologist)

**User story:** As a technologist, I want to see what happened to the exams I
completed, so that I know my work was usable and can improve.

**Acceptance criteria**
1. The Completed tab (or a new "My Completed" section) shows each exam's
   read state: waiting / in progress / reported (from `reports.status`),
   plus any QA flags on my images.
2. The state updates with the existing 30s poll (no new polling surface).
3. A rejection/flag on my images surfaces as a notification-bell event
   ("Your images need review") so the feedback is proactive.
4. Tests cover the state derivation and the bell event.

**Affected areas:** `frontend/src/technologist/TechnologistWorklist.tsx`,
`backend/api/exams.py` or `db/exams.py` (join report state for the
technologist's completed exams), notification events.

---

## P2-1 — Next-patient pointer on the Exam Console

**User story:** As a technologist, I want to see who is next on my modality
without leaving the console, so that I keep the room moving.

**Acceptance criteria**
1. The Exam Console header shows the next ready exam for my modality/station
   (accession, patient, priority) via the existing `GET /exams` query.
2. It refreshes with the console's data (no new polling loop).
3. It degrades gracefully when nothing is next ("No queued exams").

**Affected areas:** `frontend/src/technologist/ExamConsole.tsx`, small
enrichment of `db/exams.py list_for_technologist` (next-in-queue).

---

## P2-2 — Incident follow-up visibility for the technologist

**User story:** As a technologist, I want to see when QA resolves an incident
I logged, so that I trust the loop and learn from it.

**Acceptance criteria**
1. An incident-status event feeds the notification bell (no QA_READ needed —
   the event, not the queue, reaches me).
2. My incidents list (Exam Console or worklist) shows resolution state.
3. Tests cover the notification event for the incident author.

**Affected areas:** notification event types, `backend/api/exams.py`
incidents handler (author notification), Exam Console incident list.

---

## P2-3 — Prior safety/contrast history on the exam console

**User story:** As a technologist, I want to see the patient's prior
safety/contrast screening before I scan, so that I never miss a documented
allergy or reaction.

**Acceptance criteria**
1. The Safety Checks card shows prior exam safety records for the same
   patient (checked items + date + who) when they exist.
2. A prior adverse reaction (documented) renders a prominent warning.
3. No new endpoint if `exam.prior_studies`/patient history can carry it;
   otherwise a scoped read on the patient's safety records.

**Affected areas:** `backend/api/exams.py` (patient safety history),
`frontend/src/technologist/ExamConsole.tsx` (Safety Checks card).

---

## P2-4 — Worklist overdue/summary headline

**User story:** As a technologist, I want a one-line "3 ready, 1 overdue"
summary so that I know the state of my queue without scanning rows.

**Acceptance criteria**
1. Above the worklist table, a summary line shows ready count and the count
   of exams past the 30-minute attention threshold.
2. It derives from the existing `per_page=500` fetch (no new endpoint).
3. Tests cover the derivation (empty, mixed, overdue).

**Affected areas:** `frontend/src/technologist/TechnologistWorklist.tsx`.

---

## P2-5 — Add `aria-label`/ids to worklist filters (a11y parity)

**User story:** As a keyboard/screen-reader user, I want the worklist filters
to have stable labels, so that I can operate the queue like everyone else.

**Acceptance criteria**
1. The modality Select and search input carry `aria-label`s (matching the
   pattern used on ReadingWorklist filters).
2. The status chips are keyboard-reachable with `aria-pressed` state.

**Affected areas:** `frontend/src/technologist/TechnologistWorklist.tsx`.

---

## Definition of Done (whole hand-off)

- [ ] Backend: `pytest` passes (new tests for claim, critical-flag write,
      read-state derivation, incident notifications, DB-grants == matrix).
- [ ] Frontend: `tsc` + `npm run build` pass; `ruff`/prettier clean.
- [ ] The drift fix is applied in dev **and** CI (grants assert) so every
      remaining item is testable against the real role.
- [ ] No schema change ships without an Alembic migration.
- [ ] Every new endpoint is permission-gated and validated with `parse_body()`.
- [ ] E2E: technologist spec covers claim (P1-2), critical-flag (P1-1), and
      completed-read-state (P1-3) as `test.technologist` — with the real
      backend role (no API stubs).
