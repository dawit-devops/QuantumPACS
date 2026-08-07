# PACS — User Stories

**Document:** 03 of 06 · **Version:** 1.0 · **Date:** 2026-08-04

Syntax (EARS): `As a <persona>, I want <capability>, so that <benefit>.` Priorities: `M` mandatory · `D` desired · `O` optional. Each story maps to ≥1 acceptance criterion (`06_acceptance_criteria.md`) and ≥1 workflow (`02_end_to_end_workflows.md`).

---

## PAC-P01 · Radiologist

| ID | Story | Pri | WF | AC |
| :--- | :--- | :-: | :-: | :-: |
| PAC-US-P01-01 | As a radiologist, I want a prioritized reading worklist (STAT > inpatient > outpatient) with modality, site, and date filters, so that I spend my time reading the most urgent studies first. | M | WF2 | PAC-AC-P01-01 |
| PAC-US-P01-02 | As a radiologist, I want configurable hanging protocols (per anatomy/modality/priority, saved per user), so that studies open in the right layout without manual setup. | M | WF2 | PAC-AC-P01-02 |
| PAC-US-P01-03 | As a radiologist, I want prior studies automatically prefetched and available one-click away — including priors from other facilities in my health system — so that comparison is fast and diagnosis is confident. | M | WF2, WF3 | PAC-AC-P01-03 |
| PAC-US-P01-04 | As a radiologist, I want diagnostic tools (window/level, zoom, pan, cine, MPR, MIP/MinIP, 3D, PET/CT fusion, measurements) in the viewer, so that I can fully interrogate the anatomy. | M | WF2 | PAC-AC-P01-04 |
| PAC-US-P01-05 | As a radiologist, I want AI results (triage flags, segmentation, CAD) presented as overlays with confidence and accept/reject controls, so that I can use AI to speed up but still control the diagnosis. | O | WF6 | PAC-AC-P01-05 |
| PAC-US-P01-06 | As a radiologist, I want to flag critical findings with one action and have the notification tracked until acknowledged, so that urgent findings never fall through the cracks. | M | WF2 | PAC-AC-P01-06 |
| PAC-US-P01-07 | As a radiologist, I want to bookmark key images and link them to my report, so that referring physicians see the relevant finding immediately. | D | WF2 | PAC-AC-P01-07 |
| PAC-US-P01-08 | As a radiologist, I want to open a study and see the first frames in under 3 seconds on my workstation, so that I don't lose flow during peak reading. | M | WF2 | PAC-AC-P01-08 |
| PAC-US-P01-09 | As a radiologist, I want my work-in-progress (unfinished reads, open reports) preserved if I switch devices or sessions, so that I can continue reading without redoing work. | D | WF2 | PAC-AC-P01-09 |
| PAC-US-P01-10 | As a radiologist, I want a stable viewer that never loses my place on large studies (progressive/partial retrieval), so that multi-GB studies are readable on reference bandwidth. | M | WF2, WF7 | PAC-AC-P01-10 |

## PAC-P02 · Radiology Technologist

| ID | Story | Pri | WF | AC |
| :--- | :--- | :-: | :-: | :-: |
| PAC-US-P02-01 | As a technologist, I want the modality worklist to auto-populate patient demographics, accession, and requested procedure, so that I never manually re-type patient data at the console. | M | WF1 | PAC-AC-P02-01 |
| PAC-US-P02-02 | As a technologist, I want a clear Storage Commitment acknowledgment before purging the scanner cache, so that images are never lost due to premature purge. | M | WF1 | PAC-AC-P02-02 |
| PAC-US-P02-03 | As a technologist, I want instant feedback on DICOM send success/failure with retry, so that failed transfers are fixed immediately instead of discovered later. | M | WF1 | PAC-AC-P02-03 |
| PAC-US-P02-04 | As a technologist, I want MPPS status updates to flow automatically (in-progress/completed/discontinued), so that the tracking board stays accurate without manual entry. | M | WF1 | PAC-AC-P02-04 |
| PAC-US-P02-05 | As a technologist, I want to redo or add series and have them appear in the correct study, so that repeat scans stay with the original accession. | M | WF1 | PAC-AC-P02-05 |
| PAC-US-P02-06 | As a technologist, I want image QC tools (review, mark as adequate/inadequate, reject with reason), so that only diagnostically acceptable images reach the archive. | D | WF1 | PAC-AC-P02-06 |
| PAC-US-P02-07 | As a sonographer/mammography tech, I want modality-specific workflows (cine loops, tomosynthesis series, MQSA QC records), so that my specialty exams archive completely. | D | WF1 | PAC-AC-P02-07 |

## PAC-P03 · Teleradiologist / Nighthawk

| ID | Story | Pri | WF | AC |
| :--- | :--- | :-: | :-: | :-: |
| PAC-US-P03-01 | As a teleradiologist, I want to launch a tokenized session from anywhere (no VPN) and read studies from multiple client facilities, so that I can provide coverage across sites efficiently. | M | WF4 | PAC-AC-P03-01 |
| PAC-US-P03-02 | As a teleradiologist, I want progressive image streaming so the first frames appear fast on my home bandwidth, so that remote reads are not slower than on-site reads. | M | WF4 | PAC-AC-P03-02 |
| PAC-US-P03-03 | As a teleradiologist, I want audited access to priors across my client facilities, so that I can compare current with prior exams for continuity of care. | D | WF4 | PAC-AC-P03-03 |
| PAC-US-P03-04 | As a teleradiologist, I want to trigger a critical-results notification to on-site staff and have acknowledgment tracked, so that urgent findings reach the treating team immediately. | M | WF4 | PAC-AC-P03-04 |
| PAC-US-P03-05 | As a teleradiologist, I want my signed reports routed to the correct ordering facility's RIS/EMR automatically, so that reports land in the right record without manual forwarding. | M | WF4 | PAC-AC-P03-05 |

## PAC-P04 · PACS Administrator

| ID | Story | Pri | WF | AC |
| :--- | :--- | :-: | :-: | :-: |
| PAC-US-P04-01 | As a PACS administrator, I want to register modalities with AE title + IP allow-list per tenant, so that only known machines can send images. | M | WF1 | PAC-AC-P04-01 |
| PAC-US-P04-02 | As a PACS administrator, I want routing rules (by modality, site, anatomy) with a queue monitor, so that studies flow to the right archive/viewer without manual intervention. | M | WF1 | PAC-AC-P04-02 |
| PAC-US-P04-03 | As a PACS administrator, I want configurable retention policies (5–30+ yr, pediatric mandates) with legal-hold override, so that we comply with regulations and never purge protected data. | M | WF5 | PAC-AC-P04-03 |
| PAC-US-P04-04 | As a PACS administrator, I want storage usage visibility with quota alerts at 75/90%, so that I can plan capacity and avoid tenant quota exhaustion. | M | WF5 | PAC-AC-P04-04 |
| PAC-US-P04-05 | As a PACS administrator, I want an exception/orphan worklist (failed validation, missing accession, mismatched patient), so that problem studies are reconciled instead of lost. | M | WF1 | PAC-AC-P04-05 |
| PAC-US-P04-06 | As a PACS administrator, I want audited export (CD/DVD, XDS-I.b, anonymized) with reason codes, so that every data release is documented for HIPAA. | D | WF8 | PAC-AC-P04-06 |
| PAC-US-P04-07 | As a PACS administrator, I want DR failover with defined RPO/RTO and quarterly drills, so that the archive is recoverable and the team knows the procedure. | M | WF9 | PAC-AC-P04-07 |
| PAC-US-P04-08 | As a PACS administrator, I want interface health dashboards (DICOM queues, HL7 failures, modality online/offline) with alerting, so that I catch issues before clinicians notice. | M | WF1 | PAC-AC-P04-08 |
| PAC-US-P04-09 | As a PACS administrator, I want to migrate legacy studies into the archive with automated count reconciliation, so that migrations are verifiable and complete. | D | (migration) | PAC-AC-P04-09 |

## PAC-P05 · Imaging Informatics Specialist

| ID | Story | Pri | WF | AC |
| :--- | :--- | :-: | :-: | :-: |
| PAC-US-P05-01 | As an imaging informatics specialist, I want KPI dashboards (retrieval time, TAT, backlog, utilization) with drill-down, so that I can identify and fix workflow bottlenecks. | M | WF2, WF6 | PAC-AC-P05-01 |
| PAC-US-P05-02 | As an imaging informatics specialist, I want to define and version hanging protocol libraries and viewer defaults, so that new sites/specialties get consistent, proven configurations. | D | WF2 | PAC-AC-P05-02 |

## PAC-P06 · Referring Physician

| ID | Story | Pri | WF | AC |
| :--- | :--- | :-: | :-: | :-: |
| PAC-US-P06-01 | As a referring physician, I want to open my patient's images from the EMR with one click (SMART on FHIR) and see the report with key images, so that I can make treatment decisions without leaving my workflow. | D | WF7 | PAC-AC-P06-01 |
| PAC-US-P06-02 | As a referring physician, I want reports delivered to the EMR automatically when signed, so that I see results without logging into another system. | M | WF7 | PAC-AC-P06-02 |
| PAC-US-P06-03 | As a referring physician, I want to view images on my clinic device (responsive viewer), so that I can show results to patients during the visit. | D | WF7 | PAC-AC-P06-03 |

## PAC-P07 · Emergency Department Physician

| ID | Story | Pri | WF | AC |
| :--- | :--- | :-: | :-: | :-: |
| PAC-US-P07-01 | As an ED physician, I want STAT studies prioritized in the acquisition and reading queues, so that trauma/stroke patients get answers fast. | M | WF1, WF2 | PAC-AC-P07-01 |
| PAC-US-P07-02 | As an ED physician, I want immediate visibility of preliminary/critical reads and the ability to reach the radiologist, so that I can act on urgent findings without waiting for the final report. | M | WF2 | PAC-AC-P07-02 |

## PAC-P08 · Department Manager

| ID | Story | Pri | WF | AC |
| :--- | :--- | :-: | :-: | :-: |
| PAC-US-P08-01 | As a department manager, I want TAT, utilization, and backlog dashboards with export, so that I can report to leadership and regulators accurately. | M | WF2 | PAC-AC-P08-01 |

## PAC-P19 · Tenant Admin · PAC-P20 · Super Admin (platform)

| ID | Story | Pri | WF | AC |
| :--- | :--- | :-: | :-: | :-: |
| PAC-US-P19-01 | As a tenant admin, I want to see my storage usage vs. quota and projected growth, so that I can manage costs and capacity. | M | WF5 | PAC-AC-P19-01 |
| PAC-US-P19-02 | As a tenant admin, I want role-based user management with audit, so that access follows staff changes. | M | — | PAC-AC-P19-02 |
| PAC-US-P20-01 | As a super admin, I want atomic tenant provisioning with rollback, so that no tenant is left half-configured. | M | WF10 | PAC-AC-P20-01 |
| PAC-US-P20-02 | As a super admin, I want usage metering (WADO bytes, studies stored, API calls) feeding tenant invoices, so that billing reflects real usage. | M | — | PAC-AC-P20-02 |
| PAC-US-P20-03 | As a super admin, I want cross-tenant access (priors, teleradiology) to be explicit, policy-gated, and fully audited, so that no PHI crosses a tenant boundary accidentally. | M | WF4 | PAC-AC-P20-03 |

---

## Story counts by priority

| System | M | D | O | Total |
| :--- | :-: | :-: | :-: | :-: |
| PACS | 33 | 10 | 1 | 44 |
