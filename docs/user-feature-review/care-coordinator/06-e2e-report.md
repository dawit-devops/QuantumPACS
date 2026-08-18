# 06 — E2E Report: care_coordinator (Phase 4)

Spec: `frontend/e2e/care-coordinator-review.spec.ts` · Project: chromium (local
standard; firefox binary not installed on this box, `vite preview` flaky —
pre-existing environmental limits, same as the technologist review).

**Result: 6/6 passed · 12/12 under `--repeat-each=2` · zero console errors on
the covered surfaces (only the benign, pre-existing tenant-selector 403).**

## Traceability (acceptance criteria → test)

| # | Test | AC (from 03-handoff) | Pass |
|---|------|----------------------|------|
| 1 | P1-2: lands on `/orders`, not `/reading`; sidebar has Orders, no Reading Worklist item | P1-2 AC1–2 (landing is role-scoped; other roles unchanged — verified separately in Phase 3) | ✅ |
| 2 | P0-1: Schedule Board loads day data for care_coordinator | P0-1 AC1 (board reachable, no 403) + AC3 (no write granted) | ✅ |
| 3 | P0-1: physician loads the Schedule Board too | P0-1 AC1 (cross-role) | ✅ |
| 4 | P1-1: Files page list loads, no "Missing permission: FILE_READ" | P1-1 AC1a/AC4 (read-only FILE_READ; no dead state) | ✅ |
| 5 | P0-2: seeded visit order renders on Orders page with summary headline | P0-2 AC1–2 (surface exists + reachable), P1-2 AC1 (landing) | ✅ |
| 6 | P2-1: patient page shows Reports & Results card | P2-1 AC1–2 (card renders for REPORT_READ) | ✅ |

## What each test proves

1. **P1-2 landing** — real UI login as `test.care_coordinator` (15 grants)
   lands on `/orders`; the radiologist Reading Worklist is neither the landing
   nor in the sidebar.
2. **P0-1 board** — `/schedule-board` renders the day header and totals with
   **no** "Failed to load schedule" (the pre-fix dead end); no WORKLIST_WRITE
   needed.
3. **P0-1 physician** — same board fix proven for the second affected role.
4. **P1-1 files** — `/` loads the search surface with no "Missing permission:
   FILE_READ" and no dead "No files uploaded" error state.
5. **P0-2 orders** — seeds a visit + order through the receptionist API
   (care_coordinator holds no write grants by design), then verifies the
   coordinator's Orders page renders the row ("MRI Brain") and the summary
   headline.
6. **P2-1 reports** — the patient page shows the Reports & Results card.

## Environmental notes (not regressions)
- `firefox` project: browser binary not installed (config marks optional; CI
  gates on chromium/preview).
- `preview` project: `vite preview` webServer flaky on this box — pre-existing.
- The `/v2/tenants` 403 is the tenant-selector probe: silently caught,
  invisible (selector renders only with >1 tenant), out of scope.

## Cleanup
E2E-seeded rows (`E2E-CC-*` visits/orders) deleted post-run; `visit_orders`
back to 0. No schema changes beyond migration 063 (grant data only).
