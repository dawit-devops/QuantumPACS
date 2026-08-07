# PACS vs RIS — Side-by-Side Comparison

**Team:** `pacs-ris-research` · **Compiled:** 2026-08-04 · Companion to `research/pacs-ris-research.md`

> **The one-line rule:** PACS handles the **pixels** (images). RIS handles **everything else** (orders, scheduling, reports, billing).

---

## 1. Foundational Comparison

| Dimension | PACS | RIS |
| :--- | :--- | :--- |
| **Full name** | Picture Archiving and Communication System | Radiology Information System |
| **Domain** | Clinical / Diagnostic ("back office") | Administrative / Operational ("front office") |
| **Primary data** | Pixel data — DICOM images (CT, MRI, X-ray, US, PET, NM) | Text/structured data — demographics, orders, schedules, reports, billing codes |
| **Primary users** | Radiologists, referring physicians, surgeons, cardiologists | Schedulers, receptionists, technologists, billers, administrators |
| **Core mission** | Store, retrieve, display, and distribute images | Track the patient/order from referral to final report and billing |
| **Core standards** | DICOM, DICOMweb (WADO-RS, QIDO-RS, STOW-RS) | HL7 v2/v3, FHIR; uses DICOM MWL/MPPS to talk to modalities |
| **Interop framework** | IHE SWF (image side), XDS-I.b, PDI | IHE SWF (order side) |
| **Billing involvement** | None — no financial data | Central — CPT/ICD-10 codes, claims, denials |
| **Uptime criticality** | 24/7/365 — reading is time-sensitive | High availability during clinical hours |
| **Data volume** | Terabytes–petabytes | Gigabytes–terabytes (text only) |

---

## 2. Feature-by-Feature Comparison

| Feature / Capability | PACS | RIS |
| :--- | :--- | :--- |
| **Patient registration** | Not applicable (receives demographics in DICOM headers) | Primary owner — demographics, insurance, MPI dedup, pre-registration |
| **Appointment scheduling** | Not applicable | Primary owner — multi-modality/site booking, resource allocation, reminders |
| **Order entry** | Not applicable (receives orders via MWL) | Primary owner — receives HL7 `ORM`, protocols, priorities (STAT/Urgent/Routine), prior-auth |
| **Modality Worklist (MWL)** | Consumes scheduled items (optional) | **Serves** MWL to scanner consoles (C-FIND) |
| **MPPS (status updates)** | Tracks exam status (start/completed) | Tracks exam status (start/completed/discontinued) |
| **Image acquisition** | Receives DICOM streams via C-STORE | Not applicable |
| **Image storage / archive** | **Core** — tiered storage, VNA-compatible, petabytes | Not applicable |
| **Storage commitment** | **Core** — guarantees safe custody to modalities | Not applicable |
| **Image retrieval** | C-FIND / C-MOVE / WADO-RS retrieval | Not applicable |
| **Image viewing** | **Core** — diagnostic workstation, MPR/3D/cine, zero-footprint web viewer | Not applicable (may embed viewer links) |
| **Report creation** | Optional integration (dictation from viewer) | **Core** — reading queues, structured templates, speech recognition |
| **Critical results alerting** | Not applicable | **Core** — flags urgent findings, documents notification |
| **Report distribution** | Not applicable | **Core** — HL7 `ORU` to EHR, portals, external referrers |
| **Billing / revenue cycle** | Not applicable | **Core** — CPT/ICD-10 capture, charge drop, denial mitigation |
| **Operational dashboards** | Storage/cache/performance metrics | Patient flow, modality utilization, turnaround times |
| **Teleradiology** | **Core** — secure remote reading, bandwidth optimization | Supporting — routing/access management |
| **Prefetching priors** | **Core** — auto-fetch prior studies for comparison | Supplies scheduled list used for prefetch triggers |
| **Audit & compliance** | HIPAA — view/export/delete audit, AES-256, TLS | HIPAA — RBAC, audit trails, retention policies |

---

## 3. Workflow Comparison (Exam Lifecycle)

| Workflow Stage | PACS Role | RIS Role |
| :--- | :--- | :--- |
| **1. Order** | None (receives order context later) | Receives HL7 `ORM` from EHR; assigns Accession Number; checks prior-auth |
| **2. Schedule** | None | Books slot, room, technologist; sends reminders |
| **3. Worklist** | None | Serves Modality Worklist (MWL) to scanner |
| **4. Acquire** | Receives images (C-STORE); issues Storage Commitment | Receives MPPS "IN PROGRESS" |
| **5. Complete** | Confirms series received/completed | Receives MPPS "COMPLETED"; updates tracking board |
| **6. Read** | Radiologist opens study in viewer; uses diagnostic tools | Radiologist worklist prioritized; report started via dictation/templates |
| **7. Report** | None (context for report) | Structured report authored, critical results flagged |
| **8. Sign & distribute** | None | Report signed, HL7 `ORU` sent to EHR/portal/referrer |
| **9. Bill** | None | CPT/ICD-10 charge dropped to billing engine |
| **10. Archive** | Long-term tiered archive; priors prefetched for future reads | Report/order archival and retention |

---

## 4. What Each System Must Have (Requirement Summary)

| Requirement Area | PACS (must have) | RIS (must have) |
| :--- | :--- | :--- |
| **Functional** | DICOM storage/query/retrieve; viewer tools (MPR, MIP, 3D, cine); prefetching; teleradiology; DICOMweb APIs | Scheduling; order management; MWL serving; status tracking; reporting; results distribution; billing |
| **Performance** | ~2–3 s study load; caching (SSD/NVMe) | Sub-second worklist/queue responsiveness |
| **Storage** | 3-tier lifecycle (hot 0–30 d / warm 1–12 mo / deep 5–30+ yr) | Report/order retention + audit data |
| **Security** | TLS 1.2+, AES-256 at rest, RBAC, audit trails, HIPAA/BAA | RBAC, audit trails, HIPAA compliance |
| **Availability** | Cluster failover, geo-redundant DR, RPO/RTO defined | HA during clinical hours |
| **Interoperability** | DICOM, DICOMweb (primary); HL7 ADT + limited ORM/ORU only via interface engine or RIS | HL7 v2 (ADT/ORM/ORU), FHIR, DICOM MWL/MPPS, IHE SWF |
| **Scalability** | Horizontal scale of storage + compute; growing study volumes | Multi-site/multi-tenant support |

---

## 5. Integration Touchpoints (Where They Meet)

| Integration | Protocol | Direction |
| :--- | :--- | :--- |
| Order → RIS | HL7 `ORM` | EHR/HIS → RIS |
| Worklist → Modality | DICOM C-FIND (MWL) | RIS → Modality |
| Status → RIS/PACS | DICOM N-CREATE/N-SET (MPPS) | Modality → RIS/PACS |
| Images → PACS | DICOM C-STORE | Modality → PACS |
| PACS → Modality (safe to purge) | DICOM Storage Commitment | PACS → Modality |
| Report → EHR | HL7 `ORU` | RIS → EHR |
| Demographics updates | HL7 `ADT` | HIS → RIS/PACS |
| Modern APIs | FHIR / DICOMweb | RIS/EHR ↔ PACS |

---

## 6. Decision Guide — When Do You Need Which?

| Scenario | You mainly need |
| :--- | :--- |
| Store & read images faster | **PACS** |
| Manage schedules, orders, reports, billing | **RIS** |
| End-to-end (order → report → bill) | **Both, integrated** (IHE SWF) |
| Share images across enterprises | PACS + XDS-I.b / VNA |
| Regulatory compliance (HIPAA, retention) | Both (architects required) |
