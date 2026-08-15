# 01 — Hypothetical Flows: care_coordinator (Phase 1)

What a care coordinator needs to do end-to-end that the app **cannot do today**.
Each flow: user story → step-by-step scenario (marking what exists today) → data/API impact.

---

## HF-1: Build and share a care plan

**User story:** As a care coordinator, I want to create a care plan for a patient
(mapped orders, follow-ups, imaging requests) so the clinical team has one shared
to-do list.

**Scenario:**
1. Open patient → see a "Care plan" tab — ❌ *missing* (no care-plan UI at all)
2. Add an imaging order (e.g., MRI with contrast) to the plan — ❌
3. Assign follow-up tasks to team members — ❌
4. Notify the team (bell event) — ❌
5. Mark the plan active and revisit it — ❌

**Data/API impact:** `CARE_PLAN_WRITE` + `ORDER_WRITE` exist as grants but no
endpoints are wired to a UI; needs a care-plan resource + task list + team
assignment + notify on change.

## HF-2: Track an order from request to result

**User story:** As a care coordinator, I want to see the lifecycle of every
imaging order (requested → scheduled → performed → reported) so I can chase
stuck work and answer patients.

**Scenario:**
1. Open the order/queue surface — ❌ *no order list UI*
2. See status + age per order — ❌
3. Filter by "waiting > 24h" — ❌
4. Open the order → patient, requisition, assigned modality — ❌
5. Link through to the report when it lands — ❌ (report exists, link path absent)

**Data/API impact:** `ORDER_READ` gate exists but the orders list endpoint has no
frontend consumer; needs an orders list + status-age columns + deep links.

## HF-3: Verify prior authorization before scheduling

**User story:** As a care coordinator, I want to check a patient's prior-auth
status before booking an appointment so we never scan without coverage.

**Scenario:**
1. From the patient page open "Prior auth" — ❌ *no UI*
2. See auth number, insurer, status, expiry — ❌
3. Flag "not authorized" to block booking — ❌

**Data/API impact:** `PRIOR_AUTH_READ` unused in the frontend; needs a read surface
(and ideally a schedule-block guard).

## HF-4: See the day's schedule without a permission cliff

**User story:** As a care coordinator, I want to glance at today's schedule
(bookings, capacity, cancellations) so I can coordinate with referring offices.

**Scenario:**
1. Click "Schedule" in the sidebar — ❌ *sidebar item hidden (WORKLIST_READ gate)*
2. Direct-navigate `/schedule-board` — ⚠️ *renders, then "Failed to load schedule —
   Missing permission: WORKLIST_READ"* (dead end)
3. See the day board with bookings — ❌
4. Open a booking → patient/order detail — ❌

**Data/API impact:** the board's data endpoint `GET /api/v2/worklist` requires
`WORKLIST_READ`; a `SCHEDULE_READ`-holding role gets the route but not the data.
Same defect R13 fixed for resident by adding `WORKLIST_READ` — still live for
care_coordinator (and physician).

## HF-5: Follow up on a patient's result with the referring clinician

**User story:** As a care coordinator, I want to see when a patient's imaging was
read and what it said (at a summary level) so I can close the loop with the
referrer and the patient.

**Scenario:**
1. Open the patient → "Reports" section — ⚠️ *partially: report list is not
   surfaced on the patient page for this role*
2. See status (in progress / final) — ❌
3. Share a printable summary — ❌

**Data/API impact:** `REPORT_READ`/`RESULTS_READ` exist; needs a patient-scoped
report summary + share action.

## HF-6: Log an encounter / update the patient story

**User story:** As a care coordinator, I want to record a phone call or a visit
(encounter) so the team knows the patient was contacted.

**Scenario:**
1. Open patient → "Encounters" — ❌ *no UI*
2. Add encounter (type, notes, date) — ❌
3. See the timeline — ❌

**Data/API impact:** `ENCOUNTER_WRITE` unused in the frontend.

## HF-7: A role-appropriate home

**User story:** As a care coordinator, I want to land on *my* workspace (today's
coordination items) rather than the radiologist's worklist so the app doesn't
look like a permissions mistake.

**Scenario:**
1. Log in → land on `/reading` ("Handed-off exams awaiting interpretation") — ⚠️
   *wrong workspace; reads as a misconfiguration to the user*
2. See today's coordination items instead — ❌

**Data/API impact:** landing-route decision per role; needs a coordination
dashboard or a neutral landing page.
