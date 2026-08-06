# Sprint 7 Detail — Hardening, UAT & Exit Gates (release-plan S12)

**Version:** 1.0 · **Date:** 2026-08-04 · **Source:** `requrements/PACS/RELEASE_PLAN.md` §4 Sprint S12 ("Hardening: UAT, performance, security test, DR drill") + §2 gates G1–G7; `requrements/PACS/PRD.md` §5.1 MVP exit
**Cadence:** 2-week sprint (10 working days) · **Squads:** full team, QA-heavy — 2 QA, 1 backend (fix support), 1 frontend (fix support), 1 Ops/SRE · **Format parity:** `requrements/sprint1_platform_foundation_detail.md` … `sprint6_dashboards_ops_detail.md`

> **Sprint numbering:** this is **Sprint 7** — the final MVP sprint, matching release-plan roadmap **S12**. It is deliberately a **verification and hardening sprint**: no new features are built; every deliverable lands a documented exit-gate result. Per-persona UAT scripts (S6-26) and the performance baseline (S6-25) were forward-pulled into Sprint 6 and are executed and completed here.

---

## 1. Sprint Goal

> **"The PACS MVP is declared releasable: all seven exit gates (G1–G7) pass in a production-shaped staging tenant, UAT is signed off by a radiologist, a technologist, and a PACS administrator, the full performance suite is green under load, the DR drill is documented with RTO ≤ 4 h and RPO ≤ 60 min, the security test evidence package is complete, and 99.9% availability plus P1/P2 response readiness are demonstrated."**

**Scope in:** per-persona UAT execution + sign-off + P0/P1 defect triage, full performance suite under load + fixes, security test (RLS matrix, RBAC, pen-test scope, encryption/patching evidence), final DR drill + evidence, G1–G6 re-verification, consolidated exit-gate evidence package, go-live readiness (cutover runbook, monitoring, tenant onboarding dry-run).

**Scope out:** all new feature work (v1.1+ only: advanced viewer tools, priors, teleradiology, export UI, migration tool); anything outside the G1–G7 exit-gate scope; P2/P3 security or UAT findings may be deferred with a documented backlog.

**Sprint 6 handoff (required to start):** all ten epics E-PAC-01…E-PAC-10 delivered; performance baseline (S6-25); per-persona UAT pack (S6-26); DR runbook + drill automation (S6-15/16); availability SLO wiring (S6-17); security sweep baseline (S6-24).

---

## 2. Team Capacity (10 working days)

| Role | FTE | Available dev-days | Notes |
| :--- | :-: | :-: | :--- |
| QA engineer ×2 | 2.0 | 20 | UAT execution, performance, security test, gate re-verification |
| Backend engineer ×1 | 1.0 | 10 | Fix support only (perf, security, UAT findings) |
| Frontend engineer ×1 | 1.0 | 10 | Fix support only (viewer/worklist findings) |
| Ops/SRE engineer ×1 | 1.0 | 10 | DR drill, availability evidence, cutover readiness |
| **Total** | **5.0** | **~50** | Total task estimate below: **~29 dev-days** (QA 17.0 · BE 4.5 · OPS 6.5 · FE 1.0) — ~21 days slack, absorbed per note below. *(Fix cycle S7-04 split: backend 1.0 + frontend 1.0.)* |

> **Slack absorption (not committed):** (a) UAT rework + full-suite regression reruns after every fix; (b) extended load scenarios (additional concurrent-read/ingestion-burst profiles); (c) evidence/documentation polish (gate reports, DR artifact, SOC 2 evidence pack); (d) cross-system cutover coordination with the RIS/EMR releases (shared platform). No new features enter this sprint.

---

## 3. Task Board (grouped by exit-gate area)

> Estimates in dev-days. `Owner:` QA = test, BE = backend, FE = frontend, OPS = ops/SRE. `Check:` acceptance check (maps to AC/SL/UI IDs where applicable).

### 3.1 UAT execution & sign-off — Gate G7
**Source:** PRD §2.3 (headline "done" gates); UAT pack from S6-26; PAC-AC-P01*/P02*/P04*/P19*/P20*.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S7-01 | UAT — radiologist reading path: prioritized worklist → study opens < 3 s → hanging protocol → tools → critical flag → key image | QA | 1.5 | S6-26 | PAC-AC-P01-01/02/06/07/08 pass; radiologist sign-off |
| S7-02 | UAT — technologist acquisition path: MWL auto-fill → MPPS status → C-STORE → Storage Commitment before purge prompt | QA | 1.5 | S6-26 | PAC-AC-P02-01/02/03/04 pass; technologist sign-off |
| S7-03 | UAT — PACS administrator path: modality registry, queue monitor, retention dry-run, exception worklist, audit viewer | QA | 1.5 | S6-26 | PAC-AC-P04-01/02/03/05 pass; PACS admin sign-off |
| S7-04a | UAT defect triage + fix cycle — backend share (daily triage, P0/P1 backend fixes, full-suite rerun) | BE | 1.0 | S7-01…S7-03 | 0 P0/P1 open at sprint close (G7) |
| S7-04b | UAT defect triage + fix cycle — frontend share (viewer/worklist P0/P1 fixes, full-suite rerun) | FE | 1.0 | S7-01…S7-03 | 0 P0/P1 open at sprint close (G7) |
| S7-05 | Go/no-go review: per-persona sign-off records consolidated; PRD §2.3 gate evidence | QA | 0.5 | S7-01…S7-04b | G7 sign-off package complete |

**Epic exit contribution:** G7 (UAT sign-off by radiologist, technologist, PACS administrator).

### 3.2 Performance validation — PAC-SL-10/11/16/17
**Source:** `PAC/05` PAC-SL-10/11/16/17; baseline from S6-25.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S7-06 | Full performance suite in prod-shaped staging: PAC-SL-10 (workstation < 3 s), PAC-SL-11 (first-frame < 3 s), PAC-SL-16 (QIDO < 500 ms), PAC-SL-17 (WADO metadata < 1 s) | QA | 1.5 | S6-25 | All p95 assertions green |
| S7-07 | Load test: peak concurrent radiologists, ingestion burst, MWL query storm; no degradation beyond budgets | QA | 2.0 | S7-06 | No budget breach at reference load profile |
| S7-08 | Performance defect fixes (indexing, caching, viewer tuning) | BE | 2.0 | S7-06/07 | PAC-SL-10/11/16/17 green after fixes |
| S7-09 | Performance budget sign-off + baseline recorded for SLO tracking | QA | 0.5 | S7-08 | Baseline artifact archived |

**Epic exit contribution:** G3 (study opens < 3 s p95; progressive < 3 s on multi-GB studies).

### 3.3 Security test — PAC-SL-60/61/62/63
**Source:** `PAC/05` PAC-SL-60…63; `pacs-ris-multitenancy.md` §3 (RLS); RBAC spec §6 (cross-tenant denial).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S7-10 | Security test execution: RLS isolation matrix (every clinical table, cross-facility), RBAC permission matrix, cross-tenant denial path | QA | 1.5 | S6-19/20 | PAC-SL-61: 0 cross-tenant incidents; matrix evidence |
| S7-11 | Pen-test scope: OWASP API checks, auth bypass attempts, PHI-exposure paths, IDOR on DICOMweb routes | QA | 1.5 | S7-10 | 0 critical/high findings; medium findings documented |
| S7-12 | Encryption + patching verification: TLS 1.2+, AES-256 at rest, WORM archive, CVE scan evidence, SOC 2 evidence pack | OPS | 1.0 | S6-21 | PAC-SL-62/63 evidence complete |
| S7-13 | Security finding remediation (P0/P1) + re-test; P2/P3 → documented backlog | BE | 1.5 | S7-10…S7-12 | All critical/high closed |

**Epic exit contribution:** G6 (RLS isolation verified; cross-tenant denied & logged) + security posture (PAC-SL-61/63).

### 3.4 Final DR drill & availability — PAC-SL-03/04/01/02
**Source:** `PAC/06` PAC-AC-P04-07; `PAC/05` PAC-SL-01/02/03/04; runbook from S6-15/16.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S7-14 | Full DR drill: simulated cloud-region outage → failover → edge reads continue → ingestion buffered → restore; RTO/RPO measured | OPS | 2.0 | S6-15/16 | PAC-AC-P04-07: RTO ≤ 4 h, RPO ≤ 60 min |
| S7-15 | DR drill evidence artifact + runbook sign-off (quarterly cadence established) | OPS | 0.5 | S7-14 | Documented evidence (PAC-SL-03/04) |
| S7-16 | Availability measurement: 99.9% uptime tracked over the sprint; P1 ≤ 15 min / P2 ≤ 30 min response routing live | OPS | 0.5 | S6-17/18 | PAC-SL-01/02 evidence |

**Epic exit contribution:** G3/G7 continuity + PAC-AC-P04-07 (DR drill documented).

### 3.5 Exit-gate re-verification — G1–G6
**Source:** release-plan §2 gates; `PAC/06` PAC-AC-*; `PAC/05` PAC-SL-*.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S7-17 | G1–G3 re-verify: ingestion + SC accuracy (PAC-SL-20/21), MWL/MPPS (PAC-AC-P02-01/04), study open < 3 s (PAC-SL-10/11) | QA | 1.5 | S7-06 | Gates green in staging |
| S7-18 | G4–G6 re-verify: retention/quota (PAC-AC-P04-03/04), interface > 99.9% + ≤ 5-min alert (PAC-SL-23), provisioning < 15 min + RLS + 100% audit (PAC-AC-P20-01/03) | QA | 1.5 | S7-10, S7-14 | Gates green in staging |
| S7-19 | Consolidated exit-gate evidence package: G1–G7 report with AC/SL traceability | QA | 1.0 | S7-05, S7-09, S7-13, S7-17/18 | Package complete; traceability to every gate |

**Epic exit contribution:** all seven gates G1–G7 documented.

### 3.6 Go-live readiness
**Source:** `PAC/05` PAC-SL-02/51; PRD §5.1 (99.9% availability in prod).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S7-20 | Production cutover runbook + rollback plan; rehearsed once in staging | OPS | 1.5 | S7-05 | Cutover rehearsed; rollback verified |
| S7-21 | Production monitoring/alerting baseline: uptime, P1/P2 routing, on-call roster | OPS | 1.0 | S6-18 | PAC-SL-01/02 monitoring live |
| S7-22 | Tenant onboarding dry-run: provision a production-shaped tenant; READY < 15 min | QA | 1.0 | S6-22 | PAC-SL-51 (< 15 min) asserted |

---

## 4. Sprint Milestones

| Milestone | Target | Evidence |
| :--- | :--- | :--- |
| **Day 3** | UAT starts (radiologist + technologist paths); performance suite first pass; security test scope executed | S7-01/02, S7-06, S7-10 started; daily triage running |
| **Day 5** | UAT complete with triage; perf fixes in; full DR drill run | S7-01…S7-05, S7-07/08, S7-14 closed; RTO/RPO measured |
| **Day 8** | Security remediation + re-test; DR evidence; G1–G6 re-verified | S7-10…S7-15, S7-17/18 closed; 0 critical/high |
| **Day 10 (go/no-go)** | Exit-gate package + go/no-go review; cutover rehearsal; MVP releasable | S7-19…S7-22; G1–G7 evidence; sprint review |

---

## 5. Sprint Definition of Done (acceptance checks)

| # | Check | Verifies | Method |
| :-: | :--- | :--- | :--- |
| D1 | UAT sign-off by radiologist, technologist, PACS administrator; 0 P0/P1 open | G7, PRD §2.3 | S7-01…S7-05 |
| D2 | Full performance suite green under load; baseline recorded | PAC-SL-10/11/16/17 | S7-06…S7-09 |
| D3 | Security: 0 critical/high findings; RLS/RBAC/denial matrix; encryption + patching evidence | PAC-SL-60…63 | S7-10…S7-13 |
| D4 | DR drill: RTO ≤ 4 h, RPO ≤ 60 min, evidence documented | PAC-AC-P04-07, PAC-SL-03/04 | S7-14/15 |
| D5 | G1–G6 re-verified; consolidated G1–G7 exit-gate package | release-plan §2 | S7-17…S7-19 |
| D6 | 99.9% availability measured; P1/P2 on-call ready; cutover rehearsed | PAC-SL-01/02, PRD §5.1 | S7-16, S7-20/21 |
| D7 | Engineering DoD on all fixes: `tsc --noEmit` + `vite build` clean; unit tests green | release-plan §6 | CI gate |
| D8 | No P0/P1 defects; go/no-go review passes — MVP releasable | G7 | Defect triage + S7-05 |

---

## 6. Risks & Watch Items (Sprint 7)

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| UAT finding volume exceeds fix capacity (BE/FE 6.5 dev-days total) | Daily triage P0/P1 count | Feature freeze; P0/P1 only; P2/P3 → documented v1.1 backlog |
| Performance miss under load (multi-GB progressive, QIDO p95) | PAC-SL-10/11/16/17 | Indexing/caching fixes (S7-08); budget re-baseline only with evidence |
| DR drill exposes a gap (RTO/RPO miss) | S7-14 measured times | Rehearse early (day 5); edge-cache + buffer paths proven in Sprint 6; extra rehearsal in slack |
| Security findings exceed remediation capacity | 0 critical/high target | Scope fixes to P0/P1; evidence pack for medium findings with disposition |
| Gate regression after fixes | Full-suite rerun | Every fix triggers full-suite rerun (S7-04); regression window reserved in slack |
| Go/no-go scope creep (\"one more fix\") | Gate evidence drift | Exit-gate package is the contract; changes after sign-off → v1.1 |

---

## Traceability

| Exit-gate area | Tasks |
| :--- | :--- |
| G7 — UAT & sign-off | S7-01…S7-05 (fix cycle S7-04a/S7-04b) |
| Performance (PAC-SL-10/11/16/17) | S7-06…S7-09 |
| Security test (PAC-SL-60…63) | S7-10…S7-13 |
| DR drill & availability (PAC-SL-03/04/01/02) | S7-14…S7-16 |
| G1–G6 re-verification + evidence package | S7-17…S7-19 |
| Go-live readiness (PAC-SL-02/51) | S7-20…S7-22 |
