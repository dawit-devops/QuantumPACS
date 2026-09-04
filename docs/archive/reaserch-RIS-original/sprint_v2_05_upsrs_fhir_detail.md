# Sprint V2-05 Detail — UPS-RS Workflow (E-V2-09) & FHIR / SMART-on-FHIR Backend (E-V2-10)

**Version:** 1.0 · **Date:** 2026-08-05 · **Source:** `requrements/PACS/RELEASE_PLAN_V2.md` E-V2-09, E-V2-10 (backend); `requrements/PACS/PRD.md` §3 (AI), §4.2 (integration); `research/pacs-ris-viewer-integration-spec.md` §4–§6
**Cadence:** 2-week sprint (10 working days) · **Squads:** PACS-V2 — two backend, one frontend, integration engineer (UPS-RS + FHIR conformance — critical path), QA · **Format parity:** `requrements/sprint_v2_01_advanced_viewer_priors_detail.md` … `sprint_v2_04_ai_migration_gates_detail.md`
> **Sprint numbering:** this is sprint detail **V2-05** of the V2 delivery sequence = release-plan roadmap **V2-S9–V2-S10**, the start of **Phase 2 (PRD §5.1 v2.0)**. Merged because the UPS-RS dispatch epic (E-V2-09) feeds the FHIR/SMART epic (E-V2-10) and both sit on the Phase-1 AI ingestion + DICOMweb foundations.

---

## 1. Sprint Goal

> **"AI services subscribe to studies through a standards-based UPS-RS workflow — job created on study arrival, progress reported, results pulled with scoped service keys and returned as validated SR/GSPS/FHIR within 5 minutes — while the platform exposes full FHIR R4 (ImagingStudy, DiagnosticReport, ServiceRequest, Endpoint) and the SMART-on-FHIR launch backend that an EMR uses to open the correct study in one click."**

**Scope in:** DICOMweb UPS-RS service (N-CREATE/N-GET/N-SET/N-DELETE), subscription registry + webhook fallback, WADO-RS pull with scoped service keys, AI result ingestion at scale with conformance validation, ≤ 5-min latency to worklist, AI access audit; full FHIR R4 `ImagingStudy`/`DiagnosticReport`/`ServiceRequest`/`Endpoint` (search/read/create), SMART on FHIR launch flow (`iss+launch`, token exchange, patient/encounter context, transparent refresh), no PHI in URLs, EMR conformance harness for PAC-AC-P06-01.

**Scope out (later V2 sprints):** referring-MD read-only viewer surface + FHIRcast (V2-06), non-DICOM content (V2-06), edge at scale (V2-06), schema-per-tenant + patient delivery + AI utility gate (V2-07).

**Prior program handoff (required to start):** AI result ingestion + validation (V2-04-05…08), service keys (S1-29), IUA/OAuth2 gate (S4-08), FHIR ImagingStudy read-only (S4-10), report-routing path (V2-03-12/13), exception queue (S2-21/22).

---

## 2. Team Capacity (10 working days)

| Role | FTE | Available dev-days | Notes |
| :--- | :-: | :-: | :--- |
| Backend engineer ×2 | 2.0 | 20 | UPS-RS service + FHIR server layer |
| Frontend engineer ×1 | 1.0 | 10 | SMART launch token UI plumbing (launch landing) |
| Integration engineer | 1.0 | 10 | UPS-RS + FHIR conformance — **critical path** |
| QA | 1.0 | 10 | UPS/FHIR conformance suites, launch acceptance, latency |
| **Total** | **5.0** | **~50** | Total task estimate below: **~42 dev-days** (BE 22.0 · FE 4.5 · INT 8.5 · QA 7.0) — ~8 days slack, absorbed per note below |

> **Slack absorption (not committed):** (a) forward-pull of **E-V2-10 #3** (read-only referring mode first pass) on FE slack; (b) extra UPS-RS conformance corpus; (c) FHIR search-param coverage polish. Nothing past E-V2-09/E-V2-10 backend scope is committed.

---

## 3. Task Board (grouped by source work item)

> Estimates in dev-days. `Owner:` BE = backend, FE = frontend, INT = integration engineer, QA = test. `Check:` acceptance check (maps to AC/SL/UI/PRD IDs where applicable).

### 3.1 UPS-RS service — E-V2-09 #1/2
**Source:** DICOMweb UPS-RS (IHE); `PAC/02` PAC-WF6; PRD §3.1; `research/pacs-ris-viewer-integration-spec.md` §4.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-05-01 | UPS-RS service: N-CREATE (study-arrived job with StudyInstanceUID + input refs), N-GET status, N-SET progress, N-DELETE/cancel — behind IUA/OAuth2 | INT | 3.0 | S4-08 | PAC-M05: AI service subscribes and receives jobs |
| V2-05-02 | Subscription registry: per-AI-service registration (topics, scopes, webhook fallback), enable/disable | BE | 1.5 | V2-05-01 | Dispatch works for registered services |
| V2-05-03 | Job lifecycle + persistence: `ups_jobs` table, state machine, retry, exception queue for failed jobs | BE | 1.5 | V2-05-01 | 0 silent job failures; queue shows reason |
| V2-05-04 | Webhook fallback: study-arrived webhook when UPS unavailable (modality/legacy AI) | INT | 1.0 | V2-05-02 | Fallback path delivers within SLA |

**Epic exit contribution:** E-V2-09 #1/2 (UPS-RS + subscription).

### 3.2 WADO pull & result ingestion at scale — E-V2-09 #3/4/5
**Source:** PRD §3.1/§3.2; RBAC §6; V2-04-05…08 reuse.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-05-05 | WADO-RS pull with scoped service keys (`STUDY_READ`/`RESULTS_READ`); per-key byte metering | BE | 1.5 | S1-29, V2-05-01 | Least-privilege access verified; PAC-SL-50 bytes metered |
| V2-05-06 | Result ingestion at scale: SR/GSPS + FHIR Observation/DiagnosticReport/ImagingSelection → validate, dedupe, index (extend V2-04-06) | BE | 2.0 | V2-04-06 | PRD §3.2 integrity sustained at scale |
| V2-05-07 | Latency pipeline: study-complete (C-STORE) → UPS job → result → worklist flag ≤ 5 min; metric instrumented | BE | 1.5 | V2-05-03, V2-04-07 | PRD §3.2 latency; dashboard panel |
| V2-05-08 | AI access audit: every UPS job + WADO pull + result write logged; no AI path alters pixels/report | BE | 0.5 | V2-05-05 | PAC-SL-60; PRD §3.2 safety |

**Epic exit contribution:** E-V2-09 #3/4/5 (pull, ingestion, latency — VG-6).

### 3.3 Full FHIR R4 — E-V2-10 #1
**Source:** PRD §4.2; `research/pacs-ris-viewer-integration-spec.md` §5; FHIR R4.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-05-09 | FHIR server layer: `ImagingStudy` search/read/create (study/series/instance + Endpoint linkage) | BE | 2.5 | S4-10 | Conformance smoke tests vs. public test server |
| V2-05-10 | `DiagnosticReport` read/create: report + key-image references + measurement links; `ServiceRequest` read (order link) | BE | 2.0 | V2-05-09, V2-01-11 | Report conformance; key images referenced |
| V2-05-11 | `Endpoint` resource: DICOMweb base URLs per facility; SMART `conf`/`authorize`/`token` discovery | BE | 1.5 | V2-05-09 | Endpoints resolve to QIDO/WADO |
| V2-05-12 | FHIR search params + pagination + RLS enforcement on all FHIR routes | BE | 1.5 | V2-05-09 | Search parity; RLS isolation (PAC-SL-61) |
| V2-05-13 | FHIR conformance harness: test-suite + version pinning; `DiagnosticReport`/`ImagingStudy` CI tests | INT | 2.0 | V2-05-09/10 | Conformance suite green; version drift caught |

**Epic exit contribution:** E-V2-10 #1 (full FHIR — VG-7).

### 3.4 SMART on FHIR launch backend — E-V2-10 #2
**Source:** `PAC/06` PAC-AC-P06-01; `PAC/02` PAC-WF7; PAC-SL-13; ADR-009.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-05-14 | SMART launch flow: `iss+launch` → authorize → token exchange; patient/encounter context resolution | BE | 2.0 | V2-05-11 | PAC-AC-P06-01: context resolves to correct patient |
| V2-05-15 | Token refresh transparency + session scoping (no PHI in URLs; UID-based deep links) | BE | 1.0 | V2-05-14 | Refresh seamless; URLs PHI-free |
| V2-05-16 | Launch landing: EMR launch → viewer opens correct study without search; `< 5 s` first frame (PAC-SL-13) | FE | 2.0 | V2-05-14, V2-01-01 | PAC-AC-P06-01: correct study; PAC-SL-13 |
| V2-05-17 | Test-EMR conformance harness: simulated SMART launch + FHIR interactions for CI acceptance | INT | 2.5 | V2-05-14 | PAC-AC-P06-01 runnable without a real EMR |
| V2-05-18 | SMART scope enforcement: launch scopes map to least-privilege read permissions (`VIEWER_READ`-class) | BE | 1.0 | V2-05-14 | Scope over-permission rejected |

**Epic exit contribution:** E-V2-10 #2 (SMART launch backend — VG-7).

### 3.5 Cross-cutting: conformance, E2E & gates — VG-6/VG-7 pre-checks
**Source:** PRD §3.1/§3.2; `PAC/05` PAC-SL-13/50/60/61.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-05-19 | UPS-RS conformance E2E: AI subscribe → C-STORE → N-CREATE → WADO pull → SR result → worklist flag ≤ 5 min | QA | 2.0 | V2-05-01…08 | PRD §3.2 latency + integrity pass |
| V2-05-20 | FHIR + SMART E2E: test-EMR launch → correct study → view → token refresh; key images + measurements in DiagnosticReport | QA | 2.0 | V2-05-09…18 | PAC-AC-P06-01 pass in staging |
| V2-05-21 | RLS + audit regression on FHIR/UPS routes (cross-tenant denied; every pull logged) | QA | 1.0 | V2-05-08/12 | PAC-SL-60/61 |
| V2-05-22 | Performance: FHIR ImagingStudy search + UPS job latency under load; no budget breach | QA | 1.0 | V2-05-09, V2-05-07 | p95 assertions green |
| V2-05-23 | Service-key scope audit: AI keys limited to `STUDY_READ`/`RESULTS_READ`; over-scoped key request rejected | QA | 0.5 | V2-05-05 | RBAC §6 compliance |
| V2-05-24 | UAT prep: referring-MD + AI-vendor scripts; evidence pack for VG-6/VG-7 pre-checks | QA | 1.0 | V2-05-19/20 | Scripts trace to PAC-AC-P06-01/PRD §3 |

---

## 4. Sprint Milestones

| Milestone | Target | Evidence |
| :--- | :--- | :--- |
| **Day 3** | UPS-RS N-CREATE handler live; FHIR ImagingStudy scaffold; SMART token flow design | V2-05-01, V2-05-09, V2-05-14 started |
| **Day 5** | UPS job lifecycle + subscription; FHIR DiagnosticReport/Endpoint; launch landing first pass | V2-05-02/03, V2-05-10/11, V2-05-16 closed |
| **Day 8** | Result ingestion at scale + latency pipeline; SMART refresh + scope enforcement; conformance harness | V2-05-05…08, V2-05-15/17/18, V2-05-13 closed |
| **Day 10 (demo)** | UPS-RS + FHIR/SMART E2E green; demo: AI subscribe → result ≤ 5 min; test-EMR launch → study < 5 s | V2-05-19…24; VG-6/VG-7 pre-checks; sprint review |

---

## 5. Sprint Definition of Done (acceptance checks)

| # | Check | Verifies | Method |
| :-: | :--- | :--- | :--- |
| D1 | UPS-RS workflow live (subscribe → N-CREATE → status → cancel); webhook fallback | PAC-M05, PRD §3.1 | V2-05-19 E2E |
| D2 | AI result ≤ 5 min study-complete → worklist; ≥ 95% conformance; 0 corrupt/duplicate | PRD §3.2 | V2-05-07/19 |
| D3 | Full FHIR ImagingStudy/DiagnosticReport/ServiceRequest/Endpoint conformance + RLS | VG-7, PAC-SL-61 | V2-05-13/21 |
| D4 | SMART launch: correct study, < 5 s, transparent refresh, no PHI in URLs | PAC-AC-P06-01, PAC-SL-13 | V2-05-20 |
| D5 | Service keys scoped to `STUDY_READ`/`RESULTS_READ`; over-scoped rejected | RBAC §6 | V2-05-23 |
| D6 | 100% audit on UPS/WADO/FHIR events; cross-tenant denied | PAC-SL-60/61 | V2-05-21 |
| D7 | Engineering DoD: `tsc --noEmit` + `vite build` clean; unit tests green; migrations reviewed (`ups_jobs`) | release-plan V2 §6 | CI gate |
| D8 | No P0/P1 open defects at sprint close | release-plan V2 §6 | Defect triage |

---

## 6. Risks & Watch Items (Sprint V2-05)

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| UPS-RS conformance variance across AI vendors | V2-05-19 E2E | Conformance harness first (Day 1); webhook fallback (V2-05-04); service-agnostic ingestion |
| FHIR version/search drift | V2-05-13 suite | Version pinning + public test servers; CI conformance gate |
| SMART token/scope leakage | V2-05-18/23 | Scope mapping to least privilege; launch scopes validated; no PHI in URLs |
| Latency breach (C-STORE → worklist > 5 min) | PRD §3.2 | UPS job queue sizing; ingestion pipeline profiled; latency metric dashboarded |
| **INT capacity at budget (8.5 of 10)** | INT critical path | Protect INT time; QA runs harness (V2-05-13/17); defer search-param polish to slack |
| EMR v2.0 coordination slip | PAC-AC-P06-01 | Contract-first + test-EMR harness; acceptance runnable without the real EMR |

---

## Traceability

| Source work item | Tasks |
| :--- | :--- |
| E-V2-09 #1 (UPS-RS service) | V2-05-01…03 |
| E-V2-09 #2 (subscription registry) | V2-05-02/04 |
| E-V2-09 #3 (WADO pull, scoped keys) | V2-05-05 |
| E-V2-09 #4 (ingestion at scale) | V2-05-06 |
| E-V2-09 #5 (latency + audit) | V2-05-07/08 |
| E-V2-10 #1 (full FHIR) | V2-05-09…13 |
| E-V2-10 #2 (SMART launch) | V2-05-14…18 |
| Cross-cutting (UPS/FHIR E2E, RLS/audit, perf, UAT prep) | V2-05-19…24 |
