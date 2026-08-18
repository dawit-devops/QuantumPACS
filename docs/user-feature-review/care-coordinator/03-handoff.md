# 03 — Hand-off: care_coordinator (Phase 1)

Prioritized improvement list for the dev team. Every item: user story, acceptance
criteria (numbered, testable), affected areas, priority.

---

## P0-1 — Fix the SCHEDULE_READ dead end on the Schedule Board (cross-role regression)

**User story:** As a care coordinator (and physician), I want the Schedule Board
I'm granted to actually show the day's schedule, so I can coordinate bookings
instead of hitting "Missing permission".

**Context:** `GET /api/v2/worklist` requires `WORKLIST_READ`. The board's route
gates on `SCHEDULE_READ`, and the sidebar item now gates on `WORKLIST_READ` (R13
change) — so SCHEDULE_READ-only roles get: hidden sidebar item + rendering route
+ failing data. R13 already solved this for resident by adding read-only
`WORKLIST_READ`; the same unlock is missing from `MATRIX_B_COORD` and
`MATRIX_B_PHYS`.

**Acceptance criteria:**
1. `test.care_coordinator` and `test.physician` can load `/schedule-board` and
   see day data (no 403 on `/api/v2/worklist`).
2. The Schedule sidebar item is visible to those roles (sidebar gate consistent
   with the data gate).
3. No write capability is added: `WORKLIST_WRITE` stays absent for both roles.
4. Canonical sets in `BUILT_IN_ROLES` (Matrix B) match the new grants, and the
   DB-grants-vs-matrix test (from the technologist P0-1 fix) stays green.
5. Existing roles (technologist, radiologist, resident, receptionist) unchanged.

**Affected:** `backend/api/permissions.py` (MATRIX_B_COORD, MATRIX_B_PHYS),
role-grants test, `frontend/src/common/Sidebar.tsx` (if gate needs aligning).

**Priority: P0** — blocks a granted page outright; regression of the R13 fix
pattern for two more roles.

## P0-2 — Give care_coordinator a real surface for its defining grants

**User story:** As a care coordinator, I want at least one working workflow —
care plans (HF-1) or order tracking (HF-2) — so the role does something I
recognize as my job.

**Acceptance criteria:**
1. A UI surface exists that uses ≥1 of: `CARE_PLAN_WRITE`, `ORDER_WRITE`,
   `ENCOUNTER_WRITE`, `MED_ORDER_READ`, `PRIOR_AUTH_READ`.
2. The surface is reachable from the sidebar and lands in the correct workspace.
3. Write actions enforce the matching grant; read-only views enforce the
   read grant.
4. Empty states are actionable (no dead "no data" screens).

**Affected:** new page(s) under `frontend/src/` + backend endpoints as needed.

**Priority: P0** — the role's reason for existing is unimplemented. Scoped
suggestion: ship **order tracking** first (HF-2) — it reuses `ORDER_READ` (gate
exists) and the existing worklist/exam data, and is the highest-value
coordination view.

## P1-1 — Fix the Files page dead end for STUDY_READ-only roles

**User story:** As a care coordinator, I want the Files page I'm shown to either
work or not appear, so I'm not bounced by a Retry that can't succeed.

**Acceptance criteria:**
1. Either (a) read-only `FILE_READ` is granted to care_coordinator (consistent
   with STUDY_READ/VIEWER_READ it already holds) and the file list loads; or
   (b) the Files sidebar item and route are hidden for roles without `FILE_READ`.
2. No write/delete capability added.
3. `test.care_coordinator` sees no "Missing permission: FILE_READ" dead state.

**Affected:** `backend/api/permissions.py` (MATRIX_B_COORD) or
`frontend/src/common/Sidebar.tsx` + `frontend/src/index.tsx` route gate.

**Priority: P1** — visible broken surface; but secondary to P0-1/P0-2.

## P1-2 — Land care_coordinator on a role-appropriate home

**User story:** As a care coordinator, I want my landing page to be mine (today's
coordination items or a neutral home), so the app doesn't hand me the
radiologist's worklist.

**Acceptance criteria:**
1. `test.care_coordinator` does not land on `/reading`.
2. Landing is either a role-scoped dashboard (today's orders/encounters — pairs
   with P0-2) or the Files/patient-search home with role-appropriate content.
3. Other roles' landing behavior is unchanged.

**Affected:** `frontend/src/navigator.ts` landing logic / route default.

**Priority: P1** — correctness of the role experience; low code risk.

## P2-1 — Surface report status on the patient page for read roles

**User story:** As a care coordinator, I want to see (at a glance) whether a
patient's imaging has been read and at what level, so I can close the loop with
the referrer.

**Acceptance criteria:**
1. Patient page shows a Reports/Results section for roles with REPORT_READ.
2. Status shown (in progress / final) with the read date.
3. Empty state: "No reports yet" with guidance.

**Affected:** `frontend/src/patient/Patient.tsx` + patient detail payload.

**Priority: P2.**

## P2-2 — Make permission failures actionable

**User story:** As a care coordinator, when a page can't load I want to know
whether it's me or the app, and where to go instead.

**Acceptance criteria:**
1. Permission-failure states name the missing capability and offer a working
   alternative (e.g., "Ask an administrator for file access · Go to Patient
   Search").
2. The Retry button is hidden when retry cannot succeed (permission errors).

**Affected:** shared error/empty-state component(s).

**Priority: P2.**

---

## Definition of Done (all items)
- [ ] Every AC verified live as `test.care_coordinator` (and `test.physician`
      for P0-1) on the real backend
- [ ] Backend pytest + ruff green; frontend `tsc` + build green
- [ ] Canonical sets in `BUILT_IN_ROLES` are the source of truth; DB-grants test
      green (no drift)
- [ ] Playwright E2E covers P0-1 (board loads), P0-2 (one workflow), P1-1
      (files not dead), P1-2 (landing)
