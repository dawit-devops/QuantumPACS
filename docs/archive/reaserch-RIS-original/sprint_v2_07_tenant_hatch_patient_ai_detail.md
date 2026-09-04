# Sprint V2-07 Detail — Schema-per-Tenant Escape Hatch (E-V2-14), Patient Delivery (E-V2-15), AI Utility Gate (E-V2-16) + V2 Hardening & Exit Gates

**Version:** 1.0 · **Date:** 2026-08-05 · **Source:** `requrements/PACS/RELEASE_PLAN_V2.md` E-V2-14, E-V2-15, E-V2-16, §2 gates VG-6…VG-10; `decisions/ADR-001.md` §3.4 (escape hatch); `requrements/PACS/PRD.md` §3.2 (AI utility gate)
**Cadence:** three 2-week sprints (V2-S13–V2-S15) · **Squads:** PACS-V2 — two backend, one frontend, Ops/SRE (escape hatch + DR at scale), QA · **Format parity:** `requrements/sprint_v2_01_advanced_viewer_priors_detail.md` … `sprint_v2_06_fhircast_content_edge_detail.md`
> **Sprint numbering:** this is sprint detail **V2-07** — the **V2 capstone** — matching release-plan roadmap **V2-S13–V2-S15** (3 sprints: the final Phase-2 domain epics plus the V2 hardening sprint). It delivers the schema-per-tenant escape hatch, patient imaging delivery, and the AI utility gate, then executes the **VG-6…VG-10** exit gates.

---

## 1. Sprint Goal

> **"Premium tenants can provision a dedicated schema in under 24 hours with a validated, zero-loss migration path; patients can securely access their imaging via the portal with consent and audit; the 30-day AI utility pilot produces the ≥ 70% acceptance decision that gates v2.0 rollout; and every VG-6…VG-10 gate passes with per-persona UAT sign-off — V2 is releasable."**

**Scope in (V2-S13):** dedicated-schema provisioning (< 24 h), isolation guarantees, eligibility/billing, ops tooling. **Scope in (V2-S14):** shared→dedicated migration + cutover runbook; patient portal imaging view (read-only, consent-gated), XDS-I.b sharing + secure share links, release policy. **Scope in (V2-S15):** AI utility pilot instrumentation + 30-day pilot decision, VG-6…VG-10 re-verification, full performance suite, security test (RLS incl. schema-per-tenant, IDOR on FHIR/UPS-RS, SMART token flow), DR drill at scale, per-persona UAT, evidence package, go/no-go.

**Scope out (V3+ backlog):** everything beyond the PRD §5.1 v2.0 scope — e.g., film/hardware, thick-client workstations, AI model development, patient-facing *order/schedule* features (portal domain beyond imaging).

**Prior program handoff (required to start):** all 16 V2 epics delivered (V2-01…V2-06 closures), UPS-RS + FHIR/SMART (V2-05), FHIRcast + non-DICOM + edge at scale (V2-06), prefetch engine (V2-02), perf baseline + conformance harnesses.

---

## 2. Team Capacity (three 10-day sprints)

| Role | FTE | Available dev-days (×3) | Notes |
| :--- | :-: | :-: | :--- |
| Backend engineer ×2 | 2.0 | 60 | Escape-hatch provisioning/migration, portal delivery, fix support |
| Frontend engineer ×1 | 1.0 | 30 | Portal view, share UX, fix support |
| Ops/SRE engineer ×1 | 1.0 | 30 | Schema ops, DR at scale, cutover, CVE cadence |
| QA | 1.0 | 30 | AI pilot instrumentation, VG-6…VG-10 gates, UAT |
| **Total** | **5.0** | **~150** | Total task estimate below: **~38 dev-days** (BE 15.0 · FE 6.5 · OPS 8.0 · QA 8.5) — ~12 days slack, absorbed per note below |

> **Slack absorption (not committed):** (a) VG rework + full-suite regression reruns after every fix; (b) extended AI pilot scenarios; (c) schema-per-tenant load testing; (d) evidence/documentation polish (gate reports, SOC 2 pack, cutover rehearsals). No new features enter the capstone without VG-10 change control.

---

## 3. Task Board (grouped by source work item)

> Estimates in dev-days. `Owner:` BE = backend, FE = frontend, OPS = ops/SRE, QA = test. `Check:` acceptance check (maps to AC/SL/UI/ADR/PRD IDs where applicable).

### 3.1 Schema-per-tenant escape hatch: provisioning — E-V2-14 #1/3/4
**Source:** ADR-001 §3.4; `PAC/05` PAC-SL-51 (24 h tier); `pacs-ris-multitenancy.md` §3.4.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-07-01 | Dedicated-schema provisioning: schema generation + seed + lifecycle (PROVISIONING→SEEDING→READY), READY < 24 h | BE | 2.5 | S1-09 | PAC-SL-51 (24 h tier) asserted |
| V2-07-02 | Isolation guarantees: schema owner model, no cross-schema path, app-level RBAC unchanged | BE | 2.0 | V2-07-01 | PAC-SL-61 equivalence for the dedicated tenant |
| V2-07-03 | Eligibility/billing: premium-tier feature flag + plan rules; metering unchanged | BE | 1.0 | V2-07-01 | PAC-SL-50: metering matches usage |
| V2-07-04 | Ops tooling: schema-scoped backups, partition management, upgrade cadence | OPS | 1.5 | V2-07-01 | Backup/restore drill for a dedicated tenant |

**Epic exit contribution:** E-V2-14 #1/3/4 (provisioning < 24 h + isolation + billing).

### 3.2 Escape hatch: migration & cutover — E-V2-14 #2
**Source:** ADR-001 §3.4; `PAC/06` PAC-AC-P04-09 (pattern); shared-schema → dedicated.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-07-05 | Shared→dedicated migration: data copy (logical, row-scoped), verification, duplicate-safe re-ingest | BE | 2.0 | V2-07-01, V2-04-12 | Zero-loss migration; counts reconcile 100% |
| V2-07-06 | Cutover runbook + rollback: freeze → copy → verify → switch; rollback verified | OPS | 1.5 | V2-07-05 | Rollback restores service within RTO |
| V2-07-07 | Post-migration validation: RLS-equivalent checks + sample clinical validation | QA | 1.0 | V2-07-05 | PAC-SL-61 evidence for the migrated tenant |

**Epic exit contribution:** E-V2-14 #2 (validated migration — VG-9).

### 3.3 Patient imaging delivery — E-V2-15
**Source:** PRD §2.4 (patient-facing roadmap); `PAC/02` PAC-WF8 (XDS-I.b); `PAC/05` PAC-SL-60.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-07-08 | Patient portal imaging view: read-only, consent-gated, key images + report; no PHI in URLs | FE | 2.0 | V2-06-01 | Patient-facing view live (PRD §2.4 roadmap) |
| V2-07-09 | Portal identity/consent: patient authentication + consent capture + release policy (HIM review) | BE | 1.5 | V2-07-08 | Consent recorded; release policy enforced |
| V2-07-10 | XDS-I.b sharing + secure share links with expiry and revocation (extend V2-04-02) | BE | 1.5 | V2-04-02 | PAC-WF8; PAC-SL-60 audit |
| V2-07-11 | Audit: every patient-visible access logged; share lifecycle audited | BE | 0.5 | V2-07-10 | PAC-SL-60: 100% of accesses logged |

**Epic exit contribution:** E-V2-15 (patient delivery — VG-9).

### 3.4 AI utility gate — E-V2-16
**Source:** PRD §3.2 (utility ≥ 70% acceptance, 30-day pilot, latency ≤ 5 min, safety).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-07-12 | Pilot instrumentation: acceptance/rejection capture with audit; utility + latency dashboards | QA | 1.5 | V2-05-07 | PRD §3.2 metrics measurable |
| V2-07-13 | 30-day pilot: ≥ 2 AI services (triage, CAD) with radiologist accept/reject; rejected findings audited | QA | 2.0 | V2-04-10, V2-05-06 | Utility gate decision recorded |
| V2-07-14 | Vendor conformance + fallback: ingestion is service-agnostic; result quality report | INT | 1.0 | V2-05-06 | No single-vendor lock-in; fallback proven |
| V2-07-15 | Gate decision: ≥ 70% acceptance → v2.0 rollout proceeds; else remediation plan (alternative vendors, tuning) | BE | 0.5 | V2-07-13 | Decision record in ADR/PRD §3.2 |

**Epic exit contribution:** E-V2-16 (utility gate — VG-6/VG-10).

### 3.5 V2 performance & security test
**Source:** `PAC/05` PAC-SL-10/11/12/13/16/17/50/60/61/63; PRD §3.2.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-07-16 | Full performance suite: PAC-SL-10/11/12/13/16/17 + UPS/FHIR latency under load; egress metering accuracy | QA | 1.5 | V2-05/06 closures | All p95 assertions green |
| V2-07-17 | Security test: RLS matrix (incl. schema-per-tenant), RBAC matrix, IDOR on FHIR/UPS-RS/DICOMweb, SMART token flow | QA | 1.5 | V2-07-02 | 0 critical/high; PAC-SL-61/63 evidence |
| V2-07-18 | CVE scan + patch cadence + SOC 2 Type II evidence pack | OPS | 1.0 | — | PAC-SL-63; evidence archived |

**Epic exit contribution:** VG-10 (perf/security posture).

### 3.6 V2 exit gates & go/no-go — VG-6…VG-10
**Source:** release-plan V2 §2 (VG-6…VG-10); `PAC/06` PAC-AC-*; `PAC/05` PAC-SL-*.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-07-19 | VG-6 re-verify: UPS-RS + AI latency ≤ 5 min + service-key scopes + utility pilot evidence | QA | 1.5 | V2-07-12…15 | Gate green |
| V2-07-20 | VG-7 re-verify: EMR launch < 5 s, FHIR conformance, FHIRcast, read-only mode, no PHI in URLs | QA | 1.5 | V2-06-18 | Gate green |
| V2-07-21 | VG-8 re-verify: non-DICOM content + edge at scale with DR continuity | QA | 1.0 | V2-06-19/20 | Gate green |
| V2-07-22 | VG-9 re-verify: schema-per-tenant < 24 h + migration validated; patient delivery with consent/audit | QA | 1.0 | V2-07-01…11 | Gate green |
| V2-07-23 | Per-persona UAT + sign-off: referring MD, ED MD, teleradiologist, PACS admin (plus radiologist advanced-tools regression) | QA | 2.0 | V2-06-23 | VG-10: sign-off; 0 P0/P1 |
| V2-07-24 | Final DR drill at scale: cloud-region outage → edge reads + buffered ingestion + schema-per-tenant restore; RTO/RPO measured | OPS | 2.0 | V2-06-15, V2-07-06 | PAC-AC-P04-07; RTO ≤ 4 h, RPO ≤ 60 min |
| V2-07-25 | Consolidated V2 evidence package: VG-6…VG-10 report with AC/SL traceability; availability 99.9% (PAC-SL-01) | QA | 1.0 | V2-07-19…24 | Package complete |
| V2-07-26 | Production cutover runbook (Phase-2) + rollback; rehearsed once in staging | OPS | 1.0 | V2-07-25 | Cutover rehearsed |
| V2-07-27 | V2 go/no-go review: all gates green + AI utility decision + PRD §5.1 v2.0 exit gates | QA | 0.5 | V2-07-25 | GO / NO-GO recorded |

**Epic exit contribution:** all ten V2 gates VG-1…VG-10 documented (Phase-1 gates re-confirmed as regression).

---

## 4. Sprint Milestones (three sprints)

| Sprint | Milestone | Target | Evidence |
| :--- | :--- | :--- | :--- |
| **V2-S13** | Dedicated-schema provisioning live < 24 h; isolation verified; migration path first pass | Day 8 | V2-07-01…04 closed; PAC-SL-51 asserted |
| **V2-S14** | Migration + cutover runbook rehearsed; portal view + XDS-I.b share live with consent | Day 10 | V2-07-05…11 closed; PAC-SL-60 audit green |
| **V2-S15** | AI pilot decision; perf/security suites green; VG-6…VG-10 re-verified; UAT sign-off; go/no-go | Day 10 | V2-07-12…27 closed; evidence package; sprint review |

---

## 5. Sprint Definition of Done (acceptance checks)

| # | Check | Verifies | Method |
| :-: | :--- | :--- | :--- |
| D1 | Dedicated schema READY < 24 h; isolation equivalent; migration zero-loss + rollback verified | PAC-SL-51/61 | V2-07-01…07 |
| D2 | Patient portal view consent-gated, read-only, fully audited; share expiry/revocation | PRD §2.4, PAC-SL-60 | V2-07-08…11 |
| D3 | AI utility pilot: ≥ 70% acceptance decision recorded; latency ≤ 5 min; rejected audited | PRD §3.2 | V2-07-12…15 |
| D4 | Full perf suite + security test (incl. schema-per-tenant RLS) green; SOC 2 evidence | PAC-SL-10…17/61/63 | V2-07-16…18 |
| D5 | VG-6…VG-10 green; UAT sign-off (4 personas); DR drill RTO ≤ 4 h / RPO ≤ 60 min | release-plan V2 §2 | V2-07-19…27 |
| D6 | Engineering DoD: `tsc --noEmit` + `vite build` clean; unit tests green; migrations reviewed | release-plan V2 §6 | CI gate |
| D7 | No P0/P1 open defects; V2 go/no-go review passes — V2 releasable | release-plan V2 §6 | Defect triage + V2-07-27 |

---

## 6. Risks & Watch Items (Sprint V2-07)

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| Schema-per-tenant migration complexity (data copy + cutover) | PAC-SL-51/61 | Logical row-scoped copy + duplicate-safe re-ingest; rollback verified (V2-07-06); premium tenants only |
| AI utility gate < 70% | PRD §3.2 pilot | Pilot gates rollout; service-agnostic ingestion + fallback (V2-07-14); remediation plan documented |
| Portal PHI exposure | PAC-SL-60 | Consent + release policy; no PHI in URLs; share expiry/revocation; audit every access |
| DR at scale (schema-per-tenant restore) | V2-07-24 RTO/RPO | Rehearse early; edge + buffer paths proven in V2-06; extra rehearsal in slack |
| UAT finding volume exceeds fix capacity | Daily triage P0/P1 | Feature freeze; P0/P1 only; P2/P3 → V3 backlog |
| Gate regression after fixes | VG re-runs | Every fix triggers full-suite rerun; regression window in slack |
| Go/no-go scope creep ("one more feature") | VG evidence drift | Evidence package is the contract; changes after sign-off → V3 |

---

## Traceability

| Source work item | Tasks |
| :--- | :--- |
| E-V2-14 #1 (dedicated provisioning) | V2-07-01…04 |
| E-V2-14 #2 (migration + cutover) | V2-07-05…07 |
| E-V2-15 (patient imaging delivery) | V2-07-08…11 |
| E-V2-16 (AI utility gate) | V2-07-12…15 |
| Performance + security test | V2-07-16…18 |
| V2 gates VG-6…VG-10 + go/no-go | V2-07-19…27 |
