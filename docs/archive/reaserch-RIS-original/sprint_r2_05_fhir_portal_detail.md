# Sprint R2-05 Detail — Full FHIR Read/Write (E-RIS2-08) & Portal Delivery (E-RIS2-09)

**Version:** 1.0 · **Date:** 2026-08-05 · **Source:** `requrements/RIS/RELEASE_PLAN_V2.md` E-RIS2-08, E-RIS2-09, §2 gates RVG-5; `requrements/RIS/PRD.md` §5.1 v2.0; `requrements/RIS/06_acceptance_criteria.md` RIS-AC-P08-02; `requrements/RIS/05_metrics_and_slas.md` RIS-SL-60; `requrements/PACS/RELEASE_PLAN_V2.md` E-V2-10 (shared FHIR layer), E-V2-15 (patient delivery pattern)
**Cadence:** two 2-week sprints (R2-S8–R2-S9) · **Squads:** RIS-V2 — two backend, one frontend, part-time integration engineer (FHIR/portal conformance), QA · **Format parity:** `requrements/sprint_r2_04_fhir_read_gates_detail.md`
> **Sprint numbering:** this is sprint detail **R2-05** of the RIS V2 delivery sequence = release-plan roadmap **R2-S8–R2-S9** — the start of **Phase 2 (PRD §5.1 v2.0)**. Merged because full FHIR (writes) and portal delivery both extend the v1.1 FHIR read layer and share the PACS E-V2-10/E-V2-15 patterns.

---

## 1. Sprint Goal

> **"RIS exposes full FHIR R4 — ServiceRequest and DiagnosticReport writes with search and RLS on every route (shared server layer with PACS) — while patients receive results through the portal with a release policy, secure share links with expiry/revocation, and 100% audit."**

**Scope in (R2-S8):** `ServiceRequest` create/update + `DiagnosticReport` create, FHIR search coverage + RLS, shared conformance tooling with PACS E-V2-10. **Scope in (R2-S9):** result-availability notifications, release policy + share links, portal results view (read-only, consent-gated).

**Scope out (later R2 sprint):** AI-assisted coding + chargeback analytics + pre-registration + v2.0 gates (R2-06).

**Prior program handoff (required to start):** FHIR read surface + RLS (R2-04), notification subsystem (S1-25), prior-auth linkage (R2-01-08), PACS E-V2-10 conformance tooling (V2-05-13), PACS share-link pattern (V2-04-02).

---

## 2. Team Capacity (two 10-day sprints)

| Role | FTE | Available dev-days (×2) | Notes |
| :--- | :-: | :-: | :--- |
| Backend engineer ×2 | 2.0 | 40 | FHIR writes, share links, audit |
| Frontend engineer ×1 | 1.0 | 20 | Portal results view, share UX |
| Integration engineer | 0.5 | 10 | FHIR write conformance, portal/notifications |
| QA | 0.5 | 10 | RVG-5 pre-checks, E2E |
| **Total** | **4.0** | **~80** | Total task estimate below: **~21 dev-days** (BE 9.0 · FE 3.0 · INT 5.0 · QA 4.0) — ~59 days slack, absorbed per note below |

> **Slack absorption (not committed):** (a) FHIR search-param polish; (b) share-link UX edge cases; (c) forward-pull of **E-RIS2-10 #1** (AI coding scaffold) if ingestion patterns are proven. Nothing past E-RIS2-08/E-RIS2-09 scope is committed.

---

## 3. Task Board (grouped by source work item)

> Estimates in dev-days. `Owner:` BE = backend, FE = frontend, INT = integration engineer, QA = test. `Check:` acceptance check.

### 3.1 Full FHIR (read/write) — E-RIS2-08 #1/2/3
**Source:** FHIR R4; `pacs-ris-viewer-integration-spec.md` §5; PACS E-V2-10 shared layer.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| R2-05-01 | `ServiceRequest` create/update (order status writes) + `DiagnosticReport` create (results, key images) | BE | 3.0 | R2-04-01 | Write conformance vs. test server |
| R2-05-02 | FHIR search coverage + pagination + RLS on all routes (extend R2-04-02) | BE | 2.0 | R2-05-01 | Search parity; isolation |
| R2-05-03 | Shared conformance tooling with PACS E-V2-10 (V2-05-13); version pinning | INT | 3.0 | R2-05-01 | One harness, both systems green |

**Epic exit contribution:** E-RIS2-08 (full FHIR — RVG-5).

### 3.2 Result delivery & notifications — E-RIS2-09 #1
**Source:** RIS-AC-P08-02; RIS-M05.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| R2-05-04 | Result-availability notifications on report sign-off (opt-out honored) | INT | 2.0 | E-RIS-10 | RIS-AC-P08-02; 0 silent failures |

**Epic exit contribution:** E-RIS2-09 #1 (notifications — RVG-5).

### 3.3 Release policy & share links — E-RIS2-09 #2
**Source:** RIS-SL-60; PACS V2-04-02 share pattern.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| R2-05-05 | Release policy (HIM review): which results auto-release vs. require review | BE | 1.5 | R2-05-04 | Policy enforced; audited |
| R2-05-06 | Secure share links: read-only `/view/:key` with expiry + revocation (reuse PACS V2-04-02 pattern); no PHI in URLs | BE | 2.0 | V2-04-02 | RIS-SL-60; share lifecycle audited |

**Epic exit contribution:** E-RIS2-09 #2 (share — RVG-5).

### 3.4 Portal results view — E-RIS2-09 #3
**Source:** RIS-M05; consent-gated patient view.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| R2-05-07 | Portal results view: read-only, consent-gated, plain-language context | FE | 3.0 | R2-05-05/06 | Patient-facing view live |
| R2-05-08 | Audit: every patient-visible access logged | BE | 0.5 | R2-05-07 | RIS-SL-60: 100% logged |

**Epic exit contribution:** E-RIS2-09 #3 (portal view — RVG-5).

### 3.5 Cross-cutting: E2E & gates
**Source:** RVG-5 pre-checks; RIS-SL-60.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| R2-05-09 | E2E: sign-off → notification → release → portal view → share → expire → denied | QA | 2.0 | R2-05-01…08 | RVG-5 pre-checks; audit complete |
| R2-05-10 | FHIR write + portal perf under load; no budget breach | QA | 2.0 | R2-05-03/07 | p95 assertions green |

---

## 4. Sprint Milestones

| Milestone | Target | Evidence |
| :--- | :--- | :--- |
| **Day 3** | FHIR write scaffold; shared conformance harness | R2-05-01/03 started |
| **Day 5 (R2-S8)** | ServiceRequest/DiagnosticReport writes + RLS live | R2-05-01…03 closed |
| **Day 8 (R2-S9)** | Notifications + release policy + share links live | R2-05-04…06 closed |
| **Day 10 (R2-S9, demo)** | Portal results view + audit; E2E green; demo: sign-off → portal → share → expire | R2-05-07…10; RVG-5 pre-checks; sprint review |

---

## 5. Sprint Definition of Done (acceptance checks)

| # | Check | Verifies | Method |
| :-: | :--- | :--- | :--- |
| D1 | Full FHIR write conformance; RLS on all routes | RVG-5, RIS-SL-61 | R2-05-01…03 |
| D2 | Notifications with opt-out; 0 silent failures | RIS-AC-P08-02 | R2-05-04 |
| D3 | Release policy + share links expiry/revocation; no PHI in URLs | RIS-SL-60 | R2-05-05/06 |
| D4 | Portal view consent-gated, read-only, 100% audited | RIS-SL-60 | R2-05-07/08 |
| D5 | Engineering DoD: `tsc --noEmit` + `vite build` clean; unit tests green | release-plan V2 §6 | CI gate |
| D6 | No P0/P1 open defects at sprint close | release-plan V2 §6 | Defect triage |

---

## 6. Risks & Watch Items (Sprint R2-05)

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| FHIR write conformance variance | R2-05-03 suite | Version pinning; public test servers; CI gate |
| Portal PHI exposure | RIS-SL-60 | Release policy; consent; no PHI in URLs; share expiry/revocation; audit every access |
| PACS E-V2-10 conformance tooling slip | V2-05-13 closure | Contract-first; shared harness; independent RIS harness fallback |
| Share-link abuse | Share audit | Expiry + revocation; read-only enforcement; friendly invalid state |

---

## Traceability

| Source work item | Tasks |
| :--- | :--- |
| E-RIS2-08 #1 (FHIR writes) | R2-05-01 |
| E-RIS2-08 #2 (search + RLS) | R2-05-02 |
| E-RIS2-08 #3 (shared conformance) | R2-05-03 |
| E-RIS2-09 #1 (notifications) | R2-05-04 |
| E-RIS2-09 #2 (release policy + share links) | R2-05-05/06 |
| E-RIS2-09 #3 (portal view + audit) | R2-05-07/08 |
| RVG-5 pre-checks + E2E/perf | R2-05-09/10 |
