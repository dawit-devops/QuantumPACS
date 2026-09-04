# UI/UX Redesign TDD Plan — §2.4 Radiologist & §2.5 Resident

Round 3 of the per-role implementation review of `docs/ui-ux-redesign-spec.md`
(follows Front Desk §2.1 and Technologist §2.3 rounds on `feature/ris-integration`).

## Audit method

Three parallel read-only audits (frontend / backend / platform-inheritance)
mapped every feature row against the codebase, then gaps were refined through
the platform-inheritance rule: anything QuantumPACS v2 already ships is
INHERITed — never duplicated — because this branch merges into v3-dev as one
platform.

## Verdict summary (~75% INHERIT — the entire P0 spine is built)

### §2.4 Radiologist

| # | Feature | Verdict | Evidence |
|---|---------|---------|----------|
| R-01 | Priority reading queue | INHERIT minus **unread toggle** | sort STAT→urgent→routine FIFO + critical tiering `db/reports.py:272-284`; filters/pagination `reports.py:112-182`; **no `unread` param anywhere** |
| R-02 | Reading console | INHERIT-FULL | `ReadingConsole.tsx` ResizableSplit :717, `[`/`]` collapse :405-422, Cornerstone reuse |
| R-03 | Templates | INHERIT-FULL | GET/POST `/reports/templates` seeded `reports.py:672-697`; versioned publish/rollback :874-929; admin TemplateManager page |
| R-04 | Autosave 3s | INHERIT-FULL | `AUTOSAVE_MS=3000` dirty-guarded loop `ReadingConsole.tsx:53-263`; PUT lock guards `reports.py:324-336`; saved-at indicator :631 |
| R-05 | Sign/Submit/Return | INHERIT-FULL | sign `reports.py:363-489` (+ORU distribution), submit :492-544, return-with-feedback :547-600; console wiring :301-401 |
| R-06 | Versions & diff | **PARTIAL → G-02** | history+v1/v2 diff endpoint EXISTS (`GET /reports/{report_id}/versions?v1=&v2=`, `reports.py:700-721`, `db/ris_report_versions.py:47-74`); missing restore action + console Versions panel |
| R-07 | Prior report quick-view | **GAP → G-03** | no bare `/reports` list route (falls into `/reports/{exam_id}`); `_exam_imaging` filters priors out (`reports.py:603-647`) |
| R-08 | Bookmarks/collections | DEFER (P2 greenfield) | zero hits repo-wide; pattern ready: `reading_presets` per-user table |
| R-09 | Dictation hooks | DEFER (P2) | zero hits; ws.ts client reusable when a dictation service arrives |
| R-10 | AI suggestions | DEFER (P2) | zero hits |
| R-11 | Teaching file submission | **NEW-WORK → G-08** (P1) | zero backend/frontend; ResidentHome renders Empty placeholder |
| R-12 | Multi-study comparison | PARTIAL → DEFER | layouts 1x2/2x2 + companion grid W/L mirror exist (`presets.ts:53-57`, `CompanionViewportGrid.tsx`); second-study loading is viewer-heavy → separate round |
| R-13 | Peer review inbox | INHERIT-FULL | full flow `/api/peer-reviews*` `reports.py:724-871` (spec's singular path is naming variance); accept/reject verb = minor polish |
| R-14 | Critical results workflow | INHERIT-FULL | flag→ack→15-min SLA escalation engine real (`escalation.py:14-79`, lifecycle thread); countdown viz = polish |
| R-15 | Sign & next | INHERIT-FULL | `signReport(next)` preserves queue filters `ReadingConsole.tsx:301-346`; tested |
| R-16 | Distribution confirmation | **PARTIAL → G-04** | delivery rows queryable via `GET /notifications/delivery-status?report_id=` (`notifications.py:255-271`); post-sign confirmation panel missing |
| R-17 | Reading statistics | **GAP → G-05** | only Prometheus TAT histogram at sign (`reports.py:388-400`); no personal-stats route |

### §2.5 Resident

| # | Feature | Verdict | Evidence |
|---|---------|---------|----------|
| RES-01 | Resident Home | INHERIT-FULL | `ResidentHome.tsx` counts + claimed_today consumption |
| RES-02 | Supervised queue | INHERIT-FULL minus claim nuance | lifecycle enforced; **`ExamAssignHandler` refuses assignee whose role slug ≠ `radiologist` (`reports.py:205-218`) — residents cannot explicitly Take** → G-06 (code fix, not grant) |
| RES-03 | Teaching Library | **NEW-WORK → G-08** (P1, shared with R-11) | placeholder only |
| RES-04 | My Progress | **PARTIAL → G-05** | no dedicated page/route/sidebar item; needs stats endpoint |
| RES-05 | Co-sign/return | INHERIT-FULL | submit/return endpoints + permission split deliberate (`permissions.py:282-292`) |
| RES-06 | Returned notification | INHERIT-FULL | `notify_user 'report.returned'` with feedback + deep link `reports.py:591-598`; bell + poll fallback; WS-push-on-notify = P2 enhancement |
| RES-07 | Revision filter | INHERIT-FULL | virtual `status=returned` → draft+feedback `db/reports.py:213-220` |
| RES-08 | Claimed today | INHERIT-FULL | drafts-started-today computed server-side `reports.py:165-181`; regression-tested |

### Cross-cutting

- **Configurable dashboard-widget layer**: NO widget system exists for any
  role (hard-coded analogues: KpiStrip, ResidentHome cards). This is a
  platform-level architecture concern spanning all 12 personas — deferred to
  its own initiative/ADR rather than built per-role here.
- **Latent bug found**: `reports.py:483` f-string references undefined
  `report_id` fallback inside the portal-notify try block — NameError silently
  swallows `portal.report_available` whenever `report['id']` is falsy → G-07.

## Permission review (directive #4)

Roles today:
- `radiologist = LEGACY_RADIOLOGIST ∪ MATRIX_A_RAD_TEL` (`permissions.py:364-384`):
  incl. `REPORT_READ/WRITE/SIGN`, `PEER_REVIEW_READ/WRITE`,
  `CRITICAL_RESULTS_WRITE`, `DICOMWEB_READ`, `REPORT_TEMPLATE_ADMIN`.
- `resident = MATRIX_B_RES` (`permissions.py:277-293, 436`): incl.
  `REPORT_READ`, `REPORT_WRITE`; deliberately **without** `REPORT_SIGN`.

**Result: NO new permission grants are required for any planned slice.**
Every new endpoint gates on codes both roles already hold:

| Planned endpoint | Gate | Radiologist | Resident |
|---|---|---|---|
| `GET /reports/reading-list?unread=1` | REPORT_READ (existing) | ✅ | ✅ |
| `POST /reports/{id}/versions/{v}/restore` | REPORT_WRITE | ✅ | ✅ |
| `GET /reports/priors?patient_id=&modality=` | REPORT_READ | ✅ | ✅ |
| `GET /reports/reading-stats` | REPORT_READ | ✅ | ✅ |
| teaching-files list/create | REPORT_READ / REPORT_WRITE | ✅ | ✅ |
| distribution panel | REPORT_READ (existing delivery-status) | ✅ | ✅ |

The G-06 resident-claim fix changes role-slug *logic* inside the existing
REPORT_WRITE-gated handler (allow `resident` slug), not the permission model.
No human grant request needed this round.

## Implementation slices (TDD, RED→GREEN, one commit each)

### S1 — R-01 unread toggle (G-01)
- Backend RED: `test_reports_api.py::TestReadingListUnread` — `unread=1` adds
  `r.id IS NULL` clause (never-opened exams); combined w/ status filters.
- db/reports.py `reading_list(..., unread=False)` appends
  `(r.id IS NULL)` WHERE fragment.
- FE RED: ReadingWorklist.test.tsx — "Unread only" checkbox passes
  `unread: "1"` in query; unchecking drops it.

### S2 — R-06 versions panel + restore (G-02)
- Backend RED: `TestReportVersionRestore` — POST
  `/reports/{exam_id}/versions/{version}/restore` (REPORT_WRITE; 409 when
  status submitted/final; restores findings/impression/recommendations,
  writes new snapshot version via add_version, audit `report.version_restored`).
- FE RED: ReadingConsole/ReportPanel tests — "Versions" button opens panel
  listing history (vN, editor, time, changed flags); select two → diff view;
  Restore button on non-latest versions (draft only).

### S3 — R-07 prior reports quick-view (G-03)
- Backend RED: `TestPriorReports` — GET `/reports/priors?patient_id=&modality=&exclude_exam_id=`
  returns prior final/preliminary reports (id, exam_id/accession, modality,
  signed_by_name/at or updated_at, impression excerpt ≤200 chars), newest
  first, limit 20. Route registered BEFORE `/reports/{exam_id}`.
- FE RED: ReadingConsole test — collapsible "Prior Reports" panel lists rows;
  click loads that report read-only into the panel area (fetch
  `/reports/{exam_id}` reuse).

### S4 — R-16 distribution confirmation (G-04)
- FE RED: after successful sign, confirmation panel/toast-detail fetches
  `notifications/delivery-status?report_id=` and renders
  "Distributed to N recipient(s)" with per-recipient SENT/FAILED tags +
  delivered_at; FAILED rows show retry hint.
- No backend change (endpoint exists).

### S5 — R-17 + RES-04 reading-stats (G-05)
- Backend RED: `TestReadingStats` — GET `/reports/reading-stats?days=14&role=…`
  returns `{signed_today, avg_tat_seconds(stat/routine), stat_compliance_pct,
  trend:[{date,count,avg_tat}], feedback_received}` scoped `signed_by=me`;
  resident variant identical shape (feedback_received from review_feedback on
  their reports). Route before `/reports/{exam_id}` catch-all.
- FE RED: (a) ReadingWorklist header strip "Signed today N · Avg TAT Xm · STAT
  compliance Y%" (REPORT_READ); (b) Resident "My Progress" page
  (`/reading/progress`, sidebar item role-gated resident) rendering the same
  payload as Statistic cards + simple trend list.

### S6 — RES-02 resident explicit claim (G-06)
- Backend RED: assign endpoint accepts target user whose role slug is
  `resident` (self-assign only stays enforced elsewhere); existing
  radiologist behavior unchanged; regression suite green.
- FE: none needed (Take button already gated REPORT_WRITE which residents hold).

### S7 — portal-notify NameError fix (G-07)
- Backend RED: sign flow with falsy `report['id']` still delivers
  `portal.report_available` notification (patch notify spy) — fixes undefined
  `report_id` fallback in `reports.py:483`.

### S8 — R-11 + RES-03 teaching files (full stack)
- Migration 093: `teaching_files` (id, exam_id, patient_mrn, title, modality,
  body_part, diagnosis, difficulty CHECK easy/medium/hard, teaching_points
  JSONB, annotations JSONB, findings_text, submitted_by, tenant_id,
  created_at).
- Backend RED: `TestTeachingFiles` — POST `/api/teaching-files`
  (REPORT_WRITE; from final/preliminary report context; audit
  `teaching.submitted`), GET list w/ modality/body_part/diagnosis/difficulty
  filters + pagination (REPORT_READ), GET detail.
- FE RED: Teaching Library page (`/teaching`, sidebar under Reading, visible
  radiologist+resident) browse/filter grid + detail drawer; "Submit to
  Teaching File" action in ReadingConsole for signed reports.

## Test strategy

Per spec §8: pytest async integration tests per slice (backend), Vitest +
RTL component tests (frontend), tsc + ruff gates, full suites before every
commit. E2E Playwright critical paths, axe-core, k6 load, and visual
regression remain deferred per the established round convention.

## Deferred items (recorded for backlog)

1. Configurable dashboard-widget framework (platform ADR).
2. R-12 second-study comparison loading (viewer-heavy).
3. R-08 bookmarks/collections sharing, R-09 dictation hooks, R-10 AI
   suggestions (P2 greenfield).
4. Polish: peer-review accept/reject verb, escalation countdown viz,
   WS-push-on-notify for instant bell refresh, template-admin gating
   (REPORT_TEMPLATE_ADMIN enforcement).
