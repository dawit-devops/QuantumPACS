# Product Requirements Document — RIS (Radiology Information System)

**Version:** 1.0 · **Date:** 2026-08-04 · **Type:** Engineering build spec · **Product surface:** RIS
**Status:** Active — this PRD is the **top-level source of truth** for the RIS surface. It summarizes and links the detailed requirements; implementation detail lives in the referenced documents.

| Source of truth | Document |
| :--- | :--- |
| Personas (human/institution/machine) + RBAC | `requrements/RIS/01_persona_catalog.md` |
| End-to-end workflows (swimlanes) | `requrements/RIS/02_end_to_end_workflows.md` |
| User stories (EARS, 33 stories) | `requrements/RIS/03_user_stories.md` |
| UI/UX requirements | `requrements/RIS/04_uiux_requirements.md` |
| Metrics & SLAs | `requrements/RIS/05_metrics_and_slas.md` |
| Acceptance criteria (RIS-AC-*) | `requrements/RIS/06_acceptance_criteria.md` |
| Roles/permissions/tenant scoping | `requrements/RBAC_matrix_spec.md` |
| Cross-tenant scheduling (IDN) | `requrements/cross_tenant_grants_design.md` + `_api_contract.md` |
| Data model (orders, MWL, reports, billing) | `research/pacs-ris-schema.sql`, `research/pacs-ris-multitenancy.md` |
| PACS hand-off (viewer context, MPPS echo) | `requrements/PACS/PRD.md`, `research/pacs-ris-research.md` |

---

## 1. Executive Summary

### Problem Statement

Radiology departments run fragmented paper/legacy RIS workflows: manual re-keying at the scanner, double-booked rooms, invisible order status, slow report turnaround, untracked critical results, and revenue leakage from missed charges — all in a multi-site, HIPAA-governed environment that a single-facility RIS cannot serve.

### Proposed Solution

A **RIS module** on the shared multi-tenant SaaS platform: order intake (HL7 ORM/FHIR), conflict-free multi-site scheduling, Modality Worklist (MWL) serving and MPPS consumption, a live tracking board, prioritized reading with structured reporting and critical-results alerting, HL7 ORU report distribution, and revenue-cycle capture — tenant-isolated via RLS, integrated end-to-end with PACS and EMR.

### Success Criteria (KPIs — measured at go-live and quarterly; baseline in `05_metrics_and_slas.md`)

| KPI | Target | Source |
| :--- | :--- | :--- |
| MWL query response at console | **< 1 s** p95 | RIS-SL-10 |
| Order intake → accessible for scheduling | **< 1 min** after ORM/FHIR | RIS-SL-20 |
| MPPS → tracking board update | **< 5 s**; 100% echo to PACS | RIS-SL-22 |
| Signed report → EMR delivery | **< 5 min** after sign-off; 100% delivered | RIS-SL-24 |
| Interface message delivery | **> 99.9%**, failures alerted ≤ 5 min | RIS-SL-23 |
| % exams via MWL without manual entry | **≥ 98%** | RIS-SL-33 |
| Scheduling conflicts / prior-auth before scan | **0 conflicts**; **≥ 95%** authorized pre-scan | RIS-SL-34/36 |
| Charge capture / unbilled aging | **≥ 98%**; **$0** actionable > 5 days | RIS-SL-40/41 |
| Audit completeness / cross-tenant incidents | **100%** events logged; **0** PHI incidents | RIS-SL-60/61 |
| Report TAT (STAT / Inpatient / Outpatient) | < 30–60 min / < 2–4 h / 24–48 h | RIS-SL-30–32 |

---

## 2. User Experience & Functionality

### 2.1 User Personas

Full catalog with goals, tasks, pains, and permission mapping: `requrements/RIS/01_persona_catalog.md` §1–§3.

| ID | Persona | Core need |
| :-: | :--- | :--- |
| RIS-P01 | Radiologist | Priority worklist, fast structured reporting, critical-result communication |
| RIS-P02 | Technologist | MWL auto-fill, live status via MPPS, add-on handling |
| RIS-P03 | Scheduler / Referral Coordinator | Conflict-free multi-site booking, prior-auth, reminders |
| RIS-P04 | Front-Desk / Registration Clerk | Clean demographics/insurance, one-click check-in, MPI dedup |
| RIS-P05 | Radiology Billing Coder | Auto CPT/ICD-10, unbilled/denial rework, clean claims |
| RIS-P06 | RIS Administrator | Accession uniqueness, interfaces, templates/code maps, MPI |
| RIS-P07 | Department Manager | TAT/utilization dashboards with drill-down |
| RIS-P08 / RIS-P09 | Referring MD / ED MD | Real-time order status; results & critical alerts delivered |
| RIS-P19 / RIS-P20 | Tenant Admin / Super Admin | Configure sites/schedules; provision, meter, bill, support |
| RIS-M01–M06 | **Machines**: modalities (MWL/MPPS), HIS/EMR, PACS, billing/clearinghouse, portal/SMS, dictation | Standards-based non-human actors (DICOM MWL/MPPS, HL7 v2, FHIR) |

### 2.2 User Stories

33 stories, full EARS text and priorities: `requrements/RIS/03_user_stories.md`. Representative examples:

- **As a scheduler**, I want conflict-free multi-modality/multi-site booking with room, technologist, and contrast checks, so that double-bookings never happen. *(RIS-US-P03-01)*
- **As a technologist**, I want the modality worklist populated automatically from scheduled orders, so that I never re-type patient data at the console. *(RIS-US-P02-01)*
- **As a radiologist**, I want one-action critical-results flagging with tracked notification and escalation, so that urgent findings are acted on and documented for HIPAA. *(RIS-US-P01-03)*
- **As a billing coder**, I want CPT/ICD-10 automatically suggested from the ordered procedure and signed report, so that coding is fast and accurate. *(RIS-US-P05-01)*
- **As a referring physician**, I want to place imaging orders from my EMR and see order status in real time, so that I know where my patients' exams stand. *(RIS-US-P08-01)*

Story matrix (per persona; priority counts **M=25, D=8, O=0, total=33**):

| Persona | Stories (IDs) |
| :--- | :--- |
| Radiologist | RIS-US-P01-01…06 (worklist, templates+SR, critical results, sign & distribute, viewer launch, WIP drafts) |
| Technologist | RIS-US-P02-01…03 (MWL, live MPPS, add-ons) |
| Scheduler | RIS-US-P03-01…05 (conflict-free booking, reminders, prior-auth, multi-site, day view) |
| Front Desk | RIS-US-P04-01…03 (registration+MPI, eligibility, one-click check-in) |
| Billing Coder | RIS-US-P05-01…03 (suggested codes, unbilled/denial queue, auto charge drop) |
| RIS Admin | RIS-US-P06-01…04 (accession uniqueness, interface health, config, MPI maintenance) |
| Manager | RIS-US-P07-01 (dashboards) |
| Referring MD / ED MD | RIS-US-P08-01…02, RIS-US-P09-01…02 (status, results, STAT prioritization, critical alerts) |
| Tenant/Super Admin | RIS-US-P19-01…02, RIS-US-P20-01…02 (config, usage, atomic provisioning, audited cross-tenant) |

### 2.3 Acceptance Criteria ("Done" definitions)

Every story maps to testable Given/When/Then criteria: `requrements/RIS/06_acceptance_criteria.md` (RIS-AC-P01-01…RIS-AC-P20-02). Headline "done" gates per area:

- **Scheduling path:** conflicts system-enforced (0); prior-auth blocks denied bookings with audited override; reminders send with opt-out honored. *(RIS-AC-P03-*)*
- **Order-to-result path:** ORM → accessible < 1 min; scheduled orders 100% served on MWL; MPPS updates tracking board < 5 s and echoes to PACS; signed report delivered to EMR < 5 min. *(RIS-AC-P01/02/08, RIS-SL-20–24)*
- **Critical results:** 100% notified with tracked acknowledgment + escalation; flag embedded in ORU/FHIR. *(RIS-AC-P01-03, RIS-SL-25)*
- **Billing path:** charge drop auto on sign-off (capture ≥ 98%); unbilled aging $0 > 5 days; denial rework with reason codes. *(RIS-AC-P05-*, RIS-SL-40–43)*
- **Platform:** atomic tenant provisioning < 15 min; IDN cross-facility scheduling via audited `IDN_SCHEDULE_READ` grants (CTG-AC-01…07). *(RIS-AC-P19/20, `cross_tenant_grants_design.md`)*

### 2.4 Non-Goals (explicitly out of scope)

- **Not** pixel storage, retrieval, or diagnostic viewing — that is the **PACS** surface (`requrements/PACS/PRD.md`); RIS launches the PACS viewer in context.
- **Not** the longitudinal clinical chart, medication workflows, or patient portal content — **EMR** surface (`requrements/EMR/PRD.md`).
- **Not** image *acquisition* (modalities capture; RIS serves MWL and consumes MPPS).
- **Not** e-prescribing, lab result release, or BCMA — EMR surface.
- **Not** AI model training — RIS *integrates* speech recognition and (roadmap) AI-assisted coding suggestions.
- **Not** cross-facility *writes* — IDN scheduling reads availability across sites but bookings always write to the user's home facility (`cross_tenant_grants_design.md` §6.3).
- **Not** non-radiology scheduling (OR scheduling, infusion) in v1 — roadmap.

---

## 3. AI System Requirements (If Applicable)

Two AI-adjacent integrations: **speech recognition/dictation** (core, `D` in RFP D16) and **AI-assisted coding suggestions** (roadmap `O`).

### 3.1 Tool / API Requirements

| Requirement | Detail | Source |
| :--- | :--- | :--- |
| Dictation into structured templates | SR engine transcribes into active template fields with uncertain-word highlighting and verification loop | RIS-M06, RIS-WF4 (and PACS `PAC-WF2` for viewer-side dictation) |
| Critical-finding dictation guard | Keywords/flags never auto-finalize; critical findings require radiologist confirmation before notification | Derived requirement of RIS-US-P01-03 (enforced in RIS-WF4) |
| Suggested CPT/ICD-10 | Derived from ordered procedure + signed report; coder confirms/adjusts (never auto-bills) | RIS-US-P05-01 |

### 3.2 Evaluation Strategy

- **Transcription quality:** ≥ 95% field-level accuracy on the reference template library; uncertain words highlighted at ≥ 95% of true uncertainty events (recall), verified in UAT by radiologists.
- **No silent acceptance:** 100% of dictated reports pass a human verification step before sign; critical-finding flags require explicit confirmation.
- **Coding suggestion accuracy (roadmap gate):** ≥ 90% first-pass coder acceptance on a 30-day pilot before enabling for all procedures; every suggestion/override audited.

---

## 4. Technical Specifications

### 4.1 Architecture Overview

RIS is the **workflow orchestrator** between EMR (orders/results) and PACS (study status/viewer). Data flow per `requrements/RIS/02` (RIS-WF1…WF9) and `research/pacs-ris-research.md` §6:

```
EMR/HIS ──HL7 ORM / FHIR ServiceRequest──▶ Order Intake (accession, priority, indication)
                                              │
                       Scheduling engine ──► appointment (room/modality/tech, EXCLUDE conflict guard)
                                              │
                                              ▼
                                 Modality Worklist (C-FIND) ──► Modality ──MPPS──► Tracking Board
                                              │                                    │
                        Reporting (templates + dictation + critical results) ◀── PACS viewer launch
                                              │
                                              ▼
                        Sign ──▶ HL7 ORU / FHIR DiagnosticReport ──▶ EMR  +  charge → billing → 837/835
```

Microservice domains: **Order Intake, Scheduling, Worklist (MWL SCP), MPPS Consumer, Tracking/Status, Reporting, Results Distribution, Billing/RCM, Interface Engine (HL7), Notifications**. Statuses follow the order lifecycle: Ordered → Scheduled → Arrived → In Progress → Completed → Read → Signed.

### 4.2 Integration Points

| Integration | Protocol | Contract reference |
| :--- | :--- | :--- |
| HIS/EMR | HL7 v2 ADT/ORM/ORU; FHIR R4 `ServiceRequest`/`DiagnosticReport` | RIS-WF1, WF4, WF5 |
| Modalities | DICOM C-FIND (MWL); N-CREATE/N-SET (MPPS) | RIS-WF1 |
| PACS | MPPS echo; viewer launch deep-link (StudyInstanceUID); report context | `PACS/PRD.md` §4.2 |
| Billing / PM & clearinghouse | HL7 charge messages; X12 837/835 | RIS-WF6 |
| Patient portal / SMS/email | Reminders + result availability; opt-out honored | RIS-WF5 (M05) |
| Speech recognition | WebSocket/API; FHIR `DocumentReference` for transcripts | RIS-WF4 (M06) |
| Auth | OAuth2/OIDC + SSO; machine actors via service keys (least privilege) | RBAC spec §6 |
| DB | PostgreSQL 17: `orders`, `order_procedures`, `appointments` (EXCLUDE no-double-book), `worklist_entries`, `mpps_events` (partitioned), `reports`/`report_versions`, `critical_result_notifications`, `charges`/`claims`, `hl7_messages` (partitioned) | `research/pacs-ris-schema.sql` §5, §7–§9 |

### 4.3 Security & Privacy

| Control | Requirement | Source |
| :--- | :--- | :--- |
| Tenant isolation | RLS on `facility_id` for all clinical rows (+ `WITH CHECK`); `NOBYPASSRLS` + `FORCE ROW LEVEL SECURITY` in prod | `pacs-ris-multitenancy.md` §3 |
| Accession integrity | Unique per facility (partial unique index) — 0 collisions | RIS-US-P06-01 |
| Cross-tenant (IDN scheduling) | Read-only `IDN_SCHEDULE_READ` grants; authorization < 1 s; bookings write to home facility only | `cross_tenant_grants_design.md` |
| RBAC | `ORDER_*`, `SCHEDULE_*`, `WORKLIST_*`, `REPORT_*`, `REPORT_SIGN`, `CRITICAL_RESULTS_WRITE`, `BILLING_*`, `PRIOR_AUTH_*`, `INTERFACE_*`, `AUDIT_READ` | `RBAC_matrix_spec.md` |
| Encryption | TLS 1.2+ in transit; AES-256 at rest | RIS-SL-62 |
| Audit | 100% of order/schedule/report/access/notification events logged | RIS-SL-60 |
| Retention | Report/order retention per tenant policy + legal hold; compliant purge only | schema `retention_policies` |
| Compliance | HIPAA + BAA; SOC 2 Type II; critical CVE patch ≤ 72 h | RIS-SL-62 |

### 4.4 Data Flow (order → report → bill, cross-system)

Order-to-report round-trip with EMR/PACS: `requrements/README.md` §3 and RIS-WF1 → PACS-WF1 → RIS-WF4 → RIS-WF6.

---

## 5. Risks & Roadmap

### 5.1 Phased Rollout

| Phase | Scope | Exit gate |
| :--- | :--- | :--- |
| **MVP (v1.0)** | Registration + MPI dedup, order intake (ORM), conflict-free scheduling, MWL serving + MPPS, tracking board, report templates + dictation, critical results, ORU delivery, charge capture, audit, RBAC, tenant provisioning | RIS-AC-P02-01/02, P03-01, P05-03 pass; MWL ≥ 98% auto-fill; interface > 99.9% |
| **v1.1** | Prior-auth tracking, reminders, denial rework + unbilled dashboards, report template manager, multi-site scheduling (IDN grants), speech-recognition polish, FHIR APIs | RIS-AC-P03-02/03, P05-02; prior-auth ≥ 95% pre-scan; unbilled $0 > 5 days |
| **v2.0** | Full FHIR `ServiceRequest`/`DiagnosticReport`, patient portal result delivery, AI-assisted coding (gate §3.2), enterprise chargeback analytics, patient-completed pre-registration | Coding-suggestion acceptance ≥ 90%; RIS-SL-40/41 sustained |

Aligns with `research/pacs-ris-implementation-plan.md` (Phases 3–8).

### 5.2 Technical Risks & Mitigations

| Risk | Mitigation |
| :--- | :--- |
| HL7 interface failures (ORM/ORU breaks, silent drops) | Interface engine with ≤ 5-min alerting + exception queue; > 99.9% delivery baseline |
| Double-booking regressions | DB-level EXCLUDE constraint (room/time) + UI conflict feedback; 0-conflict SLA |
| Accession collisions after merges/migration | Partial unique index + migration reconciliation |
| Billing capture leakage | Auto charge drop on sign-off; daily unbilled aging reconciliation; charge capture ≥ 98% |
| Prior-auth delays blocking scans | Status tracking + expiry alerts + audited override; ≥ 95% pre-scan authorization |
| Scheduler adoption resistance | Keyboard-first UX, calendar + list views, superuser training, UAT sign-off |
| IDN cross-facility data exposure | Read-only grants + RLS OR-clause + `cross_tenant.denied` audit (RIS-SL-61) |
| Downtime disrupting clinical flow | 99.9% availability, RTO ≤ 4 h / RPO ≤ 60 min, zero-downtime patching desired |

---

## Appendix — Traceability

| PRD section | Source docs |
| :--- | :--- |
| §1 KPIs | `05_metrics_and_slas.md` (RIS-SL-*) |
| §2.1 personas | `01_persona_catalog.md` |
| §2.2 stories | `03_user_stories.md` (RIS-US-*) |
| §2.3 acceptance | `06_acceptance_criteria.md` (RIS-AC-*) |
| §3 AI | RIS-WF4 (dictation); RIS-US-P05-01 (coding assist); RFP D16 |
| §4 architecture/integration | `02_end_to_end_workflows.md`, `pacs-ris-schema.sql`, `pacs-ris-multitenancy.md`, `RBAC_matrix_spec.md` |
| §5 roadmap/risks | `pacs-ris-implementation-plan.md` |
