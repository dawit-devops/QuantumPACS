# Sprint 6 Detail — Dashboards & Metering (E-PAC-09) + DR, Availability & Security (E-PAC-10)

**Version:** 1.0 · **Date:** 2026-08-04 · **Source:** `requrements/PACS/RELEASE_PLAN.md` E-PAC-09, E-PAC-10
**Cadence:** 2-week sprint (10 working days) · **Squads:** PACS-Core wind-down — 1.5 backend, 1 frontend, 1 Ops/SRE, 1 QA · **Format parity:** `requrements/sprint1_platform_foundation_detail.md` … `sprint5_admin_monitoring_detail.md`

> **Sprint numbering:** this is **Sprint 6** of the delivery sequence = release-plan roadmap **S10–S11** (PACS S10 = E-PAC-09 dashboards; S11 = E-PAC-09 invoices + E-PAC-10 DR/security). The release-plan **S12 hardening sprint follows as Sprint 7** (UAT, performance, DR drill, security test final). Much of E-PAC-09's foundation already exists from earlier sprints (S1-24 metering hooks, S1-26 invoice view, S4-03 QIDO metering, S5-05 storage dashboard) — this sprint completes and verifies it.

---

## 1. Sprint Goal

> **"Metered usage flows 100% accurately into tenant usage dashboards and invoices, department KPI dashboards (TAT, retrieval, backlog, utilization) support drill-down and export, and the platform can survive a cloud-region outage — reads continue from the edge cache, ingestion buffers with zero loss beyond RPO, a rehearsed failover meets RTO ≤ 4 h, and 99.9% availability plus security posture (RLS audit, cross-tenant denial, CVE cadence) are measured and documented."**

**Scope in:** metering completeness + accuracy audit, tenant usage dashboard, invoice generation + drill-down, KPI dashboards + department manager view, scheduled export (D); edge cache (D), ingestion buffering, failover runbook + DR drill automation, availability SLO + uptime dashboard + P1/P2 response, RLS isolation audit + cross-tenant denial test + CVE scan; perf baseline + UAT pack (forward-pulled from S12).

**Scope out (later):** release-plan S12 hardening final (Sprint 7); v1.1 items (advanced viewer, priors, teleradiology, export UI, migration tool); schema-per-tenant escape hatch (v2.0).

**Prior sprints handoff (required to start):** metering hooks → `usage_metering` (S1-24), invoice view base (S1-26), WADO bytes metered on DICOMweb (S4-05), storage dashboard (S5-05/06), duplicate-safe re-ingest (S2-10), `interface_events` + alerting (S2-23/25), audit + `cross_tenant.denied` path (S1-14, RBAC spec §6).

---

## 2. Team Capacity (10 working days)

| Role | FTE | Available dev-days | Notes |
| :--- | :-: | :-: | :--- |
| Backend engineer ×1.5 | 1.5 | 15 | Metering/aggregation APIs, invoice job, DR data paths |
| Frontend engineer ×1 | 1.0 | 10 | Usage/KPI/invoice dashboards |
| Ops/SRE engineer ×1 | 1.0 | 10 | Edge cache, buffering, runbook, SLO, CVE (new owner letter `OPS`) |
| QA | 1.0 | 10 | Metering E2E, DR drill, security sweep, perf baseline, UAT pack |
| **Total** | **4.5** | **~45** | Total task estimate below: **~33 dev-days** (BE 10.5 · FE 6.5 · OPS 8.0 · QA 8.0) — ~12 days slack, absorbed per note below |

> **Slack absorption (not committed):** (a) E-PAC-09 #5 (scheduled export, S6-10) and E-PAC-10 #1 (edge cache, S6-11/12) — both **D** — fully complete; (b) forward-pull of S12 items **already committed**: perf baseline (S6-25), UAT pack (S6-26); (c) DR drill rehearsal + metering/invoice rework time.

---

## 3. Task Board (grouped by source work item)

> Estimates in dev-days. `Owner:` BE = backend, FE = frontend, OPS = ops/SRE, QA = test. `Check:` acceptance check (maps to AC/SL/UI IDs where applicable).

### 3.1 Metering completeness & accuracy — E-PAC-09 #1
**Source:** `pacs-ris-schema.sql` §17 (`usage_metering`: meters `STUDIES_STORED`, `WADO_BYTES`, `MWL_QUERIES`, `API_CALLS`, `DICOM_TX`, `ACTIVE_USERS`); `PAC/05` PAC-SL-50; hooks from S1-24/S2-03/S4-03.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S6-01 | Metering completeness audit: every meter fires on its path (STUDIES_STORED, WADO_BYTES incl. DICOMweb from S4-05, MWL_QUERIES, API_CALLS, DICOM_TX, ACTIVE_USERS); fill gaps | BE | 1.0 | S1-24, S4-03, S4-05 | PAC-SL-50: 100% of events captured |
| S6-02 | Metering accuracy test: scripted actions → meter rows match (invoice variance audit = 0) | QA | 1.0 | S6-01 | PAC-SL-50: variance 0 in staging |

**Epic exit contribution:** E-PAC-09 #1 (metering pipeline 100% accurate — G6).

### 3.2 Tenant usage dashboard — E-PAC-09 #2
**Source:** `PAC/04` PAC-UI-34; `PAC/06` PAC-AC-P19-01; `usage_metering` aggregation.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S6-03 | Usage dashboard UI: studies stored, WADO bytes/egress, MWL queries, API calls by tenant/period; CSV export | FE | 1.5 | S6-04 | PAC-UI-34 parity; PAC-AC-P19-01: export matches metering |
| S6-04 | Usage aggregation API by tenant/period from `usage_metering` | BE | 1.0 | S6-01 | Aggregates match raw meter rows |

**Epic exit contribution:** E-PAC-09 #2 (tenant usage visibility).

### 3.3 Invoice generation & drill-down — E-PAC-09 #3
**Source:** `pacs-ris-schema.sql` §17 (`tenant_invoices`: `base_amount`, `overage_amount`, period); `PAC/04` PAC-UI-35; `PAC/06` PAC-AC-P20-02; base S1-26.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S6-05 | Invoice view polish + drill to usage detail (plan + overage lines, period, status) — base S1-26 | FE | 1.0 | S1-26 | PAC-UI-35 parity; drill-down consistent |
| S6-06 | Invoice generation job: period close → base + overage line items from metered usage | BE | 1.5 | S6-01 | PAC-AC-P20-02: line items match metered usage exactly |

**Epic exit contribution:** E-PAC-09 #3 (invoice/metering reconciliation — G6).

### 3.4 KPI dashboards — E-PAC-09 #4
**Source:** `PAC/06` PAC-AC-P05-01/P08-01; `PAC/04` PAC-UI-38; tracking view + `dicom_transactions`/`interface_events`.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S6-07 | KPI backend aggregates: retrieval time, TAT by priority, backlog, modality utilization + drill-down to studies | BE | 2.0 | S2-07 | PAC-AC-P05-01: data refreshes ≤ 5 min |
| S6-08 | KPI dashboards UI: time-series charts, drill-down to outliers | FE | 2.5 | S6-07 | PAC-AC-P05-01; PAC-UI-38 |
| S6-09 | Department manager view: TAT/utilization/backlog aggregates + export | FE | 1.5 | S6-08 | PAC-AC-P08-01: CSV matches on-screen data |

**Epic exit contribution:** E-PAC-09 #4 (KPI + manager dashboards).

### 3.5 Scheduled export — E-PAC-09 #5 (D)
**Source:** PAC-AC-P08-01 (export matches).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S6-10 | Scheduled dashboard export job: periodic CSV to configured recipients | BE | 1.0 | S6-09 | PAC-AC-P08-01: scheduled export matches on-screen data |

**Epic exit contribution:** E-PAC-09 #5 (scheduled department export).

### 3.6 Edge cache for active studies — E-PAC-10 #1 (D)
**Source:** `PAC/06` PAC-AC-P04-07 (partial); `PAC/05` PAC-SL-03/40.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S6-11 | Edge cache: recent/active studies served from edge; reads continue during cloud outage | OPS | 2.0 | S4-06 | PAC-AC-P04-07 partial: reads continue from edge (PAC-SL-03) |
| S6-12 | Edge-cache consistency: invalidation on `storage_objects` changes; quota-aware eviction | BE | 1.0 | S6-11 | No stale reads after archive change; eviction bounded by quota |

**Epic exit contribution:** E-PAC-10 #1 (edge continuity — D).

### 3.7 Ingestion buffering — E-PAC-10 #2
**Source:** `PAC/05` PAC-SL-04 (RPO ≤ 60 min); duplicate-safe re-ingest (S2-10).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S6-13 | Ingestion buffer during outage: modality sends accepted/buffered, replay on recovery | OPS | 1.5 | S2-03 | PAC-SL-04: no data loss window > RPO |
| S6-14 | Buffer replay: ordering + idempotency (re-ingest is duplicate-safe via S2-10) | BE | 1.5 | S6-13 | 0 duplicates on replay; RPO honored |

**Epic exit contribution:** E-PAC-10 #2 (buffered ingestion — RPO ≤ 60 min).

### 3.8 Failover runbook & DR drill — E-PAC-10 #3
**Source:** `PAC/06` PAC-AC-P04-07; `PAC/05` PAC-SL-03/04; PAC-WF9.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S6-15 | Failover runbook: failover trigger, DR site, edge-cache continuity, ingestion buffering | OPS | 1.5 | S6-11, S6-13 | PAC-AC-P04-07: runbook covers RTO ≤ 4 h, RPO ≤ 60 min |
| S6-16 | DR drill automation: quarterly drill procedure + documented evidence artifact | OPS | 1.0 | S6-15 | PAC-AC-P04-07: drill produces documented evidence |

**Epic exit contribution:** E-PAC-10 #3 (failover + quarterly drill).

### 3.9 Availability SLO & incident response — E-PAC-10 #4
**Source:** `PAC/05` PAC-SL-01/02.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S6-17 | Availability SLO wiring: uptime tracking, monthly 99.9% measurement, uptime dashboard | BE | 1.5 | S6-01 | PAC-SL-01: 99.9% monthly measurable |
| S6-18 | P1/P2 incident response SLAs: severity routing, on-call, response-time tracking | OPS | 1.0 | S6-17 | PAC-SL-02: P1 ≤ 15 min, P2 ≤ 30 min initial response |

**Epic exit contribution:** E-PAC-10 #4 (availability + response SLAs).

### 3.10 Security hardening — E-PAC-10 #5
**Source:** `PAC/05` PAC-SL-61/63; `pacs-ris-multitenancy.md` §3 (NOBYPASSRLS/FORCE RLS); RBAC spec §6 (cross-tenant denial).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S6-19 | RLS isolation audit: quarterly audit automation — verify `NOBYPASSRLS`/`FORCE ROW LEVEL SECURITY` on all clinical tables | QA | 1.0 | S1-07 | PAC-SL-61: quarterly RLS policy audit evidence |
| S6-20 | Cross-tenant denial path test: 0 grants → denied + `cross_tenant.denied` audit row | QA | 0.5 | RBAC §6 | PAC-AC-P20-03: denied and logged |
| S6-21 | CVE scan + patch cadence: critical ≤ 72 h; monthly scan evidence | OPS | 1.0 | — | PAC-SL-63: scan report + patch record |

**Epic exit contribution:** E-PAC-10 #5 (security posture — G6/G7).

### 3.11 Final E2E, perf baseline & UAT prep (cross-cutting, forward-pulled from S12)
**Source:** G6/G7 exit gates; PAC-SL-50/03/04/10/11/16/17/61/63.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S6-22 | Metering→invoice E2E: usage → invoice → drill-down; variance 0 | QA | 1.5 | S6-03…S6-06 | PAC-AC-P20-02, PAC-SL-50 pass |
| S6-23 | DR drill in staging: failover → reads from edge → ingestion buffered → restore; RTO/RPO measured | QA | 1.5 | S6-15/16 | PAC-AC-P04-07, PAC-SL-03/04 pass |
| S6-24 | Security sweep: RLS audit + denial path + CVE evidence collected and recorded | QA | 0.5 | S6-19…S6-21 | PAC-SL-61/63 evidence package |
| S6-25 | Performance baseline: full PAC-SL-10/11/16/17 suite under load; perf budget sign-off | QA | 1.0 | S4-06 | PAC-SL-10/11/16/17 p95 assertions |
| S6-26 | UAT pack: consolidated per-persona scripts (radiologist, technologist, PACS admin) | QA | 1.0 | S5-22 | PRD §2.3 sign-off gate ready |

---

## 4. Sprint Milestones

| Milestone | Target | Evidence |
| :--- | :--- | :--- |
| **Day 3** | Metering completeness audit done; usage aggregation API; KPI backend aggregates; DR runbook draft | S6-01, S6-04, S6-07, S6-15 started |
| **Day 5** | Usage dashboard + invoice drill-down; edge-cache read path; ingestion buffer replay | S6-03…S6-06, S6-11…S6-14 closed; PAC-SL-04 asserted |
| **Day 8** | KPI + manager dashboards; DR drill rehearsal; RLS audit + denial + CVE sweep | S6-07…S6-10, S6-16…S6-21 closed |
| **Day 10 (demo)** | Metering→invoice E2E, DR drill E2E, perf baseline, UAT pack; demo: outage → edge reads + buffered ingestion → restore | S6-22…S6-26; G6/G7 pre-checks; sprint review |

---

## 5. Sprint Definition of Done (acceptance checks)

| # | Check | Verifies | Method |
| :-: | :--- | :--- | :--- |
| D1 | Metering 100% event capture; invoice variance 0 | PAC-SL-50, PAC-AC-P20-02 | S6-02/S6-22 |
| D2 | Usage dashboard + invoice drill-down; export matches metering | PAC-UI-34/35, PAC-AC-P19-01 | S6-22 E2E |
| D3 | KPI + manager dashboards: refresh ≤ 5 min, CSV matches on-screen | PAC-AC-P05-01/P08-01 | S6-08/S6-09 tests |
| D4 | DR drill: reads from edge + buffered ingestion; RTO ≤ 4 h, RPO ≤ 60 min | PAC-AC-P04-07, PAC-SL-03/04 | S6-23 E2E |
| D5 | Availability 99.9% monthly measurable; P1 ≤ 15 min / P2 ≤ 30 min | PAC-SL-01/02 | S6-17/S6-18 |
| D6 | RLS audit + cross-tenant denial + CVE cadence evidence | PAC-SL-61/63, PAC-AC-P20-03 | S6-24 |
| D7 | Engineering DoD: `tsc --noEmit` + `vite build` clean; unit tests green; migrations reviewed | release-plan §6 | CI gate |
| D8 | No P0/P1 open defects; perf baseline + UAT pack ready for S12 hardening | release-plan §6 | Defect triage + S6-25/26 |

---

## 6. Risks & Watch Items (Sprint 6)

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| Metering drift (missed events across paths) | PAC-SL-50 variance | Completeness audit (S6-01) + variance test (S6-02); WADO bytes on DICOMweb verified |
| Invoice overage edge cases (partial periods, tier pricing) | PAC-AC-P20-02 line-item match | Reconciliation test; drill-down consistency (S6-05/06) |
| Edge-cache stale reads after archive change | S6-12 invalidation tests | Invalidation on `storage_objects` change; quota-aware eviction |
| DR drill complexity (RTO ≤ 4 h claim) | S6-23 measured RTO | Rehearsed in staging; edge continuity + buffer replay paths proven first |
| RLS audit false negatives | PAC-SL-61 | Automated quarterly audit; `FORCE ROW LEVEL SECURITY` check on every clinical table |
| Headcount wind-down (1.5 BE / 1 FE) | Velocity vs. budgets | D-items (S6-10/11/12) absorb rework; S12 hardening forward-pull committed only where QA/OPS slack exists |
| Cross-tenant denial regression | PAC-AC-P20-03 | S6-20 denial-path test in the security sweep |

---

## Traceability

| Source work item | Tasks |
| :--- | :--- |
| E-PAC-09 #1 (metering pipeline) | S6-01…S6-02 |
| E-PAC-09 #2 (tenant usage dashboard) | S6-03…S6-04 |
| E-PAC-09 #3 (invoice + drill-down) | S6-05…S6-06 |
| E-PAC-09 #4 (KPI dashboards) | S6-07…S6-09 |
| E-PAC-09 #5 (scheduled export, D) | S6-10 |
| E-PAC-10 #1 (edge cache, D) | S6-11…S6-12 |
| E-PAC-10 #2 (ingestion buffering) | S6-13…S6-14 |
| E-PAC-10 #3 (failover runbook + DR drill) | S6-15…S6-16 |
| E-PAC-10 #4 (availability SLO + response) | S6-17…S6-18 |
| E-PAC-10 #5 (security hardening) | S6-19…S6-21 |
| Cross-cutting (E2E, perf baseline, UAT prep — S12 pull) | S6-22…S6-26 |
