# UI/UX Redesign v2 — Technologist TDD Implementation Plan

**Spec:** `docs/ui-ux-redesign-spec.md` §2.3 (v2.0)
**Branch:** `feature/ris-integration`
**Baseline:** 2594 passed / 2 skipped backend; FE frontdesk 25 + sidebar 25 + scheduling 13 + tech 0 (untouched) = 63; tsc clean.
**Method:** Vertical TDD slices — one RED test → minimal GREEN → refactor → suite gate. One commit per slice.

## 0. Preconditions & Decisions

### D0: Platform-inheritance principle

§2.3 Technologist is ~73% **INHERIT** — the existing QuantumPACS acquisition workspace (ExamConsole, Worklist, protocols, dose, critical results, incidents, safety checks, keyboard shortcut) already satisfies the spec's needs. Only **four genuine gaps** require new builds:

| Gap | Severity | T ref | What | Strategy |
|-----|----------|-------|------|----------|
| G-01 | P0 | T-02 | Unclaim / release-to-pool | EXTEND: add release to `ExamClaimHandler` + UI |
| G-02 | P0 | T-01 | "My Exams" default filter + toggle | EXTEND: frontend-only wiring |
| G-03 | P1 | T-05 | MWL sync status indicator + manual trigger | EXTEND: backend sync trigger + frontend badge |
| G-04 | P1 | T-06 | Protocol favorites + body-part/indication filter | BUILD NEW: favorites table + API fields + UI |

### D1: Permission grants

| ID | Grant | Feature | Rationale |
|----|-------|---------|-----------|
| G1 | `EXAM_READ`, `EXAM_WRITE` → `MATRIX_A_TECH` | all | Formalize exam grants in canonical Matrix A grantset (currently only in LEGACY_TECHNOLOGIST) — **APPROVED** |

All other gaps use existing permissions (WORKLIST_WRITE, WORKLIST_READ, EXAM_READ). No other new grants required.

### D2: Contract notes

- T-09 critical-flag endpoint is `POST /api/exams/{id}/critical-flag` (not `POST /api/ris/critical-results`). The existing endpoint writes `exams.critical_flag` + `ris_critical_results` via `CRITICAL_RESULTS_WRITE` (held by tech). **No change needed.**
- T-12 incident logging is `POST /api/exams/{id}/incidents` (EXAM_WRITE, held by tech). The spec's `POST /api/qa/incidents` is `QA_WRITE` (NOT held by tech). **The exam-scoped endpoint is the correct tech surface.**
- T-10 MWL exists at `/worklist` (Worklist.tsx), not spec's `/api/worklist`. The DICOM-standard columns are present.

## 1. Refined Gap Backlog (post platform cross-check)

**P0**
1. **G-01 T-02**: Unclaim / release-to-pool — claim exists, release does not
2. **G-02 T-01**: "My Exams" default filter + toggle — backend supports `assigned=mine|pool`, frontend never passes it

**P1**
3. **G-03 T-05**: MWL sync status indicator + manual trigger — sync columns exist, no badge UI, no trigger route
4. **G-04 T-06**: Protocol favorites + body-part/indication filter — no favorites concept, no indication filter

**Deferred (P2, not genuine gaps per platform-inheritance)**
5. T-03 ETA (client-side, optional polish)
6. T-13 color spec alignment (green/yellow/red vs current gray/gold/orange)
7. T-14 pregnancy ack individual requirement
8. T-07 quality score display (simulated, optional)
9. Non-CT dose benchmarks (CTDIvol, SNR)
10. T-04 dedicated contrast-reaction history endpoint (prior safety_checks suffice)

## 2. Vertical Slices (RED → GREEN → refactor → gate)

### S1 — Unclaim / release-to-pool (P0-1, T-02 G-01)

**Behaviors:** `POST /api/exams/{id}/claim` with `{release: true}` clears `assigned_technologist = ''`, audited `exam.unclaimed`. Only the current owner can release. 404 if exam missing. The "Release" button appears on owned rows in `TechnologistWorklist.tsx`.

**RED:** `test_exams_api.py` — new `TestExamClaim` class: test_release_clears_technologist (200 + assigned_technologist=''), test_release_by_non_owner_409, test_release_missing_404. `TechnologistWorklist.test.tsx` — release button renders on owned rows, fires release API.

**GREEN:** `ExamClaimHandler.post` — if `body.release` is true, clear `assigned_technologist` (only if current owner). Audit `exam.unclaimed`. `TechnologistWorklist.tsx` — add "Release" button on rows where `assigned_technologist == current_user`.

**Files:** `backend/api/exams.py`, `backend/api/schemas/exams.py`, `frontend/src/technologist/TechnologistWorklist.tsx`, `backend/tests/test_exams_api.py`, `frontend/src/test/TechnologistWorklist.test.tsx`.

**Gate:** `pytest tests/test_exams_api.py -q` + `npx vitest run src/test/TechnologistWorklist.test.tsx`

---

### S2 — "My Exams" default filter + toggle (P0-2, T-01 G-02)

**Behaviors:** `TechnologistWorklist.tsx` defaults to `assigned=mine` (only exams assigned to current user). Segmented control toggles between "My Exams" and "Unassigned Pool". Preference persisted in sessionStorage.

**RED:** `TechnologistWorklist.test.tsx` — default fetch includes `assigned=mine`, toggle changes to `assigned=pool`, sessionStorage remembers preference.

**GREEN:** `TechnologistWorklist.tsx` — add `assigned` param to fetch, default `'mine'`, segmented control `['My Exams', 'Unassigned Pool']` wired to `assigned`, persist in `sessionStorage`.

**Files:** `frontend/src/technologist/TechnologistWorklist.tsx`, `frontend/src/test/TechnologistWorklist.test.tsx`.

**Gate:** `npx vitest run src/test/TechnologistWorklist.test.tsx`

---

### S3 — MWL sync status indicator + manual trigger (P1-3, T-05 G-03)

**Behaviors:** `GET /api/worklist` returns `mwl_synced_at` / `mwl_sync_error` per entry (already stored). `POST /api/worklist/sync` (WORKLIST_WRITE) invokes `MwlSyncer.run_once()` and returns `{synced: N, errors: M}`. The Worklist page shows a "MWL Synced ✓" / "Pending ⏳" badge per entry + last-sync timestamp + "Sync Now" button.

**RED:** `test_worklist_api.py` — sync endpoint returns counts, requires WORKLIST_WRITE. `Worklist.test.tsx` — sync status badge renders, "Sync Now" button fires POST.

**GREEN:** New `POST /api/worklist/sync` handler (`WorklistSyncHandler`) calling `MwlSyncer.run_once()`. Route registration. `Worklist.tsx` — render `mwl_synced_at`/`mwl_sync_error` as status badge, add "Sync Now" button, refresh on completion.

**Files:** `backend/api/worklist.py`, `backend/api/routes.py`, `frontend/src/worklist/Worklist.tsx`, `backend/tests/test_worklist_api.py`, `frontend/src/test/Worklist.test.tsx`.

**Gate:** `pytest tests/test_worklist_api.py tests/test_mwl_sync.py -q` + `npx vitest run src/test/Worklist.test.tsx`

---

### S4 — Protocol favorites + body-part/indication filter (P1-4, T-06 G-04)

**Behaviors:** `GET /api/protocols` accepts `body_part`, `clinical_indication`, `is_favorite` (per-user) filters. `POST /api/protocols/{id}/favorite` (EXAM_WRITE) toggles favorite status. `ExamConsole.tsx` protocol Select shows a star favorite toggle, filters by body_part/indication when available.

**RED:** `test_exams_api.py` — favorite toggle endpoint, filter params. `ExamConsole.test.tsx` — star toggle + filter UI.

**GREEN:** New `protocol_favorites` table (migration 091) or per-user JSONB on user prefs. Extend `ProtocolsHandler.get` to accept `body_part`/`clinical_indication`/`is_favorite` params. New `ProtocolFavoriteHandler` toggle endpoint. `ExamConsole.tsx` protocol step — star toggle, filter dropdowns.

**Files:** `backend/migrations/versions/`, `backend/api/exams.py`, `backend/db/exams.py`, `backend/api/routes.py`, `frontend/src/technologist/ExamConsole.tsx`, `backend/tests/test_exams_api.py`, `frontend/src/test/ExamConsole.test.tsx`.

**Gate:** `pytest tests/test_exams_api.py -q` + `npx vitest run src/test/ExamConsole.test.tsx`

## 3. Test Strategy (§8 spec)

| Test type | Target | Tool |
|-----------|--------|------|
| Unit | Endpoint contracts, permission gates, DB queries | pytest (mock-based) |
| Integration | State transitions (claim→release, sync→status) | pytest (real DB where needed) |
| FE unit | Component rendering, form validation, API calls | vitest + RTL |
| E2E (deferred) | T-11 5-step flow, T-10 MWL refresh, T-09 critical flag | Playwright |

## 4. Permission Grant Request (for human review)

| ID | Permission | Grant to | Feature | Reason |
|----|-----------|----------|---------|--------|
| G1 | `EXAM_READ`, `EXAM_WRITE` | `MATRIX_A_TECH` | all T-features | Formalize the exam console grants in the canonical Matrix A grantset (currently only in LEGACY_TECHNOLOGIST). **APPROVED 2026-08-24.** |

## 5. Verification Gates (per slice)

1. Targeted RED fails for the stated reason
2. GREEN: slice tests pass
3. `pytest tests/<affected-suites> -q` + RBAC suite if touch permissions
4. FE: `npx vitest run <touched suites>` + `npx tsc --noEmit`
5. Full backend suite before each commit: `pytest tests/ -q`
6. FE build: `npx vite build`

## 6. Commit Strategy

One commit per slice, messages referencing spec IDs (T-xx) and slice numbers. Conventional commits (`feat:`, `fix:`, `chore:`). Work tree clean after each.

```text
feat: T1 unclaim / release-to-pool endpoint and UI (T-02 G-01)
feat: T2 "My Exams" default filter with pool toggle (T-01 G-02)
feat: T3 MWL sync status indicator and manual trigger (T-05 G-03)
feat: T4 protocol favorites with body-part/indication filter (T-06 G-04)
```