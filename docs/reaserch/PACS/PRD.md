# Product Requirements Document — PACS (Picture Archiving & Communication System)

**Version:** 1.0 · **Date:** 2026-08-04 · **Type:** Engineering build spec · **Product surface:** PACS
**Status:** Active — this PRD is the **top-level source of truth** for the PACS surface. It summarizes and links the detailed requirements; implementation detail lives in the referenced documents.

| Source of truth | Document |
| :--- | :--- |
| Personas (human/institution/machine) + RBAC | `requrements/PACS/01_persona_catalog.md` |
| End-to-end workflows (swimlanes) | `requrements/PACS/02_end_to_end_workflows.md` |
| User stories (EARS, 44 stories) | `requrements/PACS/03_user_stories.md` |
| UI/UX requirements | `requrements/PACS/04_uiux_requirements.md` |
| Metrics & SLAs | `requrements/PACS/05_metrics_and_slas.md` |
| Acceptance criteria (PAC-AC-*) | `requrements/PACS/06_acceptance_criteria.md` |
| Roles/permissions/tenant scoping | `requrements/RBAC_matrix_spec.md` |
| Cross-tenant access (teleradiology/IDN) | `requrements/cross_tenant_grants_design.md` + `_api_contract.md` + `docs/specs/cross-tenant-grants_design.md` |
| DICOMweb/FHIR viewer integration | `research/pacs-ris-viewer-integration-spec.md` |
| Architecture (VNA, hybrid, DICOMweb) | `research/pacs-ris-architecture-deep-dive.md` |
| Data model & RLS | `research/pacs-ris-schema.sql`, `research/pacs-ris-multitenancy.md` |

---

## 1. Executive Summary

### Problem Statement

Radiology departments and multi-site health systems are locked into proprietary, slow, siloed PACS: active studies take >2–3 s to load, priors across facilities are unavailable, vendor lock-in blocks migration, and every pixel/access must be HIPAA-audited — impossible to satisfy with legacy appliances. The platform has no PACS surface today.

### Proposed Solution

A **PACS module** on the shared multi-tenant SaaS platform: standards-based DICOM/DICOMweb ingestion, tiered VNA-compatible archive (edge hot cache + cloud deep archive), a zero-footprint diagnostic web viewer, teleradiology, AI-result ingestion, and full HIPAA audit — isolated per tenant via RLS, delivered as a hybrid deployment.

### Success Criteria (KPIs — measured at go-live and quarterly; baseline in `05_metrics_and_slas.md`)

| KPI | Target | Source |
| :--- | :--- | :--- |
| Active-study retrieval (workstation, p95) | **< 2–3 s** | PAC-SL-10 |
| First-frame progressive render (web, reference bandwidth) | **< 3 s** | PAC-SL-11 |
| Platform availability | **99.9%** monthly | PAC-SL-01 |
| Storage Commitment accuracy | **100%** committed; **0 silent purges** | PAC-SL-21 |
| Orphan/exception rate | **< 0.5%**; 100% resolved ≤ 24 h | PAC-SL-22 |
| Interface message delivery | **> 99.9%**, failures alerted ≤ 5 min | PAC-SL-23 |
| Priors available at read time | **≥ 95%** | PAC-SL-24 |
| Audit completeness / cross-tenant incidents | **100%** events logged; **0** PHI incidents | PAC-SL-60/61 |
| TAT (STAT / Inpatient / Outpatient) | < 30–60 min / < 2–4 h / 24–48 h | PAC-SL-30–32 |

---

## 2. User Experience & Functionality

### 2.1 User Personas

Full catalog with goals, tasks, pains, and permission mapping: `requrements/PACS/01_persona_catalog.md` §1–§3.

| ID | Persona | Core need |
| :-: | :--- | :--- |
| PAC-P01 | Radiologist (incl. subspecialty) | Fast, accurate reads; priors; advanced tools (MPR/3D/fusion/AI) |
| PAC-P02 | Radiology Technologist | MWL auto-fill, guaranteed archive (Storage Commitment), QC |
| PAC-P03 | Teleradiologist / Nighthawk | Tokenized multi-facility remote reading, progressive streaming |
| PAC-P04 | PACS Administrator | 24/7 availability, routing, retention/ILM, migrations, DR |
| PAC-P05 | Imaging Informatics (CIIP) | Workflow KPIs, hanging protocols, interoperability |
| PAC-P06 | Referring Physician | One-click EMR launch, report + key images |
| PAC-P07 | ED Physician | STAT prioritization, instant preliminary/critical reads |
| PAC-P08 | Department Manager | TAT/utilization dashboards |
| PAC-P19 / PAC-P20 | Tenant Admin / Super Admin (platform) | Configure tenant; provision, meter, bill, support |
| PAC-M01–M09 | **Machines**: modalities, RIS, HIS/EMR, VNA, AI, viewers, workstations, storage tiers, export | Standards-based, non-human actors with their own auth |

### 2.2 User Stories

44 stories, full EARS text and priorities: `requrements/PACS/03_user_stories.md`. Representative examples:

- **As a radiologist**, I want a prioritized reading worklist with priors prefetched, so that I read the most urgent studies first with comparison at hand. *(PAC-US-P01-01/03)*
- **As a technologist**, I want a Storage Commitment acknowledgment before scanner-cache purge, so that images are never lost. *(PAC-US-P02-02)*
- **As a teleradiologist**, I want a tokenized session to read studies from multiple client facilities, fully audited, so that I provide cross-site coverage without VPNs. *(PAC-US-P03-01)*
- **As a PACS administrator**, I want configurable retention (5–30+ yr, pediatric) with legal hold and quota alerts, so that we comply and never purge protected data. *(PAC-US-P04-03/04)*
- **As a referring physician**, I want to open my patient's images from the EMR (SMART on FHIR) and see the report with key images, so that treatment decisions happen in my workflow. *(PAC-US-P06-01)*

Story matrix (per persona; priority counts **M=33, D=10, O=1, total=44**):

| Persona | Stories (IDs) |
| :--- | :--- |
| Radiologist | PAC-US-P01-01…10 (worklist, hanging protocols, priors, tools, AI overlay, critical flags, key images, <3 s load, WIP, large-study streaming) |
| Technologist | PAC-US-P02-01…07 (MWL, commitment, send feedback, MPPS, redo/add, QC, specialty workflows) |
| Teleradiologist | PAC-US-P03-01…05 (token session, streaming, cross-facility priors, critical callback, report routing) |
| PACS Admin | PAC-US-P04-01…09 (modality registry, routing, retention, quota, exceptions, export, DR, dashboards, migration) |
| Informatics | PAC-US-P05-01…02 (KPI dashboards, protocol libraries) |
| Referring MD | PAC-US-P06-01…03 (EMR launch, auto-delivery, responsive view) |
| ED MD | PAC-US-P07-01…02 (STAT prioritization, preliminary visibility) |
| Manager | PAC-US-P08-01 (dashboards + export) |
| Tenant/Super Admin | PAC-US-P19-01…02, PAC-US-P20-01…03 (usage, users, atomic provisioning, metering, audited cross-tenant) |

### 2.3 Acceptance Criteria ("Done" definitions)

Every story maps to testable Given/When/Then criteria: `requrements/PACS/06_acceptance_criteria.md` (PAC-AC-P01-01…PAC-AC-P20-03). Headline "done" gates per area:

- **Reading path:** study opens < 3 s; hanging protocol auto-applied; priors one click; critical flag tracked to acknowledgment; report signed & distributed. *(PAC-AC-P01-*)*
- **Acquisition path:** MWL auto-fill; Storage Commitment shown before purge prompt; failed sends show reason + retry; MPPS drives tracking board. *(PAC-AC-P02-*)*
- **Admin path:** retention/legal-hold honored with 0 accidental purges; quota alerts at 75/90%; exceptions reconciled ≤ 24 h; DR drill documented (RTO ≤ 4 h, RPO ≤ 60 min). *(PAC-AC-P04-*)*
- **Platform:** atomic tenant provisioning < 15 min; metering matches invoices; cross-tenant access policy-gated and 100% audited. *(PAC-AC-P19/20, CTG-AC-01…07)*

### 2.4 Non-Goals (explicitly out of scope)

- **Not** order entry, scheduling, registration, or billing/revenue cycle — these are the **RIS** surface (`requrements/RIS/`).
- **Not** the longitudinal clinical chart, orders, or medication workflows — **EMR** surface (`requrements/EMR/`).
- **Not** image *acquisition* (modalities capture pixels; PACS receives them).
- **Not** AI model development/training — PACS *integrates* AI results (DICOM SR/GSPS, FHIR) only.
- **Not** film-printing hardware or on-prem thick-client workstations — v1 viewer is zero-footprint web only.
- **Not** non-radiology specialty content (cardiology echo, pathology WSI, POCUS) in v1 — roadmap (`E20` optional).
- **Not** patient-facing imaging delivery in v1 — roadmap via portal/XDS-I.b.
- **Not** schema-per-tenant or DB-per-tenant deployments in v1 — documented escape hatches only (`pacs-ris-multitenancy.md` §3.4).

---

## 3. AI System Requirements (If Applicable)

AI is a **roadmap capability** (`O`, RFP E19) but specified here so the architecture doesn't need rework.

### 3.1 Tool / API Requirements

| Requirement | Detail | Source |
| :--- | :--- | :--- |
| Event-driven dispatch | AI subscribes to UPS-RS/webhook on study arrival; pulls via WADO-RS with token | PAC-WF6 |
| Result ingestion | DICOM SR/GSPS stored to VNA; or FHIR `Observation`/`DiagnosticReport`/`ImagingSelection` | RFP E19 |
| Viewer integration | AI flags render as overlays with confidence + accept/reject; rejected findings hidden | PAC-US-P01-05 |
| Access control | AI accesses via service keys with `STUDY_READ`/`RESULTS_READ` scopes (least privilege) | RBAC spec §6 |

### 3.2 Evaluation Strategy

- **Latency:** AI result visible in the reading worklist **≤ 5 min** after study-complete (C-STORE) on reference infra.
- **Integrity:** **≥ 95%** of ingested SR/GSPS validate against DICOM conformance; 0 corrupt/duplicate results stored.
- **Utility:** ≥ 70% of AI flags accepted by radiologists within a 30-day pilot (rejected flags audited); pilot gates v2.0 rollout.
- **Safety:** every AI access audited (A2/A3); no AI output can alter the original pixels or report without radiologist action.

---

## 4. Technical Specifications

### 4.1 Architecture Overview

Hybrid: **on-prem edge cache + cloud object archive**, one shared multi-tenant core (data flow per `pacs-ris-architecture-deep-dive.md` §5 and `pacs-ris-multitenancy.md` §4):

```
Modalities ──DIMSE/DICOMweb──▶ Ingestion Gateway (containers)
                                  │  parse + index metadata (Postgres, RLS-scoped)
                                  ▼
        Object Storage (S3-compatible, tenant-prefixed keys, tiered, WORM)
                                  │
                                  ▼
        DICOMweb API Gateway: QIDO-RS / WADO-RS / STOW-RS / UPS-RS
                                  │  ▲  FHIR ImagingStudy + SMART on FHIR + FHIRcast
                                  ▼  │
        Zero-footprint Viewer (OHIF/Cornerstone-class)  ── EMR / RIS / AI services
```

Component boundaries (microservice domains): **Ingestion, Metadata Indexer, Storage/ILM, DICOMweb Gateway, Viewer, AI Dispatcher, Audit/Metering** — horizontally scalable; rendering scales independently at peak hours.

### 4.2 Integration Points

| Integration | Protocol | Contract reference |
| :--- | :--- | :--- |
| Modalities | DICOM C-STORE, C-FIND (MWL), N-CREATE/N-SET (MPPS), Storage Commitment; DICOMweb STOW-RS | `02_end_to_end_workflows.md` PAC-WF1 |
| RIS | DICOM MWL/MPPS; HL7 ORM/ORU | PAC-WF1, `RIS/02` RIS-WF1 |
| HIS/EMR | HL7 ADT/ORM/ORU; FHIR R4 `ImagingStudy`/`Endpoint`/`ServiceRequest`/`DiagnosticReport` | PAC-WF7, `pacs-ris-viewer-integration-spec.md` |
| VNA | DICOM, DICOMweb, XDS-I.b | `pacs-ris-architecture-deep-dive.md` §1 |
| AI services | UPS-RS, WADO-RS, DICOM SR/GSPS, FHIR | PAC-WF6, §3 above |
| Web viewer | DICOMweb QIDO-RS/WADO-RS; SMART on FHIR; FHIRcast; IHE IUA (OAuth2) | `pacs-ris-viewer-integration-spec.md` §4–§6 |
| Export | IHE PDI (CD/DVD), XDS-I.b, anonymized export | PAC-WF8 |
| Auth | OAuth2/OIDC + IUA for web; AE-title + IP allow-list for modalities; service keys for machine clients; share keys for read-only links | RBAC spec §6, `auth_design.md` |
| DB | PostgreSQL 17: `studies`/`series`/`instances`/`storage_objects`/`storage_commitments`/`dicom_transactions` (partitioned)/`audit_log` (partitioned) | `research/pacs-ris-schema.sql` §6, §10 |

### 4.3 Security & Privacy

| Control | Requirement | Source |
| :--- | :--- | :--- |
| Tenant isolation | RLS on `facility_id` (+ `WITH CHECK`); `NOBYPASSRLS` + `FORCE ROW LEVEL SECURITY` in prod; tenant-prefixed object keys | `pacs-ris-multitenancy.md` §3–§4 |
| Cross-tenant (teleradiology/IDN priors) | Explicit time-boxed read-only grants; authorization < 1 s; 100% audited | `cross_tenant_grants_design.md` + API contract |
| RBAC | Permission-gated endpoints (`VIEWER_READ`, `STUDY_READ`, `FILE_*`, `STUDY_EXPORT`, `STORAGE_ADMIN`, …) | `RBAC_matrix_spec.md` |
| Encryption | TLS 1.2+ in transit; AES-256 at rest; WORM/immutable archive | PAC-SL-62 |
| Audit | 100% of view/retrieve/export/delete/share/access logged; cross-tenant events with source/target | PAC-SL-60, design §5 |
| Retention | Configurable 5–30+ yr per tenant; pediatric mandates; legal-hold override; compliant purge only | PAC-US-P04-03 |
| Compliance | HIPAA + BAA; SOC 2 Type II; critical CVE patch ≤ 72 h | PAC-SL-63 |
| Privacy by design | No PHI in URLs (bearer tokens, UID-based deep links); de-identification for exports | viewer-integration-spec §8 |

### 4.4 Data Flow (order → read, cross-system)

Full round-trip with RIS/EMR: `requrements/README.md` §3 and PAC-WF1/WF2/WF7.

---

## 5. Risks & Roadmap

### 5.1 Phased Rollout

| Phase | Scope | Exit gate |
| :--- | :--- | :--- |
| **MVP (v1.0)** | Ingestion (C-STORE/STOW-RS), metadata index, tiered archive + storage commitment, basic zero-footprint viewer (QIDO/WADO), MWL/MPPS echo, audit, RBAC, tenant provisioning, quota/retention admin | PAC-AC-P01-08/10, P02-01/02, P04-03/04 pass; 99.9% availability in prod |
| **v1.1** | Advanced viewer (MPR/MIP/3D/cine/fusion/measurements), priors prefetch, teleradiology (token sessions + **cross-tenant grants**), critical results, export (CD/XDS-I.b), AI result ingestion, KPI dashboards | CTG-AC-01…07; PAC-AC-P01-03/04/06; TAT SLAs met |
| **v2.0** | UPS-RS workflow, full FHIR ImagingStudy/DiagnosticReport + SMART on FHIR + FHIRcast, non-DICOM content, edge caching at scale, schema-per-tenant escape hatch, patient imaging delivery, AI utility gate (§3.2) | EMR-launch acceptance (PAC-AC-P06-01); AI acceptance ≥ 70% |

Aligns with `research/pacs-ris-implementation-plan.md` (Phases 3–8) and `research/pacs-ris-platform-decision-guide.md` (hybrid model).

### 5.2 Technical Risks & Mitigations

| Risk | Mitigation |
| :--- | :--- |
| Bandwidth/egress cost at multi-site WAN | Edge caching, prefetch policies, tiered hybrid storage; WADO bytes metered (PAC-SL-50) |
| Interface fragility (modality firmware breaks MWL/MPPS) | Interface engine with ≤ 5-min alerting; conformance testing in lab; exception queue |
| Legacy migration data loss/corruption | Automated count reconciliation (100%) + 1–2% radiologist sample validation |
| Cross-tenant PHI incident | Explicit grants + RLS OR-clause + `cross_tenant.denied` audit; quarterly RLS audit; DRR evidence (PAC-SL-61) |
| Radiologist adoption resistance | Early involvement, superusers, hanging-protocol libraries, UAT sign-off |
| Cloud compliance (HIPAA) | BAA, IUA/OAuth2, AES-256, audit trails, geo-replicated DR |
| Storage growth / quota exhaustion | Per-tenant quotas with 75/90% alerts; tier lifecycle; growth forecasting |
| Progressive rendering complexity (multi-GB studies) | Frame-level WADO-RS, server-side rendering option; acceptance PAC-AC-P01-10 |

---

## Appendix — Traceability

| PRD section | Source docs |
| :--- | :--- |
| §1 KPIs | `05_metrics_and_slas.md` (PAC-SL-*) |
| §2.1 personas | `01_persona_catalog.md` |
| §2.2 stories | `03_user_stories.md` (PAC-US-*) |
| §2.3 acceptance | `06_acceptance_criteria.md` (PAC-AC-*) |
| §3 AI | `02_end_to_end_workflows.md` PAC-WF6; RFP E19 |
| §4 architecture/integration | `pacs-ris-architecture-deep-dive.md`, `pacs-ris-viewer-integration-spec.md`, `pacs-ris-schema.sql`, `pacs-ris-multitenancy.md`, `RBAC_matrix_spec.md` |
| §5 roadmap/risks | `pacs-ris-implementation-plan.md`, `pacs-ris-platform-decision-guide.md` |
