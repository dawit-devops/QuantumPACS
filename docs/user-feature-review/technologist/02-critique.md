# 02 — Critique: The technologist experience vs expectations

Framed as the test.user's experience. Severity: **Critical** (blocks the task)
/ **High** (major friction) / **Medium** (annoyance) / **Low** (polish).

---

## Critical

### C1 — Test-user grants drifted from the canonical role (dev/CI integrity)

As a technologist, when I log in as `test.technologist` I see **every**
surface in the app — Reading Worklist, QA queue, Admin console, Front Desk,
My Records, Metrics — because the role's stored grants carry 92 permissions
instead of the canonical 15. The QA queue even shows real pending reviews.
My Account page lists 94 permission tags. I cannot tell what a real
technologist can do from this environment.

- **What I see:** sidebar shows all sections; `/qa/queue`, `/reading`,
  `/admin` all render instead of bouncing to `/exams`.
- **Why it matters:** every role-scoped E2E spec and any manual QA session
  tests a super-user, not the role. The `e2e/helpers.ts` `seedTechnologist`
  fakes localStorage grants **and stubs every `/api/**` request** — an
  admission that the real backend role can't be trusted for role-scoped
  tests. `radiologist` (92 vs 23), `resident` (27 vs 18) and `cashier`
  (8 vs 7) are drifted too; migration 048's trim was overwritten after it ran
  (role `updated_at` 08-12/13 vs migration 08-09).
- **Trust:** data displayed is not the role's data.

## High

### C2 — "Flag critical result" is a dead grant

As a technologist, the moment I see a massive bleed on the scan I want to
flag it so the radiologist reads it immediately. The grant
`CRITICAL_RESULTS_WRITE` is canonical for my role, but the app has **no
button, no endpoint, no workflow** that uses it (verified: only a label in
`frontend/src/api/roles.ts`). The capability silently doesn't exist.

- **Discoverability:** I cannot find a feature that isn't there.
- **Trust:** the permission list implies a safety capability the app lacks.

### C3 — "My Exams" is not mine

As a technologist, opening "My Exams" shows exams with
`assigned_technologist = ''` in every technologist's queue (`db/exams.py`
`list_for_technologist` includes empty assignments). There is no claim
action, so I cannot tell which rows are truly mine or take ownership of an
unassigned STAT.

- **Trust:** the headline says "Your assigned exams" but the list includes
  the shared pool.
- **Efficiency:** to be sure, I must open each exam.

### C4 — No feedback loop after handoff

As a technologist, after I complete an exam I never learn what happened —
was it read? Did the radiologist find a problem with my images? The
Completed tab shows "handed off" but nothing after.

- **Feedback:** completion is the last signal I get.
- **Trust:** I can't verify my work was usable.

## Medium

### C5 — No next-patient / queue position on the console

As a technologist mid-scan, I have no idea who is next on my modality; I
tab back to the worklist to check. With STAT stacking, that's exactly when
I'm busiest.

- **Efficiency:** extra navigation during the busiest moment.

### C6 — Incidents are write-only for me

As a technologist, I log incidents and rejections, but the QA queue
(`/qa/queue`, QA_READ) is out of my reach, so I never see resolution. The
notification bell has no incident-followup events.

- **Feedback:** I never learn whether my incident was actioned.

### C7 — Prior safety/contrast history not visible

As a technologist, safety checks are per-exam; I can't see the patient's
prior contrast reactions before I scan them.

- **Trust:** I may re-scan someone with a documented reaction because the
  history isn't in front of me.

## Low

### C8 — Worklist/console polish gaps

- Modality and Schedule surfaces are separate reads with no shared
  "changed since load" indicator (F5).
- The empty-worklist copy ("No exams assigned…") and the Completed-tab alert
  are good, but there's no overdue summary headline (F7).
- Prior-study "Open in viewer" links land in the shared viewer, which is
  fine, but the acquired-image QA thumbnails are simulated mini-canvases
  until real DICOM is stored (by design, C11).

### C9 — Pre-existing antd v6 deprecation warnings

Console shows `Alert message`, `Statistic valueStyle`, `Space direction`
deprecations on several surfaces. Cosmetic, but noisy for developers.

---

## Severity rollup

| Severity | Count | IDs |
|----------|-------|-----|
| Critical | 1 | C1 |
| High | 3 | C2, C3, C4 |
| Medium | 3 | C5, C6, C7 |
| Low | 2 | C8, C9 |

## Positive notes (what works well)

- The exam console is genuinely good: 5-step guided flow, per-item safety
  checkboxes with a radiation warning on the pregnancy item, dose ledger
  with per-series table and ACR benchmark progress (warning/exception
  states), audited emergency overrides with required justification, reject→
  retake→incident linkage.
- The worklist's live-update design is thoughtful: aria-live arrival
  announcements, visibility-gated 30s polling, sessionStorage-persisted
  filters, elapsed-time color coding, STAT-first sort.
- Denial handling is correct in code (PermissionRoute → landingRouteFor →
  `/exams`); the drift hides it, but the canonical gates are in place.
- Zero console errors beyond antd deprecations; MWL + Schedule + Files all
  render cleanly.
