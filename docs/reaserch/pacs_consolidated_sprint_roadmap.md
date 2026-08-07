# PACS — Consolidated Sprint Roadmap (Sprint Detail S1–S7 ↔ Release-Plan S1–S12)

**Version:** 1.0 · **Date:** 2026-08-04 · **Source:** `requrements/PACS/RELEASE_PLAN.md` (§4 roadmap, §2 gates) + `requrements/sprint1…sprint7_*_detail.md`
**Scope:** PACS MVP delivery program. This is the **single index** that maps every task-level sprint document onto the release-plan roadmap — sprint-to-sprint dependencies, capacity, and exit-gate checkpoints at a glance. Task-level detail lives in the linked sprint documents.

---

## 1. How the Mapping Works

The release plan schedules the MVP across **12 two-week sprints (S1–S12)**. The seven **sprint detail documents (Sprint 1–7)** are the executable refinements; each covers **one or two release-plan sprints** because consecutive release-plan sprints were merged where epics share a handoff:

| Sprint detail doc | Covers release-plan | Why merged |
| :--- | :--- | :--- |
| `sprint1_platform_foundation_detail.md` | S1–S2 | Platform foundation (E-PAC-01 + E-RIS-01) is one atomic epic |
| `sprint2_ingestion_interface_detail.md` | S3 | Ingestion (E-PAC-02) + HL7 interface (E-RIS-02) land in the same integration window |
| `sprint3_mwl_archive_detail.md` | S4–S5 | E-PAC-03 (MWL/MPPS) and E-PAC-04 (archive/SC) share the Storage-Commitment handoff |
| `sprint4_dicomweb_viewer_detail.md` | S6–S7 | Viewer consumes the DICOMweb gateway directly |
| `sprint5_admin_monitoring_detail.md` | S8–S9 | Admin console (E-PAC-07) surfaces existing backends; E-PAC-08 completes monitoring |
| `sprint6_dashboards_ops_detail.md` | S10–S11 | Final domain epics (E-PAC-09/10); much foundation already exists |
| `sprint7_hardening_detail.md` | S12 | Hardening / UAT / exit gates — the capstone verification sprint |

---

## 2. Master Roadmap

| Sprint detail | Tasks | Epics | Release-plan sprints | Focus | Key milestone | Gate checkpoint | Capacity (used / available) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :-: |
| **Sprint 1** | S1-01…S1-29 | E-PAC-01 + E-RIS-01 | S1–S2 | Platform foundation: RBAC seed, tenant middleware, atomic provisioning, audit, roles UI, metering, tenant-prefixed keys | Login + RBAC + isolation green; provisioning < 15 min | **G6 pre-check** (provisioning, RLS, 100% audit, cross-tenant denial) | 37.0 / 37.5 |
| **Sprint 2** | S2-01…S2-30 | E-PAC-02 + E-RIS-02 | S3 | Ingestion gateway (C-STORE/STOW-RS, modality auth, orphans) + HL7 interface engine (ORM/ORU/ADT, exception queue) | C-STORE accepted & indexed < 5 min; ORM → order < 1 min | **G1 + G5 pre-check** (ingestion path; > 99.9% delivery, ≤ 5-min alert) | 40.0 / 37.5 |
| **Sprint 3** | S3-01…S3-24 | E-PAC-03 + E-PAC-04 | S4–S5 | MWL serving + MPPS consumer; tiered archive + Storage Commitment, retention/legal-hold, quota | Storage Commitment "safe to purge"; MWL/MPPS loop live | **G1 (SC accuracy) + G2 + G4 pre-check** | 29.0 / 35 |
| **Sprint 4** | S4-01…S4-26 | E-PAC-05 + E-PAC-06 | S6–S7 | DICOMweb gateway (QIDO/WADO, frame-level streaming, IUA/OAuth2) + reading worklist & zero-footprint viewer | Study opens in viewer < 3 s | **G3 pre-check** (open < 3 s; progressive on multi-GB) | 36.0 / 50 |
| **Sprint 5** | S5-01…S5-22 | E-PAC-07 + E-PAC-08 | S8–S9 | Admin console (registry, queues, storage, retention, exceptions, audit) + interface monitoring completion | Admin console + health dashboard live | **G4 + G5 pre-check** (console parity; interface health) | 29.5 / 40 |
| **Sprint 6** | S6-01…S6-26 | E-PAC-09 + E-PAC-10 | S10–S11 | Dashboards & metering-to-invoice; DR (edge cache, buffering, runbook), availability SLO, security hardening | Invoices match metering; failover runbook; RLS audit + CVE evidence | **G6 pre-check** (metering accuracy) + **G7 prep** (perf baseline S6-25, UAT pack S6-26) | 33.0 / 45 |
| **Sprint 7** | S7-01…S7-22 | Hardening (all epics) | S12 | UAT per persona, full performance suite, security test, final DR drill, G1–G7 re-verification, go/no-go | MVP releasable | **ALL G1–G7 final** + go/no-go | 29.0 / 50 |
| **Σ Program** | 179 task IDs (180 rows) | 10 epics + hardening | S1–S12 | | | | **233.5 / 295** (~79% utilization) |

---

## 3. Dependency Graph & Handoffs

```
Critical path (strictly sequential):
  Sprint 1 (Platform) ──► Sprint 2 (Ingestion) ──► Sprint 3 (Archive/SC) ──► Sprint 4 (DICOMweb → Viewer) ──► Sprint 7 (Hardening/Gates)
                                                                                             │
Parallel tracks:  Sprint 5 (Admin console ∥ viewer tail) ◀── Sprint 4 finish
                  Sprint 6 (Dashboards + DR ∥ admin/monitoring tail) ◀── Sprint 5 finish
```

**Inter-sprint handoffs (what each sprint must hand the next):**

| From | To | Handoff (task IDs) |
| :--- | :--- | :--- |
| Sprint 1 → 2 | Ingestion can start | RBAC + `FILE_WRITE`/`INTERFACE_MONITOR` wiring (S1-05/22), `app.facility_id` middleware (S1-07), tenant-prefixed keys (S1-23), metering hooks (S1-24), audit triggers (S1-14), service keys (S1-29) |
| Sprint 2 → 3 | Archive/SC can start | C-STORE/STOW-RS (S2-03/04), parser → metadata index (S2-07), duplicate detection (S2-10), exception API (S2-12), interface events (S2-23); E-PAC-02 tail (S2-13/14) absorbs slack |
| Sprint 3 → 4 | Viewer can consume | Metadata index (S2-07), tiered storage + `storage_objects` (S3-09/10), Storage Commitment (S3-12…14), MWL/MPPS (S3-01…07) |
| Sprint 4 → 5 | Admin surfaces APIs | Exception API (S2-12), interface capture/health/alerting base (S2-23/24/25), retention + quota backend (S3-16…19), modality registry backend (S2-01/02), audit viewer (S1-16), conformance lab (S2-27, S3-21) |
| Sprint 5 → 6 | Dashboards/DR use everything | Storage dashboard API (S5-06), alerting (S5-16/17), routing rules (S5-12/13) |
| Sprint 6 → 7 | Hardening executes | All epics delivered; perf baseline (S6-25), UAT pack (S6-26), DR runbook (S6-15/16), SLO wiring (S6-17), security sweep (S6-24) |

**Cross-system (shared platform):** Sprint 1 platform foundation and Sprint 2's interface-engine patterns are shared with the **RIS and EMR** releases; the S4 viewer is the base for the EMR SMART-on-FHIR launch (v2.0); S6/S7 DR, availability, and security hardening apply platform-wide. Coordinate staffing and freeze dates with the RIS/EMR release plans.

---

## 4. Exit-Gate Checkpoints (G1–G7)

> **Runnable cutover form:** `requrements/PACS/go-live-checklist.md` — QA/ops checklist with per-gate steps, evidence artifacts, cutover sequence, and sign-off block.

| Gate | Criterion | Pre-checked (sprint) | Final verification (sprint) |
| :-: | :--- | :--- | :--- |
| G1 | C-STORE/STOW-RS → indexed & retrievable < 5 min; SC 100% verifiable; 0 silent purges | S2 (ingestion), S3 (SC accuracy) | S7 (S7-17) |
| G2 | MWL auto-populates ≥ 98%; MPPS drives status without manual entry | S3 | S7 (S7-17) |
| G3 | Study opens < 3 s p95; progressive < 3 s on multi-GB; viewer never blocks | S4 | S7 (S7-06…09, S7-17) |
| G4 | Retention/legal-hold honored, 0 accidental purges; quota alerts 75/90% | S3 (backend), S5 (admin UI) | S7 (S7-18) |
| G5 | Interface delivery > 99.9%; 0 silent drops; failures alerted ≤ 5 min | S2, S5 (dashboard) | S7 (S7-18) |
| G6 | Atomic provisioning < 15 min; RLS verified; 100% audit; cross-tenant denied & logged | S1, S6 (metering) | S7 (S7-10, S7-18) |
| G7 | No P0/P1 defects; UAT sign-off (radiologist, technologist, PACS admin) | S6 (UAT pack prep) | S7 (S7-01…S7-05) |

---

## 5. Capacity & Staffing Profile

| Sprint | FTE | Used / Available (dev-days) | Pressure |
| :--- | :-: | :-: | :--- |
| 1 | 3.75 (2 BE · 1 FE · 0.5 QA · 0.25 INT) | 37.0 / 37.5 | **BE overhang 2.5 d** — at capacity |
| 2 | 3.75 (2 BE · 0.75 INT · 0.5 FE · 0.5 QA) | 40.0 / 37.5 | **BE +4.5 d, INT +0.5 d over** — mitigate (slip S2-26, INT assists) |
| 3 | 3.5 (2 BE · 0.75 INT · 0.5 QA · 0.25 FE) | 29.0 / 35 | Comfortable; ~6 d slack (E-PAC-02 tail, QIDO forward-pull) |
| 4 | 5.0 (2 BE · **2 FE** · 0.5 QA · 0.5 INT) | 36.0 / 50 | **FE peak** (viewer); ~14 d slack |
| 5 | 4.0 (2 FE · 1 BE · 0.5 QA · 0.5 INT) | 29.5 / 40 | Console breadth; ~10.5 d slack |
| 6 | 4.5 (1.5 BE · 1 FE · 1 OPS · 1 QA) | 33.0 / 45 | Wind-down; ~12 d slack |
| 7 | 5.0 (2 QA · 1 BE · 1 FE · 1 OPS) | 29.0 / 50 | **QA peak** (UAT/security/perf); ~21 d slack |

**Profile:** ramp to 2 BE + 1 FE by S1; integration engineer at 0.75 FTE for S2–S3 (DICOM/HL7 conformance is the bottleneck); FE doubles to 2 for S4 (viewer); OPS joins S6–S7 (DR/availability); QA doubles S7 (hardening). Program total ≈ **233.5 dev-days** (~47 engineer-weeks) at ~79% utilization.

**Capacity risks carried forward** (full detail in each sprint doc §6):
- **S1–S2 backend overhang** — the largest execution risk; mitigations: slip D-items (S2-26), integration-engineer assist, re-estimate at stand-up.
- **S2–S3 integration engineer is critical path** — protect INT time; conformance harness reuse.
- **S4 FE at full budget** — two dedicated viewer engineers; D-items slip into slack.
- **S5 single BE** — routing-rules engine is the slippable D-item.
- **S7 QA-heavy** — P0/P1-fix-only discipline; P2/P3 to v1.1 backlog.

---

## 6. How to Use This Roadmap (change control)

1. **Task-level truth lives in the sprint detail docs** — this roadmap is the index, not a substitute. Any task change updates the owning sprint doc, not this file.
2. **A sprint's gate checkpoint is a "pre-check"** — formal exit-gate verification happens in Sprint 7 (S7-17/18); a red pre-check must be resolved before the next sprint's dependent handoff.
3. **Handoffs are the contract between sprints** — a missed handoff (e.g., S1-07 middleware late) blocks the downstream sprint start; treat the §3 handoff table as a dependency gate.
4. **Cross-system coordination** — Sprint 1 platform, Sprint 2 interface patterns, and S6/S7 hardening are shared with RIS/EMR; align freeze dates and shared-owner staffing with the RIS/EMR release plans.
5. **Versioning** — this roadmap is v1.0 for the PACS MVP; re-issue when a sprint detail doc's scope or the release-plan roadmap changes.

---

## Traceability

| Section | Source |
| :--- | :--- |
| §1 mapping rationale | `PACS/RELEASE_PLAN.md` §4; sprint doc headers |
| §2 master roadmap | Sprint docs §1–§2; release-plan §4 |
| §3 handoffs | Sprint docs §1 ("handoff" lines) |
| §4 gate checkpoints | Release-plan §2 (G1–G7); sprint docs §5 (DoD) |
| §5 capacity | Sprint docs §2 (team capacity) |
| §7 change control | this document |
