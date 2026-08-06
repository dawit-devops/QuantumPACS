# Sprint 5 Detail — PACS Admin Console (E-PAC-07) & Interface Monitoring (E-PAC-08)

**Version:** 1.0 · **Date:** 2026-08-04 · **Source:** `requrements/PACS/RELEASE_PLAN.md` E-PAC-07, E-PAC-08
**Cadence:** 2-week sprint (10 working days) · **Squads:** PACS-Core — two frontend engineers (admin console) + one backend engineer (stats/queue/routing APIs) + shared integration engineer · **Format parity:** `requrements/sprint1_platform_foundation_detail.md` … `sprint4_dicomweb_viewer_detail.md`

> **Sprint numbering:** this is **Sprint 5** of the delivery sequence = release-plan roadmap **S8–S9** (PACS S8 = E-PAC-06 tail + E-PAC-07 start; S9 = E-PAC-07 + E-PAC-08). The admin console is a **frontend-heavy sprint** — most backend APIs already exist (S2-12 exception API, S2-23…S2-25 interface capture/health/alerting, S3-16…S3-19 retention/quota, S1-16 audit viewer) and are surfaced here.

---

## 1. Sprint Goal

> **"A PACS administrator can operate the archive from one console: register and monitor modalities, watch DICOM queues, manage storage quotas and retention with dry-run purge, reconcile exception studies, and see every interface failure alerted within 5 minutes — all audited, behind `INTERFACE_MONITOR`/`STORAGE_ADMIN`-class permissions."**

**Scope in:** modality registry UI + heartbeat status, queue monitor, storage dashboard, retention policy editor + purge dry-run, exception/orphan worklist UI + reconciliation, audit log viewer (verify + polish — base S1-16), routing rules builder + engine (D); interface health completion (modality heartbeat, DICOM queue depth), ≤ 5-min alerting completion (dedup/quieting, escalation), conformance harness formalization (D).

**Scope out (later sprints):** migration tool UI (PAC-UI-33 — v1.1), export UI (E-PAC-04 v1.1), tenant/ops dashboards (E-PAC-09 — forward-pulled only as slack), DR runbook UI (E-PAC-10), AI ingestion (v1.1).

**Prior sprints handoff (required to start):** exception/orphan API (S2-12), interface `_events` capture + health dashboard + alerting base (S2-23/24/25), retention + quota backend (S3-16…19), tiered storage + `storage_objects` (S3-09/10), audit pipeline + viewer (S1-14/16), modality registry backend (S2-01/02), conformance lab scripts (S2-27, S3-21).

---

## 2. Team Capacity (10 working days)

| Role | FTE | Available dev-days | Notes |
| :--- | :-: | :-: | :--- |
| Backend engineer ×1 | 1.0 | 10 | Stats/queue/routing APIs; alerting completion |
| Frontend engineer ×2 | 2.0 | 20 | Admin console pages (dedicated per release plan) |
| Integration engineer | 0.5 | 5 | Conformance harness + modality heartbeat validation |
| QA | 0.5 | 5 | Admin + monitoring E2E, UAT prep |
| **Total** | **4.0** | **~40** | Total task estimate below: **~29.5 dev-days** (BE 9.0 · FE 14.0 · INT 2.0 · QA 4.5) — ~10.5 days slack, absorbed per note below |

> **Slack absorption (not committed):** (a) E-PAC-07 #7 routing rules (S5-12/13, D) — in scope, absorb rework; (b) forward-pull of **E-PAC-09 #4 (KPI dashboards, PAC-AC-P05-01/P08-01, first pass)** on FE slack; (c) UAT rework time. Nothing past E-PAC-08 scope is committed.

---

## 3. Task Board (grouped by source work item)

> Estimates in dev-days. `Owner:` BE = backend, FE = frontend, INT = integration engineer, QA = test. `Check:` acceptance check (maps to AC/SL/UI IDs where applicable).

### 3.1 Modality registry UI — E-PAC-07 #1
**Source:** `PAC/04` PAC-UI-26; `pacs-ris-schema.sql` §3 (`modalities`: `station_ae_title`, `active`, `last_heartbeat_at`); backend from S2-01/02.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S5-01 | Modality registry UI: table (AE title, IP/host, tenant, make/model, status online/offline/last seen), enable/disable, edit | FE | 2.0 | S2-01 | PAC-UI-26 parity; PAC-AC-P04-01 (unregistered AE rejected still enforced) |
| S5-02 | Modality heartbeat wiring: `last_heartbeat_at` fed from interface events; online/offline derived with staleness rule | BE | 1.0 | S2-23 | Modality status accurate within the staleness window |

**Epic exit contribution:** E-PAC-07 #1 (modality registry + status).

### 3.2 Queue monitor — E-PAC-07 #2
**Source:** `PAC/04` PAC-UI-28; `PAC/06` PAC-AC-P04-02 (partial); `pacs-ris-schema.sql` §6 (`dicom_transactions`), §9 (`interface_events`).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S5-03 | Queue monitor UI: DICOM queue depth, stuck-message detection, per-interface error counts, one-click retry/drain | FE | 2.0 | S5-04 | PAC-UI-28; retry/drain actions work from the row |
| S5-04 | Queue-depth + stuck-message API: from `dicom_transactions` (ERROR/TIMEOUT/REJECTED) + `interface_events` (open, severity) | BE | 1.0 | S2-23 | Depth/stuck counts match underlying rows |

**Epic exit contribution:** E-PAC-07 #2 (queue monitor + one-click retry — PAC-AC-P04-02 partial).

### 3.3 Storage dashboard — E-PAC-07 #3
**Source:** `PAC/04` PAC-UI-29; `PAC/06` PAC-AC-P19-01; `docs/specs/tenants_design.md` (color bar green <50% / orange 50–75% / red >75%); `storage_objects`, `usage_metering`.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S5-05 | Storage dashboard UI: usage vs. quota color bar, tier breakdown, growth trend, alert-threshold config | FE | 2.0 | S5-06 | PAC-UI-29 parity; colors per `tenants_design.md` |
| S5-06 | Storage stats API: usage by tier + growth trend + quota (from `storage_objects`/`usage_metering`) | BE | 1.5 | S3-10 | PAC-AC-P19-01: export matches metering data |

**Epic exit contribution:** E-PAC-07 #3 (storage visibility — PAC-AC-P19-01).

### 3.4 Retention policy editor — E-PAC-07 #4
**Source:** `PAC/04` PAC-UI-30; `PAC/06` PAC-AC-P04-03; backend from S3-16/17 (`retention_policies`, purge dry-run).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S5-07 | Retention policy editor UI: per-document-type clocks (5–30+ yr, pediatric), legal-hold toggles with reason + audit, dry-run of what would be purged | FE | 2.0 | S3-16 | PAC-UI-30 parity |
| S5-08 | Purge dry-run API wiring: preview purge candidates; execute job only from explicit dry-run confirmation | BE | 0.5 | S3-17 | PAC-AC-P04-03: dry-run before purge; 0 accidental purges (PAC-SL-43) |

**Epic exit contribution:** E-PAC-07 #4 (retention editor — G4).

### 3.5 Exception/orphan worklist UI — E-PAC-07 #5
**Source:** `PAC/04` PAC-UI-31; `PAC/06` PAC-AC-P04-05; backend from S2-12; `studies.status='QUARANTINED'`.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S5-09 | Exception/orphan worklist UI: reason, patient/accession mismatch highlight, merge/reassign/discard actions | FE | 1.5 | S2-12 | PAC-UI-31 parity |
| S5-10 | Reconciliation backend completion: merge / assign accession / discard-with-audit (extend S2-12) | BE | 1.0 | S2-12 | PAC-AC-P04-05: 100% orphans resolved ≤ 24 h (PAC-SL-22) |

**Epic exit contribution:** E-PAC-07 #5 (exception worklist + reconciliation).

### 3.6 Audit log viewer — E-PAC-07 #6
**Source:** `PAC/04` PAC-UI-32; `docs/specs/audit-logs_design.md`; base delivered S1-16.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S5-11 | Audit log viewer verification + polish: PACS event-type chips (ingestion, retrieve, export, purge, quota), CSV export, cursor pagination confirmed | FE | 0.5 | S1-16 | PAC-UI-32 parity; PACS event types filterable |

**Epic exit contribution:** E-PAC-07 #6 (audit viewer parity — base S1-16).

### 3.7 Routing rules builder & engine — E-PAC-07 #7 (D)
**Source:** `PAC/04` PAC-UI-27; `PAC/06` PAC-AC-P04-02; **migration: new `routing_rules` table** (not in `pacs-ris-schema.sql` — add: facility, source modality/site/anatomy match, destination, precedence, active, `UNIQUE (facility_id, precedence)`).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S5-12 | Routing rules builder UI: source → destination, precedence visible, dry-run validation | FE | 2.0 | S5-13 | PAC-UI-27 parity |
| S5-13 | Routing rules migration + engine: evaluate on ingest (S2-07 path); deterministic precedence; dry-run API | BE | 2.0 | S2-07 | PAC-AC-P04-02: matches route to correct destination; precedence deterministic |

**Epic exit contribution:** E-PAC-07 #7 (routing rules — PAC-AC-P04-02 full).

### 3.8 Interface health completion — E-PAC-08 #1/#2 (base S2-23/24)
**Source:** `PAC/06` PAC-AC-P04-08; `RIS/06` RIS-AC-P06-02; `interface_events`, `modalities.last_heartbeat_at`, `interface_endpoints.last_message_at`.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S5-14 | DICOM-specific health views on the dashboard (extend S2-24): modality online/offline via heartbeat, DICOM queue depth, per-interface drill-down | FE | 1.0 | S2-24, S5-02 | PAC-AC-P04-08: fault visible with drill-down |
| S5-15 | Interface health API completion: queues, HL7 failures, modality status, per-interface detail for drill-down | BE | 1.0 | S2-23 | RIS-AC-P06-02 / PAC-AC-P04-08 data complete |

**Epic exit contribution:** E-PAC-08 #1/#2 (health dashboard — G5).

### 3.9 Alerting completion — E-PAC-08 #3 (base S2-25)
**Source:** `PAC/05` PAC-SL-23; notification subsystem (S1-25).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S5-16 | Alerting config: severity thresholds, channel wiring, escalation for unresolved CRITICAL (extend S2-25) | BE | 1.0 | S2-25 | PAC-SL-23: failure alerted ≤ 5 min; 0 silent drops |
| S5-17 | Alert dedup/quieting + severity policy UI (avoid alert storms) | FE | 1.0 | S5-16 | PAC-SL-23 sustained; no duplicate alerts for one fault |

**Epic exit contribution:** E-PAC-08 #3 (≤ 5-min alerting — G5).

### 3.10 Conformance harness formalization — E-PAC-08 #4 (D)
**Source:** PAC-SL-23; lab scripts from S2-27/S3-21.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S5-18 | Formalize conformance harness (C-STORE/MWL/MPPS test set) as a repeatable modality-onboarding package + vendor docs | INT | 2.0 | S2-27, S3-21 | G5 evidence; repeatable scripts with recorded outputs |

**Epic exit contribution:** E-PAC-08 #4 (conformance harness — G5 evidence).

### 3.11 Admin & monitoring E2E + UAT prep (cross-cutting)
**Source:** G4/G5/G7 exit gates; PAC-UI-26…32; PAC-SL-23/60/61.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S5-19 | Admin console E2E: modality registry → queue monitor → storage dashboard → retention editor → exception worklist → audit viewer | QA | 1.5 | S5-01…S5-11 | PAC-UI-26…32 parity; PAC-AC-P04-05/P19-01 pass |
| S5-20 | Interface monitoring E2E: inject failure → alert ≤ 5 min → dashboard shows fault → resolve → `resolved_at` recorded | QA | 1.5 | S5-14…S5-17 | PAC-AC-P04-08, PAC-SL-23 pass |
| S5-21 | RLS + audit regression on admin routes (registry, queue, storage, retention, routing) | QA | 0.5 | S5-19 | PAC-SL-60/61; cross-facility admin read denied |
| S5-22 | UAT prep: PACS administrator sign-off scripts (G7 UAT) | QA | 1.0 | S5-19 | Scripts trace to PAC-AC-P04-*/P19-*; sign-off gate ready |

---

## 4. Sprint Milestones

| Milestone | Target | Evidence |
| :--- | :--- | :--- |
| **Day 3** | Modality registry UI + heartbeat status; storage stats API; interface health completion started | S5-01/02, S5-06, S5-14/15 started; admin shell navigation live |
| **Day 5** | Queue monitor + storage dashboard live; retention editor + dry-run | S5-03…S5-08 closed; PAC-AC-P19-01 + P04-03 dry-run asserted |
| **Day 8** | Exception worklist + reconciliation; audit viewer polish; alerting dedup/escalation; routing rules (D) | S5-09…S5-17 closed; PAC-AC-P04-05/P04-08 |
| **Day 10 (demo)** | E2E + UAT-prep suites green; demo: failure injection → ≤ 5-min alert → dashboard → resolve; admin console tour | S5-18…S5-22; G4/G5 pre-checks; sprint review |

---

## 5. Sprint Definition of Done (acceptance checks)

| # | Check | Verifies | Method |
| :-: | :--- | :--- | :--- |
| D1 | Admin console parity: modality registry, queue monitor, storage dashboard, retention editor, exception worklist, audit viewer | PAC-UI-26…32 | S5-19 E2E |
| D2 | Storage dashboard usage/quota/tier/growth matches metering; export matches | PAC-AC-P19-01 | S5-06/S5-19 |
| D3 | Retention dry-run before purge; 0 accidental purges | PAC-AC-P04-03, PAC-SL-43 | S5-08/S5-19 |
| D4 | Exception worklist reconciliation ≤ 24 h; routing precedence deterministic | PAC-AC-P04-02/05, PAC-SL-22 | S5-10/S5-13/S5-19 |
| D5 | Interface failure alerted ≤ 5 min, 0 silent drops, fault visible with drill-down | PAC-AC-P04-08, PAC-SL-23 | S5-20 E2E |
| D6 | 100% audit on admin routes; cross-facility admin access denied | PAC-SL-60/61 | S5-21 |
| D7 | Engineering DoD: `tsc --noEmit` + `vite build` clean; unit tests green; migrations reviewed (incl. `routing_rules`) | release-plan §6 | CI gate |
| D8 | No P0/P1 open defects; UAT scripts ready for PACS administrator sign-off (G7) | release-plan §6 | Defect triage + S5-22 |

---

## 6. Risks & Watch Items (Sprint 5)

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| Admin console breadth (7 pages) in one sprint | FE velocity (14 of 20 days) | Prioritize M pages; D-items (routing rules, S5-12/13) absorb rework; KPI forward-pull is uncommitted |
| Queue-depth accuracy vs. live DICOM traffic | S5-04 counts vs. lab traffic | Conformance harness data (S5-18); stuck-message heuristics validated in lab |
| Alert storms on repeated failures | PAC-SL-23; dedup (S5-17) | Dedup/quieting policy; escalation only for unresolved CRITICAL |
| Storage dashboard freshness (growth trend) | PAC-AC-P19-01 export parity | Metering aggregation timing; refresh ≤ 5 min |
| Routing-rules precedence regressions | PAC-AC-P04-02 deterministic | Precedence `UNIQUE (facility_id, precedence)` + dry-run tests; engine unit-tested on ingest path |
| UAT scope creep (PACS admin expectations) | G7 sign-off | Scripts written early (S5-22); trace to PAC-AC-P04-*/P19-* |
| Single BE engineer becomes bottleneck | BE 9.0 of 10 days | BE slack tight; routing engine (S5-13) can slip to Sprint 6 if needed |

---

## Traceability

| Source work item | Tasks |
| :--- | :--- |
| E-PAC-07 #1 (modality registry UI) | S5-01…S5-02 |
| E-PAC-07 #2 (queue monitor) | S5-03…S5-04 |
| E-PAC-07 #3 (storage dashboard) | S5-05…S5-06 |
| E-PAC-07 #4 (retention editor + dry-run) | S5-07…S5-08 |
| E-PAC-07 #5 (exception worklist UI) | S5-09…S5-10 |
| E-PAC-07 #6 (audit log viewer — base S1-16) | S5-11 |
| E-PAC-07 #7 (routing rules, D) | S5-12…S5-13 |
| E-PAC-08 #1/#2 (interface health — base S2-23/24) | S5-14…S5-15 |
| E-PAC-08 #3 (alerting — base S2-25) | S5-16…S5-17 |
| E-PAC-08 #4 (conformance harness, D — reuse S2-27/S3-21) | S5-18 |
| Cross-cutting (admin/monitoring E2E, RLS/audit, UAT) | S5-19…S5-22 |
