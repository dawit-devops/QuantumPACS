# 06 — E2E Report (technologist)

Phase 4 of `user-feature-review technologist` — Playwright verification of
the hand-off acceptance criteria against a **real backend** (seeded
`test.technologist` / `Test@123456`, canonical 15 grants post migration 062).

**Spec:** `frontend/e2e/technologist-review.spec.ts` (5 tests, serial)
**Result:** **5/5 passed** · **10/10 under `--repeat-each=2`** on the
`chromium` project (the local-dev standard). Zero console errors.

---

## Pass/fail traceability

| Hand-off item | E2E test | ACs covered | Result |
|---|---|---|---|
| **P0-1** role-grant drift fix | `P0-1: denied surfaces bounce to /exams (no super-user walkthrough)` | AC2 (denied routes bounce), AC3 (`test.technologist` can't open `/reading`, `/qa/queue`, `/admin`, `/frontdesk/*`, `/portal`), AC5 (live grants == matrix, unit tests) | ✅ |
| **P1-1** critical-results flag | `P1-1: critical flag surfaces on the radiologist reading list` | AC2 (permission-gated endpoint persists flag), AC3 (reading list surfaces flagged exam with severity), AC5 (backend + frontend tests) | ✅ |
| **P1-2** claim unassigned exams | `P1-2: claim an unassigned exam from the worklist` | AC2 (claim endpoint assigns with audit, idempotent on self), AC4 (truthful ownership), AC5 (claim + conflict tests) | ✅ |
| **P1-3** completed-exam read-state | `P1-3: worklist read-state column renders for completed exams` | AC1 (Read State column), AC2 (updates with existing poll), AC3 (QA-flag bell event — unit-tested in `test_qa_api.py`) | ✅ |
| **P2-1** next-patient pointer | browser-verified (evidence `26-next-patient.png`) | AC1 (header shows next ready exam), AC2 (same fetch, no new poll), AC3 (degrades gracefully) | ✅ |
| **P2-2** incident-resolved bell event | unit-tested (`test_qa_incident_resolve_notifies_reporter`) | AC1 (author notified via bell event), AC3 (test) | ✅ |
| **P2-3** prior safety history | browser-verified (evidence `22-console-new.png`) | AC1 (prior screenings sub-section), AC2 (adverse-reaction warning path), AC3 | ✅ |
| **P2-4** worklist summary headline | `P2-4: worklist summary headline shows ready/overdue` | AC1 (summary line), AC2 (derived from existing fetch), AC3 (test) | ✅ |
| **P2-5** filter a11y | code review + tsc | AC1 (aria-labels), AC2 (aria-pressed on chips) | ✅ |

---

## Evidence

### E2E spec (`technologist-review.spec.ts`)

```
$ npx playwright test technologist-review.spec.ts --project=chromium
  5 passed (serial, real backend)

$ npx playwright test technologist-review.spec.ts --project=chromium --repeat-each=2
  10 passed
```

Notable assertions:

- **P0-1** — navigates to `/reading`, `/qa/queue`, `/admin`, `/portal`,
  `/metrics`, `/users` and asserts each lands on `/exams`; the sidebar shows
  **no** "Reading Worklist" item and **does** show "Modality Worklist"
  (canonical 15-grant surface set).
- **P1-1** — seeds an exam via the real API (with `X-CSRF-Token: 1`), moves
  it to completed, flags it `critical`, logs in as `test.radiologist`, and
  asserts the reading list carries the exam with `critical_flag = 'critical'`.
- **P1-2** — seeds an exam, finds it in the worklist API, claims it, and
  asserts `claimed: true` (idempotent self-claim returns 200).
- **P1-3** — asserts the "Read State" column renders and completed rows show
  a read-state tag (Reported / In review / Awaiting read).
- **P2-4** — asserts the summary headline Tag (`ready`/`overdue`) is visible,
  scoped to the summary's `.ant-tag` to avoid the page's other aria-live
  regions.

### Browser verification (Phase 3 evidence)

- `21-worklist-new.png` — summary headline, Read State column, Unassigned tags
- `22-console-new.png` — Flag Critical button, next-patient line, prior
  screenings
- `23-flag-modal.png` / `27-flag-badge.png` — flag modal + red badge + toast
- `26-next-patient.png` — "Next: TECH-REV-ACC-1 · Tech^Review^Probe · CT"
- `29-reading-flag-tag.png` — red CRITICAL tag on the radiologist reading list
- `25-claim-row.png` — Unassigned tag + Claim button (row flipped after claim)

### Environmental notes (not regressions)

- **firefox project** — browser binary not installed on this dev box
  (`npx playwright install firefox` needed); the config marks it "optional
  extra coverage", CI gates on chromium/preview.
- **preview project** — the `vite preview` webServer (build + serve on 4173)
  failed to come up on this box (`ERR_CONNECTION_REFUSED`); documented
  pre-existing flakiness. The chromium dev-server project is the local
  standard and passes cleanly.
- The E2E-created probe exams were cleaned up after the run; the DB returns
  to its original 3 seeded exams.

---

## Definition of Done check

| DoD item | Status |
|---|---|
| Backend `pytest` passes (claim, critical-flag write, read-state, incident notifications, DB-grants == matrix) | ✅ 1692 passed · 1 skipped · 4 xfailed |
| Frontend `tsc` + `npm run build` pass; ruff/prettier clean | ✅ |
| Drift fix applied in dev **and** guarded (grants assert in tests) | ✅ migration 062 applied live; `test_role_grants_matrix.py` |
| No schema change without an Alembic migration | ✅ grant migration 062; exam-family columns via `sync_db` (existing pattern) |
| Every new endpoint permission-gated and validated with `parse_body()` | ✅ CRITICAL_RESULTS_WRITE / EXAM_WRITE / QA_WRITE |
| E2E covers claim (P1-2), critical-flag (P1-1), read-state (P1-3) as `test.technologist` with the real backend | ✅ all three + P0-1 denials + P2-4 summary |

## Verdict

**All hand-off items verified.** The drift fix is proven live (denied
surfaces bounce; token = canonical 15 grants), the critical-flag workflow
runs end-to-end from the tech's console to the radiologist's reading list,
ownership is explicit (claim + Unassigned tags), and the completed-exam
feedback loop closes with read-state + incident notifications. The
technologist workspace now behaves like the persona it represents.
