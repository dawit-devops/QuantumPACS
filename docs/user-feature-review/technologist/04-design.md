# 04 — Design Proposal (technologist)

Phase 2 of `user-feature-review technologist`. Input: `03-handoff.md`
(P0-1 drift fix + P1-1/2/3 + P2-1/2/3/4/5). ui-ux-pro-max baseline:
**Data-Dense Dashboard** style over the existing QuantumPACS tokens —
the recommended palette **matches the project's tokens exactly**
(`--color-primary: #0891B2`, health green `#16A34A`, destructive `#DC2626`),
so **zero token changes**. Typography: the Figtree/Noto Sans pairing maps to
the project's current sans stack — no font swap.

## Design system baseline

| Dimension | Decision |
|---|---|
| Style | Data-Dense Dashboard (already the app's character) — keep |
| Primary | `#0891B2` (existing `--color-primary`) |
| Accent / success | `#16A34A` (existing health green) |
| Destructive / critical | `#DC2626` (existing `--color-destructive`) |
| Density | High (8–32px scale) — already the console's spacing |
| Effects | Hover tooltips, row highlight on hover, smooth filter transitions (150–300ms), loading spinners — already present |
| A11y | WCAG AA: ≥4.5:1 contrast, visible focus, aria-live for queue changes (already implemented) |

**Conflicts with existing patterns:** none of the recommendations fight the
current Ant Design implementation — every component below already exists in
the app (Tag, Badge, Button, Modal, Select, Tooltip, Alert, Descriptions).

---

## P0-1 — Role-grant drift (data + guard, not UI)

No visual design. The fix is:
1. A new Alembic migration re-applying migration 048's grants for the four
   drifted slugs (`technologist`, `radiologist`, `resident`, `cashier`) —
   the canonical `BUILT_IN_ROLES` sets.
2. Harden `seed_built_in_roles()` (or add a boot-time reconciliation) so
   editable built-ins converge to the canonical set instead of preserving
   drift — with the same "preserve facility edits" concern handled by
   updating only when the row equals a known-prior drifted shape, or
   re-running a migration. (Decision left to implementation; see conflicts.)
3. A pytest asserting live-DB grants == `BUILT_IN_ROLES` per slug (guards CI).
4. `e2e/helpers.ts` drops the `/api/**` stub for the technologist.

---

## P1-1 — Critical-results flag workflow

**Design:** a red-flag affordance that converts a dead grant into a visible,
auditable safety action.

- **Exam Console:** a `danger`-styled Button "Flag Critical" in the header
  Space (next to Log Incident), rendered only when `can("CRITICAL_RESULTS_WRITE")`
  and the exam is not completed. Icon: `AlertOutlined` (exists in the app's
  icon set; no emoji). Opens a Modal:
  - Severity Select (`critical` pre-selected, options low→critical)
  - Series reference Select (from `exam.acquisitions`) — optional
  - Free-text note (TextArea, required min 10 chars, mirroring the
    Emergency Override justification pattern)
  - Alert copy: "This flag is visible to the reading team immediately."
- **Confirmation:** `message.success("Flagged for immediate read")` (toast,
  3–5s auto-dismiss per ui-ux-pro-max Feedback rule) + the flag persists on
  the console as a red Badge on the exam status ("CRITICAL FLAG").
- **Reading Worklist surfacing:** flagged exams render a red
  `Tag color="red"` "CRITICAL" in a new "Flag" column and sort above routine
  work (below in-progress STATs). The ReadingWorklist already has
  priority/status columns — this is a column + sort comparator addition.
- **States:** loading (button spinner), success (toast + badge), error
  (toast, form stays open), duplicate-flag (idempotent — re-flag updates).

## P1-2 — "My Exams" ownership: assigned vs unassigned pool + claim

**Design:** make ownership visible at a row level and claim a one-click act.

- **Worklist columns:** add a "Assignee" indicator to the existing table:
  - `assigned_technologist = me` → no extra tag (subtitle already says "Your
    assigned exams")
  - `assigned_technologist = ''` → gray `Tag` "Unassigned" + a small
    `primary ghost` "Claim" button in the Actions cell (next to Open Exam).
- **Claim:** click → `POST /exams/{id}/claim` (EXAM_WRITE) →
  `message.success("Exam claimed")` → row refreshes via the existing 30s
  poll (no new fetch surface); the tag flips to assigned.
- **Conflicts:** double-claim returns a conflict toast ("Claimed by
  another technologist") — the backend already has the "already adopted"
  pattern to mirror.
- **A11y:** Claim button has `aria-label="Claim exam {accession}"`; the
  Unassigned tag is not color-only (text label present).

## P1-3 — Completed-exam feedback loop

**Design:** close the loop with a read-state column + a proactive bell event.

- **Worklist Completed tab:** add a "Read State" column derived from
  `reports.status` for the technologist's completed exams:
  - `reported` → green Tag "Reported"
  - `submitted` → gold Tag "In review"
  - no report → default Tag "Awaiting read"
- **QA flag feedback:** when a QA review flags the tech's images, a
  notification-bell event fires ("Your images need review — exam {accession}")
  (persistent in the bell list, not a transient toast — it's actionable,
  per the Feedback rule distinction).
- **States:** the column updates with the existing 30s poll; no new polling.

## P2-1 — Next-patient pointer on the Exam Console

- A compact line in the console header (below the subtitle):
  `Next: {accession} · {patient} · {modality} {priority tag}` with a
  secondary "Open" link to that exam.
- Derived from `GET /exams` with the next ready exam for the same
  modality/station; refreshes with the console's fetch.
- Empty state: muted "No queued exams" (empty-state guidance rule).

## P2-2 — Incident follow-up visibility

- New notification-bell event "Incident resolved" to the incident author
  when QA closes it (bell list, persistent).
- The Exam Console's incident modal result shows resolution state for the
  tech's own incidents (a small `Tag` on each: "Open" / "Resolved").

## P2-3 — Prior safety/contrast history

- The Safety Checks card gains a "Prior screenings" sub-section listing the
  patient's previous exam safety records (checked item, answer, date, by).
- A documented adverse reaction renders a red Alert above the checklist
  ("Prior adverse reaction documented — verify before proceeding").
- Empty state: "No prior screenings on record."

## P2-4 — Worklist summary headline

- Above the table (under the filter chips): a one-line summary
  `{n} ready · {m} overdue (≥30m)` derived from the existing per_page=500
  fetch. Overdue in `--color-warning` (gold), ready in primary; both text +
  color (not color-only).

## P2-5 — Worklist filter a11y

- `aria-label` on the modality Select and search Input (mirroring the
  ReadingWorklist pattern already shipped: `id` + `aria-label`).
- Status chips get `aria-pressed` bound to their active state.

---

## Interaction & motion summary

| Item | Motion | Duration |
|---|---|---|
| Claim / Flag buttons | Button loading spinner | n/a |
| Row tag changes (Unassigned → assigned) | Immediate on poll refresh | 0ms (no decorative animation) |
| Critical flag surfacing | Badge appears; worklist tag renders | immediate |
| Toasts (claim/flag/complete) | Auto-dismiss | 3–5s |

All new interactions reuse existing Ant Design primitives with explicit
loading/empty/error states and WCAG AA conformance (labels, focus,
text+color indicators).

## Conflicts with existing patterns

1. **P0-1 drift reconciliation vs "preserve facility edits":**
   `seed_built_in_roles()` deliberately does NOT upsert editable built-ins so
   tenant/platform admins can tune them. The fix must reconcile only the
   *known drifted shape* (the 92-grant set) to canonical — or ship a
   migration that re-applies 048 and rely on the pytest guard — rather than
   force-resetting every boot (which would re-introduce the wipe-edits bug).
   Implementation choice; UI-invisible either way.
2. **Critical flag on the worklist:** adding a column widens the already-wide
   table (`scroll={{x: 900}}`). The Flag column must stay narrow (icon+label
   Tag) and the horizontal scroll already handles overflow (per ui-ux-pro-max
   table-handling rule).
3. **P1-2 claim semantics:** the R04 assignment flow sets
   `assigned_technologist` from the worklist. Claim must not fight it —
   claim only applies to `assigned_technologist = ''` rows; the backend
   rejects claims on already-assigned exams.
