# User Requirements — Enterprise-Grade Multi-Tenant SaaS Platform (PACS · RIS · EMR)

**Version:** 1.0 · **Date:** 2026-08-04 · **Status:** Active (input to Build / Configure / Integrate phases)

This document set is the **single source of user requirements** for building, configuring, and integrating a **hybrid-architecture, production-grade, enterprise multi-tenant SaaS platform** that delivers three clinical systems on one shared platform:

| System | Core mission | Primary data | Primary standards |
| :--- | :--- | :--- | :--- |
| **PACS** | Store, retrieve, display & distribute medical images | DICOM pixel data (CT, MR, XR, US, NM, PET, Mammo, Fluoroscopy) | DICOM, DICOMweb (QIDO-RS/WADO-RS/STOW-RS/UPS-RS), IHE SWF/XDS-I.b/PDI |
| **RIS** | Track the patient order from referral to final report & billing | Text/structured: demographics, orders, schedules, reports, CPT/ICD-10 | HL7 v2 (ADT/ORM/ORU), FHIR, DICOM MWL/MPPS, IHE SWF |
| **EMR** | Manage the longitudinal patient record, encounters, orders & results across the enterprise | Clinical documentation, orders, results, medications, billing codes | HL7 v2, FHIR, SMART on FHIR, CDS/e-prescribing |

> **One-line rule:** PACS handles the **pixels**, RIS handles **everything else in radiology** (orders, scheduling, reports, billing), and the EMR is the **clinical record of truth** that orders and consumes both.

---

## 1. Purpose of This Document Set

This documentation is organized by **real-world users, personas, and actors** — not by screens or modules — so that product owners, architects, engineering leads, QA, and implementation teams can trace every build decision back to a named human being, institution, or machine.

Each system folder contains the following deliverables, in order (plus a **`PRD.md`** entry point per system — `requrements/PACS/PRD.md`, `requrements/RIS/PRD.md`, `requrements/EMR/PRD.md` — the top-level product source of truth for each surface, and a **`RELEASE_PLAN.md`** per system — `requrements/PACS/RELEASE_PLAN.md`, `requrements/RIS/RELEASE_PLAN.md`, `requrements/EMR/RELEASE_PLAN.md` — breaking each MVP into epics/sprints with exit-gate acceptance criteria):

| # | Deliverable | File | What it contains |
| :-: | :--- | :--- | :--- |
| 0 | System index | `00_README.md` | Document map, persona at-a-glance, conventions, build/configure/integrate mapping |
| 1 | Persona catalog | `01_persona_catalog.md` | **Proposed list of real-world users & personas** — human users, institutions, machines/integrations — with goals, tasks, pains, and permission mapping |
| 2 | End-to-end workflows | `02_end_to_end_workflows.md` | Swimlane workflow maps per persona and cross-system journeys |
| 3 | User stories | `03_user_stories.md` | EARS-style `As a … I want … So that …` stories per persona with IDs |
| 4 | UI/UX requirements | `04_uiux_requirements.md` | Interface, interaction, accessibility & visual requirements per persona |
| 5 | Metrics & SLAs | `05_metrics_and_slas.md` | Measurable KPIs and service-level agreements per persona/workflow |
| 6 | Acceptance criteria | `06_acceptance_criteria.md` | Testable acceptance criteria per story/feature with traceability |
| 7 | **RBAC matrix spec** (cross-cutting) | `RBAC_matrix_spec.md` | Canonical permission catalog, persona→role mapping, role→permission matrices (PACS/RIS/EMR/platform), tenant scoping & cross-tenant policy, endpoint→permission map, idempotent seeding SQL — directly implementable |
| 8 | **Cross-tenant grants design** (cross-cutting) | `cross_tenant_grants_design.md` | DDL + RLS + audit policy for `cross_tenant_grants` — teleradiology & IDN prior/scheduling access, authorization helper, workflows, acceptance criteria |
| 9 | **Cross-tenant grants API contract** (cross-cutting) | `cross_tenant_grants_api_contract.md` | Ops API: create/list/revoke endpoints, request/response schemas, validation rules (V1–V11), error envelope, audit events, rate limiting, acceptance criteria — directly implementable |
| 10 | **Grant management UI design** (platform spec) | `docs/specs/cross-tenant-grants_design.md` | SYSTEM_ADMIN console (list/create/revoke) consistent with the tenants & roles pages: filters, cursor pagination, status/expiry badges, purpose-driven scope groups, route guard, CTG-UI acceptance criteria |
| 11 | **Sprint 1 detail — platform foundation** (cross-cutting) | `sprint1_platform_foundation_detail.md` | Task-level breakdown of E-PAC-01 + E-RIS-01 (S1-01…S1-29): owners, dev-day estimates, dependencies, acceptance checks, milestone plan — directly executable backlog |
| 12 | **Sprint 2 detail — ingestion gateway & interface engine** (cross-cutting) | `sprint2_ingestion_interface_detail.md` | Task-level breakdown of E-PAC-02 + E-RIS-02 (S2-01…S2-30): DICOM C-STORE/STOW-RS ingestion, HL7 listener + ORM/ORU mapping, exception queues, interface health + alerting, conformance lab — directly executable backlog |
| 13 | **Sprint 3 detail — MWL/MPPS & tiered archive** (cross-cutting) | `sprint3_mwl_archive_detail.md` | Task-level breakdown of E-PAC-03 + E-PAC-04 (S3-01…S3-24): MWL C-FIND serving + MPPS consumer, Storage Commitment engine, tiered object storage + ILM, retention/legal-hold, quota alerts — directly executable backlog |
| 14 | **Sprint 4 detail — DICOMweb gateway & viewer** (cross-cutting) | `sprint4_dicomweb_viewer_detail.md` | Task-level breakdown of E-PAC-05 + E-PAC-06 (S4-01…S4-26): QIDO/WADO + frame-level progressive streaming, IUA/OAuth2 gate, prioritized reading worklist, zero-footprint viewer, hanging protocols, critical flag + key images — directly executable backlog |
| 15 | **Sprint 5 detail — admin console & interface monitoring** (cross-cutting) | `sprint5_admin_monitoring_detail.md` | Task-level breakdown of E-PAC-07 + E-PAC-08 (S5-01…S5-22): modality registry UI, queue monitor, storage dashboard, retention editor + dry-run, exception worklist, routing rules, interface health + ≤ 5-min alerting, conformance harness — directly executable backlog |
| 16 | **Sprint 6 detail — dashboards, metering & DR/security** (cross-cutting) | `sprint6_dashboards_ops_detail.md` | Task-level breakdown of E-PAC-09 + E-PAC-10 (S6-01…S6-26): metering-to-invoice accuracy, tenant usage + KPI dashboards, edge cache, ingestion buffering, failover/DR drill, availability SLO, RLS audit + denial + CVE scan — directly executable backlog |
| 17 | **Sprint 7 detail — hardening, UAT & exit gates** (cross-cutting) | `sprint7_hardening_detail.md` | Task-level breakdown of release-plan S12 (S7-01…S7-22): per-persona UAT + sign-off, full performance suite under load, security test (RLS/RBAC/pen-test), final DR drill, G1–G7 re-verification + evidence package, go-live readiness — directly executable backlog |
| 18 | **PACS consolidated sprint roadmap** (cross-cutting) | `pacs_consolidated_sprint_roadmap.md` | Single index mapping the seven sprint detail docs (Sprint 1–7) onto the release-plan S1–S12 roadmap: dependencies/handoffs, per-sprint capacity, and G1–G7 gate checkpoints — the program-level execution view |
| 19 | **PACS go-live checklist** (PACS) | `PACS/go-live-checklist.md` | Standalone runnable extraction of the G1–G7 exit gates for QA/ops at cutover: per-gate steps, evidence artifacts, cutover sequence, stop/rollback triggers, and sign-off block |
| 20 | **QA & test strategy — pytest catalog** (cross-cutting) | `qa_test_strategy.md` | Executable test strategy: named pytest test per PAC-AC/PAC-SL with layer, fixtures, markers, CI gates, coverage targets, and G1–G7 traceability — the template for RIS/EMR |
| 21 | **Architecture decision records** (cross-cutting) | `decisions/README.md` | ADR series (ADR-001…009) capturing the platform's expensive-to-reverse decisions — multi-tenancy isolation, hybrid archive, DICOMweb/DIMSE, IUA/OAuth2 + RBAC, cross-tenant grants, PostgreSQL + metering, SC/retention/WORM, audit, zero-footprint viewer — with lifecycle and template |
| 22 | **E2E test plan — Playwright UI suite** (cross-cutting) | `e2e_test_plan_playwright.md` | Browser-level complement to the QA strategy: every MVP-scope PAC-UI-* mapped to a Playwright spec with Page Objects, persona storage-state auth, network mocking, cross-browser projects, WCAG AA checks, and G1–G7 gate traceability |

**Requirement ID conventions** (used throughout for traceability):

- `PAC-…` → PACS requirements
- `RIS-…` → RIS requirements
- `EMR-…` → EMR requirements
- `PLT-…` → Platform/cross-cutting requirements (multi-tenancy, security, audit, metering)

Suffixes: `-P##` persona ID · `-WF##` workflow · `-US##` user story · `-UI##` UI/UX · `-SL##` metric/SLA · `-AC##` acceptance criterion.

---

## 2. Proposed Real-World Users & Personas — Master Matrix

### 2.1 Human users (who logs in and clicks)

| # | Persona | PACS | RIS | EMR | Primary goal |
| :-: | :--- | :-: | :-: | :-: | :--- |
| H1 | Radiologist (incl. subspecialty) | ● core | ● core | ○ | Read studies fast & accurately, deliver signed reports |
| H2 | Radiology Technologist (CT/MR/XR/US/NM/Mammo) | ● core | ● core | ○ | Acquire high-quality images, keep the worklist flowing |
| H3 | Teleradiologist / Nighthawk | ● core | ○ | ○ | Read remotely with full context & tools |
| H4 | PACS Administrator | ● core | ○ | ○ | Keep archive & viewers up, routes correct, users working |
| H5 | Imaging Informatics Specialist (CIIP) | ● | ○ | ○ | Optimize workflows & interoperability across systems |
| H6 | Referring / Ordering Physician | ● view | ● view | ● core | Get answers (images + reports) that drive treatment |
| H7 | Emergency Department Physician | ● view | ● view | ● core | Rapid STAT reads & results for acute patients |
| H8 | Primary Care Physician | ○ view | ○ view | ● core | Manage panel, document, order, review results |
| H9 | Nurse (inpatient/outpatient) | ○ | ○ | ● core | Deliver safe care, administer meds, document |
| H10 | Pharmacist | — | — | ● core | Verify & optimize medication orders |
| H11 | Lab Technician / Pathologist | — | — | ● core | Process specimens, release accurate results fast |
| H12 | Scheduler / Referral Coordinator | — | ● core | ○ | Book multi-modality exams without conflicts |
| H13 | Front-Desk / Registration Clerk | ○ | ● core | ● core | Register patients & capture clean demographics/insurance |
| H14 | Radiology / Medical Billing Coder | — | ● core | ● core | Code & bill clean claims, minimize denials |
| H15 | HIM / Medical Records (ROI) | ○ | ○ | ● core | Keep the legal record complete & compliant |
| H16 | Department Manager / Radiology Director | ○ | ● | ○ | Track TAT, utilization, productivity, compliance |
| H17 | RIS Administrator | ○ | ● core | ○ | Keep schedules, codes, interfaces & rules working |
| H18 | EMR/HIT System Administrator | ○ | ○ | ● core | Keep the system up, users provisioned, integrations healthy |
| H19 | Tenant Admin (org-level SaaS admin) | ● | ● | ● | Configure tenant, users, roles, quotas, billing |
| H20 | Super Admin (platform operator) | ● | ● | ● | Run the SaaS: provision tenants, meter, invoice, support |
| H21 | Patient (portal / share links) | ○ view | ○ | ● view | See results, schedule, message care team |

`●` primary user · `○` secondary/limited · `—` not applicable

### 2.2 Institutional actors (tenants & external organizations)

| # | Institution type | Typical needs |
| :-: | :--- | :--- |
| I1 | Acute-care hospital (community / academic / trauma) | High-concurrency, 24/7 availability, ED & ICU workflows, DR |
| I2 | Freestanding imaging / diagnostic center | High-throughput scheduling, low overhead, patient satisfaction |
| I3 | Outpatient clinic / primary care practice | Order & view imaging, EMR documentation, referrals |
| I4 | Teleradiology group | Multi-tenant read coverage, remote access, workload routing |
| I5 | Integrated Delivery Network / health system (multi-facility) | Cross-facility priors (XDS-I.b), enterprise MPI, consolidated analytics, chargeback |
| I6 | Specialty practice (cardiology, orthopedics, women's health) | Specialty viewers (echo, cath, mammo), modality-specific workflows |
| I7 | Independent & hospital-based laboratory | HL7 ORM/ORU flows, result TAT |
| I8 | Pharmacy (retail/inpatient) | E-prescribing, medication orders, benefit checks |
| I9 | Payer / insurer | Prior authorization, claims (837/835), clinical summaries |
| I10 | The SaaS operator itself (this platform, as vendor) | Tenant lifecycle, metering, billing, support SLAs, SOC 2/HIPAA posture |

### 2.3 Machine & system actors (non-human "users" — integrations)

| # | Machine / system | Talks to | Primary protocol |
| :-: | :--- | :--- | :--- |
| M1 | Imaging modalities (CT, MR, DR, US, NM, PET, Mammo, Fluoro, Anglo, O-arm) | PACS, RIS | DICOM C-STORE, C-FIND (MWL), N-CREATE/N-SET (MPPS), Storage Commitment, DICOMweb STOW-RS |
| M2 | HIS/EMR (the ordering system) | RIS, PACS, EMR | HL7 v2 ADT/ORM/ORU; FHIR R4 |
| M3 | Laboratory instruments & LIS | EMR | HL7 ORU, ASTM |
| M4 | Pharmacy systems / e-prescribing (Surescripts) | EMR | HL7, NCPDP / eRx |
| M5 | Billing / practice-management systems & clearinghouses | EMR, RIS | HL7, X12 837/835 |
| M6 | Patient portal / SMS/email notification services | EMR, RIS | HTTPS, SMART on FHIR |
| M7 | VNA (vendor-neutral archive) | PACS | DICOM, DICOMweb, XDS-I.b |
| M8 | AI services (triage, CAD, segmentation, stroke detection) | PACS, EMR | DICOM SR/GSPS, UPS-RS, FHIR Observation/DiagnosticReport/ImagingSelection |
| M9 | Zero-footprint web viewers (OHIF/Cornerstone-class) | PACS | DICOMweb, SMART on FHIR, FHIRcast |
| M10 | Diagnostic workstations (calibrated displays) | PACS | DICOM, DICOMweb |
| M11 | Object storage tiers (hot/warm/cold) & edge caches | PACS | S3/Blob APIs, lifecycle policies |
| M12 | Speech-recognition / dictation engine | RIS, EMR | WebSocket/API, FHIR DocumentReference |
| M13 | Identity providers (SSO/OIDC/SAML) | All | OIDC, SAML, IHE IUA |

---

## 3. Cross-System Integration at a Glance

The three systems are **one platform with three product surfaces**, sharing a single multi-tenant core. The end-to-end clinical journey that binds them:

```
                        ┌────────────── EMR (record of truth) ──────────────┐
  Registration (H13) ──▶│ Patient chart · encounters · orders · results     │
                        └──────┬───────────────────────────┬───────────────┘
                  HL7 ORM / FHIR ServiceRequest      HL7 ORU / FHIR DiagnosticReport
                               ▼                       ▲
                        ┌────────────── RIS (radiology tracker) ────────────┐
                        │ Order → Schedule → MWL → MPPS → Read → Report     │
                        └──────┬───────────────────────────┬───────────────┘
                    DICOM C-FIND (MWL) / MPPS         HL7 ORU (report)
                               ▼                       ▲
                        ┌────────────── PACS (pixels) ──────────────────────┐
                        │ C-STORE → tiered archive → viewer → distribution   │
                        └───────────────────────────────────────────────────┘
```

**Platform shared services (built once, used by all three):** multi-tenant RLS isolation, tenant lifecycle (TRIAL→ACTIVE→…), RBAC + audit, notifications, share links, service keys/API keys, usage metering & billing, uploads/DICOM ingestion, worklist engine, viewer.

---

## 4. How to Use These Documents in Build · Configure · Integrate

| Activity | Start with | Then |
| :--- | :--- | :--- |
| **Build** (engineering) | `03_user_stories.md` + `04_uiux_requirements.md` | Implement per `06_acceptance_criteria.md`; verify against `05_metrics_and_slas.md` |
| **Configure** (tenant & org setup) | `RBAC_matrix_spec.md` (§4–§6) + each system `00_README.md` | Map personas to roles, seed permissions, assign facility-scoped role grants, set cross-tenant policy |
| **Integrate** (interfaces) | `02_end_to_end_workflows.md` (integration touchpoints) | Use machine-actor requirements in each `01_persona_catalog.md` §M; verify message-level SLAs in `05_metrics_and_slas.md` |
| **Accept / UAT** | `06_acceptance_criteria.md` | Run per-persona scripted scenarios; sign off by persona |

**Companion research (source of truth for architecture & standards):** `research/pacs-ris-multitenancy.md` (isolation & tenancy), `research/pacs-ris-architecture-deep-dive.md` (VNA/DICOMweb/FHIR), `research/pacs-ris-schema.sql` (data model), `research/pacs-ris-rfp-template.md` (procurement checklist), `research/pacs-ris-implementation-plan.md` (rollout phases).

---

## 5. Conventions

- **Story syntax (EARS):** `As a <persona>, I want <capability>, so that <benefit>.`
- **Priorities:** `M` = Mandatory (pass/fail) · `D` = Desired (scored) · `O` = Optional (bonus)
- **Workflow maps:** ASCII swimlanes; `─▶` action, `◀─` response, `◇` decision, `⏳` wait.
- Every user story links to ≥1 acceptance criterion; every acceptance criterion links back to ≥1 story.
