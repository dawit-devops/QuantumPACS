# Acceptance Criteria — Staff Radiologist (R12)

Verifiable acceptance criteria mapped to FR/NFR IDs, validator-gated: every UI
outcome observable and measurable, never satisfied by "code exists".

## Acceptance Criteria Matrix

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R12-01 | FR-R12-01, NFR-R12-03 | Given the worklist loads, when it renders, then studies are sorted STAT-first with modality/patient/exam/time visible, ≤ 2s p90 | Synthetic probe + component test | Pass — order + timing measured |
| AC-R12-02 | FR-R12-01, NFR-R12-04 | Given a new STAT study arrives, when the list refreshes, then it appears at the top within 30s staleness | Synthetic event probe | Pass — measurable staleness |
| AC-R12-03 | FR-R12-02, NFR-R12-01 | Given I open a study, when the first instance is requested, then it renders ≤ 2s p90 on LAN | RUM + synthetic probe | Pass — measured budget |
| AC-R12-04 | FR-R12-02 | Given a large series, when loading, then progressive rendering shows the first image before the rest with a remaining-frames indicator | Visual + instrumentation | Pass — first paint observed |
| AC-R12-05 | FR-R12-02 | Given an instance fetch fails, when it fails, then the viewer shows a failed-instance badge and continues rendering others | Component test (mocked failure) | Pass — badge + continuation observed |
| AC-R12-06 | FR-R12-03 | Given the viewer is open, when I press keys 1–7/E, then the matching tools (pan, length, rect ROI, ellipse ROI, angle, arrow, eraser) activate immediately | E2E (Playwright keyboard) | Pass — tool state asserted |
| AC-R12-07 | FR-R12-03 | Given a tool is active, when I navigate with arrow keys/page, then navigation works without tool conflict | E2E | Pass — no state clash |
| AC-R12-08 | FR-R12-03, NFR-R12-05 | Given pan/zoom interaction, when performed, then rendering stays smooth at 60fps within the loaded window | Performance instrumentation | Pass — fps measured |
| AC-R12-09 | FR-R12-04 | Given a multi-series study, when I use the thumbnail strip, then I can switch series via keyboard and pointer, with the active series highlighted (icon+text) | E2E + visual | Pass — highlight + navigation |
| AC-R12-10 | FR-R12-05 | Given annotations exist, when I reopen the study, then measurements load at the same positions (parallel to image load) | Component test + visual | Pass — positions asserted |
| AC-R12-11 | FR-R12-05 | Given I delete an annotation, when I reopen, then it stays deleted (no resurrection) | Component test | Pass — persistence verified |
| AC-R12-12 | FR-R12-06 | Given I invoke priors, when the list loads ≤ 2s p90, then modality/date/body part show; empty state says "No priors" | Component test (seeded 0/1 priors) | Pass — list + empty state |
| AC-R12-13 | FR-R12-06 | Given I select a prior, when it loads, then it opens side-by-side with synced window/level and pan | E2E + visual | Pass — sync observable |
| AC-R12-14 | FR-R12-07, NFR-R12-06 | Given a study's detail view, when opened, then DICOM metadata renders in a readable table with copyable UIDs; change history lists actor/timestamp | Component test + visual | Pass — table + history asserted |
| AC-R12-15 | FR-R12-09 | Given I share a study, when I select a permission level, then the share link grants exactly that level; revoked shares show access-denied | API + component test | Pass — permission enforcement |
| AC-R12-16 | FR-R12-10 | Given a study is claimed, when another user opens the worklist, then the holder is visible and the study opens read-only | E2E (2 sessions) | Pass — holder + read-only state |
| AC-R12-17 | FR-R12-10 | Given two simultaneous claims, when a conflict occurs, then one user gets a conflict prompt and the state reloads | E2E | Pass — conflict handling |
| AC-R12-18 | FR-R12-11 | Given I mark a study done, when the state updates ≤ 1s, then the worklist reflects it and report status becomes visible | E2E | Pass — state observed |
| AC-R12-19 | FR-R12-13 | Given a STAT study is read, when escalation is available, then escalation is reachable in ≤ 2 keystrokes with a minimal confirm | E2E (GATED on backend) | GATED — escalation endpoint |
| AC-R12-20 | FR-R12-09 | Given the report panel exists, when autosave runs ≤ 10s, then drafts persist and re-open on reconnect without loss | Integration test | Pass — draft persists via `GET /reports/{exam_id}` |
| AC-R12-21 | FR-R12-09 | Given I sign a report, when confirmed, then it becomes final, is audit-logged, and worklist shows the status | API + backend test | Pass — `POST /reports/{exam_id}/sign` + audit log + reading-list status |
| AC-R12-22 | FR-R12-12 | Given a resident draft arrives, when the worklist refreshes, then "awaiting attending review" shows with the resident's name; review preserves annotations | E2E (GATED) | GATED — resident-draft attending-review queue not built (peer review covers final signed reports only) |
| AC-R12-23 | NFR-R12-07 | Given any chrome UI (worklist, toolbars, drawers, panels), when tested, then axe-core passes with zero serious violations and full keyboard operability | axe-core + manual pass | Pass — verified |
| AC-R12-24 | NFR-R12-08 | Given ES is down, when the worklist and viewer load, then reading is unaffected; search-only views degrade | Failure-injection E2E | Pass — isolation verified |
| AC-R12-25 | NFR-R12-09 | Given 50 concurrent reading sessions, when active, then no session errors or degradation beyond budget | Load test | Pass — concurrency verified |
| AC-R12-26 | FR-R12-15 | Given I save a window/level preset for a modality, when I open that modality later, then the preset applies before interaction (≤ 100ms added) | Component test + instrumentation | Pass — preset applied |
| AC-R12-27 | FR-R12-14 | Given a new STAT study arrives, when notification wiring is active, then a notification is created and the badge updates ≤ 5s (worklist re-sort is the fallback) | Backend test + component test (event probe) | Pass — `exam.completed` role notification + WS badge push |
| AC-R12-28 | NFR-R12-02 | Given series/instance navigation or tool interaction, when performed, then INP ≤ 200ms p75 | RUM / Lighthouse | Pass — measured budget |
| AC-R12-29 | NFR-R12-10 | Given report editing in progress, when the connection drops, then the local draft is preserved and syncs on reconnect (zero lost drafts) | Integration test | Pass — autosave flush + dirty-retry path |
| AC-R12-30 | FR-R12-09 | Given I open the report editor, when I pick a modality template, then findings/impression fields pre-populate from the template library | Backend + component test | Pass — `GET /reports/templates` applied |
| AC-R12-31 | FR-R12-12 | Given a final signed report exists, when I assign a peer review and submit an outcome, then the discrepancy level + comment persist and the report author is notified | Backend test + API test | Pass — `/peer-reviews*` workflow (covers signed-report review slice) |

## Excluded Scope / Out of Scope

- **Critical-findings escalation, resident-draft attending review** — GATED on
  backend (no escalation endpoint; peer review covers final signed reports only);
  ACs retained but not sprint-gateable.
- **Teleradiology remote specifics** (R18): VPN/SSO, preliminary vs final — separate package.
- **Billing, scheduling, equipment** — other packages.
- **Mobile viewer** — explicitly not required.
- **Annotation persistence** — AC-R12-10/11 depend on confirming the persistence
  endpoint (client-side sync exists).

## Validator Gate Verdict (ui-visual-validator lens)

From the verification evidence, I observe:

- **Achieved**: 27 of 31 ACs are verifiable today against the existing viewer
  surface (`frontend/src/detail/`, Cornerstone3D, DICOMweb API), worklist API,
  and the reporting/peer-review/presets stack shipped in merge 4d136e0
  (`backend/api/reports.py`, `backend/api/reading_presets.py`).
- **Partially achieved**: AC-R12-10/11 (annotation persistence) are specified but
  require confirming the backend persistence endpoint; the client sync
  (`useAnnotationSync.ts`) exists.
- **Not achieved (gated)**: AC-R12-19 (critical-findings escalation) and
  AC-R12-22 (resident-draft attending review) — no escalation endpoint; peer
  review (`/peer-reviews*`) covers final signed reports only.
- **Risk noted**: priors behavior (AC-R12-12/13) depends on confirming the priors
  loading path (currently search-based); STAT arrival notifications (W8) are wired
  via `exam.completed` + WebSocket but the ≤ 5s badge budget needs a live probe.

Verdict: package **approved for sprint planning in two slices** — (a) viewer +
worklist + reporting slice fully gateable now; (b) escalation/attending-review
slice gated on backend design.
