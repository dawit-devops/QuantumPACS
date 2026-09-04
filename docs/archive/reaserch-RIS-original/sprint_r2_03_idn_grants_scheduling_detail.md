# Sprint R2-03 Detail — Multi-Site Scheduling & IDN Grants (E-RIS2-05, shared with PACS E-V2-03)

**Version:** 1.0 · **Date:** 2026-08-05 · **Source:** `requrements/RIS/RELEASE_PLAN_V2.md` E-RIS2-05, §2 gates RVG-3; `requrements/RIS/03_user_stories.md` RIS-US-P03-04; `requrements/RIS/06_acceptance_criteria.md` RIS-AC-P03-04; `requrements/RIS/05_metrics_and_slas.md` RIS-SL-61; `requrements/cross_tenant_grants_design.md` + `_api_contract.md` (purpose `IDN_SCHEDULE_READ`, scope `SCHEDULE_READ`); `requrements/sprint_v2_02_priors_grants_detail.md` (V2-02-09…17, PACS-side)
**Cadence:** two 2-week sprints (R2-S5–R2-S6) · **Squads:** RIS-V2 — two backend, one frontend, part-time integration engineer, QA · **Shared epic:** grants DDL/RLS/API/UI are implemented **once** in PACS V2-02 (V2-S3–S4); this sprint reuses them and builds the RIS multi-site scheduling surface.
> **Sprint numbering:** this is sprint detail **R2-03** of the RIS V2 delivery sequence = release-plan roadmap **R2-S5–R2-S6** (Phase 1, v1.1). **Coordination contract:** PACS V2-02 (V2-S3–S4) must close the grants DDL/RLS/helper/API/UI (V2-02-09…V2-02-17) before R2-S5 starts; a missed handoff blocks this sprint.

---

## 1. Sprint Goal

> **"An IDN tenant's schedulers search availability across all sites with a shared resource pool — reads authorized through audited `IDN_SCHEDULE_READ` grants (< 1 s), bookings writing to the user's home facility only (0 cross-tenant writes possible), and site chargeback data captured per booking."**

**Scope in (R2-S5):** grants reuse (schema/RLS/helper/API/UI smoke), multi-site availability search, home-facility write enforcement. **Scope in (R2-S6):** site chargeback capture, per-site SLA preservation, audit + RLS regression, E2E + RVG-3 pre-checks.

**Scope out (later R2 sprints):** FHIR read + v1.1 gates (R2-04), full FHIR/portal (R2-05), AI-assisted coding + chargeback analytics + v2.0 gates (R2-06).

**Prior program handoff (required to start):** PACS V2-02 grants implementation (V2-02-09…17 — one schema/API/UI), scheduling resource model (E-RIS-05), audit + `cross_tenant.denied` path (S1-14, RBAC §6), prior-auth rule (R2-01-05).

---

## 2. Team Capacity (two 10-day sprints)

| Role | FTE | Available dev-days (×2) | Notes |
| :--- | :-: | :-: | :--- |
| Backend engineer ×2 | 2.0 | 40 | Grants reuse, home-facility writes, chargeback capture |
| Frontend engineer ×1 | 1.0 | 20 | Multi-site search & book (RIS-UI-18) |
| Integration engineer | 0.5 | 10 | Grants API smoke, cross-facility conformance |
| QA | 0.5 | 10 | RLS regression, RVG-3 pre-checks |
| **Total** | **4.0** | **~80** | Total task estimate below: **~21 dev-days** (BE 11.0 · FE 3.5 · INT 2.0 · QA 4.5) — ~59 days slack, absorbed per note below |

> **Slack absorption (not committed):** (a) RLS regression expansion (merged patients, revoked-mid-search); (b) per-site SLA dashboards; (c) forward-pull of **E-RIS2-07 #1** (FHIR read scaffold) once FHIR patterns are proven. Nothing past E-RIS2-05 scope is committed.

---

## 3. Task Board (grouped by source work item)

> Estimates in dev-days. `Owner:` BE = backend, FE = frontend, INT = integration engineer, QA = test. `Check:` acceptance check (maps to AC/SL/CTG/RBAC IDs).

### 3.1 Grants reuse & enforcement — E-RIS2-05 #1/5
**Source:** `cross_tenant_grants_design.md` (§2/§3/§4, purpose `IDN_SCHEDULE_READ` → scope `SCHEDULE_READ`); `cross_tenant_grants_api_contract.md`; CTG-AC-01…07.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| R2-03-01 | Grants smoke: PACS V2-02 tables/RLS/helper/API/UI live in RIS tenant; `IDN_SCHEDULE_READ` grant create → read | INT | 2.0 | V2-02-17 | CTG-API-01…07 smoke |
| R2-03-02 | `app_cross_accessible_facilities()` reuse in schedule read path (`SCHEDULE_READ` RLS OR-clause on appointments/rooms/modalities) | BE | 2.0 | V2-02-09…12 | CTG-AC-01/02: granted reads return |
| R2-03-03 | Per-request facility-array cache + `cross_tenant.read`/`.denied` audit events | BE | 1.5 | R2-03-02 | PAC-SL-25 (auth < 1 s); 100% audited |
| R2-03-04 | Denial path: 0 grants → denied + logged (`cross_tenant.denied`), friendly UI state | FE | 1.0 | R2-03-02 | RIS-SL-61; CTG-AC-05 |

**Epic exit contribution:** E-RIS2-05 #1/5 (grants reuse + audit — RVG-3).

### 3.2 Multi-site availability & booking — E-RIS2-05 #2/3
**Source:** RIS-AC-P03-04; RIS-UI-18; design §6.3 (home-facility writes).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| R2-03-05 | Multi-site availability search: shared resource pool, sites side-by-side, site selection recorded (RIS-UI-18) | BE + FE | 4.0 | R2-03-02 | RIS-AC-P03-04: availability spans sites |
| R2-03-06 | Booking writes to **home facility only** (`SCHEDULE_WRITE` + RLS `WITH CHECK`); site recorded on appointment | BE | 2.0 | R2-03-05 | Design §6.3: 0 cross-tenant writes |
| R2-03-07 | Revoked/expired grant mid-search → next request denied + audited; UI refresh 403 friendly | BE + FE | 1.5 | R2-03-04 | CTG-AC-03 (expiry case) |

**Epic exit contribution:** E-RIS2-05 #2/3 (multi-site + home-facility writes — RVG-3).

### 3.3 Chargeback & SLAs — E-RIS2-05 #4/5
**Source:** RIS-AC-P03-04 (chargeback); RIS-SL-61.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| R2-03-08 | Site chargeback data capture per booking (site, contract, modality) | BE | 1.5 | R2-03-06 | RIS-AC-P03-04: chargeback captured |
| R2-03-09 | Per-site SLA preservation (availability/booking latency per site) | BE | 1.0 | R2-03-05 | Site SLAs measured |

**Epic exit contribution:** E-RIS2-05 #4/5 (chargeback + SLAs — RVG-3).

### 3.4 Cross-cutting: RLS regression, E2E & gates
**Source:** RVG-3; RIS-SL-61.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| R2-03-10 | RLS regression: home-facility behavior unchanged; cross-tenant writes impossible; revoked → denied | QA | 2.0 | R2-03-01…07 | PAC-SL-61 equivalence |
| R2-03-11 | E2E: grant CLINIC → cross-site search → book (home) → revoke → denied + audited | QA | 2.5 | R2-03-10 | CTG-AC-01…07; RVG-3 pre-checks |

---

## 4. Sprint Milestones

| Milestone | Target | Evidence |
| :--- | :--- | :--- |
| **Day 3** | Grants smoke green (PACS V2-02 delivered); schedule-read RLS scaffold | R2-03-01/02 started |
| **Day 5 (R2-S5)** | Multi-site search + home-facility write enforcement live | R2-03-02…06 closed |
| **Day 8 (R2-S6)** | Chargeback capture + per-site SLAs; revocation UX | R2-03-07…09 closed |
| **Day 10 (R2-S6, demo)** | RLS regression + E2E green; demo: grant → cross-site search → book → revoke → denied | R2-03-10/11; RVG-3 pre-checks; sprint review |

---

## 5. Sprint Definition of Done (acceptance checks)

| # | Check | Verifies | Method |
| :-: | :--- | :--- | :--- |
| D1 | `IDN_SCHEDULE_READ` grants reused (one schema/API/UI with PACS); auth < 1 s; 100% audited | CTG-AC-01…07, PAC-SL-25 | R2-03-01…04 |
| D2 | Multi-site availability; bookings write home facility only; 0 cross-tenant writes | RIS-AC-P03-04, design §6.3 | R2-03-05…07 |
| D3 | Site chargeback captured; per-site SLAs preserved | RIS-AC-P03-04 | R2-03-08/09 |
| D4 | RLS regression green; revoked/expired denied + audited next request | RIS-SL-61, CTG-AC-03/05 | R2-03-10/11 |
| D5 | Engineering DoD: `tsc --noEmit` + `vite build` clean; unit tests green | release-plan V2 §6 | CI gate |
| D6 | No P0/P1 open defects at sprint close | release-plan V2 §6 | Defect triage |

---

## 6. Risks & Watch Items (Sprint R2-03)

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| PACS V2-02 grants slip (shared epic) | V2-02-17 closure | Contract-first; freeze dates aligned; R2-S5 start gated on handoff |
| Divergent schema/API (RIS copies PACS) | Schema diff review | One implementation, no fork; reuse-only this sprint |
| Cross-facility data exposure | RIS-SL-61 | Read-only grants; RLS OR-clause; `cross_tenant.denied` audit; regression suite |
| Multi-site booking write leak | RLS `WITH CHECK` | Home-facility enforcement tested on every schema change |

---

## Traceability

| Source work item | Tasks |
| :--- | :--- |
| E-RIS2-05 #1 (grants reuse) | R2-03-01…03 |
| E-RIS2-05 #5 (per-site SLA + audit) | R2-03-04, R2-03-09 |
| E-RIS2-05 #2 (multi-site availability) | R2-03-05 |
| E-RIS2-05 #3 (home-facility writes) | R2-03-06/07 |
| E-RIS2-05 #4 (chargeback capture) | R2-03-08 |
| RVG-3 pre-checks + RLS regression | R2-03-10/11 |
