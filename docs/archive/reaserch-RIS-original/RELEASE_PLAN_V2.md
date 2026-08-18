# Release Plan — RIS V2 (v1.1 Backlog + v2.0 Scope)

**Version:** 1.0 · **Date:** 2026-08-05 · **Source:** `requrements/RIS/PRD.md` (§5.1 phased rollout, §2.4 non-goals, §3 AI), `requrements/RIS/RELEASE_PLAN.md` (§4 post-MVP backlog), `requrements/cross_tenant_grants_design.md` + `_api_contract.md` (IDN grants, shared with PACS E-V2-03), `requrements/PACS/RELEASE_PLAN_V2.md` (coordination), `requrements/pacs_v2_roadmap.md` (§3 cross-system), `requrements/RIS/06_acceptance_criteria.md` (RIS-AC-*), `requrements/RIS/05_metrics_and_slas.md` (RIS-SL-*)
**Planning assumptions:** 2-week sprints · one dedicated squad — **RIS-V2** (2 backend · 1 frontend · part-time integration engineer for HL7/FHIR conformance · QA) — plus the shared **Platform** squad for cross-tenant grants (same implementation as PACS E-V2-03, coordinated with the PACS V2 release) and the **EMR-V2** squad for portal/patient-facing delivery. **V2 program estimated at 12 sprints (~6 months): Phase 1 (v1.1 backlog) = 7 sprints; Phase 2 (v2.0 scope) = 5 sprints.**

---

## 1. Release Overview

**What "V2" means in this plan:** the entire **post-MVP program** — Phase 1 executes the **v1.1 backlog** (prior-auth engine, reminders, denial rework + unbilled dashboards, template manager, multi-site scheduling + IDN grants, speech-recognition polish, FHIR read APIs), and Phase 2 executes the **PRD §5.1 v2.0 scope** (full FHIR read/write, portal delivery, AI-assisted coding, chargeback analytics, pre-registration). Phase-1 items are prerequisites for most Phase-2 items (IDN grants → chargeback analytics; FHIR read → full FHIR).

**Already delivered in MVP v1.0 (NOT re-planned):** conflict-free single-site scheduling, MWL/MPPS loop, tracking board, reporting + SR integration (base), critical results loop, ORU distribution, auto charge drop + unbilled aging view (base), eligibility stub (v1 local only), read-only FHIR endpoints (D), platform/interface foundations (shared with RIS release). **Lifted from v1 non-goals into V2:** cross-facility IDN scheduling (read-only grants — was "not cross-facility writes"); AI-assisted coding (was roadmap `O`); digital pre-registration (was roadmap).

| Phase | Scope | Est. duration | Exit gate |
| :--- | :--- | :--- | :--- |
| **Phase 1 (v1.1 backlog)** | Prior-auth tracking + booking rules, appointment reminders, denial rework + unbilled dashboards, report/template manager, multi-site scheduling + IDN grants (`IDN_SCHEDULE_READ`, shared with PACS), speech-recognition polish, FHIR read APIs | 7 sprints | **RVG-1…RVG-4** |
| **Phase 2 (v2.0)** | Full FHIR (read/write, shared server layer with PACS), portal delivery, AI-assisted coding (utility gate), chargeback analytics, pre-registration | 5 sprints | **RVG-5…RVG-6** |

**Non-goals (unchanged from PRD §2.4):** AI model training (RIS integrates SR + AI-assisted coding suggestions only) · cross-facility *writes* (IDN scheduling reads availability across sites; bookings always write to the user's home facility — `cross_tenant_grants_design.md` §6.3) · non-radiology scheduling (OR scheduling, infusion) · pixel storage/viewing (PACS surface).

---

## 2. V2 Exit-Gate Acceptance Criteria (Definition of "releasable")

> **Runnable form:** replicate the PACS pattern — extend the system go-live checklist with the RVG gates at each phase cutover (Phase-1 cutover after R2-S7; V2 cutover after R2-S12). Exit-gate detail: §4 sprint groups R2-04 (v1.1 gates) and R2-06 (v2.0 gates).

### Phase 1 gates (v1.1 releasable)

| Gate | Criterion | Verifies |
| :-: | :--- | :--- |
| **RVG-1** | Prior-auth: ≥ 95% of required exams authorized pre-scan (RIS-SL-36); missing/expired/denied auth blocks booking with audited override; expiry alerts ≤ 7 days; approved auth links to order and claim | RIS-AC-P03-03, RIS-SL-36, RIS-UI-16/33 |
| **RVG-2** | Denial & revenue: unbilled aging $0 actionable > 5 days sustained (RIS-SL-41); denial rework queue with reason codes + correction + resubmission with history; reminders send on configured channels with opt-out honored (100% logged); template manager versioned with one-click rollback | RIS-AC-P05-02, RIS-AC-P03-02, RIS-AC-P06-03, RIS-SL-41 |
| **RVG-3** | IDN multi-site scheduling + grants: `IDN_SCHEDULE_READ` grants live (shared implementation with PACS E-V2-03 — one schema/API/UI); availability spans all sites with shared resource visibility; authorization < 1 s and 100% audited; bookings write to home facility only; **0 cross-tenant writes possible**; site chargeback data captured per booking | RIS-AC-P03-04, CTG-AC-01…07, RIS-SL-61, PAC-SL-25 (shared) |
| **RVG-4** | v1.1 continuity: FHIR read APIs conformance green; SR polish acceptance (dictation verify loop); 0 P0/P1 open; UAT sign-off by scheduler (prior-auth/multi-site), biller (denial), RIS admin (templates/grants), radiologist (SR) | PRD §2.3, RIS-SL-60/61 |

### Phase 2 gates (v2.0 releasable)

| Gate | Criterion | Verifies |
| :-: | :--- | :--- |
| **RVG-5** | Full FHIR read/write conformance (shared FHIR server layer with PACS E-V2-10; RLS on all routes); portal delivery live (result notifications with opt-out, release policy, read-only consent-gated view, audit); pre-registration data visible at check-in | RIS-SL-60, RIS-AC-P08-02 (delivery), RIS-UI-23 |
| **RVG-6** | v2.0 program: AI-assisted coding 30-day pilot acceptance ≥ 90% (gate — else remediation plan); chargeback analytics live; charge capture ≥ 98% and unbilled $0 > 5 days sustained (RIS-SL-40/41); 0 P0/P1; UAT sign-off (biller, manager, scheduler, front desk) | PRD §3, RIS-SL-40/41 |

---

## 3. V2 Epics & Sprint-Sized Work Items

> Work items sized ≤ 3 dev-days (2–4 per sprint per engineer). Story/AC/UI/SL IDs reference the RIS requirement docs and the cross-tenant-grants design/contract. Backend = schema+API; Frontend = UI; Integration = HL7/FHIR/payer/portal.

### Phase 1 — Epics (v1.1 backlog)

### E-RIS2-01 · Prior-Auth Engine (Scheduler + Biller)
**Source:** RIS-US-P03-03; RIS-AC-P03-03; RIS-SL-36; RIS-UI-16/33; RBAC `PRIOR_AUTH_*` (NEW in `RBAC_matrix_spec.md` §8). **Dependency:** order model + eligibility stub (E-RIS-03 #5).
> **Task-level detail (R2-S1–S2):** `requrements/sprint_r2_01_prior_auth_reminders_detail.md` — task IDs R2-01-01…R2-01-15.

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | Prior-auth status model per order: NOT_REQUIRED / REQUIRED / PENDING / APPROVED / DENIED / EXPIRED + CPT linkage | M | RIS-AC-P03-03: flag + link to claim |
| 2 | Live payer/eligibility integration (extend MVP stub to real provider API) + manual fallback | M | RIS-AC-P04-02 (v2 live) |
| 3 | Booking rule: missing/denied auth blocks booking; **audited override** with reason | M | RIS-AC-P03-03 (blocked + override cases) |
| 4 | Expiry alerts ≤ 7 days + expiring-auth reminder | M | RIS-AC-P03-03 (alert case) |
| 5 | Prior-auth linkage on claim line; missing auth highlighted (RIS-UI-33) | D | Billing view parity |
| 6 | Prior-auth dashboard (status mix, aging, denial reasons) | D | Manager visibility |

**Epic exit:** RVG-1; RIS-AC-P03-03 + RIS-SL-36.

### E-RIS2-02 · Appointment Reminders (Scheduler / Patient comms)
**Source:** RIS-US-P03-02; RIS-AC-P03-02; RIS-UI-17; RIS-M05.

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | Per-order reminder config (channel SMS/email/phone, time, template) | M | RIS-AC-P03-02 config |
| 2 | Provider integrations + **opt-out registry honored** | M | Opt-out honored (RIS-AC-P03-02) |
| 3 | Send success/failure logging + ≤ 5-min alerting | M | 0 silent send failures; every send logged (RIS-SL-60) |
| 4 | No-show analytics feed | D | No-show trend metric |

**Epic exit:** RVG-2 (reminders part); RIS-AC-P03-02.

### E-RIS2-03 · Denial Rework & Unbilled Dashboards (Biller)
**Source:** RIS-US-P05-02; RIS-AC-P05-02; RIS-SL-41; RIS-M04 (835).

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | Denial intake (835) → rework queue with reason codes + priority | M | RIS-AC-P05-02: appears with reason |
| 2 | Correction workflow + resubmission; full history preserved | M | RIS-AC-P05-02: resubmit + history |
| 3 | Unbilled aging dashboard ($0 actionable > 5 days), daily reconcile | M | RIS-SL-41 |
| 4 | Prior-auth linkage reuse (E-RIS2-01 #5) | D | Claim line parity |

**Epic exit:** RVG-2 (denial part); RIS-AC-P05-02 + RIS-SL-41.

### E-RIS2-04 · Template Manager (RIS Admin)
**Source:** RIS-US-P06-03; RIS-AC-P06-03; RIS-UI-36.

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | Scheduling templates + procedure/CPT maps, versioned | M | RIS-AC-P06-03: versioned apply |
| 2 | Report template manager: tree, version history, publish/rollback, permissions (RIS-UI-36) | M | Template parity |
| 3 | Site-apply with duplicate validation; **one-click rollback** | M | RIS-AC-P06-03: rollback verified |

**Epic exit:** RVG-2 (templates part); RIS-AC-P06-03.

### E-RIS2-05 · Multi-Site Scheduling & IDN Grants (Platform — shared with PACS E-V2-03)
**Source:** RIS-US-P03-04; RIS-AC-P03-04; RIS-WF7; `cross_tenant_grants_design.md` (purpose `IDN_SCHEDULE_READ`, scope `SCHEDULE_READ` only); `cross_tenant_grants_api_contract.md`; RIS-UI-18. **Coordination:** PACS V2-02 (V2-S3–S4) implements the grants DDL/RLS/API/UI once; RIS reuses — one schema, one API, one SYSTEM_ADMIN console.
> **Task-level detail (R2-S5–S6):** `requrements/sprint_r2_03_idn_grants_scheduling_detail.md` — task IDs R2-03-01…R2-03-11; PACS-side tasks in `requrements/sprint_v2_02_priors_grants_detail.md` (V2-02-09…V2-02-17).

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :-: |
| 1 | `IDN_SCHEDULE_READ` grants: shared DDL/RLS/helper/API/UI (join PACS E-V2-03 implementation; no divergence) | M | CTG-AC-01…07 + CTG-API-01…07 green |
| 2 | Multi-site availability search: shared resource pool, sites side-by-side, site selection recorded (RIS-UI-18) | M | RIS-AC-P03-04: availability spans sites |
| 3 | Booking writes to **home facility only** (`SCHEDULE_WRITE` + RLS `WITH CHECK`); site recorded on appointment | M | Design §6.3: 0 cross-tenant writes |
| 4 | Site chargeback data capture per booking | M | RIS-AC-P03-04: chargeback captured |
| 5 | Per-site SLA preservation; authorization < 1 s + 100% audit (`cross_tenant.read`/`.denied`) | M | RIS-SL-61, PAC-SL-25 (shared) |

**Epic exit:** RVG-3; RIS-AC-P03-04 + CTG-AC-01…07; 0 cross-tenant PHI incidents (RIS-SL-61).

### E-RIS2-06 · Speech-Recognition Polish (Radiologist)
**Source:** RIS-US-P01-02 (SR, D); RIS-M06.

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | Accuracy tuning + specialty lexicons (MSK, neuro, cardiac) | M | Dictation verify-loop acceptance |
| 2 | Verification highlight loop polish (uncertain words) | M | RIS-AC-P01-02 (SR) |
| 3 | FHIR `DocumentReference` export of dictated report | D | DocumentReference smoke test |

**Epic exit:** RVG-4 (SR part); radiologist UAT.

### E-RIS2-07 · FHIR Read APIs (v1.1)
**Source:** MVP D-item (read-only FHIR) promoted to robust v1.1: `Patient`, `ServiceRequest`, `DiagnosticReport`, `ImagingStudy` read + RLS enforcement.

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | FHIR read API surface: Patient/ServiceRequest/DiagnosticReport/ImagingStudy + search params + pagination | M | Conformance smoke tests |
| 2 | RLS enforcement on all FHIR routes (incl. cross-facility denial) | M | RIS-SL-61; `cross_tenant.denied` on 0-grant reads |
| 3 | FHIR conformance harness + version pinning | M | Suite green; version drift caught |

**Epic exit:** RVG-4 (FHIR part); conformance suite green.

### Phase 2 — Epics (v2.0 scope)

### E-RIS2-08 · Full FHIR (read/write)
**Source:** PRD §5.1 v2.0; shared FHIR server layer with PACS E-V2-10 (`pacs_v2_roadmap.md` §3). **Dependency:** E-RIS2-07; PACS V2-05.

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | `ServiceRequest` create/update (order status writes) + `DiagnosticReport` create (results) | M | Write conformance vs. test server |
| 2 | FHIR search coverage + RLS on all routes (extend E-RIS2-07) | M | Search parity; isolation |
| 3 | Shared conformance tooling with PACS E-V2-10; version pinning | M | One harness, both systems |

**Epic exit:** RVG-5 (FHIR part); conformance green.

### E-RIS2-09 · Portal Delivery (Patient comms — overlaps PACS E-V2-15 + EMR portal)
**Source:** RIS-M05; RIS-AC-P08-02 (delivery); PRD §5.1 v2.0; PACS E-V2-15 share pattern.

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | Result-availability notifications (opt-out honored) | M | RIS-AC-P08-02; 0 silent failures |
| 2 | Release policy (HIM review) + secure share links with expiry/revocation (reuse PACS V2-04-02 pattern) | M | RIS-SL-60 audit |
| 3 | Portal results view: read-only, consent-gated, no PHI in URLs | M | Patient-facing view live |

**Epic exit:** RVG-5 (portal part); RIS-SL-60.

### E-RIS2-10 · AI-Assisted Coding (Biller — roadmap `O`, gated)
**Source:** PRD §3 (AI-assisted coding suggestions, roadmap `O`); RIS-M04. **Gate:** ≥ 90% coder acceptance on a 30-day pilot.

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | Coding suggestion service: CPT/ICD-10 from procedure + signed report, with confidence | M | Suggestions confirmable |
| 2 | Accept/override workflow, every suggestion/override audited | M | RIS-SL-60; audit rows |
| 3 | 30-day pilot ≥ 90% coder acceptance → gate decision | M | RVG-6 gate evidence |

**Epic exit:** RVG-6 (AI part); gate decision recorded.

### E-RIS2-11 · Chargeback Analytics (Department Manager)
**Source:** RIS-AC-P03-04 (chargeback data); RIS-SL-40/41; RIS-P08.

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | Per-site chargeback aggregation from bookings (E-RIS2-05 #4) | M | Chargeback by site reconciles |
| 2 | Manager dashboard: chargeback, denial rate, unbilled aging by site, drill-down | M | Dashboard parity (RIS-P08) |

**Epic exit:** RVG-6 (analytics part); RIS-SL-40/41 sustained.

### E-RIS2-12 · Pre-Registration (Front Desk / Patient)
**Source:** RIS-UI-23; PRD §5.1 v2.0.

| # | Work item | Size | Done when |
| :-: | :--- | :-: | :--- |
| 1 | Portal-submitted pre-registration data visible for completion before arrival | M | RIS-UI-23 parity |
| 2 | One-click completion at check-in (extends E-RIS-03 check-in) | D | Check-in pre-fill |

**Epic exit:** RVG-5 (pre-reg part); RIS-UI-23.

---

## 4. Sprint Roadmap (V2, 2-week sprints)

> **Task-level sprint detail docs (mirroring the PACS `sprint_v2_*` pattern):** `sprint_r2_01_prior_auth_reminders_detail.md` (R2-01-01…15), `sprint_r2_02_denial_templates_sr_detail.md` (R2-02-01…14), `sprint_r2_03_idn_grants_scheduling_detail.md` (R2-03-01…11), `sprint_r2_04_fhir_read_gates_detail.md` (R2-04-01…08), `sprint_r2_05_fhir_portal_detail.md` (R2-05-01…10), `sprint_r2_06_ai_chargeback_gates_detail.md` (R2-06-01…16).

| Sprint | Phase | Focus (epics) | Key milestone |
| :--- | :--- | :--- | :--- |
| R2-S1–S2 | v1.1 | E-RIS2-01 (prior-auth) + E-RIS2-02 (reminders) | Prior-auth blocks denied booking with audited override; reminders send with opt-out |
| R2-S3–S4 | v1.1 | E-RIS2-03 (denial) + E-RIS2-04 (templates) + E-RIS2-06 (SR polish) | Rework queue + unbilled $0 > 5 days; templates versioned/rollback |
| R2-S5–S6 | v1.1 | E-RIS2-05 (IDN grants + multi-site) — **concurrent with PACS V2-S3–S4** | Grants live (shared); multi-site availability + home-facility writes |
| R2-S7 | v1.1 | E-RIS2-07 (FHIR read) + v1.1 gates | **RVG-1…RVG-4**; Phase-1 go/no-go |
| R2-S8–S9 | v2.0 | E-RIS2-08 (full FHIR) + E-RIS2-09 (portal) — **concurrent with PACS V2-05/15** | FHIR writes conformance; portal delivery live |
| R2-S10–S11 | v2.0 | E-RIS2-10 (AI coding) + E-RIS2-11 (chargeback) + E-RIS2-12 (pre-reg) | AI 30-day pilot; chargeback dashboards |
| R2-S12 | v2.0 | Hardening + v2.0 gates | **RVG-5…RVG-6**; V2 go/no-go |

---

## 5. Critical Path & Dependencies

```
Prior-Auth (E-RIS2-01) ──► Denial Rework (E-RIS2-03) ──► Chargeback Analytics (E-RIS2-11)
Reminders (E-RIS2-02) ∥ Templates (E-RIS2-04) ∥ SR Polish (E-RIS2-06)
IDN Grants (E-RIS2-05) ──► Multi-site scheduling ──► (PACS E-V2-03 shared)
FHIR Read (E-RIS2-07) ──► Full FHIR (E-RIS2-08) ──► Portal Delivery (E-RIS2-09) ──► Pre-Reg (E-RIS2-12)
AI-Assisted Coding (E-RIS2-10) ──► RVG-6 gate
```

- **Blocking:** E-RIS2-05 (grants) before multi-site scheduling before chargeback analytics; E-RIS2-07 before E-RIS2-08.
- **Cross-system coordination (contract between releases):**
  - **PACS V2 (E-V2-03, V2-S3–S4)** — `cross_tenant_grants` implementation is **shared**: RIS `IDN_SCHEDULE_READ` uses the same DDL/RLS/helper/API/SYSTEM_ADMIN UI (V2-02-09…17). Align migration + freeze dates; a missed PACS grants handoff blocks R2-S5 start.
  - **PACS V2 (E-V2-10, E-V2-15)** — full-FHIR server layer and patient/share-link delivery overlap with E-RIS2-08/09; share conformance tooling and the FHIR server layer.
  - **EMR V2 portal** — patient-facing delivery is coordinated with the EMR portal release (EMR `E-EMR2-01`); one release policy, one opt-out registry.
- **External:** payer prior-auth APIs, clearinghouse 835, SMS/email providers, portal/SSO (MFA), SR vendor lexicon packs.

---

## 6. Definition of Done (per work item)

- Backend: schema migration reviewed; API behind `@requires_permission`; Pydantic validation; unit tests green; audit event emitted where applicable (incl. `cross_tenant.*` for grant-scoped reads).
- Frontend: Ant Design conventions, design tokens, WCAG 2.1 AA, `tsc --noEmit` + `vite build` clean.
- Integration: HL7/FHIR/payer conformance verified in lab; exception queue covered; grant RLS regression (0 cross-tenant writes) on every grants change.
- Acceptance: the item's RIS-AC-* criteria pass in staging; traceability link updated.
- No P0/P1 defects open at sprint close.

---

## 7. Risks & Watch Items

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| IDN grants coordination slip (PACS V2-02) | V2-02-17 closure | Contract-first shared implementation; freeze dates aligned; single schema/API/UI |
| Prior-auth integration variance (payer APIs) | RIS-SL-36 | Provider API + manual fallback; booking block + audited override; expiry alerts |
| AI-assisted coding < 90% acceptance | RVG-6 pilot | Pilot gates rollout; audited suggestions; remediation plan documented |
| Chargeback data drift across sites | RIS-SL-40/41 | Capture at booking time (E-RIS2-05 #4); daily reconcile; by-site dashboard |
| Portal PHI exposure | RIS-SL-60 | Release policy; no PHI in URLs; share expiry/revocation; audit every access |
| Denial rework volume exceeds capacity | Unbilled aging | Reason-code triage + resubmission automation; escalation on aging |
| Scope creep into PACS/EMR domains | Non-goals (PRD §2.4) | RIS schedules/authorizes/bills radiology; never stores pixels or charts |

---

## Traceability

| Source work item | Epics |
| :--- | :--- |
| RIS-US-P03-03, RIS-AC-P03-03, RIS-SL-36 (prior-auth) | E-RIS2-01 |
| RIS-US-P03-02, RIS-AC-P03-02 (reminders) | E-RIS2-02 |
| RIS-US-P05-02, RIS-AC-P05-02, RIS-SL-41 (denial/unbilled) | E-RIS2-03 |
| RIS-US-P06-03, RIS-AC-P06-03 (template manager) | E-RIS2-04 |
| RIS-US-P03-04, RIS-AC-P03-04, IDN_SCHEDULE_READ grants | E-RIS2-05 |
| RIS-US-P01-02 (SR polish) | E-RIS2-06 |
| MVP FHIR D-item → v1.1 read APIs | E-RIS2-07 |
| PRD §5.1 v2.0 full FHIR (shared with PACS E-V2-10) | E-RIS2-08 |
| PRD §5.1 v2.0 portal delivery (overlaps PACS E-V2-15) | E-RIS2-09 |
| PRD §3 AI-assisted coding (roadmap O, gate ≥ 90%) | E-RIS2-10 |
| RIS-AC-P03-04 chargeback + RIS-SL-40/41 | E-RIS2-11 |
| RIS-UI-23 pre-registration | E-RIS2-12 |
| RVG-1…RVG-6 gates | §4 sprint groups R2-04/R2-06 |
