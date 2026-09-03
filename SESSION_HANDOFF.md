# SESSION_HANDOFF — QuantumPACS

**Branch:** `feature/ris-integration` (targets `v3-dev` — merge via PR, no direct pushes)
**Last updated:** 2026-09-02 (Session 3 — handoff to opencode; next job: auto reading-handoff feature)

---

## Scoreboard (quick reference)

| Scope | Status |
|---|---|
| Gap-audit Tier 0 keystones (§3/§4/§5/§6/§7) | ✅ done |
| Gap-audit Tier 1 (P1) orphan wiring (7) | ✅ done |
| Gap-audit Tier 2 (P4) clinical/UX completions | ✅ done |
| Gap-audit Tier 3 (P5) scheduling cluster (S-01..S-14) | ✅ done |
| P5 reading/coordinator/portal/frontdesk/kiosk/QA | ✅ done |
| P5 admin gaps | 🟡 partial — ADM-11, ADM-16, DM-07 done; **ADM-04, ADM-12 deferred** |
| DM-02 / DM-04 (manager dashboards) | ✅ done via S12 (`RISDashboard.tsx` + analytics endpoints) |
| QA regression from `2381fe9` (backend boot) | ✅ fixed (`2a11b83`) |
| Zip upload of DICOM archives | ✅ done (`cd7d708`) |
| Dark reading-room console | ✅ done (`1686b28`); E2E mostly verified, `[`/`]` collapse ⚠️ |
| **Auto reading-handoff of uploaded studies** | 🔴 **NOT started — design done, see ACTIVE JOB** |
| assign-endpoint int8/str 500 bug | 🔴 open — `backend/api/reports.py` ~:220 |
| Uncommitted work | 🟡 SESSION_HANDOFF.md edited this session (intentionally uncommitted) |

---

## Session History (append-only)

### Session 1 — `4c086fc8-714c-46b8-8699-bb79a67ff167` (2026-08-25 → 2026-08-26)
Ended by `/compact` after OpenRouter `402` (prompt-token budget exceeded). All work from this
session was committed before the compact.

#### Goal / Context

Execute the integrated PACS+RIS scope on `feature/ris-integration` in 3 phases:

1. Multi-reviewer code review of the round-5 commits (nursing N-01..N-04 + ADM-14/17 quota; 28 files) across Security / Performance / Architecture / Testing.
2. Fix all review findings in conventional-commit rounds.
3. Full audit of `docs/ui-ux-redesign-spec.md` v2.0 (~130 feature IDs) vs code, then implement gaps via a TDD pipeline with the pre-commit gates (ruff, prettier, tsc, pytest, vite build).

#### What Was Done

##### Phase 1 — Code review (18 findings closed)
8-agent parallel audit; findings closed across:
- `07eecd7` fix: signature integrity, checklist gate, atomic audits
- `74df221` fix: CR-002/009/010/012/013 — checklist arbiter migration, prep list DB, kiosk consent read paths, tier boundary
- `37dced6` test: consent read paths, tier boundary, hygiene

##### Phase 2 — Gap audit
- **`docs/RIS-integration/UI_UX_REDESIGN_GAP_AUDIT.md`** (untracked/new) — gap register: **78 IMPLEMENTED, 4 INHERITED, 7 DEFERRED, 30 PARTIAL, 21 GAP**; 5 gap patterns (P1–P5); zero new Permission enum values needed.

##### Phase 3 — T0 keystone features (committed)
- `188dc3b` per-user preference documents (migration 102) — `backend/migrations/versions/102_user_preferences.py`, `frontend/src/api/preferences.ts`
- `909fd9e` configurable widget framework core (§3)
- `f821ed5` persona widget sets on the §3 registry
- `e344846` immersive reader mode + §5.2 keyboard map — `frontend/src/radiologist/useReaderShortcuts.ts`
- `7cf6727` kanban view + drag-and-drop (§6) — `frontend/src/worklist/TrackingKanban.tsx`
- `404a584` `/schedule` landing + §7.2 sidebar role accents

##### Phase 4 — Tier 1 (P1) orphan wiring (7 committed)
`33f6942` FD-04 check-in · `9955643` QA-02 reject breakdown · `45bd1ae` S-10 prior-auth warning · `9522452` fix prior-auth read · `43c4280` B-02 claim submit · `9790a99` B-03 responsibility · `625728c` S-13 no-show · `f498ed1` S-05 template save/apply

##### Phase 5 — Tier 2 (P4) clinical completions (5 committed)
- `be6025a` **T-14** server-enforced pregnancy acknowledgment gate before acquisition (ionizing modalities CT/CR/DX/XR/MG/NM)
- `55fa41b` **T-04** red badge for documented prior contrast reactions
- `744d845` **T-03** queue-wait ETA on next-patient banner
- `dc4f92f` **T-06** clinical-indication filter on protocol registry
- `b112cd5` **T-07** simulated deterministic quality score on QA-queue series

##### Phase 6 — Tier 2 (P4) scheduling + portal completions (7 committed)
- `42aa933` **S-02** conflict UX — BookingFormModal stays open on 409 + alt-slot suggestions; CalendarGrid red overlap highlights + hover tooltips (`schedule.css` `.cell-conflict`)
- `ec91bc1` **S-03** week/month calendar views — Segmented Day/Week/Month toggle, `WeekMonthView` component, range API reuse (`listAppointmentsDateRange`), prev/next shifts by view unit
- `4a9048b` **S-09** order-to-schedule link — Schedule row action in coordinator/Orders → `/schedule?order=<id>`, BookingFormModal auto-loads + pre-fills patient/procedure/prior-auth
- `011cf63` **S-11** calendar filters — Resource type (Rooms/Modalities/Technologists) + Modality Selects drive `listRisResources` server-side; modality options from an unfiltered full-resource fetch
- `0fd2cff` **P-04** ReportList columns — Body Part (`reports.body_part` added to `list_final_reports` SQL) + Signed By (`signed_by_name`) on the portal Results table; `PortalReport` type extended
- `7a49515` **P-02** check-in badge — `checked_in_at` plumbed from `ris_appointments` into the portal appointments payload; ARRIVED badge shows check-in time on hover
- `3a710f1` **R-15** Sign & Next toast — "Report signed ✓ — Next: <patient>" named from the reading queue; queue-complete fallback; tests now wrap console in antd `App` provider so `App.useApp()` toasts render
- `958f112` **S-14** Gantt multi-day view — 4th Segmented option (Day/Week/Month/Gantt); resource rows × Mon–Sun columns with time-positioned appointment bars (07:00–19:00 lane, height ∝ duration); reuses week-range fetch; click opens detail drawer (41 tests in ScheduleCalendar)
- `a340e22` **portal.css spec classes** — `.portal-card-header`, `.portal-card-body`, `.portal-appt-prep` (wired into PortalHome), `portal-pulse` animation on `.portal-result-new`, `.portal-followup-timeline` + `.portal-followup-status.{submitted,in-progress,completed,cancelled}` pills (FollowUpHub now uses pills instead of antd Tag)

**All Tier 2 (P4) items are now committed.**

##### Phase 7 — Tier 3 (P5) scheduling cluster (4 committed, cluster complete)
- `cfb62d4` **S-01** drag-to-rebook — HTML5 drag blocks onto free cells → `rescheduleAppointment` preserving duration; conflicts via existing warning path (3 tests)
- `3cdfcb4` **S-04** room utilization heatmap — 5th Segmented option; resource × 30-min-slot grid colored free/partial/full/closed; click opens drawer/booking (3 tests)
- `3940935` **S-06** batch booking — `POST /ris/appointments/batch` books per-item, returns per-item results (partial success support); frontend BatchBookingModal (3 pytest + 2 vitest)
- `1476ad5` **S-08** waitlist — migration 103 `ris_waitlist`; CRUD + PATCH status endpoints; WaitlistModal with add form + Notify/Remove (4 pytest + 2 vitest)

**Scheduling cluster (S-01..S-14) is now fully implemented.**

##### Phase 8 — P5 completions + admin gaps (12 committed)
- `246cb40` **P-05** portal consent toggle
- `a6d0003` **R-13** peer-review accept/decline lifecycle
- `f4deed7` **CC-08** handoff notes (migration 104)
- `c0fc109` **CC-05** referral tracking (migration 105)
- `7eede54` **CC-06** discharge checklists (migration 106)
- `c0d42d0` **R-08** study bookmarks (migration 107)
- `831ca00` **portal.appointment_reminder emitter** — `reminder_sent_at` column on `ris_appointments` (migration 108), `Portal.emit_appointment_reminders(window_hours=24)` with consent gate + dedup, 4 tests
- `2381fe9` **QA-09 protocol registry + QA-11 corrective actions** — `ris_protocols` (version control, modality assignment, default) + `ris_corrective_actions` (status lifecycle, due date, assignee, incident linkage, overdue escalation via `notify_role`), migration 109, full CRUD endpoints, 11 tests
- `2616447` **R-12 multi-study compare** — `StudyCompare.tsx` + `StudyCompare.css` for side-by-side Cornerstone3D viewports with synced W/L; compare toggle + layout selector in viewer toolbar
- `2729984` **ADM-11 backup restore** — Restore button in Backups page with confirmation modal showing verification report + download-as-recovery
- `08f0b24` **ADM-16 OIDC test connection** — `POST /api/v2/oauth/providers/{id}/test-connection` hits discovery + JWKS; Test button on Integrations page; 4 backend tests

**Tier 3 (P5) scheduling/reading/coordinator/portal/frontdesk/kiosk/QA items committed. Admin gaps ADM-11, ADM-16 done.**

### Session 2 — (2026-08-27)
Critical-regression fix + DM-07 staff time-off (backend + frontend). Session did not hit the
OpenRouter 402 budget; work was committed incrementally.

#### What Was Done

- `2a11b83` **fix: restore full QA program + DM-07 time-off backend** — recovered old QA-01..QA-08 handlers (queue, reviews, incidents, dashboard, analytics, export) from pre-2381fe9 git history and merged with QA-09/11 Protocol/CorrectiveAction handlers, fixing critical backend boot regression (`ImportError: cannot import name 'QAQueueHandler' from 'api.qa'` in `api/routes.py`). Added DM-07 staff time-off: migration 110 `ris_staff_time_off`, repo `db/ris_staff_time_off.py`, 3 handlers (GET/POST list+create, PATCH status, GET coverage-gaps), 11 tests.
- `8579223` **feat: DM-07 time-off & coverage-gap frontend tab** — Tabs layout in StaffSchedule.tsx with "Scheduled Exams" + "Time Off & Coverage" tabs; request modal, approve/reject/cancel buttons, coverage-gap alert. 5 vitest tests.

**DM-07 (staff time-off) complete. All gap-audit work committed.**

### Session 3 — (2026-08-31 → 2026-09-02)
Ended by user request for an opencode handoff mid-feature. Priorities in this session:
reading-console browser E2E, then a NEW FEATURE request: **auto-handoff of uploaded
studies to the radiologist reading list (per tenant)** — NOT yet implemented, design is
done (see below). Also committed two features and diagnosed two real bugs.

#### Committed this session
- `cd7d708` **feat(upload): accept .zip archives of DICOM instances in /files/upload** —
  `backend/api/files.py`: `Upload._process_upload` detects PK\x03\x04 magic (or .zip name)
  → `_process_zip_upload()` fans every member through the same persistence path
  (`_persist_zip_member`): DICM magic + `_REQUIRED_DICOM_TAGS` check, hash dedup,
  tenant quota, storage copy, replica registration. Response
  `{format:'zip', stored, duplicates, failed, skipped, errors}`.
- `1686b28` **feat(reading): ergonomic dark reading-room console per docs/viewer spec** —
  `frontend/src/radiologist/ReadingConsole.tsx/.css`, `ReportPanel.tsx/.css`,
  `RichTextEditor.css`, `SeriesNavigator.css`, `frontend/index.html` (IBM Plex),
  `src/test/ReadingConsole.test.tsx`. User's pre-existing edits
  (`CornerstoneElement.tsx`, `UploadProgress.tsx`, `UploadZone.tsx`) were included in cd7d708.

#### Verified E2E (live Playwright MCP browser, `test.radiologist` / `Test@123456`)
- Login → `/reading` worklist renders; reading console `/reading/<examId>` renders:
  topbar (patient name, mono IDs, ROUTINE/DRAFT pills, autosave indicator, icon buttons,
  Sign Report), series navigator, viewport renders DICOM, Measurements/Key images panel,
  `.reading-viewport-footer` hints, bottom shortcut bar.
- **Rich-text toolbar reveals on field focus** ✅ (Findings/Impression/Recommendations
  each get a "Text formatting" toolbar: Bold/Italic/Underline/Bullet/Numbered/Clear).
- **Typing + autosave** ✅ — typed into Findings; "Last autosave" indicator updated
  (1:58:43 AM → 2:23:22 AM) (backend PATCH fired; network-verify still TODO).
- **`[` / `]` report-pane collapse** ⚠️ pressed both with viewport focused — panel stayed
  visible in snapshot + screenshot (`e2e-04-report-collapsed.png`). Needs code check
  (`frontend/src/radiologist/ReadingConsole.tsx` + `useReaderShortcuts.ts`) — could be a
  real bug or a keybinding target issue.
- **Not yet exercised:** `Space` immersive, `F1` help, `←/→` queue nav, sign flow
  (deliberately skipped — mutates report state), console "1 errors" identity.
- Scratch screenshots `e2e-0{1..4}-*.png` in repo root are UNTRACKED — delete after use.

#### Manual exam seeding done for E2E (test data, keep or clean)
Created + completed + assigned 10 exams (one per uploaded study) via API as
`test.technologist` (POST `/api/v2/exams`, POST `/api/v2/exams/{id}/complete` with
`{"dose_recorded":true,"sequences_complete":true}`), then tried assign as
`test.super_admin`. Exam IDs were in `/tmp/new-exam-ids.txt` (tmpfs — GONE after
reboot; recover via `SELECT id FROM exams WHERE accession_number LIKE 'ODR-0116%'
...` or by patient_name). Accessions map 1:1 to the 10 uploaded zip studies.

#### Bugs found (real, unfixed — candidate follow-ups)
1. **`POST /reports/reading-list/{exam_id}/assign` 500s — int8/str bind** (repro'd):
   `api/reports.py` `ExamAssignHandler.post` ~line 220 does
   `conn.fetchrow("... WHERE u.id = $1", radiologist_id)` where `radiologist_id` is the
   `AssignRadiologistRequest.radiologist_id` **string** but `users.id` is BIGINT →
   `asyncpg.exceptions.DataError: invalid input for query argument $1: '29'/'36'`.
   Fix: cast in handler (`int(radiologist_id)` when truthy) or `$1::bigint`. Note the
   frontend "Take" button posts with **no body** → empty string → falsy → assigns
   requesting user, so UI path works; only explicit-string payloads crash.
2. **Uploaded (zip) studies never reach the reading list** — root cause chain:
   - Zip upload path (`_persist_zip_member`) does NOT run
     `match_worklist_in_progress` / `_bump_study_counts` / any exam creation
     (`dcm/store.py::store_instance` does for C-STORE).
   - `studies.study_status` stays `'receiving'` (zip path never bumps counts;
     expected_instances=0 → C-STORE path would leave 'receiving' anyway).
   - The reading list (`db/reports.py::reading_list`) ONLY reads the `exams` table —
     so any ingest path that doesn't create/complete an exam row is invisible to
     radiologists. Fix = the feature below.

---

## ⏭️ ACTIVE JOB (next session): "uploaded studies auto-appear in the radiologist
## reading list of their tenant"

### User intent (verbatim)
"i want you to make uploaded studies automatically goes to the radiologist working
list in the tenant" — i.e. any study that lands in the QuantumPACS store (zip upload,
single upload, and ideally C-STORE without an MWL entry) should surface in
`/reading` (Reading Worklist) for the tenant's radiologists **without manual
exam creation**.

### Design settled in Session 3 (verified against code, ready to implement)
**Mechanism:** a `study.arrived → exams` bridge with idempotent completion, driven
per-instance at ingest time (no new worker needed — store_instance and the zip path
are the only writers).

1. **Shared helper — new module `backend/services/reading_handoff.py`** (mirrors
   `services/dcm4chee_sync.py` conventions; `log = get_logger(__name__)`):
   - `async def ensure_reading_exam(meta, tenant_slug, source) -> exam_id | None`
     called ONCE PER INSTANCE but **idempotent per (study_instance_uid)**:
     - `INSERT INTO exams (... patient_id, patient_name, patient_birth_date,
       patient_sex, accession_number, requested_procedure_desc, modality, priority,
       status='ready', tenant_id, created_by='') ... ON CONFLICT ... WHERE NOT EXISTS
       (SELECT 1 FROM exams WHERE tenant_id=$t AND accession_number=$acc AND
       accession_number <> '')` — accessions collide across patients, so guard on
       (tenant_id, accession_number, patient_id). When the study has **no accession**
       (ATIRA/SAFIYA cases), synthesize one deterministic: e.g.
       `AUTO-<first 12 of study_instance_uid>` so the idempotency key exists.
     - `requested_procedure_desc` = study description; `modality` = study modality.
     - After creating a **new** exam (only then): `notify_role(conn, 'radiologist',
       'study.arrived', 'Study arrived: <acc>', '<name> — <modality> ready for review',
       f'/reading/{exam_id}')` (use `api.notify.notify_role`; it honors
       notification_prefs) + `AuditLog.log_event('exam.auto_created', actor_id='system',
       resource_type='exam', ..., tenant=tenant_slug)`.
   - **Completion gating — the crucial semantics:** exams start `status='ready'`;
     `reading_list()` only shows `status='completed'`. Do NOT auto-complete instantly
     (partial/multi-instance uploads would list half-arrived studies). Instead, in the
     SAME helper, after ensuring the exam exists, evaluate completeness and flip
     `ready → completed` (set `completed_at=now()`) **atomically only when**:
     `studies.received_instances > 0 AND studies.study_status = 'complete'`, OR
     (fallback for expected_instances=0 zips) use a **settle window**: flip when
     `now() - studies.updated_at >= COALESCE(int(config['auto_handoff_settle_seconds']),
     60)` and no new instance arrived since. Store the settle seconds in
     `default_config` (see config key below). The per-instance call naturally retries
     the flip on each subsequent instance (last instance wins).
   - Concurrency: wrap create+complete in `async with conn.transaction()`; make the
     INSERT conditional (`INSERT ... SELECT ... WHERE NOT EXISTS`) so parallel C-STOREs
     of the same study create exactly one exam.
2. **Wire-in points (both):**
   - `dcm/store.py::store_instance` — inside the `tenant_db_scope` block, after
     `_bump_study_counts(conn, ds)`: `await ensure_reading_exam(ds, tenant_slug, 'dicom')`.
   - `api/files.py::_persist_zip_member` — after successful persist, call the same
     helper with the parsed `ds` meta (it has all needed keys via `get_meta`).
   - Skip when a worklist entry already owns the study:
     `match_worklist_in_progress` already ran for C-STORE; add guard in the helper:
     if a `worklist_entries` row with this accession exists, return None (the MWL →
     exam adoption flow owns that study; don't double-create).
3. **Config:** add `'auto_reading_handoff': 'true'` and
   `'auto_handoff_settle_seconds': '60'` to `default_config` in `backend/config.py`
   (place near `max_upload_size_mb`); helper returns early when
   `auto_reading_handoff` falsy. Run `scripts/verify_config.sh` after.
4. **Tenant safety:** helper must run inside the caller's scope — C-STORE path already
   inside `tenant_db_scope`; zip path runs under the HTTP request's tenant ContextVar
   (or main store for platform uploads). Pass `tenant_slug` explicitly for the exam's
   `tenant_id` column (use `get_tenant_slug() or tenant_slug or 'default'` — match
   `Exams.create`, which stamps `get_tenant_slug() or 'default'`).
5. **Migration NOT needed** — exams table already has all columns (verified schema).
   Alembic head is `114`; no DDL required for the core feature.

### Test plan (TDD, mirror `backend/tests/test_dcm.py` mocking style)
- New `backend/tests/test_reading_handoff.py`:
  - idempotency: two instances of same study → one exam;
  - no-accession study → synthesized `AUTO-*` accession;
  - worklist-owned accession → None (no exam);
  - completion: settle window not elapsed → stays 'ready'; elapsed or
    study_status='complete' → 'completed' + completed_at set;
  - `auto_reading_handoff=false` → None;
  - zip path test in a new/existing `test_files_zip` style file (mock conn like
    test_dcm does; assert helper called with parsed ds).
- Run: `pytest backend/tests/test_reading_handoff.py backend/tests/test_dcm.py`
  from `backend/` (or repo root as configured).

### Then verify E2E (browser, continuing Session-3 E2E)
Re-upload a small zip (e.g. `/tmp/dicom-uploads/ATIRA_FUAD_DR_AYAN.zip`) → as
`test.radiologist` open `/reading` → case appears without manual exam creation →
open console → images render (accession match via `_exam_imaging` in
`api/reports.py` ~line 633: studies.accession_number = exams.accession AND
patients.patient_id = exams.patient_id — so the synthesized/real accession in the
exam MUST equal the studies row's, and patient_id must equal the MRN; the helper
gets both from `ds`/meta directly, so they match by construction).
Also finish the leftover E2E items: autosave network check, `[`/`]` bug triage,
Space/F1/←→ shortcuts, console "1 errors" identity; then delete `e2e-0*.png`.

### Key code locations (clickable)
- Ingest write path (C-STORE): `backend/dcm/store.py:201` `store_instance`
  (calls `match_worklog`… actually `match_worklist_in_progress` :121,
  `_bump_study_counts` :163).
- Zip ingest: `backend/api/files.py:254` `_process_zip_upload`, `:343` `_persist_zip_member`.
- Reading list SQL (the ONLY source of the worklist): `backend/db/reports.py:191`
  `reading_list` — `WHERE e.status='completed' AND (r.status IS NULL OR != 'final')`.
- Imaging resolution for the console: `backend/api/reports.py:633` `_exam_imaging`
  (accession+MRN → patient studies tree), `:691` `ExamImagesHandler`.
- Exam create/complete endpoints (reference for status semantics):
  `backend/api/exams.py:223` POST /v2/exams, `:659` ExamCompleteHandler (requires
  dose_recorded+sequences_complete — the auto path bypasses the endpoint and updates
  the row directly, same as ExamComplete does via `Exams.update_status`).
- `Exams.create` stamps `tenant_id = get_tenant_slug() or 'default'`:
  `backend/db/exams.py:81-113`. `Exams.update_status`: `backend/db/exams.py:203`.
- notify fan-out honoring prefs: `backend/api/notify.py:16` `notify_role`.
- Audit: `backend/db/audit_log.py:22` `log_event`.
- Config block to extend: `backend/config.py` `default_config` (near line 122).
- Startup conventions if you add any worker: `backend/lifecycle.py:500-545`
  (daemon thread + main-loop scheduling like dcm4chee_sync) — core design needs NO
  worker; do not add one unless the settle-window approach is replaced by polling.

### Data facts for the 10 uploaded studies (from Session 3, for testing)
DB (patients/studies/files in MAIN db, tenant 'default'):
| patient db id | mrn | name | study row | accession | modality | files | series |
|---|---|---|---|---|---|---|---|
| 8021 | 0005154 | Kedar Abdi Jeli | 5330 | ODR-011655 | CT | 453 | 11 |
| 3559 | 0005156 | Abdulbasit Ahmed Hassen | 868 | ODR-011687 | CT | 745(8195?) | 11 |
| 9342 | 0005158 | Zeytuna Musa Ali | 6651 | ODR-011666 | CT | 1063 | 13 |
| 6147 | 0005159 | Belaynesh Arghunow | 3456 | ODR-011699 | CT | 1318 | 11 |
| 8474 | 0005161 | Mrs Sauda Wali Abdi | 5783 | ODR-011697 | CT | 714 | 8 |
| 5898 | 0005162 | Baby Asha Ibrahim | 3207 | ODR-011704 | CT | 249 | 8 |
| 7465 | 0005164 | Hamdi Abdi Mohammed | 4774 | ODR-011718 | CT | 556 | 11 |
| 4304 | 0005165 | Aslima Abdi Mame | 1613 | ODR-011722 | CT | 1594 | 14 |
| 37 | DR AYAN | ATIRA FUAD | 57 | (none) | DX | 1 | 1 |
| 39 | 100725 | SAFIYA^AHMED | 7374 | (none) | MR | 156(936?) | 6 |
(file counts >study sums reflect shared/zip-dedup; use the counts from
`SELECT study_id, count(*) FROM files GROUP BY study_id` at handoff time, not this table.)
`studies.study_status` for all ten is `'receiving'` — the settle-window fallback is
what completes these.

### Auth quick reference for API-driven testing (Session 3 verified)
- Login: `curl -c jar -X POST http://localhost:8080/api/login -H 'Content-Type: application/json'
  -d '{"username":"test.<role>","password":"Test@123456"}'` → HttpOnly cookies.
- Mutating calls need `-H "X-CSRF-Token: $(awk '$6=="csrf_token" {print $7}' jar)"`.
- `test.technologist` perms include EXAM_WRITE (can create/complete exams);
  `test.super_admin` has REPORT_WRITE; `test.radiologist` id = 29.
- DB: `docker exec quantumpacs-postgres-1 psql -U quantumpacs -d quantumpacs -c "SQL"`.

### Environment Notes (Session 3 deltas)
- PostgreSQL may answer on **5433** if 5432 was taken — check
  `docker port quantumpacs-postgres-1 5432` (dev is currently on 5432).
- Zip test archives from Session 3 live in `/tmp/dicom-uploads/*.zip` (tmpfs —
  regenerate from `/home/dev/Documents/OPP/openpacs/DICOM/` folders if gone).
- Cookie jars `/tmp/rc-cookies.txt` (technologist), `/tmp/sa2-cookies.txt`
  (super_admin), `/tmp/rad-cookies.txt` (radiologist id 29).
- Untracked in repo root (do not commit blindly): `SESSION_HANDOFF.md`, `docs/IHE/`,
  `docs/RIS-integration/UI_UX_REDESIGN_GAP_AUDIT.md`, `docs/viewer/`, `rag/`,
  `e2e-0{1..4}-*.png` (scratch — delete), `.playwright-mcp/` (scratch — delete).

---

## Current State / Blockers

### Uncommitted (in working tree — DO NOT lose)
- `SESSION_HANDOFF.md` — updated with Session 3 + ACTIVE JOB (this edit; commit or keep per next session's preference).
- Untracked, pre-existing (user's docs — do NOT commit blindly): `docs/IHE/`,
  `docs/RIS-integration/UI_UX_REDESIGN_GAP_AUDIT.md`, `docs/viewer/`, `rag/`.
- Scratch (safe to delete): `e2e-01-worklist.png`, `e2e-02-console-split.png`,
  `e2e-03-field-focus-toolbar.png`, `e2e-04-report-collapsed.png`, `.playwright-mcp/`.

### Resolved blockers (this session)
- **QA backend-boot regression from `2381fe9`** — `api/routes.py` imported `QA*Handler` names deleted by the QA-09/11 rewrite. Fixed in `2a11b83` by restoring the full QA handler set from git history and merging (with `api.schemas.ris_qa` aliased to avoid schema-name collisions). Verify on future module rewrites: run `.venv/bin/python -c "import api.routes"` + the module's old test suite before committing.

### Active blockers / constraints
- **antd Modal + userEvent hangs jsdom** — use `fireEvent` inside Modals; prefer Drawers.
- **StrictMode** double-fires effects in tests.
- **Alembic version-table drift** — apply additive DDL directly where needed.
- **OpenRouter 402** — not hit this session, but remains a standing budget risk on long sessions; `/compact` early or resume fresh.

---

## Next Steps (priority-ordered)

0. **ACTIVE (Session 4 target)** — implement the auto reading-handoff feature above
   (design + code locations in the ACTIVE JOB section), TDD, then browser-verify with a
   fresh zip upload and finish the leftover reading-console E2E items.
1. **Pulled-in scope** — B-08 payer contracts, B-09 fee schedule, DM-03/05/06/08, RES-04 peer percentile, Playwright visual-regression rig, k6 load harness.
2. **Deferred (user decision)** — ADM-04 impersonation, ADM-12 YAML diff editor, CC-07 med-rec, R-09 dictation, R-10 AI suggestions, live payer eligibility.
3. **Regression watch** — when a feature commit rewrites a module that registers routes/imports in `api/routes.py`, run `.venv/bin/python -c "import api.routes"` + the module's old test suite before committing. Commit `2381fe9` replaced `api/qa.py` (dropping QA-01..QA-08) but left `routes.py` importing the deleted `QA*Handler` names → backend could not boot. Lesson: restore full handler set via `git show <bad>^:<path>` and merge (aliasing colliding schema names, e.g. `api.schemas.ris_qa` vs `api.schemas.qa`).

Conventions: Conventional Commits, TDD, per-feature `backend/migrations/versions/` for schema changes, run `scripts/verify_config.sh` after config changes.

---

## Environment Notes

- **Provider/model:** OpenRouter — `stealth/ox-alpha` (primary, 1,116 responses) with `z-ai/glm-5.3-flash` (75) fallback. Expect 402 budget limits on long sessions; `/compact` early or resume fresh.
- **Services:** systemd user units — backend `quantumpacs-backend.service` :8080, frontend `quantumpacs-frontend.service` :5173; PostgreSQL `quantumpacs-postgres-1` Docker on `127.0.0.1:5432` (password in `backend/config.local.yaml`; dev DB `pa55w0rd`). Manage via `scripts/dev.sh {start|stop|restart|status|logs|logs-fe}`. ES 9 not running — search degrades gracefully.
- **Backend tests:** run `pytest` from `backend/` only. **Frontend gates:** `vitest`, `tsc --noEmit`, `prettier`, `vite build` (pre-commit).
- **Auth:** JWT via `api/tokens.py` (`create_token` / `verify_token`); seeded test logins `test.<role>` / `Test@123456`.
- **DICOM/Weasis:** `arc.config.list` must stay in `docker/dcm4chee/weasis-pacs-connector.properties` (see CLAUDE.md gotchas).
- **PWA gotcha:** if API calls fail with "NetworkError", clear SW: `rm -rf frontend/dist/` + hard refresh + unregister in DevTools.
