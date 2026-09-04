# Sprint V2-03 Detail — Teleradiology (E-V2-04) & Export Backend (E-V2-05)

**Version:** 1.0 · **Date:** 2026-08-05 · **Source:** `requrements/PACS/RELEASE_PLAN_V2.md` E-V2-04, E-V2-05 (backend); `requrements/PACS/02_end_to_end_workflows.md` PAC-WF4/WF8
**Cadence:** 2-week sprint (10 working days) · **Squads:** PACS-V2 — two backend, one and a half frontend, integration engineer (streaming + report routing), QA · **Format parity:** `requrements/sprint_v2_01_advanced_viewer_priors_detail.md`, `requrements/sprint_v2_02_priors_grants_detail.md`
> **Sprint numbering:** this is sprint detail **V2-03** of the V2 delivery sequence = release-plan roadmap **V2-S5–V2-S6**. Merged because the teleradiology epic (E-V2-04) needs the grants epic (V2-02) for multi-facility reads, and the export backend (E-V2-05) shares the distribution/report-routing path.

---

## 1. Sprint Goal

> **"A teleradiologist launches one tokenized session, reads studies from every facility granted by contract with first frames under 5 seconds on home bandwidth, flags critical findings that reach on-site staff with tracked acknowledgment, and signs reports that route to the correct ordering facility — while the export service can push audited, anonymized DICOM/PDF media and XDS-I.b documents."**

**Scope in:** multi-facility worklist (grants-backed, facility context per row), low-bandwidth progressive streaming tuning (PAC-SL-12), cross-facility priors in the panel, critical callback to on-site staff + acknowledgment tracking + escalation, report routing to the ordering facility (ORU/FHIR), per-facility audit + denied-and-audited unauthorized access; export backend service: format selection (DICOM/PDF/PDI media/XDS-I.b), anonymization profile, reason codes, export job queue + retry + exception handling, export record retention.

**Scope out (later V2 sprints):** export UI + share links (V2-04), AI ingestion/overlays (V2-04), migration tooling (V2-04), QC/specialty completion (V2-04), UPS-RS (V2-05), FHIR/SMART (V2-05/06), non-DICOM/edge scale (V2-06), schema-per-tenant/patient delivery/AI gate (V2-07).

**Prior program handoff (required to start):** grants DDL/RLS/helper/API/UI (V2-02-09…17), prefetch engine + priors panel (V2-02-01…08), responsive viewer (V2-01-16/17), notification subsystem (S1-25), report/dictation pipeline (RIS E-RIS-08 — shared surface), interface engine + exception queue (S2-21/22).

---

## 2. Team Capacity (10 working days)

| Role | FTE | Available dev-days | Notes |
| :--- | :-: | :-: | :--- |
| Backend engineer ×2 | 2.0 | 20 | Telerad session/worklist/routing + export service |
| Frontend engineer ×1.5 | 1.5 | 15 | Multi-facility worklist + callback UX + export job views |
| Integration engineer | 0.75 | 7.5 | Streaming SLA + ORU/FHIR report routing conformance |
| QA | 0.5 | 5 | Telerad E2E, export E2E, cross-tenant audit |
| **Total** | **4.75** | **~47.5** | Total task estimate below: **~39.5 dev-days** (BE 20.0 · FE 9.5 · INT 5.5 · QA 4.5) — ~8 days slack, absorbed per note below |

> **Slack absorption (not committed):** (a) forward-pull of **E-V2-06 #1/#2** (AI dispatch + result validation) once the report-routing path exists; (b) extra streaming profiles (very-low-bandwidth tests); (c) export dry-run polish. Nothing past E-V2-04/E-V2-05 backend scope is committed.

---

## 3. Task Board (grouped by source work item)

> Estimates in dev-days. `Owner:` BE = backend, FE = frontend, INT = integration engineer, QA = test. `Check:` acceptance check (maps to AC/SL/UI IDs where applicable).

### 3.1 Multi-facility session & worklist — E-V2-04 #1
**Source:** `PAC/06` PAC-AC-P03-01; `PAC/04` PAC-UI-08…12 extension; `cross_tenant_grants_design.md` §6.1.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-03-01 | Telerad session model: OAuth2 token + grant-scoped facility set; facility context per request (no per-facility logins) | BE | 1.5 | V2-02-10 | PAC-AC-P03-01: single session covers all granted facilities |
| V2-03-02 | Multi-facility worklist: aggregates studies from granted facilities; facility badge per row; unauthorized facility → denied + audited | FE | 2.0 | V2-03-01 | PAC-AC-P03-01 (denied case); PAC-SL-60 |
| V2-03-03 | Worklist filters/pagination across facilities (server `total`); priors indicator per facility | FE | 1.0 | V2-03-02, V2-02-08 | PAC-UI-09/10 parity across facilities |

**Epic exit contribution:** E-V2-04 #1 (tokenized multi-facility session).

### 3.2 Low-bandwidth streaming — E-V2-04 #2
**Source:** `PAC/06` PAC-AC-P03-02; `PAC/05` PAC-SL-12.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-03-04 | Streaming tuning: frame-level WADO-RS prefetch window, JPEG/JPEG-LS rendering, prioritized frame order for 25 Mbps links | INT | 2.5 | S4-06 | PAC-SL-12: first frame < 5 s @ 25 Mbps, 500 MB study |
| V2-03-05 | Client-side bandwidth adaptation: dynamic quality/bitrate per connection; render-service fallback for weak clients | FE | 1.5 | V2-03-04, V2-01-04 | PAC-AC-P03-02: read proceeds while later frames stream |
| V2-03-06 | SLA instrumentation: `PAC-SL-12` metric on telerad sessions + dashboard panel | BE | 0.5 | V2-03-04 | Metric measurable per session |

**Epic exit contribution:** E-V2-04 #2 (progressive streaming — PAC-SL-12).

### 3.3 Cross-facility priors — E-V2-04 #3
**Source:** `PAC/06` PAC-AC-P03-03; `PAC/02` PAC-WF3/4.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-03-07 | Cross-facility priors in the panel: grants-backed retrieval into the existing priors panel; source-facility label + audited access | FE | 1.5 | V2-02-06, V2-02-10 | PAC-AC-P03-03; CTG-AC-01 audited |
| V2-03-08 | Prior prefetch across facilities for telerad sessions (edge staging under grant) | BE | 1.0 | V2-03-07, V2-02-03 | Priors staged without bandwidth degradation |

**Epic exit contribution:** E-V2-04 #3 (cross-facility priors).

### 3.4 Critical callback & acknowledgment — E-V2-04 #4
**Source:** `PAC/06` PAC-AC-P03-04; `PAC/05` PAC-SL-25; notification subsystem (S1-25).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-03-09 | Critical callback: one-action flag → notification to on-site staff at the ordering facility (call task/message/page) with ack tracking + escalation timer | BE | 1.5 | S1-25, S4-20 | PAC-AC-P03-04: ack tracked; unacknowledged escalates |
| V2-03-10 | Callback UX: recipient selection (ordering facility on-call), ack receipt, worklist badge until acknowledged | FE | 1.0 | V2-03-09 | PAC-UI-13 parity for remote reads |
| V2-03-11 | Callback audit: flag → notification → ack chain logged with facility context | BE | 0.5 | V2-03-09 | PAC-SL-60: chain complete |

**Epic exit contribution:** E-V2-04 #4 (critical callback — PAC-AC-P03-04).

### 3.5 Report routing to ordering facility — E-V2-04 #5
**Source:** `PAC/06` PAC-AC-P03-05; RIS E-RIS-10 (ORU delivery) + E-RIS-08 (signing).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-03-12 | Report routing: signed remote report → ORU/FHIR to the ordering facility's RIS/EMR only; per-facility delivery queue + retry | INT | 2.0 | S2-21 (queue), RIS E-RIS-10 | PAC-AC-P03-05: report lands in the ordering tenant's records only |
| V2-03-13 | Routing rules by facility/contract: destination resolution from grant purpose + engagement contract | BE | 1.0 | V2-03-12, V2-02-13 | Deterministic destination; 0 misroutes (audited) |
| V2-03-14 | Critical flag embedded in the routed ORU/FHIR payload | BE | 0.5 | V2-03-12, S4-20 | PAC-AC-P01-06 (remote case) |

**Epic exit contribution:** E-V2-04 #5 (report routing — PAC-AC-P03-05).

### 3.6 Export backend service — E-V2-05 #1/2/3
**Source:** `PAC/06` PAC-AC-P04-06; `PAC/02` PAC-WF8; IHE PDI + XDS-I.b per `pacs-ris-architecture-deep-dive.md` §1/§3.5.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-03-15 | Export service: study/series selection, format resolution (DICOM, PDF incl. report+key images, PDI CD/DVD media set, XDS-I.b push) | BE | 2.0 | S4-21 (key images), RIS report pipeline | PAC-AC-P04-06: format + recipient captured |
| V2-03-16 | Anonymization profile: de-identification (name/ID/dates) per configurable profile; toggle + preview | BE | 1.5 | V2-03-15 | Anonymized export has no PHI (sample-checked) |
| V2-03-17 | Export job queue + status + retry + exception handling (reuses interface-engine patterns) | BE | 1.5 | V2-03-15, S2-21 | 0 silent failures; queue shows reason |
| V2-03-18 | Export record retention: who/what/why/recipient persisted; audit event on every export | BE | 1.0 | V2-03-15 | PAC-SL-60: 100% of exports logged |
| V2-03-19 | PDI/XDS-I.b conformance harness for export (repeatable media + push tests) | INT | 1.0 | V2-03-15 | G5-style conformance evidence for export |

**Epic exit contribution:** E-V2-05 #1/2/3 (audited export backend — VG-4 distribution part).

### 3.7 Cross-cutting: E2E & gates — VG-3/VG-4 pre-checks
**Source:** `PAC/06` PAC-AC-P03-01…05; `PAC/05` PAC-SL-12/25/60/61.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-03-20 | Telerad E2E: token session → multi-facility worklist → read @25 Mbps < 5 s → priors cross-facility → critical callback ack → sign → route to ordering facility | QA | 2.0 | V2-03-01…14 | PAC-AC-P03-01/02/03/04/05 pass |
| V2-03-21 | Export E2E: select → anonymize → PDI/XDS-I.b push → audit row with reason | QA | 1.0 | V2-03-15…19 | PAC-AC-P04-06 pass |
| V2-03-22 | Cross-tenant audit regression: granted read → `cross_tenant.read`; revoked → denied + `cross_tenant.denied`; 0 incidents | QA | 1.0 | V2-02-11 | PAC-SL-60/61 evidence |
| V2-03-23 | RLS regression on routing/delivery tables (report routing never crosses facility without grant) | QA | 0.5 | V2-03-12 | Isolation assertion green |
| V2-03-24 | UAT prep: teleradiologist script (session, streaming, callback, routing) + PACS admin export script | QA | 1.0 | V2-03-20/21 | Scripts trace to PAC-AC-P03-*/P04-06 |

---

## 4. Sprint Milestones

| Milestone | Target | Evidence |
| :--- | :--- | :--- |
| **Day 3** | Session model + multi-facility worklist query; export format resolution; streaming tuning start | V2-03-01/02, V2-03-15, V2-03-04 started |
| **Day 5** | Multi-facility worklist + priors cross-facility; ORU routing path first pass; anonymization profile | V2-03-03/07, V2-03-12/16 closed; PAC-SL-12 asserted |
| **Day 8** | Critical callback + ack chain; export queue + retry + records; streaming SLA green | V2-03-09…11, V2-03-17/18, V2-03-05/06 closed |
| **Day 10 (demo)** | Telerad + export E2E green; demo: session → read 4 facilities → callback → route; export anonymized PDI | V2-03-19…24; VG-3/VG-4 pre-checks; sprint review |

---

## 5. Sprint Definition of Done (acceptance checks)

| # | Check | Verifies | Method |
| :-: | :--- | :--- | :--- |
| D1 | Tokenized multi-facility session; unauthorized facility denied + audited | PAC-AC-P03-01 | V2-03-20 E2E |
| D2 | First frame < 5 s @ 25 Mbps on 500 MB study | PAC-SL-12, PAC-AC-P03-02 | V2-03-04/06 + E2E |
| D3 | Cross-facility priors served under grant, audited | PAC-AC-P03-03, CTG-AC-01 | V2-03-20 |
| D4 | Critical callback tracked to ack with escalation; flag in routed payload | PAC-AC-P03-04, PAC-AC-P01-06 | V2-03-09…11, V2-03-14 |
| D5 | Reports route to the ordering facility only; 0 misroutes | PAC-AC-P03-05 | V2-03-12/13 + E2E |
| D6 | Export audited (format/anonymization/reason/recipient); 0 silent failures | PAC-AC-P04-06, PAC-SL-60 | V2-03-21 |
| D7 | Engineering DoD: `tsc --noEmit` + `vite build` clean; unit tests green; migrations reviewed | release-plan V2 §6 | CI gate |
| D8 | No P0/P1 open defects at sprint close | release-plan V2 §6 | Defect triage |

---

## 6. Risks & Watch Items (Sprint V2-03)

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| Streaming SLA miss on 25 Mbps (multi-GB studies) | PAC-SL-12 p95 | Frame-order prioritization, JPEG/JPEG-LS, render-service fallback (V2-03-04/05); bandwidth adaptation E2E |
| Report misrouting (PHI at wrong facility) | PAC-AC-P03-05; RLS regression | Destination from grant purpose + contract only; per-facility queue; RLS regression (V2-03-23) |
| Critical callback reliability (off-hours on-call) | PAC-AC-P03-04 ack rate | Escalation timers; notification subsystem channels; ack chain audited |
| Anonymization completeness | V2-03-16 sample check | Profile-based de-identification + automated PHI scan on anonymized output |
| **INT capacity (5.5 of 7.5)** | INT on streaming/routing | Protect INT time; QA runs conformance harness (V2-03-19); defer ORU edge-case polish to slack |
| Grants regression under session load | CTG-AC-01 latency | Per-request cached facility array; load-tested in V2-03-20 |

---

## Traceability

| Source work item | Tasks |
| :--- | :--- |
| E-V2-04 #1 (tokenized multi-facility session) | V2-03-01…03 |
| E-V2-04 #2 (progressive streaming) | V2-03-04…06 |
| E-V2-04 #3 (cross-facility priors) | V2-03-07/08 |
| E-V2-04 #4 (critical callback) | V2-03-09…11 |
| E-V2-04 #5 (report routing) | V2-03-12…14 |
| E-V2-05 #1 (export service) | V2-03-15 |
| E-V2-05 #2 (anonymization) | V2-03-16 |
| E-V2-05 #3 (queue + records) | V2-03-17/18 |
| E-V2-05 #4 (conformance harness) | V2-03-19 |
| Cross-cutting (telerad/export E2E, audit/RLS, UAT prep) | V2-03-20…24 |
