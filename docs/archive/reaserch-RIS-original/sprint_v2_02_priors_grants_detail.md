# Sprint V2-02 Detail — Priors Prefetch (E-V2-02) & Cross-Tenant Grants (E-V2-03) & QC (E-V2-08)

**Version:** 1.0 · **Date:** 2026-08-05 · **Source:** `requrements/PACS/RELEASE_PLAN_V2.md` E-V2-02, E-V2-03, E-V2-08 (QC); `requrements/cross_tenant_grants_design.md` + `_api_contract.md`
**Cadence:** 2-week sprint (10 working days) · **Squads:** PACS-V2 (prefetch engine) + shared **Platform** squad (cross-tenant grants — coordinated with RIS v1.1 multi-site scheduling) + integration engineer · **Format parity:** `requrements/sprint_v2_01_advanced_viewer_priors_detail.md`
> **Sprint numbering:** this is sprint detail **V2-02** of the V2 delivery sequence = release-plan roadmap **V2-S3–V2-S4**. Merged because the priors epic (E-V2-02) needs the grants epic (E-V2-03) for its cross-facility part, and both sit on the Phase-1 viewer/data foundations from V2-01.

---

## 1. Sprint Goal

> **"At least 95% of exams have their priors staged to the reading site's edge cache before read time and open side-by-side in under 3 seconds — including priors held under a sibling facility via explicit, time-boxed, read-only cross-tenant grants — while a technologist can QC acquired series with mandatory reject reasons."**

**Scope in:** prefetch triggers (schedule + ED arrival), prior resolution via patient history/MPI + location (same facility / sibling facility / external VNA), prefetch queue + edge staging with skip/prioritize rules and bandwidth guard, priors panel UI (thumbnails, synchronized scroll, one-click swap, explicit no-priors state), priors indicator + `PAC-SL-24` instrumentation; cross-tenant grants DDL + RLS + helper + DICOMweb enforcement + ops API (V1–V11) + SYSTEM_ADMIN UI + audit facets + expiry sweep; QC review screen (Adequate/Inadequate + mandatory reject reason + redo flow).

**Scope out (later V2 sprints):** teleradiology session UI + critical callback + report routing (V2-03), export/share UI (V2-04), AI ingestion/overlays (V2-04), UPS-RS (V2-05), FHIR/SMART (V2-05/06), non-DICOM/edge scale (V2-06), schema-per-tenant/patient delivery/AI gate (V2-07).

**Prior program handoff (required to start):** edge cache + invalidation (S6-11/12), measurement/SR-GSPS layer (V2-01-09/10), responsive viewer (V2-01-16/17), audit triggers + middleware (S1-07/14), service keys (S1-29), notification subsystem (S1-25), RIS MWL feed (S3-01).

---

## 2. Team Capacity (10 working days)

| Role | FTE | Available dev-days | Notes |
| :--- | :-: | :-: | :--- |
| Backend engineer ×2 | 2.0 | 20 | Prefetch engine + grants DDL/RLS/API (one each) |
| Frontend engineer ×1 | 1.0 | 10 | Priors panel + SYSTEM_ADMIN grants UI + QC screen |
| Integration engineer | 0.5 | 5 | Prefetch conformance (patient history resolution, XDS-I.b read-across) |
| QA | 1.0 | 10 | CTG-AC/API suites, prefetch SLA, RLS regression |
| **Total** | **4.5** | **~45** | Total task estimate below: **~36 dev-days** (BE 19.5 · FE 7.5 · INT 2.5 · QA 6.5) — ~9 days slack, absorbed per note below |

> **Slack absorption (not committed):** (a) forward-pull of **E-V2-04 #1/#2** (multi-facility worklist query, streaming tuning) once grants are live; (b) QC screen polish; (c) extra grant edge-case tests (merged patients, revoked-mid-read). Nothing past E-V2-02/E-V2-03/E-V2-08 QC scope is committed.

---

## 3. Task Board (grouped by source work item)

> Estimates in dev-days. `Owner:` BE = backend, FE = frontend, INT = integration engineer, QA = test. `Check:` acceptance check (maps to AC/SL/UI/CTG IDs where applicable).

### 3.1 Prefetch trigger & prior resolution — E-V2-02 #1/2
**Source:** `PAC/06` PAC-AC-P01-03; `PAC/02` PAC-WF3; `pacs-ris-multitenancy.md` §3.3 (XDS-I.b read-across).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-02-01 | Prefetch trigger: schedule event + ED arrival for known patients → eligibility evaluation (same modality/anatomy first, skip rules) | BE | 1.5 | S3-01 | PAC-AC-P01-03: priors staged before read time |
| V2-02-02 | Prior resolution: patient history/MPI lookup + location (home facility, sibling facility via grants, external VNA via XDS-I.b) | INT | 1.5 | V2-02-01 | Resolution covers all three locations |
| V2-02-03 | Prefetch queue + edge staging: pull to reading-site edge cache; retry + dedupe (duplicate-safe) | BE | 2.0 | V2-02-02, S6-11 | Priors staged; 0 duplicates on re-trigger |
| V2-02-04 | Bandwidth guard: prefetch throttled to not degrade active-traffic bandwidth; off-peak window config | BE | 1.0 | V2-02-03 | Active-study p95 (PAC-SL-10) unaffected during prefetch |
| V2-02-05 | `PAC-SL-24` instrumentation: priors-available-at-read metric + KPI dashboard panel | BE | 0.5 | V2-02-03 | ≥ 95% availability measurable (PAC-SL-24) |

**Epic exit contribution:** E-V2-02 #1/#2 (prefetch engine + resolution).

### 3.2 Priors panel UI — E-V2-02 #3/4
**Source:** `PAC/04` PAC-UI-15; `PAC/06` PAC-AC-P01-03.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-02-06 | Priors panel: thumbnails with modality/anatomy labels, one-click swap, synchronized scrolling, list < 3 s | FE | 2.0 | V2-02-03 | PAC-AC-P01-03: priors open side-by-side < 3 s |
| V2-02-07 | Explicit "No prior studies found" state (no blank/empty UI) | FE | 0.5 | V2-02-06 | PAC-AC-P01-03 (no-priors case) |
| V2-02-08 | Priors indicator on worklist rows (PAC-UI-08) fed by the prefetch metric | FE | 0.5 | V2-02-05 | Indicator shows when priors available |

**Epic exit contribution:** E-V2-02 #3/4 (panel + indicator — VG-2).

### 3.3 Cross-tenant grants: DDL + RLS + helper — E-V2-03 #1/2/4
**Source:** `cross_tenant_grants_design.md` §2/§3/§4; `RBAC_matrix_spec.md` §6; CTG-AC-01/02/04.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-02-09 | DDL migration: `cross_tenant_grants` + `cross_tenant_grant_scopes` + CHECKs + RLS (`ctg_self`, `ctg_scopes_read`); no permissive write policies | BE | 1.5 | S1-03 (permissions seed) | Design §2/§3 applied; `chk_no_self_grant`/`chk_revoke_consistency` hold |
| V2-02-10 | `app_cross_accessible_facilities()` helper (SECURITY DEFINER, index-backed) + `rls_cross_read` SELECT policies on studies/series/instances/storage_objects/reports/worklist_entries/patients + join-policies for identifiers/coverages | BE | 2.5 | V2-02-09 | CTG-AC-01: granted reads return; CTG-AC-02: writes impossible; PAC-SL-25 (< 1 s) |
| V2-02-11 | Middleware: per-request facility-array cache; `cross_tenant.read` + `cross_tenant.denied` audit events with source/target/grant_id | BE | 1.5 | V2-02-10 | PAC-SL-25; 100% of cross-tenant events audited (PAC-SL-60) |
| V2-02-12 | DICOMweb enforcement: QIDO/WADO authorized only with ACTIVE grant covering `STUDY_READ`; unauthorized → empty/403 + audited denial | BE | 1.5 | V2-02-10, S4-08 | Design §4.1: cross-tenant pixel egress gated; denial logged |

**Epic exit contribution:** E-V2-03 #1/2/4 (grants enforced at DB + DICOMweb layers).

### 3.4 Cross-tenant grants: ops API + UI — E-V2-03 #5/6
**Source:** `cross_tenant_grants_api_contract.md` §3/§4/§5; `docs/specs/cross-tenant-grants_design.md`.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-02-13 | Ops API: `POST /api/cross-tenant-grants`, `POST /{id}/revoke`, `GET` list/detail, `/scopes`, `/mine` — Pydantic schemas + V1–V11 validation + error envelope | BE | 2.5 | V2-02-09 | CTG-API-01…07 pass; duplicate-create serialized (409) |
| V2-02-14 | Grant lifecycle audit in-txn (`cross_tenant_grant.created/revoked/expired`) | BE | 1.0 | V2-02-13 | CTG-AC-05; rollback removes grant + audit together |
| V2-02-15 | SYSTEM_ADMIN console UI: list/create/revoke, purpose-driven scope groups, status/expiry badges, route guard | FE | 2.5 | V2-02-13 | `cross-tenant-grants_design.md` parity; WCAG AA |
| V2-02-16 | Audit-logs UI `purpose`/`grant_id` facet + Data Access grouping (`cross_tenant.*`) | FE | 1.0 | V2-02-11, S1-16 | Super-admin query "all cross_tenant.read at CLINIC, 30 days" works |
| V2-02-17 | Expiry sweep (pg_cron daily) → `EXPIRED` + audit event; suspension interplay (target SUSPENDED → blocked at app layer) | BE | 1.0 | V2-02-09 | CTG-AC-03 (expiry) + CTG-AC-07 |

**Epic exit contribution:** E-V2-03 #5/6/7 (API + UI + sweep).

### 3.5 QC review screen — E-V2-08 #1
**Source:** `PAC/06` PAC-AC-P02-06; `PAC/04` PAC-UI-24; MVP acquisition paths (S2-11, S3-08).

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-02-18 | QC review screen: open acquired series, mark Adequate/Inadequate with mandatory reject reason code, redo flow offered | FE | 2.0 | V2-01-16 (viewer), S2-11 | PAC-AC-P02-06: reject reason mandatory; series flagged; redo offered |
| V2-02-19 | QC status plumbing: QC decision on study/series state machine + audit of QC actions | BE | 1.0 | V2-02-18 | QC action audited (PAC-SL-60) |

**Epic exit contribution:** E-V2-08 #1 (QC review — VG-4).

### 3.6 Cross-cutting: tests & gates — VG-2/VG-3 prerequisite
**Source:** CTG-AC-01…07; CTG-API-01…07; `PAC/05` PAC-SL-24/25/60/61.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| V2-02-20 | CTG test suite: unit + integration for API (CTG-API-01…07) and RLS behavior (CTG-AC-01…07 incl. merged-patient edge case) | QA | 2.0 | V2-02-09…17 | All CTG suites green |
| V2-02-21 | Prefetch SLA E2E: schedule 50 exams → prefetch → priors ≥ 95% at read; active-traffic p95 unaffected; no-priors explicit state | QA | 1.5 | V2-02-01…08 | PAC-SL-24/10 assertions green |
| V2-02-22 | RLS regression: home-facility behavior unchanged; cross-tenant reads denied without grant + audited; 0 cross-tenant PHI incidents | QA | 1.0 | V2-02-10 | PAC-SL-61 assertion; denial evidence |

---

## 4. Sprint Milestones

| Milestone | Target | Evidence |
| :--- | :--- | :--- |
| **Day 3** | Prefetch trigger + resolution live; grants DDL + helper in; QC screen scaffold | V2-02-01/02, V2-02-09/10, V2-02-18 started |
| **Day 5** | Prefetch queue + staging; `rls_cross_read` policies on core tables; ops API create/list | V2-02-03…05, V2-02-11…13 closed; CTG-AC-01 asserted |
| **Day 8** | Priors panel + indicator; revoke/sweep + audit facets; SYSTEM_ADMIN UI; QC actions | V2-02-06…08, V2-02-14…17, V2-02-19 closed |
| **Day 10 (demo)** | CTG + prefetch + QC E2E suites green; demo: schedule → prefetch → priors side-by-side; grant CLINIC → telerad read; revoke → denied + audited | V2-02-20…22; VG-2 pre-checks; VG-3 grants prerequisite; sprint review |

---

## 5. Sprint Definition of Done (acceptance checks)

| # | Check | Verifies | Method |
| :-: | :--- | :--- | :--- |
| D1 | Prefetch stages priors ≥ 95% at read; panel < 3 s; no-priors explicit | PAC-AC-P01-03, PAC-SL-24 | V2-02-21 E2E |
| D2 | Cross-facility priors authorized < 1 s and audited (grant path) | PAC-SL-25, CTG-AC-01 | V2-02-20 suite |
| D3 | Grants: CTG-AC-01…07 + CTG-API-01…07 green; revocation immediate; denied + audited; 0 writes cross-tenant | CTG suites, PAC-AC-P20-03 | V2-02-20 + V2-02-22 |
| D4 | DICOMweb cross-tenant pixels gated; denial logged | Design §4.1, PAC-SL-60 | V2-02-12 + V2-02-22 |
| D5 | QC: reject reason mandatory; series flagged; redo offered; QC audited | PAC-AC-P02-06 | V2-02-18/19 tests |
| D6 | Audit completeness incl. `cross_tenant.*`; RLS isolation intact | PAC-SL-60/61 | V2-02-22 |
| D7 | Engineering DoD: `tsc --noEmit` + `vite build` clean; unit tests green; migrations reviewed (grants DDL) | release-plan V2 §6 | CI gate |
| D8 | No P0/P1 open defects at sprint close | release-plan V2 §6 | Defect triage |

---

## 6. Risks & Watch Items (Sprint V2-02)

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| Prefetch bandwidth contention | PAC-SL-24 vs. PAC-SL-10 | Bandwidth guard (V2-02-04); off-peak; skip rules; active-traffic p95 monitored in E2E |
| Prior resolution misses (MPI gaps, external VNA) | PAC-SL-24 % | XDS-I.b read-across (V2-02-02); exception log for unresolvable priors |
| Grant RLS regression on home-facility reads | V2-02-22 isolation suite | OR-clause composes with `rls_all`; full isolation regression on every policy change |
| Revocation latency expectations | CTG-AC-03 | Per-request authorization (no token to expire); sweep + immediate deny both tested |
| **Shared epic coordination (grants)** | RIS v1.1 freeze dates | Single schema/API/UI implementation; contract-first; RIS `IDN_SCHEDULE_READ` reuse |
| BE capacity (19.5 of 20 dev-days) | Velocity | Grants DDL/RLS is the critical path; slip V2-02-08 (indicator) to slack; INT assists prefetch resolution |

---

## Traceability

| Source work item | Tasks |
| :--- | :--- |
| E-V2-02 #1 (prefetch trigger) | V2-02-01/02 |
| E-V2-02 #2 (resolution incl. cross-facility) | V2-02-02/03 |
| E-V2-02 #3 (skip/prioritize + bandwidth) | V2-02-03/04 |
| E-V2-02 #4 (priors panel) | V2-02-06/07 |
| E-V2-02 #5 (indicator + metric) | V2-02-05/08 |
| E-V2-03 #1 (DDL + RLS) | V2-02-09 |
| E-V2-03 #2 (helper + cross-read policies) | V2-02-10/11 |
| E-V2-03 #3 (DICOMweb enforcement) | V2-02-12 |
| E-V2-03 #4 (audit events) | V2-02-11/14 |
| E-V2-03 #5 (ops API) | V2-02-13 |
| E-V2-03 #6 (SYSTEM_ADMIN UI + audit facet) | V2-02-15/16 |
| E-V2-03 #7 (expiry sweep) | V2-02-17 |
| E-V2-08 #1 (QC review) | V2-02-18/19 |
| Cross-cutting (CTG suites, prefetch E2E, RLS regression) | V2-02-20…22 |
