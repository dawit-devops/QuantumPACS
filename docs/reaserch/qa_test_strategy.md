# QA & Test Strategy — pytest Test-Case Catalog

**Document:** cross-cutting (PACS-first, platform-wide) · **Version:** 1.0 · **Date:** 2026-08-04
**Sources:** `requrements/PACS/06_acceptance_criteria.md` (PAC-AC-*), `requrements/PACS/05_metrics_and_slas.md` (PAC-SL-*), `requrements/PACS/RELEASE_PLAN.md` (§2 gates G1–G7), `requrements/pacs_consolidated_sprint_roadmap.md` (sprint ↔ gate mapping), `requrements/PACS/go-live-checklist.md` (cutover execution)
**Method:** pytest — layered unit / integration / E2E / performance / security / DR suites, each test mapped to a named acceptance criterion or SLA.

> **One-line rule:** every **MVP-scope** PAC-AC-* has a named pytest test; every MVP-scope PAC-SL-* has a measured assertion; every gate G1–G7 is verified by a defined test set, and the same set is runnable at cutover via the go-live checklist. v1.1/v2.0 and tenant-KPI ACs/SLAs are tracked in §3.7 (deferred catalog).

---

## 1. Purpose & Scope

This document turns the PACS acceptance criteria and SLAs into an **executable, engineer-ready test strategy**:

1. **Test-case catalog** — a named pytest test for each acceptance criterion and SLA, with layer, fixtures, markers, owning sprint, and the exit gate it verifies.
2. **Fixture & data strategy** — the reusable test infrastructure (multi-tenant fixture, DICOM conformance set, modality simulator, freezegun time control, metering capture).
3. **Markers & CI gates** — how the suite is sliced by runtime tier and wired into the sprint cadence (PR → nightly → pre-release), with coverage targets.
4. **Traceability** — every G1–G7 gate and every PAC-SL assertion lists the tests that prove it, mirroring the go-live checklist evidence artifacts.

The same catalog pattern extends to RIS (`RIS-AC-*` / `RIS-SL-*`) and EMR (`EMR-AC-*` / `EMR-SL-*`) — this document ships the PACS slice now and is the template for the other two surfaces.

**Scope out (explicitly not covered here):** UI pixel tests and manual UAT script authoring (see `sprint7_hardening_detail.md` S7-01…S7-05 for the UAT pack); it covers the API/backend/service layer that the UI consumes.

---

## 2. Test Pyramid & Layering

| Layer | What it exercises | Typical runtime | Where it runs | Example |
| :--- | :--- | :--- | :--- | :--- |
| **L1 Unit** | Single function/class in isolation; DB mocked or in-memory | < 1 s each | PR gate | Routing-rule precedence function, SC status machine |
| **L2 Integration** | Service + real Postgres (transaction-rolled) + real object-storage stub | seconds | PR + nightly | Ingestion pipeline: C-STORE → metadata index → tier placement |
| **L3 E2E (API contract)** | Full HTTP/DICOM surface against a test tenant | minutes | Nightly | QIDO-RS query → WADO-RS metadata → frames, end-to-end |
| **L4 Performance** | Latency SLAs under synthetic load | 10s of minutes | Nightly + pre-release | PAC-SL-10/11/16/17 p95 assertions |
| **L5 Security** | RLS isolation, RBAC, cross-tenant denial, audit completeness | minutes | Nightly + pre-release | PAC-AC-P20-03, PAC-SL-60/61/62/63 |
| **L6 DR / availability** | Failover, RTO/RPO, buffered ingestion, edge reads | hours (drill) | Pre-release (quarterly drill) | PAC-AC-P04-07, PAC-SL-01/03/04 |
| **L7 UAT** | Per-persona scripted scenarios; human sign-off | scheduled | Sprint 7 (S7-01…S7-05) | G7 UAT pack |

Strategy: **L1/L2 at every commit, L3–L5 nightly, L6 quarterly, L7 at the hardening sprint** — matching the sprint gate pre-checks in `pacs_consolidated_sprint_roadmap.md` §4.

---

## 3. Test-Case Catalog (pytest)

### 3.0 Test-ID conventions

- Test IDs: `T-<AC-ID>` (e.g., `T-PAC-AC-P01-01`) or `T-SL-<SLA-ID>` (e.g., `T-SL-16`) for SLA performance assertions.
- pytest function names: `test_<ac_id_lower>_<scenario>` (e.g., `test_pac_ac_p01_01_priority_sort_order`), per the AAA pattern (Arrange / Act / Assert).
- QA ownership: each test row lists owning **sprint**; the sprint-doc `✓` check column (S1-xx…S7-xx) tracks the named owner at delivery time.

### 3.1 Radiologist reading path (PAC-P01) → gates G3, G7

| Test ID | pytest function | AC / SLA | Layer | Key fixtures | Markers | Sprint | Gate |
| :--- | :--- | :--- | :-: | :--- | :--- | :-: | :-: |
| T-PAC-AC-P01-01 | test_pac_ac_p01_01_priority_sort_order | PAC-AC-P01-01 | L3 | fx_worklist, fx_tenant_two_facilities | e2e | 4 | G3 |
| T-PAC-AC-P01-01b | test_pac_ac_p01_01_pagination_server_total | PAC-AC-P01-01 (server `total`) | L3 | fx_worklist_300 | e2e | 4 | G3 |
| T-PAC-AC-P01-02 | test_pac_ac_p01_02_hanging_protocol_default | PAC-AC-P01-02 | L2 | fx_viewer_ctx, fx_hanging_lib | integration | 4 | G3 |
| T-PAC-AC-P01-06 | test_pac_ac_p01_06_critical_flag_notify_ack | PAC-AC-P01-06 | L2 | fx_notifier_mock | integration | 4 | — |
| T-PAC-AC-P01-07 | test_pac_ac_p01_07_key_image_in_report | PAC-AC-P01-07 | L2 | fx_report_ctx | integration | 4 | — |
| T-PAC-AC-P01-08 | test_pac_ac_p01_08_first_frame_under_3s | PAC-AC-P01-08 | L4 | fx_viewer_ctx, fx_conformance_ct | perf | 4/7 | G3 |
| T-PAC-AC-P01-09 | test_pac_ac_p01_09_wip_restore | PAC-AC-P01-09 | L2 | fx_worklist, fx_auth_tokens | integration | 4 | — |
| T-PAC-AC-P01-10 | test_pac_ac_p01_10_progressive_frames_2gb | PAC-AC-P01-10 | L4 | fx_viewer_ctx, fx_conformance_multi_gb | perf | 4/7 | G3 |
| T-SL-10 | test_sl_10_active_study_load_p95 | PAC-SL-10 | L4 | fx_benchmark_client | perf | 7 | G3 |
| T-SL-11 | test_sl_11_progressive_first_frame_p95 | PAC-SL-11 | L4 | fx_benchmark_client | perf | 7 | G3 |

### 3.2 Acquisition path (PAC-P02) → gates G1, G2

| Test ID | pytest function | AC / SLA | Layer | Key fixtures | Markers | Sprint | Gate |
| :--- | :--- | :--- | :-: | :--- | :--- | :-: | :-: |
| T-PAC-AC-P02-01 | test_pac_ac_p02_01_mwl_autofill | PAC-AC-P02-01 | L3 | fx_modality, fx_mwl | e2e | 3 | G2 |
| T-PAC-AC-P02-01b | test_pac_ac_p02_01_mwl_empty_result_message | PAC-AC-P02-01 (empty) | L2 | fx_modality | integration | 3 | G2 |
| T-PAC-AC-P02-02 | test_pac_ac_p02_02_sc_success_before_purge | PAC-AC-P02-02 | L3 | fx_modality, fx_storage_commit | e2e | 3 | G1 |
| T-PAC-AC-P02-02b | test_pac_ac_p02_02_sc_failure_no_purge | PAC-AC-P02-02 (failure) | L3 | fx_modality, fx_storage_commit | e2e | 3 | G1 |
| T-PAC-AC-P02-03 | test_pac_ac_p02_03_retry_and_duplicate_flag | PAC-AC-P02-03 | L3 | fx_upload, fx_modality | e2e | 2 | G1 |
| T-PAC-AC-P02-04 | test_pac_ac_p02_04_mpps_state_transitions | PAC-AC-P02-04 | L3 | fx_modality, fx_mpps | e2e | 3 | G2 |
| T-PAC-AC-P02-04b | test_pac_ac_p02_04_mpps_mismatch_exception | PAC-AC-P02-04 (mismatch) | L2 | fx_modality, fx_exception_queue | integration | 3 | G2 |
| T-PAC-AC-P02-05 | test_pac_ac_p02_05_redo_appends_study | PAC-AC-P02-05 | L2 | fx_modality | integration | 3 | G1 |
| T-PAC-AC-P02-07 | test_pac_ac_p02_07_specialty_series_preserved | PAC-AC-P02-07 | L2 | fx_modality, fx_conformance_us | integration | 3 | G1 |
| T-SL-14 | test_sl_14_mwl_query_p95 | PAC-SL-14 | L4 | fx_modality, fx_mwl_loaded | perf | 7 | G2 |
| T-SL-15 | test_sl_15_sc_ack_under_60s | PAC-SL-15 | L4 | fx_modality | perf | 7 | G1 |
| T-SL-20 | test_sl_20_indexed_under_5min | PAC-SL-20 | L4 | fx_modality | perf | 7 | G1 |

### 3.3 Teleradiology & cross-tenant (PAC-P03 / PAC-AC-P20-03) → gate G6

| Test ID | pytest function | AC / SLA | Layer | Key fixtures | Markers | Sprint | Gate |
| :--- | :--- | :--- | :-: | :--- | :--- | :-: | :-: |
| T-PAC-AC-P03-01 | test_pac_ac_p03_01_granted_multi_facility_session | PAC-AC-P03-01 | L3 | fx_tenant_two_facilities, fx_cross_tenant_grant | e2e | 6/7 | G6 |
| T-PAC-AC-P03-01b | test_pac_ac_p03_01_denied_facility_audited | PAC-AC-P03-01 (denied) | L3 | fx_tenant_two_facilities | e2e | 6 | G6 |
| T-PAC-AC-P03-03 | test_pac_ac_p03_03_cross_facility_priors | PAC-AC-P03-03 | L3 | fx_tenant_two_facilities, fx_cross_tenant_grant | e2e | 6 | G6 |
| T-PAC-AC-P03-05 | test_pac_ac_p03_05_report_routes_ordering_facility | PAC-AC-P03-05 | L2 | fx_hl7_client, fx_oru | integration | 6 | G6 |
| T-PAC-AC-P20-03 | test_pac_ac_p20_03_audited_cross_tenant_read | PAC-AC-P20-03 | L3 | fx_tenant_two_facilities | e2e | 6 | G6 |
| T-SL-25 | test_sl_25_cross_tenant_auth_under_1s_audited | PAC-SL-25 | L4 | fx_tenant_two_facilities | perf | 7 | G6 |

### 3.4 PACS administration (PAC-P04) → gates G1, G4, G5

| Test ID | pytest function | AC / SLA | Layer | Key fixtures | Markers | Sprint | Gate |
| :--- | :--- | :--- | :-: | :--- | :--- | :-: | :-: |
| T-PAC-AC-P04-01 | test_pac_ac_p04_01_unregistered_ae_rejected_logged | PAC-AC-P04-01 | L2 | fx_modality, fx_ae_allowlist | integration | 2 | G1 |
| T-PAC-AC-P04-02 | test_pac_ac_p04_02_routing_precedence_deterministic | PAC-AC-P04-02 | L1 | fx_routing_rules | unit | 5 | — |
| T-PAC-AC-P04-03 | test_pac_ac_p04_03_legal_hold_blocks_purge_audited | PAC-AC-P04-03 | L2 | fx_retention, fx_legal_hold | integration | 3/5 | G4 |
| T-PAC-AC-P04-04 | test_pac_ac_p04_04_quota_alerts_75_90 | PAC-AC-P04-04 | L2 | fx_quota, fx_admin_user | integration | 3/5 | G4 |
| T-PAC-AC-P04-05 | test_pac_ac_p04_05_exception_reconcile_24h | PAC-AC-P04-05 | L2 | fx_exception_queue | integration | 2/5 | G5 |
| T-PAC-AC-P04-07 | test_pac_ac_p04_07_dr_edge_reads_buffered_ingest | PAC-AC-P04-07 | L6 | fx_edge_cache, fx_region_down | dr | 6/7 | G6 |
| T-PAC-AC-P04-07b | test_pac_ac_p04_07_rto_rpo_evidence | PAC-AC-P04-07 (RTO/RPO) | L6 | fx_region_down | dr | 7 | G6 |
| T-PAC-AC-P04-08 | test_pac_ac_p04_08_alert_within_5min | PAC-AC-P04-08 | L2 | fx_interface_health, fx_alert_mock | integration | 2/5 | G5 |
| T-SL-43 | test_sl_43_zero_accidental_purges | PAC-SL-43 | L2 | fx_retention | integration | 7 | G4 |
| T-SL-45 | test_sl_45_quota_alert_thresholds | PAC-SL-45 | L2 | fx_quota | integration | 7 | G4 |
| T-SL-23 | test_sl_23_delivery_999_alerts_5min | PAC-SL-23 | L4 | fx_interface_health | perf | 7 | G5 |

### 3.5 Informatics, manager, tenant & super admin (PAC-P05/P08/P19/P20) → gates G6, G7

| Test ID | pytest function | AC / SLA | Layer | Key fixtures | Markers | Sprint | Gate |
| :--- | :--- | :--- | :-: | :--- | :--- | :-: | :-: |
| T-PAC-AC-P05-01 | test_pac_ac_p05_01_kpi_refresh_drilldown | PAC-AC-P05-01 | L2 | fx_kpi_agg | integration | 6 | — |
| T-PAC-AC-P08-01 | test_pac_ac_p08_01_manager_export_matches | PAC-AC-P08-01 | L2 | fx_kpi_agg | integration | 6 | — |
| T-PAC-AC-P19-01 | test_pac_ac_p19_01_usage_vs_quota_matches_metering | PAC-AC-P19-01 | L2 | fx_metering, fx_usage_capture | integration | 6 | G6 |
| T-PAC-AC-P19-02 | test_pac_ac_p19_02_role_change_token_bump | PAC-AC-P19-02 | L2 | fx_rbac, fx_auth_tokens | integration | 1 | G6 |
| T-PAC-AC-P20-01 | test_pac_ac_p20_01_provision_atomic_under_15min | PAC-AC-P20-01 | L3 | fx_provisioner | e2e | 1/7 | G6 |
| T-PAC-AC-P20-01b | test_pac_ac_p20_01_failed_provision_rolls_back | PAC-AC-P20-01 (rollback) | L2 | fx_provisioner_fail | integration | 1 | G6 |
| T-PAC-AC-P20-02 | test_pac_ac_p20_02_invoice_matches_metering | PAC-AC-P20-02 | L2 | fx_metering, fx_invoice | integration | 6 | G6 |
| T-SL-50 | test_sl_50_metering_accuracy_zero_variance | PAC-SL-50 | L2 | fx_metering | integration | 6/7 | G6 |
| T-SL-51 | test_sl_51_provisioning_under_15min | PAC-SL-51 | L4 | fx_provisioner | perf | 7 | G6 |

### 3.6 Performance & security SLAs (cross-cutting)

| Test ID | pytest function | AC / SLA | Layer | Key fixtures | Markers | Sprint | Gate |
| :--- | :--- | :--- | :-: | :--- | :--- | :-: | :-: |
| T-SL-01 | test_sl_01_availability_999_slo | PAC-SL-01 | L6 | fx_uptime_probe | dr | 6/7 | G6 |
| T-SL-02 | test_sl_02_incident_response_tiers | PAC-SL-02 | L6 | fx_oncall_roster | dr | 7 | G6 |
| T-SL-03 | test_sl_03_rto_4h | PAC-SL-03 | L6 | fx_region_down | dr | 7 | G6 |
| T-SL-04 | test_sl_04_rpo_60min | PAC-SL-04 | L6 | fx_region_down | dr | 7 | G6 |
| T-SL-16 | test_sl_16_qido_p95_500ms | PAC-SL-16 | L4 | fx_benchmark_client | perf | 4/7 | G3 |
| T-SL-17 | test_sl_17_wado_metadata_p95_1s | PAC-SL-17 | L4 | fx_benchmark_client | perf | 4/7 | G3 |
| T-SL-40/41/42 | test_sl_40_42_tier_retrieval_latency | PAC-SL-40/41/42 | L4 | fx_storage_tiers | perf | 7 | G3 |
| T-SL-60 | test_sl_60_audit_completeness_100pct | PAC-SL-60 | L3 | fx_audit_reader | e2e | 1/7 | G6 |
| T-SL-61 | test_sl_61_cross_tenant_isolation_zero_incidents | PAC-SL-61 | L3 | fx_tenant_two_facilities | e2e | 6/7 | G6 |
| T-SL-62 | test_sl_62_tls_aes256_at_rest | PAC-SL-62 | L5 | fx_crypto_probe | security | 7 | G6 |
| T-SL-63 | test_sl_63_cve_patch_window_72h | PAC-SL-63 | L5 | fx_cve_scan | security | 6/7 | G6 |

### 3.7 Deferred catalog (v1.1 / v2.0 & tenant-KPI — tracked, not MVP-tested)

These ACs/SLAs are **out of MVP scope** per `PACS/RELEASE_PLAN.md` (v1.1: advanced viewer tools, priors prefetch, teleradiology token sessions + cross-tenant grants, critical results, export CD/XDS-I.b, AI result ingestion; v2.0: SMART-on-FHIR referring-MD launch). Each gets a test when its epic enters the release; the row below is the backlog placeholder so traceability stays complete.

| AC / SLA | Deferred feature | Release | Test to add when epic starts |
| :--- | :--- | :--- | :--- |
| PAC-AC-P01-03 | Priors prefetch & one-click comparison | v1.1 | T-PAC-AC-P01-03 (fx_prefetch, fx_edge_cache) |
| PAC-AC-P01-04 | Diagnostic tools (MPR/MIP/3D/cine/fusion/measure) | v1.1 | T-PAC-AC-P01-04 (fx_viewer_ctx, fx_conformance_ct) |
| PAC-AC-P01-05 | AI results overlay accept/reject | v1.1 | T-PAC-AC-P01-05 (fx_ai_result) |
| PAC-AC-P02-06 | QC reject/redo flow | v1.1 | T-PAC-AC-P02-06 (fx_modality) |
| PAC-AC-P03-02, PAC-SL-12 | Teleradiology 25 Mbps streaming | v1.1 | T-PAC-AC-P03-02 (fx_conformance_500mb), T-SL-12 |
| PAC-AC-P03-04 | Critical callback escalation | v1.1 | T-PAC-AC-P03-04 (fx_notifier_mock) |
| PAC-AC-P04-06 | Audited export (CD/XDS-I.b) | v1.1 | T-PAC-AC-P04-06 (fx_export_ctx) |
| PAC-AC-P04-09 | Migration reconciliation | v1.1 | T-PAC-AC-P04-09 (fx_migration) |
| PAC-AC-P05-02 | Hanging-protocol library versioning | v1.1 | T-PAC-AC-P05-02 (fx_hanging_lib) |
| PAC-AC-P06-01/02/03, PAC-SL-13 | Referring-MD SMART launch, report delivery, responsive viewing | v2.0 | T-PAC-AC-P06-* (fx_smart_launch), T-SL-13 |
| PAC-AC-P07-01/02 | ED STAT prioritization & preliminary reads | v1.1 | T-PAC-AC-P07-* (fx_ed_ctx) |
| PAC-SL-05 | Planned-downtime windows | v1.1 | T-SL-05 (fx_uptime_probe) |
| PAC-SL-21 | SC accuracy (covered by T-PAC-AC-P02-02 at MVP) | MVP ✓ | (no separate test — asserted via P02-02) |
| PAC-SL-22 | Orphan rate < 0.5% / 24-h work | v1.1 metric | T-SL-22 (fx_exception_queue) |
| PAC-SL-24 | Prior availability ≥ 95% | v1.1 | T-SL-24 (fx_prefetch, fx_edge_cache) |
| PAC-SL-30…37 | Department KPIs (TAT, utilization, reject rate) | v1.1 dashboards | T-SL-30…37 (fx_kpi_agg) |
| PAC-SL-52 | Invoice delivery & disputes | v1.1 | T-SL-52 (fx_invoice) |

---

## 4. Fixture Library (conftest.py)

Reusable fixtures shared across the catalog; all DB-backed fixtures create their own tenant and roll back the transaction after each test (no shared state — test isolation per the pytest conventions).

| Fixture | Purpose | Used by |
| :--- | :--- | :--- |
| fx_auth_tokens | Signed OIDC/IUA tokens for a persona+role pair; token-version bump support | T-PAC-AC-P19-02, P01-09, P20-01 |
| fx_tenant_two_facilities | Two facilities in one tenant + one facility in a second tenant; RLS-clean data | T-PAC-AC-P03-01/03, P20-03, T-SL-61 |
| fx_cross_tenant_grant | Active `cross_tenant_grants` row (per `cross_tenant_grants_design.md`) | T-PAC-AC-P03-01/03 |
| fx_modality | Simulated DICOM modality with AE title + allow-listed IP | T-PAC-AC-P02-*, P04-01 |
| fx_upload | STOW-RS / C-STORE upload client with duplicate-detection hooks | T-PAC-AC-P02-03 |
| fx_storage_commit | Storage-Commitment engine client; injectable success/failure | T-PAC-AC-P02-02 |
| fx_mwl / fx_mpps | MWL C-FIND responder and MPPS N-CREATE/N-SET sender | T-PAC-AC-P02-01/04, T-SL-14 |
| fx_exception_queue | Orphan/exception worklist with `studies.status='QUARANTINED'` | T-PAC-AC-P02-04b, P04-05 |
| fx_conformance_ct / fx_conformance_us / fx_conformance_multi_gb | Deterministic DICOM conformance sets (CT chest, US cine, 2+ GB) from the S2-27/S3-21 harness | T-PAC-AC-P01-08/10, P02-07, T-SL-10/11 |
| fx_viewer_ctx | Zero-footprint viewer session over QIDO/WADO with hanging-protocol library | T-PAC-AC-P01-02/08/10 |
| fx_hanging_lib | Versioned hanging-protocol library (PAC-AC-P05-02) | T-PAC-AC-P01-02 |
| fx_report_ctx | Report draft/sign context with key-image binding | T-PAC-AC-P01-07 |
| fx_notifier_mock | Mocked notification/call-task gateway (monkeypatched) | T-PAC-AC-P01-06, P04-08 |
| fx_hl7_client / fx_oru | HL7 v2 ADT/ORM/ORU senders and message assertions | T-PAC-AC-P03-05 |
| fx_ae_allowlist | AE-title + IP allow-list registry per facility | T-PAC-AC-P04-01 |
| fx_routing_rules | `routing_rules` table seed + precedence resolver | T-PAC-AC-P04-02 |
| fx_retention / fx_legal_hold | Retention clocks per document type; legal-hold overrides (**freezegun** to advance clocks) | T-PAC-AC-P04-03, T-SL-43 |
| fx_quota | Quota meter with 75%/90% threshold crossing | T-PAC-AC-P04-04, T-SL-45 |
| fx_edge_cache / fx_region_down | Edge-cache object client + simulated cloud-region outage | T-PAC-AC-P04-07, T-SL-03/04/01 |
| fx_interface_health | Interface events + `last_heartbeat_at` / `is_resolved` capture | T-PAC-AC-P04-08, T-SL-23 |
| fx_metering / fx_usage_capture / fx_invoice | `usage_metering` capture + `tenant_invoices` reconciliation | T-PAC-AC-P19-01, P20-02, T-SL-50 |
| fx_provisioner / fx_provisioner_fail | Atomic tenant provisioning; injectable mid-transaction failure | T-PAC-AC-P20-01 |
| fx_rbac | Role/permission seed per `RBAC_matrix_spec.md` §4–§6 | T-PAC-AC-P19-02 |
| fx_benchmark_client | Locust/`pytest-benchmark` load driver for p95 assertions | T-SL-10/11/14/15/16/17/20 |
| fx_audit_reader | Tamper-evident audit log reader + completeness counter | T-SL-60 |
| fx_crypto_probe / fx_cve_scan | TLS/AES-256 config probe; CVE scan result reader | T-SL-62/63 |
| fx_worklist / fx_worklist_300 | Prioritized worklist view + a 300-study workload for server-`total` pagination | T-PAC-AC-P01-01/01b |
| fx_admin_user | PACS-admin / tenant-admin session with elevated role grants | T-PAC-AC-P04-04 |
| fx_alert_mock | Mocked alert-route (email/webhook) with delivery-time capture | T-PAC-AC-P04-08 |
| fx_kpi_agg | KPI aggregation over `v_order_lifecycle`-style read models | T-PAC-AC-P05-01, P08-01 |
| fx_mwl_loaded | Worklist pre-populated to a representative load for p95 queries | T-SL-14 |
| fx_storage_tiers | Hot/warm/cold tier placement + retrieval latency controls | T-SL-40/41/42 |
| fx_uptime_probe / fx_oncall_roster | Availability probe + incident-response roster | T-SL-01/02 |

**Time-dependent tests** use `freezegun` (`@freeze_time`) to control retention clocks (T-PAC-AC-P04-03), session expiry (T-PAC-AC-P19-02 token bump), and alert escalations without waiting in real time.

**Retry behavior tests** (T-PAC-AC-P02-03, P04-08) use `unittest.mock` `side_effect` sequences to model transient failures (fail twice, then succeed) and assert exact retry counts — per the pytest retry-pattern.

---

## 5. Markers & CI Gates

| Marker | Tier | Runs at | Purpose |
| :--- | :--- | :--- | :--- |
| `unit` (default) | L1 | every commit (PR) | Fast, isolated, no external deps |
| `integration` | L2 | PR + nightly | Real Postgres + stubbed storage |
| `e2e` | L3 | nightly | Full API/DICOM contract against a disposable test tenant |
| `perf` | L4 | nightly + pre-release | p95 latency assertions (PAC-SL-10…20) |
| `security` | L5 | nightly + pre-release | RLS/RBAC/audit/encryption assertions |
| `dr` | L6 | pre-release + quarterly drill | Failover, RTO/RPO, buffered ingestion |
| `slow` | any | nightly only (excluded from PR) | Aggregated runtime guard |
| `skip` / `xfail` | — | — | Not-yet-implemented / known-issue (P2/P3 backlog) |

**CI gate wiring (sprint cadence):**

| Gate | Command (CI) | Fails the build when |
| :--- | :--- | :--- |
| PR gate | `pytest -m "not perf and not dr and not slow"` | any L1/L2/L3 regression; coverage below target |
| Nightly | `pytest -m perf or security or e2e or slow` + `pytest -m integration` | any p95 SLA breach; isolation/audit breach |
| Pre-release (Sprint 7) | full suite + `pytest --cov --cov-fail-under` per §6 + DR drill | any gate G1–G7 red (mirrors go-live checklist) |
| Quarterly | DR drill (`-m dr`) + availability soak | RTO/RPO/99.9% evidence missing |

---

## 6. Coverage Targets

| Scope | Target | Note |
| :--- | :-: | :--- |
| Overall unit/integration | **≥ 80%** line, **≥ 75%** branch | `pytest --cov --cov-report=term-missing` |
| Critical paths (ingestion → index → retrieve; SC; RLS; metering) | **≥ 90%** | Explicitly measured per package |
| RLS-critical code (`app.facility_id` middleware, `NOBYPASSRLS` paths, cross-tenant grant checks) | **100%** of decision points | Mandatory — a missed branch is a PHI leak (PAC-SL-61) |
| SLA performance assertions | 100% of PAC-SL-* have a perf test | `perf` suite measures p95, not just smoke |

Coverage quality rule: **meaningful coverage, not just percentage** — every MVP-scope `PAC-AC-*` GIVEN/WHEN/THEN clause maps to ≥ 1 assertion; a clause with no test is flagged in the traceability table (§7) or the deferred catalog (§3.7).

---

## 7. Traceability — Gates → Tests (mirrors go-live-checklist.md)

| Gate | Criterion (release plan §2) | Proving tests | Evidence artifact (checklist) |
| :-: | :--- | :--- | :--- |
| **G1** | Ingestion < 5 min; SC 100% verifiable; 0 silent purges | T-PAC-AC-P02-02/02b/03/05, T-PAC-AC-P04-01, T-SL-20/15 | `G1_ingestion_evidence.md` |
| **G2** | MWL ≥ 98% auto; MPPS drives status | T-PAC-AC-P02-01/01b/04/04b, T-SL-14 | `G2_mwl_mpps_evidence.md` |
| **G3** | Study opens < 3 s p95; progressive on multi-GB | T-PAC-AC-P01-01/01b/02/08/10, T-SL-10/11/16/17/40-42 | `G3_viewer_evidence.md` |
| **G4** | Retention/legal-hold honored; quota 75/90% | T-PAC-AC-P04-03/04, T-SL-43/45 | `G4_storage_evidence.md` |
| **G5** | Interface delivery > 99.9%; alerts ≤ 5 min | T-PAC-AC-P04-05/08, T-SL-23 | `G5_interface_evidence.md` |
| **G6** | Provision < 15 min; RLS verified; 100% audit; cross-tenant denied & logged | T-PAC-AC-P20-01/01b/02/03, T-PAC-AC-P03-01/01b/03, T-PAC-AC-P19-01/02, T-SL-50/51/60/61/62/63/01/02/03/04/25 | `G6_security_evidence.md` |
| **G7** | No P0/P1 defects; UAT sign-off (3 personas) | UAT pack (S7-01…S7-05) + full suite green | `G7_uat_signoff.md` |

**Sprint handoff:** pre-checks are exercised at the sprint shown in the catalog (e.g., G1 pre-check tests run at Sprints 2–3), final verification at Sprint 7 — consistent with `pacs_consolidated_sprint_roadmap.md` §4.

---

## 8. Test Data & Environment Strategy

- **Deterministic DICOM sets** — the S2-27/S3-21 conformance-lab harness produces the CT-chest, US-cine, and multi-GB sets used by `fx_conformance_*`; checked into a fixtures bucket, never generated at runtime.
- **Disposable test tenants** — every L2+ suite provisions its own tenant (`fx_tenant_*`) and drops it after the run; never shares data across runs (test isolation).
- **PHI hygiene** — all synthetic demographics use the conformance-lab fake MRN/name pool; no production-derived data in any environment; viewer asserts "no PHI in URLs" (PAC-AC-P06-01) are part of the security suite.
- **Environments** — `test` (PR/nightly) and `staging` (pre-release, production-shaped per Sprint 7 §1); DR drill runs against staging with a documented region-down script.
- **Secrets** — test service keys from a vault-backed dev integration, never committed (matches `docs/specs/service-keys_design.md` conventions).

---

## 9. How to Run

```bash
# PR gate (fast)
pytest -m "not perf and not dr and not slow"

# Nightly
pytest -m "perf or security or e2e or slow"
pytest -m integration

# Pre-release (Sprint 7) with coverage gates
pytest --cov=app --cov-report=term-missing --cov-fail-under=80
pytest -m dr            # DR drill, staging

# Single SLA assertion
pytest tests/test_perf/test_sl_16_qido.py -m perf
```

pytest config lives in `pyproject.toml` / `pytest.ini`: markers registered (`unit integration e2e perf security dr slow`), `addopts = -ra --strict-markers`, and a rootdir `conftest.py` exposing the §4 fixture library.

---

## 10. Adoption Plan

| When | What lands | Evidence |
| :--- | :--- | :--- |
| Sprint 1 (platform) | fx_tenant_*, fx_auth_tokens, fx_provisioner, fx_rbac; T-PAC-AC-P20-01/19-02, T-SL-60 | G6 pre-check |
| Sprint 2–3 (ingestion/archive) | fx_modality, fx_upload, fx_storage_commit, fx_mwl/mpps, fx_retention; T-PAC-AC-P02-*, P04-03/04 | G1/G2/G4 pre-checks |
| Sprint 4 (DICOMweb/viewer) | fx_viewer_ctx, fx_conformance_*; T-PAC-AC-P01-*, T-SL-10/11/16/17 | G3 pre-check |
| Sprint 5 (admin/monitoring) | fx_interface_health, fx_routing_rules, fx_exception_queue; T-PAC-AC-P04-02/05/08 | G4/G5 pre-checks |
| Sprint 6 (dashboards/DR) | fx_metering, fx_edge_cache, fx_region_down; T-PAC-AC-P20-02/03, T-SL-50/01-04/61-63 | G6 pre-check |
| Sprint 7 (hardening) | Full suite + perf/security/DR + UAT pack; all G1–G7 final | G1–G7 evidence, go/no-go |

---

## Traceability

| Section | Source |
| :--- | :--- |
| §3 catalog | `PACS/06_acceptance_criteria.md` (PAC-AC-*), `PACS/05_metrics_and_slas.md` (PAC-SL-*) |
| §3 sprint/gate columns | `pacs_consolidated_sprint_roadmap.md` §4 |
| §5 CI gates | `pacs_consolidated_sprint_roadmap.md` §5; `sprint7_hardening_detail.md` §5 (DoD) |
| §7 gate evidence | `PACS/go-live-checklist.md` §3 |
| §8 conformance sets | `sprint2_ingestion_interface_detail.md` (S2-27), `sprint3_mwl_archive_detail.md` (S3-21) |
