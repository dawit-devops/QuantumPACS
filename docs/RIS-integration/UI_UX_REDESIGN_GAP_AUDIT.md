# UI/UX Redesign Spec — Full Implementation Gap Audit (Refined)

**Date:** 2026-08-26 · **Branch:** `feature/ris-integration` · **Spec:** `docs/ui-ux-redesign-spec.md` v2.0 (2026-08-23)
**Method:** 8 parallel role-cluster audits, every feature ID verified against code (file:line evidence), classified
`IMPLEMENTED / PARTIAL / GAP / INHERITED / DEFERRED`, then refined through the platform-inheritance rule:
anything QuantumPACS already provides that integrated RIS inherits is NOT a gap — no duplicate surfaces.

**Headline:** ~100 of ~130 catalog IDs are implemented or satisfied by platform inheritance. The real gaps
concentrate into five patterns, not a long tail of scattered missing features.

---

## 1. Verdict distribution

| Status | Count | Notes |
|---|---|---|
| IMPLEMENTED | 78 | Reading suite, admin suite, kiosk, nursing, billing core, coordinator core, tech core, front desk core |
| INHERITED | 4 | T-09 critical flag, T-10 MWL view, T-12 incidents, B-04 manual posting (v2 handlers) |
| DEFERRED (documented) | 7 | FD-08/09/10 + widgets (front-desk plan), B-04 X12, S-07 transport stubs, ADM-13 channels (GAP_AUDIT §0.3) |
| PARTIAL | 30 | see register below — mostly FE completions on live endpoints |
| GAP | 21 | see register below |

## 2. The five gap patterns

### P1 — Backend shipped, frontend never wired (highest value/effort ratio)
Backend endpoints exist and work; no UI consumes them.
| Item | Endpoint (exists) | Missing UI |
|---|---|---|
| FD-04 one-click appointment check-in | `POST /ris/appointments/{id}/check-in` (`api/scheduling.py:253`) | row action on ScheduleToday |
| S-05 schedule templates | `/ris/schedule-templates*` CRUD+apply (`api/scheduling.py:301`) | save/load/apply in ResourceManager |
| S-13 no-show marking | `PUT` status transition handler (`api/scheduling.py:364`) | drawer action; rate metric needs new aggregation |
| B-02 claim submission | `/ris/billing/claims/{id}/submit` + batch (`api/billing.py:1042,1138`) | review-and-submit UI from queue/claims |
| B-03 patient responsibility | `/ris/billing/patients/{id}/responsibility` (`api/billing.py:1073`) | view page |
| QA-02 by-protocol reject analysis | `/api/qa/reject-analysis` returns `by_protocol` today | render it + drill-down |
| S-10 proactive prior-auth warning | order detail already carries `prior_auth_status` | warning panel in BookingFormModal before confirm |

### P2 — §3 Configurable Widget Dashboard (~15%): the keystone
Zero spec widget IDs exist for any persona; no registry, no role defaults, no `dashboard_layout`
persistence, no generic user-preferences endpoint. Grid CSS skeleton exists in `AdminDashboard.css`.
**Decision required:** build once as a platform layer → every persona's widget table inherits;
or formally defer widget configurability and keep static dashboards.
Blocked backend piece: user preferences storage (`GET/PUT /users/me/preferences`, migration).

### P3 — Cross-cutting systems partial
| System | State | Remaining |
|---|---|---|
| §5 Immersive reader | ~20% (`[`/`]` toggle only) | dark override, 48px sidebar strip, Ctrl+S/Ctrl+Enter/Ctrl+Shift+S, ←/→ queue nav, F1 help binding, Space toggle, >1920px auto-enter, status bar — pure FE in ReadingConsole |
| §6 Tracking kanban | ~35% (click-to-transition done, table default) | kanban column view, @dnd-kit drag (dep absent) + confirm dialog, role column configs, view toggle — FE only |
| §7 Theme | ~70% | token values diverge from spec (shipped cyan/slate 3-layer system arguably superior → recommend inherit-not-retint); role accent borders absent (`data-role` attr + 7 CSS rules) |
| §4 Navigation | ~85% | `/schedule` landing step missing; scheduler/qa_manager slugs unmapped; DM hybrid sidebar deliberately deviates (documented) |

### P4 — Small clinical/UX completions (FE-mostly)
T-03 next-patient ETA · T-04 contrast-reaction red badge · T-06 protocol indication filter · T-07 quality-score display ·
**T-14 pregnancy acknowledgment not enforced server-side before proceed** · S-02 conflict highlight/tooltip/alt-slot ·
S-03 week/month views (range API shipped, helper written, zero callers) · S-09 per-order Schedule entry point ·
S-11 calendar resource filters · P-04 report-list columns · P-02 check-in badge · portal.css spec classes

### P5 — Full-stack new builds
| Cluster | Items | Pattern to follow |
|---|---|---|
| Scheduling | S-01 drag-to-book, S-04 room heatmap, S-06 batch booking (+BE), S-08 waitlist (+BE), S-14 Gantt | scheduling engine + CalendarGrid |
| Reading | R-08 bookmarks/collections (+BE), R-12 multi-study compare, R-13 peer-review accept/reject (+BE-lite) | care_plans pair pattern |
| Coordinator | CC-05 referrals, CC-06 discharge checklists, CC-08 handoff notes (all +BE) | care_plans/communications donors |
| Portal | `consent_appointments` second toggle, `portal.appointment_reminder` emitter trigger | existing consent predicate + notify_patient_scoped |
| Front desk/kiosk | FD-01 demographics field extension (+schema), K-04 copay-from-eligibility + receipt render | registration/check-in flows |
| QA substance | QA-09 protocol versioning (+migration), QA-11 due dates + escalation sweep (+migration) | lifecycle worker pattern |
| Admin | ADM-04 impersonation (audit-logged), ADM-11 restore action, ADM-12 YAML diff view, ADM-16 OIDC test conn, DM-02 3-stage TAT, DM-04 maintenance overlay, DM-07 shifts/time-off | admin handlers exist to extend |

### Recommended formal deferrals (ratify → move to §0.3-style list)
External-dependency or low-roster-value: **R-09 dictation hooks** (Nuance/M*Modal procurement),
**R-10 AI suggestions** (needs CAD source), **CC-07 med-rec + CC-09 tabs** (needs FHIR MedicationRequest read),
**DM-03 forecast / DM-05 satisfaction / DM-06 budget / DM-08 staffing optimizer** (analytics roadmap),
**B-08 payer contracts / B-09 fee schedule** (P2, clearinghouse-adjacent),
live payer eligibility (FD-02 live half), RES-04 peer percentile (privacy design decision pending).
§8 tooling: **k6 load harness** (k6 not installed) and **visual-regression rig** need infra decisions.

## 3. Permission & grant mapping (step 4)

**No new Permission enum values are required.** Every implementable item above fits the existing catalog
(SCHEDULE_READ/WRITE, BILLING_READ/WRITE, EXAM_*, REPORT_*, PEER_REVIEW_*, QA_*, PROTOCOL_MANAGE,
ORDER_READ/WRITE, PORTAL_READ, NURSING_*, WORKLIST_*, SYSTEM_ADMIN). Widget persistence is self-service
(own preferences). Bookmarks are user-scoped. Landings are permission-driven.

Items that DO need human sign-off (RBAC/identity/security decisions):
1. Role slugs: add `scheduler` + `qa_manager` built-in roles (spec-literal) vs permission-mapped landings (recommended — platform-inherited, zero matrix churn).
2. Tenant-admin impersonation (ADM-04): sensitive session-swap capability even under SYSTEM_ADMIN — build-with-audit vs defer.
3. RES-04 anonymized peer comparison anonymity rule.
4. New dependency `@dnd-kit/core` + `@dnd-kit/sorted` for §6.

## 4. Test strategy (per spec §8)
Per feature cycle: vitest RED→GREEN (+ axe scan on touched pages via `src/test/axe.ts`) for FE;
pytest RED→GREEN for BE (real-DB fixtures for charge/sign/checkin chains per GAP_AUDIT ground rules);
Playwright E2E extension for touched critical flows (E1–E10 mapping, 26 specs exist, config has retries:1);
full gates per commit: prettier/tsc/vitest-full/build + ruff/pytest-full. k6 + visual regression deferred pending tooling ratification.
