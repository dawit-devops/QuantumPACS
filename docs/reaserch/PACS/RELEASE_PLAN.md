# Release Plan — PACS (Picture Archiving & Communication System)

**Version:** 1.0 · **Date:** 2026-08-04 · **Source:** `requrements/PACS/PRD.md` (§5.1 phased rollout)
**Planning assumptions:** 2-week sprints · two squads — **Platform** (shared services: auth/RBAC, tenant provisioning, audit, interface engine — built with the RIS release, reused here) and **PACS-Core** (ingestion, archive/ILM, DICOMweb, viewer) · part-time integration engineer for DICOM/DICOMweb conformance and a frontend engineer dedicated to the zero-footprint viewer. **MVP estimated at 12 sprints (~6 months), with the Platform foundation largely inherited from the RIS release.**

---

## 1. Release Overview

| Phase | Scope (PRD §5.1) | Est. duration | Exit gate |
| :--- | :--- | :--- | :--- |
| **MVP v1.0** | Ingestion (C-STORE/STOW-RS), metadata index, tiered archive + storage commitment, basic zero-footprint viewer (QIDO/WADO), MWL/MPPS echo, audit, RBAC, tenant provisioning, quota/retention admin | 12 sprints | PAC-AC-P01-08/10, P02-01/02, P04-03/04 pass; 99.9% availability in prod |
| **v1.1** | Advanced viewer (MPR/MIP/3D/cine/fusion/measurements), priors prefetch, teleradiology (token sessions + **cross-tenant grants**), critical results (teleradiology callback; on-site flag loop already in MVP per §2.3), export (CD/XDS-I.b), AI result ingestion, KPI dashboards, migration tooling | 6–8 sprints | CTG-AC-01…07; PAC-AC-P01-03/04/06; TAT SLAs met |
| **v2.0** | UPS-RS workflow, full FHIR ImagingStudy/DiagnosticReport + SMART on FHIR + FHIRcast, non-DICOM content, edge caching at scale, schema-per-tenant escape hatch, patient imaging delivery, AI utility gate | 6–8 sprints | EMR-launch acceptance (PAC-AC-P06-01); AI acceptance ≥ 70% |

---

## 2. MVP Exit-Gate Acceptance Criteria (Definition of "releasable")

> **Runnable form:** `requrements/PACS/go-live-checklist.md` — a standalone QA/ops cutover checklist extracting these gates into steps, evidence artifacts, a cutover sequence, and a sign-off block.

| Gate | Criterion | Verifies |
| :-: | :--- | :--- |
| G1 | C-STORE/STOW-RS → indexed & retrievable < 5 min; Storage Commitment 100% verifiable; 0 silent purges | PAC-AC-P02-02, PAC-SL-20/21 |
| G2 | MWL auto-populates at the console (≥ 98% without manual entry); MPPS drives status without manual entry | PAC-AC-P02-01/04, PAC-SL-14/34 |
| G3 | Study opens < 3 s p95; first frames progressive < 3 s on multi-GB studies; viewer never blocks | PAC-AC-P01-08/10, PAC-SL-10/11 |
| G4 | Retention/legal-hold honored with 0 accidental purges; quota alerts at 75/90% | PAC-AC-P04-03/04, PAC-SL-43/45 |
| G5 | Interface message delivery > 99.9%; 0 silent drops; failures alerted ≤ 5 min | PAC-AC-P04-08, PAC-SL-23 |
| G6 | Atomic tenant provisioning < 15 min; RLS isolation verified; 100% audit; cross-tenant reads denied & logged without grants | PAC-AC-P20-01/03, PAC-SL-51/60/61 |
| G7 | No P0/P1 open defects; UAT sign-off by radiologist, technologist, PACS administrator | PRD §2.3 |

---

## 3. MVP Epics & Sprint-Sized Work Items

> Work items sized ≤ 3 dev-days (2–4 per sprint per engineer). Story/AC/UI/SL IDs reference the PACS requirement docs. Backend = schema+API; Frontend = UI; Integration = DICOM/DICOMweb/HL7.

### E-PAC-01 · Platform Foundation (Platform squad — shared with RIS release)
**Source:** PAC-US-P19-01/02, PAC-US-P20-01/02; `RBAC_matrix_spec.md`; `pacs-ris-schema.sql` §15–17; `pacs-ris-multitenancy.md` §4–7.
Reuse from `RIS/RELEASE_PLAN.md` E-RIS-01: auth, tenant middleware, `provision_tenant()`, audit pipeline, user/role UI, metering.
> **Task-level detail (Sprint 1):** `requrements/sprint1_platform_foundation_detail.md` — task IDs S1-01…S1-29 with owners, dev-day estimates, dependency graph, and acceptance checks (shared with E-RIS-01).

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | RBAC seed: permissions, roles, role_permissions (incl. PACS roles: RADIOLOGIST, TELERADIOLOGIST, TECHNOLOGIST, PACS_ADMIN, IMAGING_INFORMATICS, DEPARTMENT_MANAGER, REFERRING_PHYSICIAN, ED_PHYSICIAN) + `@requires_permission` | M | Seed matches `RBAC_matrix_spec.md` §8; unit tests |
| 2 | PACS-specific permission surface: `VIEWER_READ`, `STUDY_READ`, `FILE_*`, `STUDY_EXPORT`, `STORAGE_ADMIN` wired to endpoints | M | Endpoint→permission map (§7) verified by tests |
| 3 | Object-storage tenant-prefixed key policy (`s3://vna/{tenant_code}/{facility_id}/…`) enforced in upload path | M | Cross-tenant key writes impossible |
| 4 | Storage quota + metering hooks (`STUDIES_STORED`, `WADO_BYTES`, `API_CALLS`, `MWL_QUERIES`) | M | PAC-AC-P20-02; metering matches usage |
| 5 | Atomic provisioning: PACS seed data (modalities, retention defaults, AE registry) added to `provision_tenant()` | M | PAC-AC-P20-01; rollback leaves no partial tenant |
| 6 | Audit completeness for view/retrieve/export/delete/share/access events | M | 100% of events; PAC-SL-60 |

**Epic exit:** G6 passes in a staging tenant; platform foundations shared with RIS/EMR.

### E-PAC-02 · Ingestion Gateway (Integration + Backend)
**Source:** PAC-US-P02-03/05, PAC-US-P04-01/05; PAC-WF1; schema §6 (`studies`, `series`, `instances`, `dicom_transactions`); `docs/specs/uploads_design.md`.
> **Task-level detail (Sprint 2):** `requrements/sprint2_ingestion_interface_detail.md` — task IDs S2-01…S2-30 with owners, dev-day estimates, dependency graph, and acceptance checks (shared with E-RIS-02).

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | Modality registry + AE-title/IP allow-list auth (per tenant) | M | PAC-AC-P04-01; unregistered AE rejected & logged |
| 2 | DIMSE C-STORE SCP + DICOMweb STOW-RS receiver | M | Test modality accepted on both protocols |
| 3 | DICOM parser → metadata index (patient/accession/SOP class) | M | Study retrievable < 5 min after C-STORE (PAC-SL-20) |
| 4 | Validation + duplicate detection (`200 {duplicate: true}`) | M | PAC-AC-P02-03 |
| 5 | Exception/orphan worklist (no accession, mismatched patient) | M | PAC-AC-P04-05; 0 silent drops (PAC-SL-22) |
| 6 | Redo/add-series append to correct accession | M | PAC-AC-P02-05 |

**Epic exit:** G1 ingestion path; PAC-AC-P02-03/05, P04-01/05.

### E-PAC-03 · MWL/MPPS & Acquisition Feedback (Integration)
**Source:** PAC-US-P02-01/04; PAC-WF1; schema `worklist_entries`, `mpps_events`; `docs/specs/worklist_design.md`.
> **Task-level detail (Sprint 3):** `requrements/sprint3_mwl_archive_detail.md` — task IDs S3-01…S3-24 with owners, dev-day estimates, dependency graph, and acceptance checks (shared with E-PAC-04).

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | MWL SCP (DICOM C-FIND) serving scheduled entries from RIS | M | PAC-AC-P02-01; query < 1 s p95 (PAC-SL-14) |
| 2 | MPPS N-CREATE/N-SET consumer → status (IN_PROGRESS/COMPLETED/DISCONTINUED) + RIS echo | M | PAC-AC-P02-04; board updates without manual entry |
| 3 | Upload/ingest status panel (per-series progress, success/failure, retry) | M | PAC-UI-23 parity with `uploads_design.md` |
| 4 | MPPS mismatch (wrong accession) → exception worklist, never dropped | M | PAC-AC-P02-04 (mismatch case) |
| 5 | Query-count metering hook (`MWL_QUERIES`) | D | Metering accurate |

**Epic exit:** G2; PAC-AC-P02-01/04.

### E-PAC-04 · Tiered Archive & Storage Commitment (Backend/Storage)
**Source:** PAC-US-P02-02, PAC-US-P04-03/04; PAC-WF5; schema `storage_objects`, `storage_commitments`; `pacs-ris-multitenancy.md` §4.
> **Task-level detail (Sprint 3):** `requrements/sprint3_mwl_archive_detail.md` — task IDs S3-01…S3-24 with owners, dev-day estimates, dependency graph, and acceptance checks (shared with E-PAC-03).

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | Object storage layer: S3-compatible, tenant-prefixed, tiered (hot/warm/cold) | M | Tier keys immutable; retrieval per PAC-SL-40/41/42 |
| 2 | Storage Commitment engine: validate → commit → N-EVENT success; failure path returns failure | M | PAC-AC-P02-02; scanner cache not purged on failure (PAC-SL-15/21) |
| 3 | Retention policy engine (5–30+ yr, pediatric) + legal-hold override, dry-run before purge | M | PAC-AC-P04-03; 0 accidental purges (PAC-SL-43) |
| 4 | Quota tracking + 75/90% alerts via notification subsystem | M | PAC-AC-P04-04; hard-stop configurable (PAC-SL-45) |
| 5 | ILM lifecycle transitions + WORM/immutable archive | D | PAC-SL-44 |

**Epic exit:** G1 (SC accuracy) + G4 (retention/quota); PAC-AC-P02-02, P04-03/04.

### E-PAC-05 · DICOMweb Gateway & Progressive Retrieval (Backend + Viewer Frontend)
**Source:** PAC-US-P01-08/10; PAC-WF2/WF7; `research/pacs-ris-viewer-integration-spec.md` §4–5; schema §6.
> **Task-level detail (Sprint 4):** `requrements/sprint4_dicomweb_viewer_detail.md` — task IDs S4-01…S4-26 with owners, dev-day estimates, dependency graph, and acceptance checks (shared with E-PAC-06).

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | QIDO-RS study/series query API (filters, pagination, `total`) | M | PAC-SL-16 (< 500 ms p95) |
| 2 | WADO-RS metadata + full-frame retrieval | M | PAC-SL-17 (< 1 s p95) |
| 3 | Frame-level WADO-RS (progressive/partial retrieval) | M | PAC-AC-P01-10; first frames < 3 s on multi-GB studies |
| 4 | DICOMweb auth: IHE IUA/OAuth2 token gate on all routes | M | Token-only access; no PHI in URLs |
| 5 | FHIR R4 `ImagingStudy` read endpoint (MVP read-only) | D | Conformance smoke tests |

**Epic exit:** G3 (retrieval path); PAC-AC-P01-10.

### E-PAC-06 · Reading Worklist & Viewer (Frontend — radiology path)
**Source:** PAC-US-P01-01/02/06/07/08/09; PAC-WF2; PAC-UI-08…22 (MVP subset); `docs/specs/worklist_design.md`.
> **Task-level detail (Sprint 4):** `requrements/sprint4_dicomweb_viewer_detail.md` — task IDs S4-01…S4-26 with owners, dev-day estimates, dependency graph, and acceptance checks (shared with E-PAC-05).
Advanced tools (MPR/MIP/3D/fusion) and AI overlay are **v1.1/v2.0** per PRD §5.1.

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | Prioritized reading worklist (STAT > inpatient > outpatient), filters, server pagination | M | PAC-AC-P01-01; PAC-UI-08/09/10 |
| 2 | Viewer shell: study/series navigator, window/level presets, zoom/pan, cine | M | PAC-AC-P01-04 (MVP subset); PAC-UI-16/19 |
| 3 | Hanging protocols: auto-apply per anatomy/modality, per-user override, saved | M | PAC-AC-P01-02; PAC-UI-14 |
| 4 | First-frame < 3 s + explicit loading/error-with-retry states (never blank viewport) | M | PAC-AC-P01-08; PAC-UI-20 |
| 5 | WIP preservation (open study, draft state) across sessions/devices | D | PAC-AC-P01-09 |
| 6 | Critical-finding flag + tracked notification + key-image bookmark | M | PAC-AC-P01-06/07; PAC-UI-13/17 |

> **Deviation note (item 6):** PRD §5.1 phases "critical results" to v1.1, but the on-site radiologist critical-flag + acknowledgment loop is included in MVP because PAC-US-P01-06 is **M**-priority and the PRD §2.3 reading-path gate requires "critical flag tracked to acknowledgment". Key-image bookmarking (PAC-US-P01-07, **D**) rides along in the same item. The teleradiology critical *callback* (PAC-US-P03-04) remains v1.1.
| 7 | Keyboard-first shortcuts + WCAG 2.1 AA pass (PAC-UI-03/05) | M | Accessibility audit green |

**Epic exit:** G3; PAC-AC-P01-01/02/06/07/08.

### E-PAC-07 · PACS Admin Console (Frontend)
**Source:** PAC-US-P04-02/04/05, PAC-US-P19-01; PAC-UI-26…32; `docs/specs/tenants_design.md`, `docs/specs/audit-logs_design.md`.
> **Task-level detail (Sprint 5):** `requrements/sprint5_admin_monitoring_detail.md` — task IDs S5-01…S5-22 with owners, dev-day estimates, dependency graph, and acceptance checks (shared with E-PAC-08).

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | Modality registry UI (AE title, IP/host, status online/offline, enable/disable) | M | PAC-UI-26 |
| 2 | Queue monitor (depth, stuck-message detection, one-click retry/drain) | M | PAC-UI-28; PAC-AC-P04-02 partial |
| 3 | Storage dashboard (usage vs. quota color bar, tier breakdown, growth trend) | M | PAC-UI-29; PAC-AC-P19-01 |
| 4 | Retention policy editor + legal-hold toggles + dry-run of purge | M | PAC-UI-30 |
| 5 | Exception/orphan worklist UI (reason, mismatch highlight, merge/reassign) | M | PAC-UI-31; PAC-AC-P04-05 |
| 6 | Audit log viewer (structured columns, filters, CSV export, cursor pagination) | M | PAC-UI-32 per `audit-logs_design.md` |
| 7 | Routing rules builder (source → destination, precedence, dry-run) | D | PAC-UI-27 |

**Epic exit:** G4; admin console UAT with PACS administrator.

### E-PAC-08 · Interface Health, Monitoring & Alerting (Integration + Ops)
**Source:** PAC-US-P04-08; PAC-SL-23; schema §9 (`interface_endpoints`, `interface_events`).
> **Task-level detail (Sprint 5):** `requrements/sprint5_admin_monitoring_detail.md` — task IDs S5-01…S5-22 with owners, dev-day estimates, dependency graph, and acceptance checks (shared with E-PAC-07).

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | DICOM/HL7/MPPS interface event capture (queues, errors, modality online/offline) | M | Events persisted with timestamps |
| 2 | Interface health dashboard (queues, failures, modality status, drill-down) | M | PAC-AC-P04-08; `INTERFACE_MONITOR` |
| 3 | ≤ 5-min alerting on interface failure (severity events → notification) | M | PAC-SL-23; 0 silent drops |
| 4 | Conformance lab harness (C-STORE/MWL/MPPS test set) for modality onboarding | D | G5 evidence; repeatable scripts |

**Epic exit:** G5; PAC-AC-P04-08.

### E-PAC-09 · Dashboards & Metering (Backend + Frontend)
**Source:** PAC-US-P05-01, PAC-US-P08-01, PAC-US-P19-01, PAC-US-P20-02; PAC-UI-34/35/38.
> **Task-level detail (Sprint 6):** `requrements/sprint6_dashboards_ops_detail.md` — task IDs S6-01…S6-26 with owners, dev-day estimates, dependency graph, and acceptance checks (shared with E-PAC-10).

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | Metering pipeline (studies stored, WADO bytes/egress, API calls) → `usage_metering` | M | PAC-SL-50; 100% events captured |
| 2 | Tenant usage dashboard (usage vs. quota, tier breakdown, CSV export) | M | PAC-UI-34; PAC-AC-P19-01 |
| 3 | Invoice/billing view (plan + overage lines, period, drill to usage) | M | PAC-UI-35; PAC-AC-P20-02 |
| 4 | KPI dashboards (retrieval time, TAT by priority, backlog, utilization) with drill-down | M | PAC-AC-P05-01, P08-01; refresh ≤ 5 min |
| 5 | Scheduled dashboard export for department reporting | D | PAC-AC-P08-01 (CSV matches) |

**Epic exit:** G6 (metering accuracy); PAC-AC-P05-01, P08-01, P20-02.

### E-PAC-10 · DR, Availability & Security Hardening (Ops/Platform)
**Source:** PAC-US-P04-07; PAC-WF9; PAC-SL-01/03/04.
> **Task-level detail (Sprint 6):** `requrements/sprint6_dashboards_ops_detail.md` — task IDs S6-01…S6-26 with owners, dev-day estimates, dependency graph, and acceptance checks (shared with E-PAC-09).

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | Edge cache for active studies (reads continue during cloud outage) | D | PAC-AC-P04-07 partial; PAC-SL-03 |
| 2 | Ingestion buffering during outage (no data loss window > RPO) | M | PAC-SL-04 |
| 3 | Failover runbook + quarterly DR drill automation with documented evidence | M | PAC-AC-P04-07; RTO ≤ 4 h |
| 4 | 99.9% availability SLO wiring + uptime dashboard + P1/P2 response SLAs | M | PAC-SL-01/02 |
| 5 | Security test: RLS isolation audit, cross-tenant denial path (0 grants → denied & logged), CVE scan | M | PAC-SL-61/63 |

**Epic exit:** G6/G7; quarterly DR drill documented.

---

## 4. Sprint Roadmap (MVP, 2-week sprints)

> **Consolidated view:** `requrements/pacs_consolidated_sprint_roadmap.md` maps this S1–S12 roadmap onto the seven task-level sprint detail docs (Sprint 1–7) with dependencies, capacity, and gate checkpoints.

| Sprint | Focus (epics) | Key milestone |
| :-: | :--- | :--- |
| S1–S2 | E-PAC-01 (platform foundation) | Login + RBAC + tenant isolation green; atomic provisioning incl. PACS seed |
| S3 | E-PAC-02 (ingestion gateway) | C-STORE from test modality accepted & indexed |
| S4 | E-PAC-02 (orphans/dupes) + E-PAC-03 (MWL/MPPS) | Scanner pulls MWL; MPPS updates status |
| S5 | E-PAC-04 (tiered archive/SC) | Storage Commitment returned — "safe to purge" |
| S6 | E-PAC-05 (DICOMweb gateway) | QIDO/WADO serving; frames stream progressively |
| S7 | E-PAC-06 (viewer) | Study opens in viewer < 3 s |
| S8 | E-PAC-06 (worklist/hanging/critical) + E-PAC-07 (admin start) | Reading path UAT-ready |
| S9 | E-PAC-07 (admin console) + E-PAC-08 (interface monitoring) | Admin console + health dashboard live |
| S10 | E-PAC-08 (alerting) + E-PAC-09 (dashboards) | ≤ 5-min alerts; KPI dashboards |
| S11 | E-PAC-09 (invoices) + E-PAC-10 (DR/security) | Invoices match metering; failover runbook |
| S12 | Hardening: UAT, performance (PAC-SL-10/11), security test, DR drill | MVP exit gates G1–G7 |

> **Task-level detail (Sprint 7, hardening):** `requrements/sprint7_hardening_detail.md` — task IDs S7-01…S7-22 with owners, dev-day estimates, dependency graph, and acceptance checks for UAT sign-off, performance, security test, DR drill, and the consolidated G1–G7 exit-gate package.

> v1.1/v2.0 epic-level backlog (post-MVP): **Advanced viewer tools** (PAC-US-P01-04 full: MPR/MIP/3D/cine/fusion/measurements), **Priors prefetch** (PAC-WF3, PAC-AC-P01-03, PAC-SL-24), **Teleradiology** (PAC-US-P03-01/02/04/05 — token sessions + `cross_tenant_grants_design.md`), **Cross-facility priors** (PAC-US-P03-03, CTG-AC-01…07), **Export CD/XDS-I.b/anonymized** (PAC-US-P04-06), **AI result ingestion** (PAC-US-P01-05, PAC-WF6, PRD §3 gates), **Migration tooling** (PAC-US-P04-09), **UPS-RS AI dispatch + SMART on FHIR/FHIRcast** (PAC-US-P06-01, PAC-AC-P06-01), **Patient imaging delivery** (XDS-I.b), **Responsive viewer** (PAC-US-P06-03), **QC + specialty workflows** (PAC-US-P02-06/07).

---

## 5. Critical Path & Dependencies

```
Platform Foundation (E-PAC-01) ──► Ingestion Gateway (E-PAC-02) ──► Tiered Archive/SC (E-PAC-04) ──► DICOMweb (E-PAC-05) ──► Viewer (E-PAC-06)
                                                                          │
                                              MWL/MPPS (E-PAC-03) ◀── RIS order feed (external)
                                                                          │
                                              Admin Console (E-PAC-07) ◀── (ops surface for all epics)
                                              Interface Monitoring (E-PAC-08) ◀── (instruments all epics)
```

- **Blocking:** E-PAC-02 before E-PAC-04/05; E-PAC-04 before E-PAC-05 (retrieval needs committed storage); E-PAC-05 before E-PAC-06 (viewer consumes DICOMweb); E-PAC-01 before everything (shared auth/RBAC/audit/provisioning).
- **Parallelizable:** E-PAC-03 ∥ E-PAC-08 (both consume interface events); E-PAC-07 ∥ E-PAC-06 once DICOMweb exists; E-PAC-09 ∥ E-PAC-10 in the last phase.
- **External:** modality conformance statements (C-STORE/MWL/MPPS test set), RIS MWL feed + MPPS echo (RIS release — coordinate), EMR ORU/FHIR report delivery (v1.1, EMR release), VNA/XDS-I.b endpoints (v1.1).
- **Shared with RIS/EMR releases:** E-PAC-01 platform foundation, audit viewer, notification subsystem, interface engine patterns, worklist engine — coordinate to avoid divergence.

---

## 6. Definition of Done (per work item)

- Backend: schema migration reviewed; API behind `@requires_permission`; Pydantic validation; unit tests green; audit event emitted where applicable.
- Frontend: Ant Design conventions, design tokens, WCAG 2.1 AA, `tsc --noEmit` + `vite build` clean.
- DICOM/Integration: conformance verified in lab (C-STORE/MWL/MPPS); exception queue covered; Storage Commitment success/failure semantics verified; RLS cross-tenant denial tested.
- Acceptance: the item's PAC-AC-* criteria pass in staging; traceability link updated.
- No P0/P1 defects open at sprint close.

---

## 7. Risks & Watch Items

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| Storage Commitment correctness (premature purge) | PAC-SL-21 SC accuracy | SC validation suite; failure path never signals success; conformance lab |
| First-frame latency on multi-GB studies | PAC-SL-10/11 | Frame-level WADO-RS, edge cache, progressive render acceptance (PAC-AC-P01-10) |
| Interface fragility (modality firmware breaks MWL/MPPS) | PAC-SL-23 delivery | Interface lab, ≤ 5-min alerting, exception queue, conformance harness |
| Cross-tenant PHI incident (v1.1 teleradiology/priors) | PAC-SL-61 | Explicit grants + RLS OR-clause + `cross_tenant.denied` audit; quarterly RLS audit |
| Retention purge regression | PAC-SL-43 | Dry-run before purge; legal-hold test suite; 0 accidental purges |
| Legacy migration data loss | PAC-SL-22 | Count reconciliation 100% + 1–2% radiologist sample validation |
| Bandwidth/egress cost at multi-site WAN | PAC-SL-50 | Edge caching, tiering, prefetch policies; WADO bytes metered |
| Radiologist adoption resistance | PAC-SL-30 TAT + UAT | Superusers, hanging-protocol libraries, early involvement, UAT sign-off |
| Scope creep into RIS/EMR domains | Non-goals (PRD §2.4) | PACS stores/distributes pixels; never schedules, charts, or bills |
