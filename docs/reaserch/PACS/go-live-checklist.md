# PACS MVP — Go-Live Checklist (Exit Gates G1–G7)

**Version:** 1.0 · **Date:** 2026-08-04 · **Source:** `requrements/PACS/RELEASE_PLAN.md` §2 (gates), `requrements/PACS/06_acceptance_criteria.md` (PAC-AC-*), `requrements/PACS/05_metrics_and_slas.md` (PAC-SL-*), `requrements/pacs_consolidated_sprint_roadmap.md` §4
**Owners:** QA (gates G1–G4, G7) · Ops (gates G5–G6) · **When:** pre-cutover dry run, then cutover day · **Exit-gate detail:** `requrements/sprint7_hardening_detail.md` (S7-17/18/19)

---

## 1. How to Use This Checklist

1. **Dry run (T-2 weeks):** run all seven gates in the production-shaped staging tenant (Sprint 7 S7-17/18). Any red gate → fix before cutover; re-run affected gate + dependent gates.
2. **Cutover day:** run in the §4 sequence. Checkboxes are for QA/Ops execution; **P0/P1 findings make a gate red regardless of check state** (G7).
3. **Evidence:** every gate produces an artifact (listed in §3); archive with the go-live record. No evidence = gate not passed.
4. **Sign-off:** complete §5. All gates green (or waived per §6) = MVP releasable.

---

## 2. The Checklist

### G1 — Ingestion & Storage Commitment *(PAC-AC-P02-02, PAC-SL-20/21/15)*

- [ ] **C-STORE ingest:** send the conformance-lab 3-series DICOM set (S2-27/S3-21 harness) → study indexed and retrievable **< 5 min** after C-STORE completes (PAC-SL-20).
- [ ] **STOW-RS ingest:** push the same study via DICOMweb STOW-RS → accepted; `txn_type='STOW-RS'` logged.
- [ ] **Duplicate:** resend one instance → `200 {duplicate: true}` (PAC-AC-P02-03); no second object.
- [ ] **SC success:** request Storage Commitment → N-EVENT SUCCESS **< 60 s** for the complete series set (PAC-SL-15); study `storage_status` = ARCHIVED.
- [ ] **SC failure:** send an incomplete series and request commitment → FAILURE with reason; **no purge signal** returned (PAC-AC-P02-02 failure case).
- [ ] **0 silent purges:** reconcile `storage_objects` vs committed studies — counts match (PAC-SL-21).
- **Evidence:** conformance lab report + SC log excerpt + reconciliation output.

### G2 — MWL & MPPS *(PAC-AC-P02-01/04, PAC-SL-14/34)*

- [ ] **MWL query:** 10 seeded scheduled orders → scanner C-FIND returns all entries; response **< 1 s p95** (PAC-SL-14).
- [ ] **Auto-fill ≥ 98%:** run 10 acquisitions with zero manual console entry (PAC-SL-34) — measure auto-fill rate.
- [ ] **MPPS flow:** IN_PROGRESS → COMPLETED updates the tracking board **without manual entry**; DISCONTINUED shows `reason_discontinued` (PAC-AC-P02-04).
- [ ] **MPPS mismatch:** send MPPS with a wrong accession → lands in the exception worklist, never dropped.
- **Evidence:** MWL query log + tracking-board screenshots + MPPS event excerpt.

### G3 — Reading Path & Performance *(PAC-AC-P01-08/10, PAC-SL-10/11/16/17)*

- [ ] **Workstation load:** open an active study → first frames render **< 3 s p95** on reference hardware (PAC-SL-10, PAC-AC-P01-08).
- [ ] **Web first frame:** first frame **< 3 s** on reference bandwidth (PAC-SL-11).
- [ ] **Progressive streaming:** open a **2+ GB** CT study → first frames appear progressively, viewer never blocks, error + Retry shown for a failed series, **never a blank viewport** (PAC-AC-P01-10).
- [ ] **DICOMweb latency:** QIDO-RS < 500 ms p95; WADO-RS metadata < 1 s p95 (PAC-SL-16/17).
- **Evidence:** performance run output (S7-06/07 baseline) with p95 figures.

### G4 — Retention & Quota *(PAC-AC-P04-03/04, PAC-SL-43/45)*

- [ ] **Retention dry-run:** configure a 5-yr policy + a pediatric policy → dry-run lists the correct purge candidates; executing the purge produces **0 accidental purges** (PAC-SL-43).
- [ ] **Legal hold:** toggle legal-hold on a candidate → purge is blocked and the override is audited (PAC-AC-P04-03).
- [ ] **Quota alerts:** set a low quota → 75% and 90% alerts fire via the notification subsystem (PAC-SL-45); optional hard-stop blocks new ingestion (PAC-AC-P04-04).
- **Evidence:** purge dry-run report + legal-hold audit rows + quota alert log.

### G5 — Interface Delivery & Alerting *(PAC-AC-P04-08, PAC-SL-23)*

- [ ] **Delivery baseline:** monitor `interface_events` + DICOM/HL7 queues over 24 h → delivery **> 99.9%**, **0 silent drops** (PAC-SL-23).
- [ ] **Failure injection:** break an interface → **alert fires ≤ 5 min**; dashboard shows the fault with drill-down; message is in the exception queue with retry (PAC-AC-P04-08).
- [ ] **Resolve:** clear the fault → `resolved_at` recorded; alert deduplicated (no storm).
- **Evidence:** interface health dashboard export + alert timestamps + exception-queue excerpt.

### G6 — Platform: Provisioning, RLS, Audit, Cross-Tenant *(PAC-AC-P20-01/03, PAC-SL-51/60/61)*

- [ ] **Atomic provisioning:** create a tenant → READY **< 15 min** (PAC-SL-51); an injected mid-seed failure rolls back leaving **no partial tenant** (PAC-AC-P20-01).
- [ ] **RLS isolation:** user with a role at NGH sees **0 rows** at CLINIC; `NOBYPASSRLS` + `FORCE ROW LEVEL SECURITY` verified on all clinical tables (PAC-SL-61).
- [ ] **Audit completeness:** scripted view / retrieve / export / delete / share events → **100%** have audit rows (PAC-SL-60).
- [ ] **Cross-tenant denial:** attempt a cross-tenant read with **0 grants** → denied and logged (`cross_tenant.denied`); a granted read is policy-gated and audited (PAC-AC-P20-03).
- **Evidence:** provisioning log, RLS audit report, audit-completeness report, denial-path log excerpt.

### G7 — Defects & UAT Sign-Off *(PRD §2.3)*

- [ ] **Defect state:** **0 open P0/P1** defects (defect report attached).
- [ ] **Radiologist sign-off:** reading path — worklist → open < 3 s → hanging protocol → tools → critical flag → key image (S7-01).
- [ ] **Technologist sign-off:** acquisition path — MWL → MPPS → C-STORE → Storage Commitment (S7-02).
- [ ] **PACS admin sign-off:** admin path — registry, queue monitor, retention dry-run, exception worklist, audit viewer (S7-03).
- **Evidence:** signed UAT records (per-persona).

---

## 3. Evidence Archive

| Gate | Artifact | Stored as |
| :-: | :--- | :--- |
| G1 | Conformance lab report; SC log excerpt; object reconciliation output | `evidence/g1-*.log/.pdf` |
| G2 | MWL query log; tracking-board screenshots; MPPS excerpt | `evidence/g2-*` |
| G3 | Perf run output (p95 for PAC-SL-10/11/16/17) | `evidence/g3-perf-*.csv` |
| G4 | Purge dry-run report; legal-hold audit rows; quota alert log | `evidence/g4-*` |
| G5 | Interface dashboard export; alert timestamps; exception-queue excerpt | `evidence/g5-*` |
| G6 | Provisioning log; RLS audit report; audit-completeness report; denial excerpt | `evidence/g6-*` |
| G7 | Defect report; signed UAT records | `evidence/g7-*` |

---

## 4. Cutover Sequence (run in this order)

```
G6 Platform (provision a production-shaped tenant; RLS/audit/denial)
  └─► G1 Ingestion + SC (modalities can send and purge safely)
        └─► G2 MWL/MPPS (acquisition loop live)
              └─► G3 Reading path (radiologists can read)
                    └─► G4 Retention/Quota + G5 Interface/Alerting (admin + ops loop)
                          └─► G7 Sign-off (all personas) → GO / NO-GO
```

- **Stop conditions (any red):** G1 or G3 red → **stop** (data-loss or reading-path risk); G6 red → hold tenant onboarding; G2/G4/G5 red → fix-and-recheck before sign-off.
- **Rollback triggers:** data-loss signs (G1), cross-tenant leak (G6), interface-delivery breach (G5) → invoke the cutover rollback plan (S7-20). Availability (PAC-SL-01) is a post-cutover watch metric, not a gate.
- **Post-cutover watch (72 h):** interface delivery baseline (G5), audit completeness (G6), first-frame latency (G3), and 99.9% availability (PAC-SL-01) monitored continuously; incidents routed per P1/P2 SLAs (PAC-SL-02).

---

## 5. Sign-Off Block

| Gate | Result (PASS / PASS-WAIVER / FAIL) | Evidence ID | Checked by | Date |
| :-: | :--- | :--- | :--- | :--- |
| G1 | | | | |
| G2 | | | | |
| G3 | | | | |
| G4 | | | | |
| G5 | | | | |
| G6 | | | | |
| G7 | | | | |
| **GO / NO-GO** | | | | |

---

## 6. Waiver Rules

- **P0/P1 defect** → gate is **red**; no waiver. The MVP does not ship.
- **P2/P3 finding** → may be recorded as **PASS-WAIVER** with a documented mitigation and a v1.1 backlog item; the finding is tracked to closure.
- **Evidence missing** → gate treated as **red** regardless of informal results.
- Waivers require sign-off by QA lead + product owner; the waiver register lives with the go-live record.

---

## Traceability

| Gate | Criterion (release-plan §2) | Verifies |
| :-: | :--- | :--- |
| G1 | Ingestion < 5 min; SC 100% verifiable; 0 silent purges | PAC-AC-P02-02, PAC-SL-20/21 |
| G2 | MWL ≥ 98% auto-fill; MPPS without manual entry | PAC-AC-P02-01/04, PAC-SL-14/34 |
| G3 | Open < 3 s p95; progressive < 3 s; never blocks | PAC-AC-P01-08/10, PAC-SL-10/11 |
| G4 | Retention/legal-hold; 0 accidental purges; quota 75/90% | PAC-AC-P04-03/04, PAC-SL-43/45 |
| G5 | Interface > 99.9%; 0 silent drops; alert ≤ 5 min | PAC-AC-P04-08, PAC-SL-23 |
| G6 | Provisioning < 15 min; RLS; 100% audit; denial logged | PAC-AC-P20-01/03, PAC-SL-51/60/61 |
| G7 | 0 P0/P1; UAT sign-off (3 personas) | PRD §2.3 |
