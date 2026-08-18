# 01 — Hypothetical Flows: What the technologist expects but can't do

Flows a technologist needs end-to-end that the app cannot fully do today.
Marked exists / missing against the current implementation (inventory `00`).

---

## F1 — Scan a patient end-to-end under time pressure

**User story:** As a technologist, I want to move a patient from the waiting
queue to a completed, radiologist-ready study in as few interruptions as
possible, so that wait times stay short and STAT orders never stall.

**Scenario:**
1. See my assigned exams sorted with STAT/urgent first (exists — priority sort, red STAT tag)
2. Open the exam, confirm the patient against the order (exists — identity card + Confirm Patient)
3. Pick the protocol the facility has already configured (exists — protocol select, default auto-picked)
4. Acquire, QA each series (exists — Acquire Image, per-series Accept/Reject)
5. Record dose and safety before contrast (exists — dose ledger + per-item safety checks)
6. Complete and hand off to radiology (exists — Complete Exam with handoff message)
7. **Know the patient is next on the modality without leaving the console**
   (missing — no "next in queue" / patient order view; the technologist must
   tab back to the worklist or the MWL)
8. **See that my completed study was actually read / picked up**
   (missing — no read-status feedback loop after handoff)

**Data/API impact:** read-status or report-state per exam the technologist
completed (e.g. `report.status` surfaced on the Completed tab), and a
"next patient" pointer on the console.

---

## F2 — Flag a critical finding the moment I see it on the image

**User story:** As a technologist, I want to flag something alarming I see
during acquisition (e.g. massive bleed, pneumothorax) without waiting for the
radiologist, so that the reading happens immediately, not in queue order.

**Scenario:**
1. Notice the finding on the viewport during acquisition (viewer exists)
2. Click "Flag critical" on the exam console (missing — **no such control**)
3. Choose severity and attach the series (missing)
4. The radiologist worklist surfaces it as a critical read (exists only if
   routed — no writer end exists)

**Data/API impact:** a `critical_results` write path. **The grant exists
(`CRITICAL_RESULTS_WRITE` is canonical for technologist) but has no backend
gate and no UI** — verified: the permission appears only as a label in
`frontend/src/api/roles.ts` and nowhere in `api/`. This is a dead grant.

---

## F3 — Retake a rejected series and log the incident without duplicate paperwork

**User story:** As a technologist, I want the retake of a rejected series to
carry its reject reason and auto-suggest an incident, so that QA learns from
mistakes and I don't re-type the story.

**Scenario:**
1. Reject a series with a reason (exists — reject modal)
2. Retake it (exists — Retake button, next series number, "Retake —" description)
3. Log the incident (exists — Log Incident pre-filled from reject reason)
4. **See the incident I logged in the facility's QA queue with my name on it**
   (missing for the canonical role — QA_READ absent; QA is radiologist/pacs
   territory, so the tech writes but never sees resolution)
5. **Get told when QA closes the incident**
   (missing — no incident-status notification; the bell exists but has no
   incident-followup event)

**Data/API impact:** incident lifecycle events into the notification system.

---

## F4 — Run a stat contrast study while the patient is already on the table

**User story:** As a technologist, I want the safety screening for a contrast
study to be a quick, explicit checklist, so that I never scan someone with a
documented allergy and never lose the audit trail.

**Scenario:**
1. Open a STAT CT (exists)
2. Confirm identity (exists)
3. Check the three safety items individually (exists — allergies / pregnancy / renal, per-item)
4. Record and proceed (exists)
5. **See the screening history from the patient's last visit** (missing —
   safety checks are per-exam; no prior-contrast-history view)
6. **Override the protocol in an emergency and have the override visible in
   the QA trail** (exists — Emergency Override with required justification,
   "audited and logged")

**Data/API impact:** prior safety/screening history on the exam console.

---

## F5 — Keep my modality worklist accurate when schedules change

**User story:** As a technologist, I want the DICOM worklist and the exam
schedule to agree, so that I never scan the wrong patient or wait for an
entry that was already moved.

**Scenario:**
1. Look at today's schedule (exists — Schedule Board day view)
2. See the modality worklist (exists — MWL with table/calendar)
3. **See cancelled/STAT changes reflected on both surfaces in real time**
   (partial — MWL and Schedule are separate data reads; no shared
   live-update indicator, no cross-highlight)
4. **Create an ad-hoc worklist entry when the front desk is busy**
   (exists — MWL Create Entry modal)

**Data/API impact:** shared refresh or a "changed since load" marker on both
surfaces.

---

## F6 — Report an equipment problem without leaving the console

**User story:** As a technologist, I want to flag a scanner fault from the
exam console, so that downtime is recorded and the next shift knows.

**Scenario:**
1. See repeated failures during acquisition (exists — reject / incident)
2. **File an equipment/incident with modality and station context** (exists —
   incident modal takes type/severity/description, but no station/modality
   auto-fill and no EQUIPMENT_* surface)
3. **See the equipment status / maintenance board** (missing — EQUIPMENT_READ/
   EQUIPMENT_WRITE exist in the drift role but have no UI or gates)

**Data/API impact:** equipment registry + incident linkage (the drift grant
list even contains EQUIPMENT_READ/WRITE with zero surface).

---

## F7 — Know my queue and workload at a glance

**User story:** As a technologist, I want a quick sense of my pending volume,
time in queue, and anything overdue, so that I can decide what to do next
without counting rows.

**Scenario:**
1. See per-status counts (exists — status chips with counts)
2. See elapsed time per exam (exists — Elapsed column, color-coded)
3. **See a headline "N ready, X overdue" summary** (missing — counts exist,
   overdue summary does not)
4. **See my personal productivity over the day** (missing — no per-user
   stats; the tech's own completed count only exists in the metrics role's
   world, which the tech can't reach)

**Data/API impact:** a lightweight `GET /exams/summary` or client-side
derivation from the existing per_page=500 fetch.

---

## F8 — Hand an exam to a colleague without breaking the audit trail

**User story:** As a technologist, I want to reassign an exam I claimed to a
colleague when I'm pulled away, so that the patient is still scanned and
responsibility is explicit.

**Scenario:**
1. See an exam assigned to me (exists — My Exams)
2. **Reassign it to another technologist with a reason** (missing — no
   reassign action; `assigned_technologist` is only set by the R04
   assignment flow)
3. The colleague sees it in their worklist (would exist — the list shows
   `assigned_technologist = me OR ''`)

**Data/API impact:** `PATCH /exams/{id}/assign` (permission-gated) + audit.

---

## F9 — See my own unassigned pool fairly

**User story:** As a technologist, I want "My Exams" to mean *mine*, so that I
can trust the queue when I pick the next patient.

**Scenario:**
1. Open My Exams (exists)
2. **Notice exams with `assigned_technologist = ''` appear in EVERY tech's
   queue** (exists today — `list_for_technologist` includes empty assignments;
   verified in `db/exams.py`)
3. **Claim one explicitly** (missing — no Take/Claim action; opening the exam
   does not assign it)
4. My completed tab shows my handoffs (exists — Completed tab + handoff alert)

**Data/API impact:** an explicit claim (`EXAM_WRITE`), or a visual
distinction between "assigned to me" vs "unassigned pool".
