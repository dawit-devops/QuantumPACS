# RIS — User Requirements Index

**System:** Radiology Information System · **Platform:** multi-tenant SaaS · **Version:** 1.0 · **Date:** 2026-08-04

Companion research: `research/pacs-ris-research.md`, `research/pacs-ris-comparison.md`, `research/pacs-ris-schema.sql` (orders/patients/worklist tables), `docs/specs/worklist_design.md`, `docs/specs/notifications_design.md`, `docs/specs/roles_design.md`.

---

## 1. Document Map

| # | Document | Contents |
| :-: | :--- | :--- |
| **PRD** | **`PRD.md`** | **Product Requirements Document — top-level source of truth for the RIS surface: executive summary + KPIs, personas, stories, acceptance, AI (dictation/coding assist), technical spec, risks & roadmap. Start here.** |
| **REL** | **`RELEASE_PLAN.md`** | **Release plan: MVP → v1.1 → v2.0 broken into 11 epics and sprint-sized work items (12-sprint MVP roadmap) with exit-gate acceptance criteria, critical path & DoD.** |
| **V2 RELEASE** | **`RELEASE_PLAN_V2.md`** | **V2 release plan: post-MVP program (Phase 1 = v1.1 backlog: prior-auth, reminders, denial rework, template manager, IDN grants/multi-site scheduling; Phase 2 = v2.0: full FHIR, portal delivery, AI-assisted coding, chargeback analytics, pre-registration) — 12 epics (E-RIS2-01…12), 12-sprint roadmap (R2-S1…R2-S12), exit gates RVG-1…RVG-6, coordinated with PACS V2 (grants) & EMR V2.** |
| **V2 SPRINTS** | **`../sprint_r2_01…06_*_detail.md`** | **V2 sprint detail docs: task-level breakdown of R2-S1…R2-S12 (prior-auth/reminders, denial/templates/SR, IDN grants/multi-site, FHIR read + v1.1 gates, FHIR/portal, AI/chargeback + v2.0 gates) — directly executable backlog.** |
| 01 | `01_persona_catalog.md` | Proposed real-world users & personas: human (radiologist, technologist, scheduler, front-desk, biller, RIS admin, …), institutions, machines (modalities via MWL/MPPS, HIS/EMR, PACS, billing, portal) + permission mapping |
| 02 | `02_end_to_end_workflows.md` | Swimlane maps: order→schedule→MWL→MPPS→tracking→report→critical alert→ORU→billing; prior-auth; reminders; denials; multi-site scheduling |
| 03 | `03_user_stories.md` | `As a … I want … So that …` stories per persona (IDs `RIS-US-…`) |
| 04 | `04_uiux_requirements.md` | Scheduling, tracking board, worklist, reporting, billing & admin UI/UX (IDs `RIS-UI-…`) |
| 05 | `05_metrics_and_slas.md` | TAT, MWL reliability, scheduling accuracy, interface delivery, billing capture, availability (IDs `RIS-SL-…`) |
| 06 | `06_acceptance_criteria.md` | Testable acceptance criteria per story/feature (IDs `RIS-AC-…`) |

## 2. Personas at a Glance

- **Human:** Radiologist (RIS-P01) · Technologist (RIS-P02) · Scheduler/Referral Coordinator (RIS-P03) · Front-Desk/Registration Clerk (RIS-P04) · Radiology Billing Coder (RIS-P05) · RIS Administrator (RIS-P06) · Department Manager (RIS-P07) · Referring Physician (RIS-P08) · ED Physician (RIS-P09) · Tenant Admin (RIS-P19) · Super Admin (RIS-P20)
- **Institutions:** Hospitals, imaging centers, teleradiology groups, IDNs, outpatient clinics, payers (RIS-I01–I06)
- **Machines:** Modalities (RIS-M01), HIS/EMR (RIS-M02), PACS (RIS-M03), Billing/PM & clearinghouse (RIS-M04), Patient portal/notifications (RIS-M05), Speech recognition (RIS-M06)

## 3. Build · Configure · Integrate mapping

| Phase | RIS focus | Docs |
| :--- | :--- | :--- |
| Build | Registration, scheduling, order entry, status lifecycle, reporting, critical alerts, billing capture | 01, 02 (WF1–WF9), 03, 04 |
| Configure | Scheduling templates, procedure/CPT maps, report templates, worklist routing, user roles | 01 (H3/H5/H6/H7), 04 |
| Integrate | HL7 ADT/ORM/ORU ↔ HIS/EMR; MWL/MPPS ↔ modalities; report ↔ PACS/EHR; charge ↔ billing | 02 (WF1, WF4, WF6, WF8), 05 (interface SLAs) |
| Accept | Scheduler/technologist/radiologist/biller sign-off on order-to-bill journeys | 06 |

## 4. Non-Negotiable Constraints

- **Order data integrity:** accession number uniqueness enforced per tenant (`worklist_design.md` migration 027); every order has a deterministic lifecycle (Ordered→Scheduled→Arrived→In Progress→Completed→Read→Signed).
- **Interface reliability:** HL7 message delivery > 99.9%, zero silent drops; failed messages go to an exception queue with alerting.
- **Billing accuracy:** CPT/ICD-10 captured at order/procedure level; charge drop traceable to report sign-off.
- **Multi-site scheduling:** conflict-free booking across rooms, modalities, and staff; contrast/contraindication checks.
