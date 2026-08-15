# 04 — Design Proposal: care_coordinator (Phase 2)

Source: `03-handoff.md` (P0-1, P0-2, P1-1, P1-2, P2-1, P2-2) · Stack: React 19 +
Ant Design v6 + Cornerstone3D · Style baseline: **Data-Dense Dashboard** (product
searches: analytics/productivity dashboards) over the existing QuantumPACS tokens
— **zero token or font changes** (`src/common/tokens.css`: primary cyan-700,
success teal-500, warning amber-500, error red-600, Inter typeface).

---

## P0-1 — Schedule Board: permission reconciliation (data fix, not UI)

The board itself is well-designed and needs **no visual change**. The defect is a
grant gap: the route gates on `SCHEDULE_READ`, the data (`GET /api/v2/worklist`)
gates on `WORKLIST_READ`, and the sidebar gates on `WORKLIST_READ`.

**Design decision:** follow the R13 pattern verbatim — add read-only
`WORKLIST_READ` to `MATRIX_B_COORD` and `MATRIX_B_PHYS` (comment mirrors the
resident rationale). The sidebar gate and data gate then agree for every
SCHEDULE_READ holder; the route gate stays as the schedule-surface definition.

- No new components. One configuration change + comment + matrix test update.
- **Conflict:** none — pure grant reconciliation, same shape as the shipped R13 fix.

## P0-2 — Order Tracking (the role's first real surface)

**Design:** an **Orders page** (`/orders`) — a coordination worklist, not a
radiology queue. Uses existing `ORDER_READ` (read) and `ORDER_WRITE` (update)
gates; deep-links to the exam/worklist data that already exists.

**Layout (Data-Dense, mirrors Reading Worklist structure so it feels native):**

```
[ PageHeader: "Orders" — "Imaging requests across the facility, from request to report." ]
[ Summary row:  N open · M waiting >24h · K reported today ]        ← P2-4-style headline
[ Filters: Status | Modality | Patient | Assigned coordinator ]     ← aria-labels (P2-5 pattern)
[ Table:  Status Tag │ Accession │ Patient │ Modality │ Requested │ Age │ Report ]
```

- **Status Tag** (semantic, existing antd Tag colors): `requested` (blue) →
  `scheduled` (cyan) → `performed` (green) → `reported` (default) · `cancelled`
  (red). An **age chip** ("2d") turns amber at >24h, red at >72h — the
  coordination-relevant signal (stuck work).
- **Row actions** (ORDER_WRITE): "Update status", "Assign coordinator",
  "Request prior auth" (links into P2-2's prior-auth chip, HF-3).
- **Report cell:** when a report exists, a `Link` to the reading view (closes the
  loop — HF-2 step 5).
- **Empty state** (UX guideline: never blank): "No open orders — new imaging
  requests will appear here. Book one from the Schedule Board." + a button.

**Where the other defining grants live (future tabs, same page):** Order row →
drawer with three tabs: **Care Plan** (CARE_PLAN_WRITE, HF-1), **Encounters**
(ENCOUNTER_WRITE, HF-6), **Prior Auth** (PRIOR_AUTH_READ, HF-3). This gives the
role a home for *all five* ghost grants without five separate pages. Tab content
is read-only where only the read grant exists; write tabs enforce their grant.

## P1-1 — Files page: grant read-only FILE_READ

**Design decision:** add `FILE_READ` (read-only) to `MATRIX_B_COORD`. Rationale:
the role already holds `STUDY_READ` + `VIEWER_READ` (the full read imaging
stack); `FILE_READ` is the list/download-read tier the Files page needs and every
other viewer role (technologist, radiologist, resident, teleradiologist) holds.
No UI change — the existing Files page renders correctly once the data call
succeeds.

- **Conflict:** must NOT include `FILE_WRITE`/`FILE_DELETE` — upload/delete stay
  with technologist/pacs_admin. Matches the resident grant shape (FILE_READ only).

## P1-2 — Care-coordinator landing (role-scoped home)

**Design:** `/orders` becomes the landing for care_coordinator (replacing
`/reading`). The PageHeader + summary row *is* the dashboard: today's open
orders, waiting >24h count, recent reports — the coordinator's "what needs me"
view, with the patient search reachable in the top bar.

- Workspace mapping: `care_coordinator → orders` in the navigator (same pattern
  as `technologist → exams`).
- **Conflict:** landing changes are global — must not disturb
  technologist/radiologist/receptionist landing behavior (regression-checked in
  E2E, P1-2 AC3).

## P2-1 — Report status on the Patient page

**Design:** a **"Reports & Results"** card on the patient page, visible to roles
holding `REPORT_READ` (care_coordinator, physician, resident, radiologist,
referrer). Lists the patient's reports with status Tag (draft / preliminary /
final) + read date, linking to the reading view. Empty state: "No reports yet."

## P2-2 — Actionable permission failures

**Design:** replace the bare "Missing permission: X · Retry" with a small shared
component (extend the existing error/empty state):

```
[ Alert (error) ]
"File access isn't enabled for your role."
[ "Go to Patient Search" ] [ "Ask an administrator" ]
```

- Hide **Retry** when the failure is a permission error (403) — retry can never
  succeed; keep it for transient errors (5xx/network).
- `role="alert"` for screen readers (UX guideline: error announced, not
  visual-only).

---

## Conflicts flagged

1. **P0-2 scope:** Order Tracking is a real feature build (new page + endpoints
   or reuse). The minimal-slice fallback: ship the Orders page read-only
   (ORDER_READ only) first, add ORDER_WRITE actions + the tabs drawer in a
   follow-up. Recommend the minimal slice in Phase 3 if time-boxed.
2. **P1-2 landing change** is global; verify no other role's landing shifts.
3. **P0-1 + P1-1 grant changes** must keep the DB-grants-vs-matrix test green and
   stay read-only (no WORKLIST_WRITE, no FILE_WRITE).

## Component inventory (all exist in the app — no new deps)

PageHeader · Alert · Tag · Table · Drawer · Descriptions · Select (aria-labels) ·
Statistic (summary row) · Empty · Button · Popconfirm — all already used in
ReadingWorklist / TechnologistWorklist / ScheduleBoard.
