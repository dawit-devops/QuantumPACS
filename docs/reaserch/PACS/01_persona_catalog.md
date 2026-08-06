# PACS — Persona Catalog: Real-World Users, Institutions & Machines

**Document:** 01 of 06 · **Version:** 1.0 · **Date:** 2026-08-04

This document proposes the **real-world users and personas** for the PACS product surface. Personas are grouped into three actor classes — **human users** (PAC-P##), **institutions** (PAC-I##), and **machines/systems** (PAC-M##) — because each class has different authentication, permission, and interface requirements.

---

## 1. Human Users (PAC-P##)

### PAC-P01 · Radiologist (Diagnostic, incl. Subspecialty)

| Attribute | Description |
| :--- | :--- |
| **Real-world identity** | Staff radiologist, subspecialty radiologist (neuroradiology, MSK, body, breast, cardiac, nuclear medicine), academic faculty, or private-practice partner |
| **Environment** | Reading room (multi-monitor diagnostic workstations), remote/home reading sessions, on-call/nighthawk rotations |
| **Primary goals** | Read high study volume accurately and fast; deliver signed, high-quality reports; maintain low turnaround time (TAT); use priors and advanced tools (MPR, 3D, fusion, AI) to increase diagnostic confidence |
| **Key tasks** | Open/prioritize worklist; apply hanging protocols; scroll/cine/zoom/pan/window-level; MPR/MIP/3D reconstruction; PET/CT fusion; measure (linear, angle, ROI, volumetric); bookmark key images; dictate/type report; flag critical findings; sign & distribute |
| **Pain points** | Slow study load (>2–3 s), poor hanging protocol defaults, fragmented worklists, no priors prefetched, voice recognition errors, alert/notification fatigue, viewer tool instability during a read |
| **Success metrics** | TAT per priority class; reading throughput (studies/hr); % reads needing rework; % priors available at read time |
| **Permissions** | Worklist read/prioritize · study view/retrieve · report author/sign · critical-results flag · share key images |
| **Regulatory** | HIPAA; report must be accurate, complete, timely; e-signature integrity |

### PAC-P02 · Radiology Technologist / Radiographer

| Attribute | Description |
| :--- | :--- |
| **Real-world identity** | CT tech, MR tech, radiographer (XR/CR), sonographer, nuclear medicine tech, mammography tech, fluoroscopy/angio tech |
| **Environment** | Modality console at the scanner, department workstations, QC area |
| **Primary goals** | Acquire diagnostically adequate images efficiently and safely; keep patient throughput high; ensure every acquired series reaches the archive intact |
| **Key tasks** | Query Modality Worklist (MWL) at console; verify patient/accession; position & scan; perform QC on images; send series via C-STORE/STOW-RS; verify Storage Commitment before purging scanner cache; enter MPPS status (IN PROGRESS/COMPLETED/DISCONTINUED); add-protocol or redo scans; document contrast/radiation dose |
| **Pain points** | Manual demographic re-entry (MWL not populated), missing accession numbers, DICOM send failures with no feedback, slow image transfer, double-scans due to no storage commitment, MPPS mismatch |
| **Success metrics** | % orders served via MWL without manual entry; image reject/repeat rate; time from exam complete → archive verified; interface error rate |
| **Permissions** | Worklist read · perform exam (MPPS) · image upload/store · image QC · retry sends |
| **Regulatory** | Dose documentation (DICOM SR), patient safety, MQSA for mammography QC |

### PAC-P03 · Teleradiologist / Nighthawk Reader

| Attribute | Description |
| :--- | :--- |
| **Real-world identity** | Remote/nighthawk radiologist covering after-hours, overflow, or subspecialty reads across multiple facilities/tenants |
| **Environment** | Home/remote office, any device with a browser; tokenized OAuth2/SMART session (no site VPN) |
| **Primary goals** | Maintain diagnostic quality and throughput across multiple client facilities; low latency with full clinical context; instant access to priors |
| **Key tasks** | Session launch via OAuth2 token; multi-tenant worklist (per-facility consent); pull studies via WADO-RS progressive streaming; priors across tenants (XDS-I.b); dictation; STAT notification to referring MD; report delivery back to each tenant's RIS/EMR |
| **Pain points** | WAN latency, missing outside priors, no local context (clinical history), disjointed communication with on-site staff, per-facility logins |
| **Success metrics** | First-frame render time on reference bandwidth; reads/hr; overnight STAT TAT; cross-tenant prior access success % |
| **Permissions** | Multi-tenant read access scoped per engagement contract; report author/sign; no billing access |
| **Regulatory** | HIPAA BAA for cross-entity access; documented audit of every remote session |

### PAC-P04 · PACS Administrator

| Attribute | Description |
| :--- | :--- |
| **Real-world identity** | PACS systems administrator, DICOM engineer, imaging IT analyst |
| **Environment** | Admin consoles, interface engine dashboards, storage/archive consoles, on-call rotation |
| **Primary goals** | Keep archive & viewers available 24/7/365; maintain data integrity; keep interfaces healthy; support users; manage storage growth & tiers |
| **Key tasks** | Provision modalities (AE titles, IP allow-lists); configure routing rules; monitor DICOM queues & Storage Commitment; manage cache/archive tiers & retention; troubleshoot retrieval failures; run migrations (legacy → VNA); manage user permissions; upgrade & patch; DR drills |
| **Pain points** | Night/weekend outages, rogue modality configs, silent interface drops, storage quota exhaustion, cross-tenant routing mistakes, unannounced vendor firmware changes |
| **Success metrics** | Interface availability; % queries failing; storage headroom; MTTR for P1/P2 incidents; audit-complete % |
| **Permissions** | Admin: modality provisioning, routing, retention, storage quotas, audit logs, tenant-scoped or platform-scoped |
| **Regulatory** | HIPAA security rule (access control, audit, contingency); retention & legal hold enforcement |

### PAC-P05 · Imaging Informatics Specialist (CIIP)

| Attribute | Description |
| :--- | :--- |
| **Real-world identity** | Certified imaging informatics professional (CIIP) bridging clinical radiology and IT |
| **Environment** | Cross-functional: works with clinicians, IT, vendors, AI teams |
| **Primary goals** | Optimize end-to-end imaging workflows; drive interoperability (HL7/DICOM/FHIR/DICOMweb); evaluate new tools (AI, VNA) and ensure they fit clinical workflow |
| **Key tasks** | Map order→report workflows; define hanging protocol libraries; specify integration contracts; lead UAT for viewers & AI; monitor KPI dashboards (TAT, utilization); train superusers |
| **Pain points** | Siloed stakeholders, competing priorities, missing data for decisions, slow vendor responses |
| **Success metrics** | Workflow optimization wins (TAT reduction), UAT completion, KPI dashboard adoption |
| **Permissions** | Analytics dashboards, configuration (non-destructive), read access to audit/ops data |

### PAC-P06 · Referring / Ordering Physician

| Attribute | Description |
| :--- | :--- |
| **Real-world identity** | Primary care, hospitalist, surgeon, oncologist, orthopedist ordering imaging and reviewing results |
| **Environment** | EMR-embedded viewer (SMART on FHIR), web viewer, mobile |
| **Primary goals** | Order the right exam; see results (report + key images) quickly to guide treatment |
| **Key tasks** | View finalized reports; open key images (via EMR launch); compare priors; review critical alerts |
| **Pain points** | Slow report delivery, dense reports without key images, cannot view images from clinic devices |
| **Success metrics** | Report delivery time to EMR; % reports with key images; viewer first-paint |
| **Permissions** | Read-only: view reports & studies for own patients (EMR-scoped) |

### PAC-P07 · Emergency Department Physician

| Attribute | Description |
| :--- | :--- |
| **Real-world identity** | ED attending/resident using imaging for acute care (trauma, stroke, PE) |
| **Environment** | ED workstations, EMR with embedded viewer, on the move |
| **Primary goals** | Fast STAT reads; instant access to preliminary reads & critical alerts; minimal TAT |
| **Key tasks** | Request STAT imaging; view preliminary/critical findings; open images immediately; communicate with radiologist |
| **Pain points** | Acquisition bottlenecks, off-hours teleradiology handoff delays, missing STAT prioritization |
| **Success metrics** | STAT study-to-read TAT; critical-result acknowledgment time |
| **Permissions** | Read-only ED scope + critical-result alerting |

### PAC-P08 · Department Manager / Radiology Director

| Attribute | Description |
| :--- | :--- |
| **Real-world identity** | Radiology manager, imaging operations director, service-line leader |
| **Environment** | Ops dashboards, reports, meetings |
| **Primary goals** | Track TAT, modality utilization, radiologist productivity; meet regulatory & SLA commitments; control costs |
| **Key tasks** | Review KPI dashboards (retrieval time, TAT, utilization, backlog); run reports; investigate outliers; report to executive/regulatory bodies |
| **Pain points** | Inaccurate/absent data, no drill-down, manual report assembly |
| **Success metrics** | KPI accuracy; % SLA targets met; dashboard usage |
| **Permissions** | Department analytics (read), report exports |

### PAC-P19 · Tenant Admin (Org-level SaaS Administrator)

| Attribute | Description |
| :--- | :--- |
| **Real-world identity** | Hospital/imaging-center IT lead or designated tenant administrator who buys & configures the SaaS |
| **Environment** | Tenant admin console |
| **Primary goals** | Onboard the facility, manage users/roles/quotas, watch usage, control costs |
| **Key tasks** | Provision users & roles; set storage quota; configure retention; view usage & invoices; manage SSO; escalate support |
| **Pain points** | Opaque usage/billing, slow onboarding, no quota visibility |
| **Success metrics** | Time-to-provision; usage forecast accuracy; billing disputes = 0 |
| **Permissions** | Tenant-scoped admin (TENANT_ADMIN), user/role management, invoice visibility |

### PAC-P20 · Super Admin (Platform Operator / SaaS Vendor)

| Attribute | Description |
| :--- | :--- |
| **Real-world identity** | Platform operations team of the SaaS vendor (this company) |
| **Environment** | Platform ops console (tenant-ops, billing, metering, support) |
| **Primary goals** | Run the SaaS: provision tenants atomically, enforce isolation, meter & bill, keep 99.9% uptime, support tenants |
| **Key tasks** | Provision/terminate tenants; lifecycle transitions (suspend/reactivate/plan change); cross-tenant analytics; incident response; DR |
| **Pain points** | Cross-tenant data leaks, billing disputes, capacity planning |
| **Success metrics** | Tenant NPS, uptime %, revenue leakage, P1 MTTR |
| **Permissions** | Platform-scoped (`BYPASSRLS` ops role, audited) |

---

## 2. Institutions (PAC-I##)

| ID | Institution | PACS-relevant needs |
| :-: | :--- | :--- |
| PAC-I01 | **Acute-care hospital** (community/academic/trauma) | 24/7 availability, ED & ICU STAT workflows, high concurrency, DR with defined RPO/RTO, trauma/CT-heavy |
| PAC-I02 | **Freestanding imaging / diagnostic center** | High-throughput scheduling, low IT staff, strong patient experience, efficient bandwidth use to central archive |
| PAC-I03 | **Outpatient clinic** (ordering/viewing site) | EMR-embedded viewing, report access, low-friction priors |
| PAC-I04 | **Teleradiology group** | Multi-tenant read coverage, remote tokenized access, workload routing, cross-facility context |
| PAC-I05 | **Integrated Delivery Network (IDN) / health system** | Cross-facility priors (XDS-I.b), enterprise MPI, consolidated analytics & chargeback, one viewer across sites |
| PAC-I10 | **SaaS operator (vendor itself)** | Tenant lifecycle, metering/billing, compliance (SOC 2/HIPAA), support SLAs |

---

## 3. Machines & Systems (PAC-M##) — Integration Actors

Machines are **first-class actors**: they authenticate differently (AE-title + IP allow-list, service keys, OAuth tokens) and drive measurable traffic.

| ID | Machine actor | Role in PACS | Protocols | Key requirements |
| :-: | :--- | :--- | :--- | :--- |
| PAC-M01 | **Imaging modalities** (CT, MR, DR/CR, US, NM, PET, Mammo, Fluoro, Anglo, O-arm) | Generate & send images; query worklist; report status | DICOM C-STORE, C-FIND (MWL), N-CREATE/N-SET (MPPS), Storage Commitment, DICOMweb STOW-RS | Registered AE title + IP per tenant; conformance-aware; retry/backoff; Storage Commitment honored; never silently drop |
| PAC-M02 | **RIS** | Supplies MWL, consumes MPPS, receives reports | DICOM MWL/MPPS; HL7 ORM/ORU | Worklist entries ready before patient arrives; MPPS echoed; report delivered via ORU |
| PAC-M03 | **HIS/EMR** | Provides patient demographics/orders; consumes report | HL7 ADT/ORM/ORU; FHIR R4 ImagingStudy/ServiceRequest/DiagnosticReport | Patient merge handling; accession matching; ImagingStudy endpoint linkage |
| PAC-M04 | **VNA (Vendor-Neutral Archive)** | Long-term neutral archive, cross-enterprise sharing | DICOM, DICOMweb, XDS-I.b | Store once, serve many; non-DICOM content (PDF, video, WSI); data-exit capability |
| PAC-M05 | **AI services** (triage, CAD, segmentation, stroke/PE) | Consume studies, return SR/GSPS/ImagingSelection | DICOM SR/GSPS, UPS-RS, WADO-RS pull, FHIR Observation/DiagnosticReport | Subscribe to UPS-RS; pull via WADO-RS; results stored & visible; audit every AI access |
| PAC-M06 | **Zero-footprint web viewers** (OHIF/Cornerstone-class) | Render studies in browser (EMR-embedded or standalone) | DICOMweb QIDO-RS/WADO-RS, SMART on FHIR, FHIRcast, IHE IUA | Token-based (no PHI in URLs); progressive/partial retrieval; CORS allow-list; frame-level requests |
| PAC-M07 | **Diagnostic workstations** (calibrated displays) | Primary reading stations | DICOM C-FIND/C-MOVE/C-GET, DICOMweb | Calibration consistency; full-res pixels; low-latency retrieval; hanging protocol persistence |
| PAC-M08 | **Storage tiers & edge caches** (hot/warm/cold, cloud object store, local edge node) | ILM + hybrid performance | S3/Blob APIs, lifecycle policies | Tenant-prefixed keys; immutable objects; WORM for ransomware; lifecycle tiering per retention |
| PAC-M09 | **Print/export services** (film printers, CD/DVD, XDS-I.b, portable media) | Distribution & discharge media | DICOM Print, PDI, XDS-I.b | IHE PDI conformance; anonymization options; audit of exports |

---

## 4. Permission Mapping (RBAC skeleton for PACS)

| Capability | Radiologist | Technologist | Referring MD | ED MD | PACS Admin | Tenant Admin | Super Admin |
| :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| Study view/retrieve | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ (audited) |
| Worklist read/prioritize | ✓ | ✓ | — | — | ✓ | — | — |
| Upload/store (C-STORE/STOW-RS) | — | ✓ | — | — | ✓ | — | ✓ |
| Perform/complete exam (MPPS) | — | ✓ | — | — | — | — | — |
| Report author/sign | ✓ | — | — | — | — | — | — |
| Critical-results flag/alert | ✓ | ✓ | — | ✓ | — | — | — |
| Modality provisioning (AE/IP) | — | — | — | — | ✓ | — | ✓ |
| Routing/retention/storage quota | — | — | — | — | ✓ | ✓ | ✓ |
| Audit log view | — | — | — | — | ✓ (tenant) | ✓ (tenant) | ✓ (all) |
| Usage/billing visibility | — | — | — | — | — | ✓ | ✓ |
| Share/export studies | ✓ | — | ✓ (view) | ✓ (view) | ✓ | — | ✓ |

> **Platform note:** all rows scoped by `facility_id` (RLS); cross-tenant access (e.g., priors across a health system, teleradiology) is a deliberate, audited policy decision — never an accident. *(Per `pacs-ris-multitenancy.md` §3.)*
>
> **Read-only personas** (teleradiologist PAC-P03, referring MD PAC-P06, ED MD PAC-P07) and **informatics** (PAC-P05) derive view-only capabilities from the rows above — study view/retrieve, worklist read, critical-alert visibility — with no write/billing capabilities.
