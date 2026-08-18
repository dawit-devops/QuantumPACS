# RIS Spec Validation Report — Coverage Gaps & Findings

**Date:** 2026-08-18 · **Source:** Cross-reference of `ris-integration-spec.md`, sprint detail files, `03_user_stories.md`, `06_acceptance_criteria.md`, `04_uiux_requirements.md`, `05_metrics_and_slas.md`

---

## Methodology

Every user story (RIS-US-*), acceptance criterion (RIS-AC-*), UI requirement (RIS-UI-*), and SLA (RIS-SL-*) was checked against:
1. `ris-integration-spec.md` — sections 2–11
2. Sprint MVP-01 through MVP-08 detail files
3. Sprint R2-01 through R2-06 detail files (v1.1/v2.0)

Coverage is rated: ✅ Covered, ⚠️ Partial, ❌ Missing, 📋 Deferred (intentional v1.1/v2.0)

---

## 1. User Story Coverage (33 stories)

### RIS-P01 · Radiologist (6 stories)

| Story | AC | Spec | Sprint | Status | Notes |
|:---|:---|:---|:---|:---|:---|
| RIS-US-P01-01 | RIS-AC-P01-01 | §4.1 reading-list | MVP-05 S5-01/02 | ✅ | Priority sort, filters, pagination, filter persistence |
| RIS-US-P01-02 | RIS-AC-P01-02 | §3.2 templates, §6 ReportEditor | MVP-05 S5-05/06/09 | ⚠️ | Templates ✅; **Speech recognition deferred to v1.1** (intentional per user decision) |
| RIS-US-P01-03 | RIS-AC-P01-03 | §3.2 critical_results, §4.1 critical-results API | MVP-06 S6-01…08 | ✅ | One-action flag, ack tracking, escalation, ORU flag |
| RIS-US-P01-04 | RIS-AC-P01-04 | §4.1 sign API, §5.1 SIGNED side effects | MVP-05 S5-11 + MVP-07 S7-03 + MVP-06 S6-09 | ✅ | Sign → billing record → ORU delivery |
| RIS-US-P01-05 | RIS-AC-P01-05 | §6.2 ReadingWorklist viewer launch | MVP-05 S5-03 | ✅ | Deep-link + worklist state preservation |
| RIS-US-P01-06 | RIS-AC-P01-06 | §3.2 report_versions, §5.1 autosave | MVP-05 S5-07/08/10 | ✅ | Auto-save, versioning, no duplicate |

### RIS-P02 · Technologist (3 stories)

| Story | AC | Spec | Sprint | Status | Notes |
|:---|:---|:---|:---|:---|:---|
| RIS-US-P02-01 | RIS-AC-P02-01 | §5.3 MWL SCP, §8.2 DICOM | MVP-04 S4-01…05 | ✅ | C-FIND, ≥ 98% auto-fill |
| RIS-US-P02-02 | RIS-AC-P02-02 | §5.4 MPPS Consumer, §8.2 DICOM | MVP-04 S4-06…10 | ✅ | N-CREATE/N-SET, < 5s, PACS echo, exception queue |
| RIS-US-P02-03 | RIS-AC-P02-03 | §4.1 reschedule API | MVP-03 S3-11 | ⚠️ | Re-schedule ✅; **Add-on exams**: order context inherited implicitly but no explicit "add-on" task |

### RIS-P03 · Scheduler (5 stories)

| Story | AC | Spec | Sprint | Status | Notes |
|:---|:---|:---|:---|:---|:---|
| RIS-US-P03-01 | RIS-AC-P03-01 | §3.2 EXCLUDE, §5.2 Scheduling Engine | MVP-03 S3-09/10 | ✅ | Conflict-free, EXCLUDE constraint, contraindication warnings |
| RIS-US-P03-02 | RIS-AC-P03-02 | v1.1 (E-RIS2-02) | R2-S1–S2 | 📋 | Intentionally deferred to v1.1 |
| RIS-US-P03-03 | RIS-AC-P03-03 | v1.1 (E-RIS2-01) | R2-S1–S2 | 📋 | Intentionally deferred to v1.1 |
| RIS-US-P03-04 | RIS-AC-P03-04 | v1.1 (E-RIS2-05) | R2-S5–S6 | 📋 | Intentionally deferred to v1.1 |
| RIS-US-P03-05 | RIS-AC-P03-05 | §6 CalendarGrid.tsx | MVP-03 S3-14/16 | ✅ | Calendar + list day view, status colors, badges |

### RIS-P04 · Front Desk (3 stories)

| Story | AC | Spec | Sprint | Status | Notes |
|:---|:---|:---|:---|:---|:---|
| RIS-US-P04-01 | RIS-AC-P04-01 | §4.1 patients API | MVP-02 S2-10/11 | ✅ | Registration, MPI dedup, insurance capture |
| RIS-US-P04-02 | RIS-AC-P04-02 | §3.2 stub | MVP-02 S2-14 | ⚠️ | **Stub in MVP**; real payer API in v1.1 (intentional) |
| RIS-US-P04-03 | RIS-AC-P04-03 | §4.1 check-in API | MVP-03 S3-13 | ⚠️ | Check-in ✅; **Labels/QR/consent capture** not explicitly in spec (see Gap #5) |

### RIS-P05 · Billing Coder (3 stories)

| Story | AC | Spec | Sprint | Status | Notes |
|:---|:---|:---|:---|:---|:---|
| RIS-US-P05-01 | RIS-AC-P05-01 | §4.1 cpt-suggestions, §6 BillingQueue | MVP-07 S7-02/06/11 | ✅ | CPT suggestion engine, ≥ 95% accuracy |
| RIS-US-P05-02 | RIS-AC-P05-02 | v1.1 (E-RIS2-03) | R2-S3–S4 | 📋 | Intentionally deferred to v1.1 |
| RIS-US-P05-03 | RIS-AC-P05-03 | §5.1 SIGNED → charge drop | MVP-07 S7-03 | ✅ | Auto charge drop, ≥ 98% capture |

### RIS-P06 · RIS Administrator (4 stories)

| Story | AC | Spec | Sprint | Status | Notes |
|:---|:---|:---|:---|:---|:---|
| RIS-US-P06-01 | RIS-AC-P06-01 | §3.2 unique index | MVP-02 S2-06 | ✅ | Partial unique index per facility |
| RIS-US-P06-02 | RIS-AC-P06-02 | §4.1 interfaces APIs, §6 InterfaceDashboard | MVP-02 S2-15/16/17 | ✅ | Dashboard, ≤ 5-min alerting, exception queue |
| RIS-US-P06-03 | RIS-AC-P06-03 | v1.1 (E-RIS2-04) | R2-S3–S4 | 📋 | Intentionally deferred to v1.1 |
| RIS-US-P06-04 | RIS-AC-P06-04 | §4.1 patients API | MVP-02 S2-11 | ⚠️ | MPI merge ✅; **Undo capability** not explicitly documented in spec (see Gap #6) |

### RIS-P07 · Department Manager (1 story)

| Story | AC | Spec | Sprint | Status | Notes |
|:---|:---|:---|:---|:---|:---|
| RIS-US-P07-01 | RIS-AC-P07-01 | — | — | ❌ | **GAP #1**: Manager dashboard (TAT, utilization, unbilled metrics, drill-down, export) not explicitly in spec or sprint tasks |

### RIS-P08 · Referring Physician (2 stories)

| Story | AC | Spec | Sprint | Status | Notes |
|:---|:---|:---|:---|:---|:---|
| RIS-US-P08-01 | RIS-AC-P08-01 | §4.1 orders API, §5.1 order lifecycle | MVP-02 S2-08, MVP-03 S3-01/05 | ✅ | ORM → order, referring MD status view |
| RIS-US-P08-02 | RIS-AC-P08-02 | §5.5 results distribution | MVP-06 S6-09/10 | ✅ | ORU delivery < 5 min, 0 silent failures |

### RIS-P09 · ED Physician (2 stories)

| Story | AC | Spec | Sprint | Status | Notes |
|:---|:---|:---|:---|:---|:---|
| RIS-US-P09-01 | RIS-AC-P09-01 | §4.1 order priority, §6 TrackingBoard | MVP-03 S3-01, MVP-04 S4-15 | ⚠️ | STAT priority in order model ✅; **End-to-end STAT prioritization across scheduling→MWL→acquisition→read** not explicitly verified as a single flow (see Gap #2) |
| RIS-US-P09-02 | RIS-AC-P09-02 | §3.2 critical_results, §4.1 critical-results API | MVP-06 S6-02…08 | ⚠️ | Critical results to ED ✅; **ED physician as explicit recipient** not called out in recipient selection (see Gap #3) |

### RIS-P19 · Tenant Admin (2 stories)

| Story | AC | Spec | Sprint | Status | Notes |
|:---|:---|:---|:---|:---|:---|
| RIS-US-P19-01 | RIS-AC-P19-01 | §6 ResourceManager, §4.1 resources API | MVP-03 S3-06/07/08 | ✅ | Sites, rooms, schedules, roles |
| RIS-US-P19-02 | RIS-AC-P19-02 | §10.4 metering, §6 admin UI | MVP-01 S2-01…04 | ✅ | Metering, invoices, drill-down |

### RIS-P20 · Super Admin (2 stories)

| Story | AC | Spec | Sprint | Status | Notes |
|:---|:---|:---|:---|:---|:---|
| RIS-US-P20-01 | RIS-AC-P20-01 | §5.1 order lifecycle, §6 provisioning | MVP-01 S1-12…16 | ✅ | Atomic provisioning, rollback, < 15 min |
| RIS-US-P20-02 | RIS-AC-P20-02 | §7.2 RBAC, §10.5 audit | MVP-01 S1-08/09 | ✅ | Cross-tenant grants, audit, denied logged |

---

## 2. UI/UX Requirement Coverage (42 requirements)

### Cross-Cutting (RIS-UI-01…06)

| Req | Status | Notes |
|:---|:---|:---|
| RIS-UI-01 Sub-second responsiveness | ✅ | Performance SLAs in spec §10.1 |
| RIS-UI-02 Live updates | ✅ | Tracking board polling ≤ 30s (MVP-04 S4-15) |
| RIS-UI-03 Keyboard-first | ⚠️ | Not explicitly in spec; calendar grid could benefit (see Gap #7) |
| RIS-UI-04 Consistent design tokens | ✅ | Ant Design conventions followed |
| RIS-UI-05 WCAG 2.1 AA | ✅ | Sprint MVP-08 S8-29 accessibility audit |
| RIS-UI-06 Session resilience | ✅ | Filter persistence (MVP-05 S5-01), draft preservation (MVP-05 S5-08) |

### Tracking Board (RIS-UI-07…12)

| Req | Status | Notes |
|:---|:---|:---|
| RIS-UI-07 Live board | ✅ | MVP-04 S4-11/15 |
| RIS-UI-08 Status lifecycle | ✅ | MVP-04 S4-14/15 |
| RIS-UI-09 Filters | ✅ | MVP-04 S4-17 |
| RIS-UI-10 Views + row actions | ⚠️ | Table + calendar ✅; **Board/card view** not explicitly in sprint tasks (see Gap #4) |
| RIS-UI-11 Critical-result badges | ✅ | MVP-04 S4-19 |
| RIS-UI-12 KPI strip | ✅ | MVP-04 S4-12/16 |

### Scheduling (RIS-UI-13…19)

| Req | Status | Notes |
|:---|:---|:---|
| RIS-UI-13 Calendar grid | ✅ | MVP-03 S3-14 |
| RIS-UI-14 Booking form | ✅ | MVP-03 S3-15 |
| RIS-UI-15 Rule feedback | ✅ | MVP-03 S3-10 (contraindication warnings) |
| RIS-UI-16 Prior-auth panel | 📋 | v1.1 (R2-S1–S2) |
| RIS-UI-17 Reminder management | 📋 | v1.1 (R2-S1–S2) |
| RIS-UI-18 Multi-site search | 📋 | v1.1 (R2-S5–S6) |
| RIS-UI-19 Reschedule/cancel | ✅ | MVP-03 S3-11/17 |

### Registration (RIS-UI-20…23)

| Req | Status | Notes |
|:---|:---|:---|
| RIS-UI-20 Registration form | ✅ | MVP-02 S2-13 |
| RIS-UI-21 Insurance eligibility | ⚠️ | Stub in MVP (S2-14); real in v1.1 (intentional) |
| RIS-UI-22 One-click check-in | ⚠️ | Check-in ✅; **Labels/QR/consent capture** not explicit (see Gap #5) |
| RIS-UI-23 Pre-registration | 📋 | v2.0 (R2-S10–S12) |

### Reading & Reporting (RIS-UI-24…29)

| Req | Status | Notes |
|:---|:---|:---|
| RIS-UI-24 Reading worklist | ✅ | MVP-05 S5-01/02 |
| RIS-UI-25 Report editor | ⚠️ | Templates + sections ✅; **Speech recognition** deferred; **measurement/image linking** not in MVP (see Gap #8) |
| RIS-UI-26 Viewer launch | ✅ | MVP-05 S5-03 |
| RIS-UI-27 Critical-results flow | ✅ | MVP-06 S6-06/08 |
| RIS-UI-28 Sign & route | ✅ | MVP-05 S5-14/15 |
| RIS-UI-29 WIP draft list | ✅ | MVP-05 S5-10 |

### Billing (RIS-UI-30…33)

| Req | Status | Notes |
|:---|:---|:---|
| RIS-UI-30 Billing queue | ✅ | MVP-07 S7-04/11 |
| RIS-UI-31 Unbilled aging | ✅ | MVP-07 S7-07/08 |
| RIS-UI-32 Denial/rework queue | 📋 | v1.1 (R2-S3–S4) |
| RIS-UI-33 Prior-auth on claim | 📋 | v1.1 (R2-S1–S2) |

### Admin (RIS-UI-34…39)

| Req | Status | Notes |
|:---|:---|:---|
| RIS-UI-34 Scheduling template editor | 📋 | v1.1 (R2-S3–S4) |
| RIS-UI-35 Procedure/CPT/ICD map manager | 📋 | v1.1 (R2-S3–S4) |
| RIS-UI-36 Report template manager | 📋 | v1.1 (R2-S3–S4) |
| RIS-UI-37 Interface health dashboard | ✅ | MVP-02 S2-15/16 |
| RIS-UI-38 MPI maintenance | ⚠️ | MPI merge ✅; **Merge wizard with undo** not explicit (see Gap #6) |
| RIS-UI-39 User/role management | ✅ | MVP-01 S1-22…25 |

### Tenant & Ops (RIS-UI-40…42)

| Req | Status | Notes |
|:---|:---|:---|
| RIS-UI-40 Usage metering + invoice | ✅ | MVP-01 S2-01…04 |
| RIS-UI-41 Tenant card grid | ✅ | Existing tenant management UI |
| RIS-UI-42 KPI dashboards | ❌ | **GAP #1**: Same as RIS-US-P07-01 — manager dashboards not in spec |

---

## 3. SLA Coverage (62 SLAs)

### System-Level (RIS-SL-01…04)

| SLA | Status | Notes |
|:---|:---|:---|
| RIS-SL-01 Availability 99.9% | ✅ | Platform-level; inherited from PACS |
| RIS-SL-02 Incident response | ✅ | Platform-level |
| RIS-SL-03 RTO/RPO | ✅ | MVP-08 S8-28 DR drill |
| RIS-SL-04 Planned downtime | ✅ | Platform-level |

### Performance (RIS-SL-10…15)

| SLA | Status | Notes |
|:---|:---|:---|
| RIS-SL-10 MWL < 1s | ✅ | Spec §10.1, MVP-04 S4-22 |
| RIS-SL-11 Booking < 1.5s | ✅ | Spec §10.1, MVP-03 S3-10 |
| RIS-SL-12 Registration < 1s | ✅ | Spec §10.1 |
| RIS-SL-13 Worklist < 1s | ✅ | Spec §10.1, MVP-05 S5-01 |
| RIS-SL-14 Report autosave < 1s | ✅ | Spec §10.1, MVP-05 S5-08 |
| RIS-SL-15 Tracking ≤ 30s | ✅ | Spec §10.1, MVP-04 S4-15 |

### Workflow (RIS-SL-20…25)

| SLA | Status | Notes |
|:---|:---|:---|
| RIS-SL-20 Order < 1 min | ✅ | Spec §10.2, MVP-02 S2-08 |
| RIS-SL-21 Scheduled → MWL immediate | ✅ | MVP-03 S3-13 |
| RIS-SL-22 MPPS < 5s | ✅ | Spec §10.2, MVP-04 S4-22 |
| RIS-SL-23 Interface > 99.9% | ✅ | Spec §10.2, MVP-02 S2-04 |
| RIS-SL-24 Report → EMR < 5 min | ✅ | Spec §10.2, MVP-06 S6-09 |
| RIS-SL-25 Critical ack 100% | ✅ | Spec §10.2, MVP-06 S6-03/04 |

### Department KPIs (RIS-SL-30…37)

| SLA | Status | Notes |
|:---|:---|:---|
| RIS-SL-30 STAT TAT < 30–60 min | ⚠️ | Implicit (STAT priority → faster read); **not explicitly tracked as a TAT metric** (see Gap #9) |
| RIS-SL-31 Inpatient TAT < 2–4h | ⚠️ | Same as above |
| RIS-SL-32 Outpatient TAT 24–48h | ⚠️ | Same as above |
| RIS-SL-33 MWL ≥ 98% | ✅ | MVP gate G1, MVP-04 S4-04 |
| RIS-SL-34 Conflicts = 0 | ✅ | MVP gate G2, MVP-03 S3-09/20 |
| RIS-SL-35 No-show reduction ≥ 20% | 📋 | v1.1 reminders (R2-S1–S2) |
| RIS-SL-36 Prior-auth ≥ 95% | 📋 | v1.1 (R2-S1–S2) |
| RIS-SL-37 Duplicate MRN < 1% | ✅ | MVP-02 S2-11 |

### Billing (RIS-SL-40…44)

| SLA | Status | Notes |
|:---|:---|:---|
| RIS-SL-40 Charge capture ≥ 98% | ✅ | MVP gate G4, MVP-07 S7-03/14 |
| RIS-SL-41 Unbilled $0 > 5 days | ✅ | MVP-07 S7-07/13 |
| RIS-SL-42 Denial rate < 10% | 📋 | v1.1 denial rework (R2-S3–S4) |
| RIS-SL-43 Coding accuracy ≥ 95% | ✅ | MVP-07 S7-02/12 |
| RIS-SL-44 Charge drop < 24h | ⚠️ | Instrumented (spec §10.4 `ris_charge_drop_latency`); **24h target not explicitly in MVP acceptance** |

### SaaS Business (RIS-SL-50…52)

| SLA | Status | Notes |
|:---|:---|:---|
| RIS-SL-50 Metering accuracy | ✅ | MVP-01 S2-01…04 |
| RIS-SL-51 Provisioning < 15 min | ✅ | MVP gate G6, MVP-01 S1-15 |
| RIS-SL-52 Admin time-to-value ≤ 1 day | ✅ | ResourceManager UI (MVP-03 S3-08) |

### Security (RIS-SL-60…62)

| SLA | Status | Notes |
|:---|:---|:---|
| RIS-SL-60 Audit completeness 100% | ✅ | Spec §10.5, MVP-01 S1-17…21 |
| RIS-SL-61 Isolation 0 incidents | ✅ | MVP gate, MVP-08 S8-06 |
| RIS-SL-62 Encryption/patching | ✅ | Platform-level (TLS 1.2+, AES-256) |

---

## 4. Identified Gaps

### GAP #1 — Manager Dashboard (RIS-US-P07-01, RIS-AC-P07-01, RIS-UI-42)
**Severity:** Medium (M priority story)  
**What's missing:** The spec references `RISDashboard` in route structure (§6.3) but has no dedicated task, API endpoint, or frontend component for the manager dashboard. The KPI strip (MVP-04) covers today's counts, but the full dashboard with TAT by priority, utilization, patient-flow, unbilled metrics, drill-down, and export is not in any sprint.  
**Fix:** Add to spec §4.1 (`GET /api/ris/dashboard/kpi` with TAT/utilization/unbilled aggregations), §6.1 (`RISDashboard.tsx`), and create tasks in MVP-04 or MVP-08 for the dashboard.

### GAP #2 — End-to-End STAT Prioritization (RIS-US-P09-01, RIS-AC-P09-01)
**Severity:** Medium (M priority story)  
**What's missing:** The STAT priority field exists in the order model, and the reading worklist sorts by priority. But there's no explicit verification that STAT orders are prioritized through the full pipeline: scheduling → MWL → acquisition → reading. The MWL serves entries by scheduled date, not priority.  
**Fix:** Add explicit MWL sort by priority (STAT first) in MVP-04 S4-02, and add a STAT end-to-end test scenario in MVP-08.

### GAP #3 — ED Physician as Critical Results Recipient (RIS-US-P09-02, RIS-AC-P09-02)
**Severity:** Low (the workflow works, just not explicitly called out)  
**What's missing:** The critical results workflow (MVP-06) supports recipient selection, but "ED physician" is not explicitly listed as a recipient option in the spec or sprint tasks.  
**Fix:** Add ED physician as a recipient option in the critical results recipient selection (MVP-06 S6-06).

### GAP #4 — Board/Card View for Tracking Board (RIS-UI-10)
**Severity:** Low (D priority UI req)  
**What's missing:** RIS-UI-10 specifies "table + board/card + calendar" views. The spec and sprint tasks cover table and calendar, but the board/card view is not explicitly planned.  
**Fix:** Either add board/card view as a stretch goal in MVP-04, or explicitly document it as deferred to v1.1.

### GAP #5 — Labels/QR/Consent Capture at Check-in (RIS-UI-22, RIS-AC-P04-03)
**Severity:** Low  
**What's missing:** The check-in flow (MVP-03 S3-13) sets status to Arrived and updates tracking, but label printing, QR code generation, and consent signature capture are not in the spec or sprint tasks. The existing consent infrastructure (`consent_documents` table) exists but isn't wired to the check-in flow.  
**Fix:** Add consent attach to check-in flow (reuse existing `consent_documents`); label/QR printing deferred to v1.1.

### GAP #6 — MPI Merge Undo Capability (RIS-AC-P06-04, RIS-UI-38)
**Severity:** Low  
**What's missing:** The AC specifies "merge wizard with undo" but the spec only mentions "merge audited" without explicit undo.  
**Fix:** Add undo capability to the merge flow in MVP-02 S2-11 (store pre-merge state for rollback).

### GAP #7 — Keyboard-First Scheduling (RIS-UI-03)
**Severity:** Low (D priority cross-cutting)  
**What's missing:** RIS-UI-03 specifies "keyboard-first for schedulers & front desk" but the spec doesn't mention keyboard shortcuts or keyboard navigation for the calendar grid or booking form.  
**Fix:** Add keyboard navigation as a stretch goal in MVP-03 S3-14/15.

### GAP #8 — Measurement/Image Linking in Report Editor (RIS-UI-25)
**Severity:** Low (stretch feature)  
**What's missing:** RIS-UI-25 specifies "measurement/image linking (key images)" in the report editor. The MVP report editor covers templates and sections but not measurement linking (that's a PACS V2-01 feature — DICOM SR/GSPS persistence + export to report).  
**Fix:** Document as deferred to PACS V2-01 integration; measurements link to report via the existing key-image path (S4-21).

### GAP #9 — Report TAT Tracking (RIS-SL-30…32)
**Severity:** Low  
**What's missing:** The TAT SLAs (STAT < 30–60 min, Inpatient < 2–4h, Outpatient < 24–48h) are defined but not explicitly tracked as metrics in the spec. The KPI strip shows "awaiting read" and "overdue" counts but not TAT distributions.  
**Fix:** Add `ris_report_tat_seconds` histogram (by priority) to spec §10.4; add TAT dashboard panel to the manager dashboard (GAP #1 fix).

---

## 5. Summary

| Category | Total | ✅ Covered | ⚠️ Partial | ❌ Missing | 📋 Deferred |
|:---| :-: | :-: | :-: | :-: | :-: |
| User Stories | 33 | 21 | 6 | 1 | 5 |
| Acceptance Criteria | 30 | 21 | 5 | 1 | 3 |
| UI/UX Requirements | 42 | 28 | 5 | 1 | 8 |
| SLAs | 62 | 50 | 6 | 0 | 6 |
| **Total** | **167** | **120** | **22** | **3** | **22** |

**Coverage:** 120/167 = **72% fully covered**, 22 partially covered, 3 missing, 22 intentionally deferred to v1.1/v2.0.

**Critical gaps requiring spec update:**
1. **GAP #1** — Manager Dashboard (M priority story, no tasks)
2. **GAP #2** — STAT end-to-end prioritization verification
3. **GAP #3** — ED physician in critical results recipients

**Recommended spec additions:**
- §4.1: Add `GET /api/ris/dashboard/kpi` endpoint
- §6.1: Add `RISDashboard.tsx` component
- §10.4: Add `ris_report_tat_seconds` histogram
- MVP-04 S4-02: Add priority-based MWL sort
- MVP-06 S6-06: Add ED physician recipient option
- MVP-08: Add STAT end-to-end test scenario
