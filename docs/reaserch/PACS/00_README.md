# PACS — User Requirements Index

**System:** Picture Archiving and Communication System · **Platform:** multi-tenant SaaS, hybrid (edge cache + cloud archive) · **Version:** 1.0 · **Date:** 2026-08-04

Companion research: `research/pacs-ris-research.md`, `research/pacs-ris-comparison.md`, `research/pacs-ris-architecture-deep-dive.md`, `research/pacs-ris-viewer-integration-spec.md`, `research/pacs-ris-schema.sql`, `docs/specs/*`.

---

## 1. Document Map

| # | Document | Contents |
| :-: | :--- | :--- |
| **PRD** | **`PRD.md`** | **Product Requirements Document — top-level source of truth for the PACS surface: executive summary + KPIs, personas, stories, acceptance, AI requirements, technical spec, risks & roadmap. Start here.** |
| **RELEASE** | **`RELEASE_PLAN.md`** | **Release plan decomposing the PRD MVP into epics + sprint-sized work items with exit-gate acceptance criteria (G1–G7), sprint roadmap, critical path, Definition of Done & risks.** |
| **ROADMAP** | **`../pacs_consolidated_sprint_roadmap.md`** | **Consolidated sprint roadmap: single index mapping the seven task-level sprint detail docs (Sprint 1–7) onto the release-plan S1–S12 roadmap — dependencies/handoffs, capacity, and gate checkpoints.** |
| **CHECKLIST** | **`go-live-checklist.md`** | **Go-live checklist: standalone runnable extraction of the G1–G7 exit gates — per-gate steps, evidence artifacts, cutover sequence, and sign-off block for QA/ops at cutover.** |
| **TEST** | **`../qa_test_strategy.md`** | **QA & test strategy: named pytest test per PAC-AC/PAC-SL with layer, fixtures, markers, CI gates, coverage targets, and G1–G7 gate traceability.** |
| **E2E** | **`../e2e_test_plan_playwright.md`** | **E2E test plan: Playwright UI suite — every MVP-scope PAC-UI-* mapped to a spec with Page Objects, persona storage-state auth, network mocking, cross-browser projects, WCAG AA, and gate traceability.** |
| 01 | `01_persona_catalog.md` | Proposed real-world users & personas: human (radiologist, technologist, PACS admin, …), institutions (hospitals, imaging centers, …), machines (modalities, VNA, AI, viewers, …) + permission mapping |
| 02 | `02_end_to_end_workflows.md` | Swimlane workflow maps: acquisition → archive → read → distribute; prefetch, teleradiology, DR, AI |
| 03 | `03_user_stories.md` | `As a … I want … So that …` stories per persona (IDs `PAC-US-…`) |
| 04 | `04_uiux_requirements.md` | Viewer, worklist, admin console & dashboard UI/UX per persona (IDs `PAC-UI-…`) |
| 05 | `05_metrics_and_slas.md` | Retrieval latency, availability, TAT, DICOM reliability, storage/ILM, metering (IDs `PAC-SL-…`) |
| 06 | `06_acceptance_criteria.md` | Testable acceptance criteria per story/feature (IDs `PAC-AC-…`) |

## 2. Personas at a Glance

- **Human:** Radiologist (PAC-P01) · Technologist (PAC-P02) · Teleradiologist (PAC-P03) · PACS Administrator (PAC-P04) · Imaging Informatics Specialist (PAC-P05) · Referring Physician (PAC-P06) · ED Physician (PAC-P07) · Department Manager (PAC-P08) · Tenant Admin (PAC-P19) · Super Admin (PAC-P20)
- **Institutions:** Hospitals, imaging centers, teleradiology groups, IDNs, outpatient clinics, SaaS operator (PAC-I01–I05, I10)
- **Machines:** Modalities (PAC-M01), RIS (PAC-M02), HIS/EMR (PAC-M03), VNA (PAC-M04), AI services (PAC-M05), Web viewers (PAC-M06), Diagnostic workstations (PAC-M07), Storage tiers/edge cache (PAC-M08), Print/export (PAC-M09)

## 3. Build · Configure · Integrate mapping

| Phase | PACS focus | Docs |
| :--- | :--- | :--- |
| Build | Ingestion (C-STORE/STOW-RS), metadata index, viewer (DICOMweb), storage commitment, ILM, audit | 01 (M personas), 02 (WF1–WF9), 03, 04 |
| Configure | Tenant storage quotas, retention policies, routing rules, hanging protocols, viewer defaults | 01 (H4/H5/H19 permission map), 04 |
| Integrate | Modalities, RIS (MWL/MPPS), HIS/EMR (HL7/FHIR), VNA, AI (UPS-RS), web viewer (QIDO/WADO) | 02 (WF1, WF4, WF6, WF8), 05 (interface SLAs) |
| Accept | Radiologist/technologist sign-off on reading & acquisition journeys | 06 |

## 4. Non-Negotiable Platform Constraints (cross-cutting)

- **Tenant isolation:** every DICOM object and metadata row is scoped to `facility_id` via RLS; object storage keys are tenant-prefixed (`s3://vna/{tenant_code}/{facility_id}/…`). *(Per `pacs-ris-multitenancy.md` §4.)*
- **Interoperability:** DICOMweb (QIDO-RS/WADO-RS/STOW-RS/UPS-RS) + DIMSE (C-STORE/C-FIND/C-MOVE/C-GET) + HL7/FHIR as documented in `pacs-ris-viewer-integration-spec.md`.
- **Security:** TLS 1.2+, AES-256 at rest, RBAC, tamper-evident audit logs for every view/export/delete, IHE IUA/OAuth2 for web access.
- **Performance floor:** active-study retrieval < 2–3 s; first frame progressive render < 3 s; 24/7/365 availability (99.9%).
