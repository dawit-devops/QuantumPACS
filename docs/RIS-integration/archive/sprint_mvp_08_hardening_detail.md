# Sprint MVP-08 Detail — Hardening, UAT & MVP Exit Gates (S12)

**Version:** 1.0 · **Date:** 2026-08-18 · **Source:** `ris-integration-spec.md` §9.1; `RELEASE_PLAN.md` §4 (S12); `06_acceptance_criteria.md` RIS-AC-*; `05_metrics_and_slas.md` RIS-SL-*
**Cadence:** one 2-week sprint (S12) · **Squads:** RIS-MVP — two backend, two frontend, part-time integration engineer, QA

---

## 1. Sprint Goal

> **"Every MVP exit gate G1–G7 passes; the full order-to-report-to-bill journey is verified end-to-end; performance SLAs are met under load; security and RLS are regression-tested; and the MVP is declared releasable with per-persona UAT sign-off."**

**Scope in:** Full regression suite, performance testing (sub-second MWL, booking, tracking), security test (RLS, RBAC, IDOR), DR drill, per-persona UAT (radiologist, technologist, scheduler, front desk, billing coder, RIS admin), MVP exit gate G1–G7 verification, evidence package, go/no-go.

**Scope out:** v1.1 features (prior-auth, reminders, denial rework, IDN grants, FHIR read).

---

## 2. Team Capacity (one 10-day sprint)

| Role | FTE | Available dev-days | Notes |
| :--- | :-: | :-: | :--- |
| Backend engineer ×2 | 2.0 | 20 | Bug fixes, perf tuning, regression support |
| Frontend engineer ×2 | 2.0 | 20 | Bug fixes, UAT fixes, accessibility audit |
| Integration engineer | 0.5 | 5 | DICOM conformance regression, HL7 regression |
| QA | 1.0 | 10 | Full regression, performance, security, UAT, evidence package |
| **Total** | **5.5** | **~55** | Total task estimate below: **~30 dev-days** (BE 6.0 · FE 4.0 · INT 3.0 · QA 12.0 · OPS 5.0) — ~25 days slack for bug fixes |

---

## 3. Task Board

### 3.1 Performance Testing
**Source:** `05_metrics_and_slas.md` RIS-SL-10–15/20–24.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S8-01 | MWL query perf: 50 concurrent C-FIND queries → p95 < 1s (RIS-SL-10) | QA | 1.5 | All MWL code | PAC-SL-10 |
| S8-02 | Booking perf: 50 concurrent bookings → p95 < 1.5s (RIS-SL-11) | QA | 1.0 | All scheduling code | RIS-SL-11 |
| S8-03 | Tracking board perf: 500 exams, 50 concurrent status updates → board updates < 30s (RIS-SL-15) | QA | 1.0 | All tracking code | RIS-SL-15 |
| S8-04 | Worklist load perf: 1000 reading list entries, filtered → p95 < 1s (RIS-SL-13) | QA | 1.0 | All reporting code | RIS-SL-13 |
| S8-05 | HL7 message throughput: 100 messages/min → all processed, 0 failures, latency < 5s | QA | 1.0 | All interface code | RIS-SL-23 |

### 3.2 Security & RLS Regression
**Source:** `05_metrics_and_slas.md` RIS-SL-60/61.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S8-06 | Full RLS regression: test every clinical table (orders, appointments, worklist, exams, reports, charges, critical_results, hl7_messages) — cross-facility denied, home-facility reads | QA | 2.0 | All tables | PAC-SL-61 |
| S8-07 | RBAC regression: test every permission against every endpoint — 403 without permission, 200 with | QA | 1.5 | All permissions | RBAC matrix enforced |
| S8-08 | IDOR test: attempt to access another facility's order/appointment/report/charge via direct ID manipulation — denied | QA | 1.0 | All APIs | 0 IDOR vulnerabilities |
| S8-09 | Audit completeness: verify every write event across all RIS tables is audit-logged; no silent writes | QA | 1.0 | All audit triggers | RIS-SL-60 |

### 3.3 Bug Fixes & Regression
**Source:** `RELEASE_PLAN.md` §6.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S8-10 | Bug fix sprint: fix all P0/P1 defects found during S1–S11 testing | BE+FE | 4.0 | — | 0 P0/P1 open at sprint close |
| S8-11 | Full regression suite: run all existing PACS tests + all new RIS tests; verify no regressions | QA | 2.0 | S8-10 | All tests green |

### 3.4 Per-Persona UAT
**Source:** `RELEASE_PLAN.md` §4 (S12); `06_acceptance_criteria.md`.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S8-12 | UAT script: Radiologist — open reading list → priority sort → open study → select template → dictate report → autosave → sign → critical flag → ack | QA | 1.0 | S8-11 | RIS-AC-P01-01…06 |
| S8-13 | UAT script: Technologist — query MWL → verify patient → perform exam → MPPS N-CREATE → N-SET → tracking board updates | QA | 1.0 | S8-11 | RIS-AC-P02-01/02 |
| S8-14 | UAT script: Scheduler — book appointment → conflict detected → override → reschedule → cancel → day view | QA | 1.0 | S8-11 | RIS-AC-P03-01/05 |
| S8-15 | UAT script: Front Desk — register patient → MPI dedup → insurance → check-in → tracking board shows Arrived | QA | 1.0 | S8-11 | RIS-AC-P04-01/03 |
| S8-16 | UAT script: Billing Coder — billing queue → CPT suggestion → confirm → charge drop → unbilled aging → $0 | QA | 1.0 | S8-11 | RIS-AC-P05-01/03 |
| S8-17 | UAT script: RIS Admin — interface health dashboard → exception queue → retry → user/role management → audit viewer | QA | 1.0 | S8-11 | RIS-AC-P06-01/02 |

### 3.5 MVP Exit Gates & Evidence Package
**Source:** `RELEASE_PLAN.md` §2 (G1–G7).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S8-18 | G1 verify: MWL ≥ 98% auto-fill from modality test set | QA | 0.5 | S8-01 | G1 green |
| S8-19 | G2 verify: 0 scheduling conflicts (EXCLUDE constraint + E2E) | QA | 0.5 | S8-02 | G2 green |
| S8-20 | G3 verify: MPPS → tracking < 5s (latency measurement) | QA | 0.5 | S8-03 | G3 green |
| S8-21 | G4 verify: charge capture ≥ 98% (daily reconciliation) | QA | 0.5 | S8-16 | G4 green |
| S8-22 | G5 verify: interface delivery > 99.9% (message count + exception queue) | QA | 0.5 | S8-05 | G5 green |
| S8-23 | G6 verify: tenant provisioning < 15 min (automated test) | QA | 0.5 | S1-16 | G6 green |
| S8-24 | G7 verify: 0 P0/P1 open defects (defect triage) | QA | 0.5 | S8-10 | G7 green |
| S8-25 | MVP evidence package: G1–G7 report with AC/SL traceability + audit completeness (RIS-SL-60/61) + performance results + security results + go/no-go | QA | 1.5 | S8-18…24 | Package complete; MVP releasable |
| S8-26 | Production cutover runbook + rollback; rehearsed once in staging | OPS | 1.0 | S8-25 | Cutover rehearsed |
| S8-27 | MVP go/no-go review: all gates green + UAT sign-off + evidence package | QA | 0.5 | S8-25/26 | GO / NO-GO recorded |

### 3.6 Cross-cutting: DR & Accessibility

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S8-28 | DR drill: database backup → restore → verify data integrity → service resumes | OPS | 1.5 | — | RTO ≤ 4h, RPO ≤ 60min |
| S8-29 | Accessibility audit: WCAG 2.1 AA on all new RIS pages (tracking board, scheduling, reporting, billing, registration) | QA | 1.5 | All UI | WCAG 2.1 AA pass |

---

## 4. Sprint Milestones

| Milestone | Target | Evidence |
| :--- | :--- | :--- |
| **Day 3** | Performance tests started; RLS/RBAC regression started; bug fixes prioritized | S8-01/06/10 started |
| **Day 5** | Performance tests green; RLS/RBAC/IDOR green; bug fixes in progress | S8-01…05/06…09 closed; S8-10 in progress |
| **Day 8** | Bug fixes complete; full regression green; UAT scripts ready | S8-10/11 closed; S8-12…17 ready |
| **Day 10 (go/no-go)** | UAT sign-off (6 personas); G1–G7 verified; evidence package; go/no-go | S8-12…27; MVP go/no-go; sprint review |

---

## 5. Sprint Definition of Done

| # | Check | Verifies | Method |
| :-: | :--- | :--- | :--- |
| D1 | Performance SLAs met: MWL < 1s, booking < 1.5s, tracking < 30s, worklist < 1s | RIS-SL-10/11/13/15 | S8-01…04 |
| D2 | RLS regression: 0 cross-facility PHI incidents; all tables isolated | PAC-SL-61 | S8-06 |
| D3 | RBAC regression: all permissions enforced; 0 over-permissioned paths | RBAC matrix | S8-07 |
| D4 | Audit completeness: 100% write events logged | RIS-SL-60 | S8-09 |
| D5 | UAT sign-off: 6 personas (radiologist, technologist, scheduler, front desk, billing coder, RIS admin) | PRD §2.3 | S8-12…17 |
| D6 | G1–G7 all green; MVP evidence package complete | release-plan §2 | S8-18…25 |
| D7 | DR drill: RTO ≤ 4h, RPO ≤ 60min | PAC-SL-03/04 | S8-28 |
| D8 | WCAG 2.1 AA on all new RIS pages | RIS-UI-05 | S8-29 |
| D9 | Engineering DoD: `tsc --noEmit` + `vite build` clean; unit tests green | release-plan §6 | CI gate |
| D10 | No P0/P1 open defects; MVP go/no-go = GO | release-plan §6 | S8-24/27 |

---

## 6. Risks & Watch Items

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| Performance SLA misses under load | S8-01…05 | Profile early; optimize queries; add indexes; cache hot paths |
| RLS regression from accumulated changes | S8-06 | Full isolation suite; every policy change triggers regression |
| UAT finding volume exceeds fix capacity | Daily P0/P1 triage | P0/P1 only; P2/P3 → v1.1 backlog; feature freeze |
| Go/no-go scope creep ("one more feature") | Evidence drift | Evidence package is the contract; changes → v1.1 |
| DR drill reveals data loss risk | S8-28 | Backup verification; incremental backups; restore tested |

---

## Traceability

| Source work item | Tasks |
| :--- | :--- |
| Performance testing | S8-01…05 |
| Security & RLS regression | S8-06…09 |
| Bug fixes | S8-10/11 |
| Per-persona UAT | S8-12…17 |
| MVP exit gates G1–G7 | S8-18…24 |
| Evidence package + go/no-go | S8-25…27 |
| DR + accessibility | S8-28/29 |
