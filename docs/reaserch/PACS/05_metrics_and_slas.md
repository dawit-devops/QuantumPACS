# PACS — Metrics & SLAs

**Document:** 05 of 06 · **Version:** 1.0 · **Date:** 2026-08-04

All SLAs are **contractual baselines for the multi-tenant SaaS** and map to the platform's metering (`usage_metering`, `v_tenant_billable` — `pacs-ris-multitenancy.md` §7). Metrics are grouped by persona/workflow so each stakeholder has an objective number to hold the platform to.

---

## 1. System-Level SLAs (platform contract)

| ID | Metric | SLA Target | Rationale / Source |
| :--- | :--- | :--- | :--- |
| PAC-SL-01 | **Availability (uptime)** | **99.9%** monthly (≤ ~43 min downtime/mo); 99.95% for core read-path in a documented premium tier | Research: 24/7/365 imaging; RFP F2 |
| PAC-SL-02 | **Incident response** | P1 ≤ 15 min initial response, 24/7; P2 ≤ 30 min; P3 next business day | RFP G7 |
| PAC-SL-03 | **Recovery Time Objective (RTO)** | ≤ 4 h full restore; core reading via edge cache continues during outage | Industry benchmark |
| PAC-SL-04 | **Recovery Point Objective (RPO)** | ≤ 60 min data loss window; ingestion buffered during outage | Industry benchmark |
| PAC-SL-05 | **Planned downtime** | ≤ 4 h/quarter, notified ≥ 7 days ahead; zero-downtime patching desired | RFP G8/F17 |

## 2. Performance SLAs (per-persona experience)

| ID | Persona | Metric | SLA Target |
| :--- | :--- | :--- | :--- |
| PAC-SL-10 | Radiologist | Active-study load (worklist → first frames on diagnostic workstation) | **< 2–3 s** |
| PAC-SL-11 | Radiologist | First-frame progressive render (web viewer, reference bandwidth) | **< 3 s** |
| PAC-SL-12 | Teleradiologist | First-frame render on 25 Mbps home link, 500 MB study | **< 5 s** |
| PAC-SL-13 | Referring MD | EMR-launch → correct study displayed | **< 5 s** |
| PAC-SL-14 | Technologist | MWL query response at console | **< 1 s** (sub-second, p95) |
| PAC-SL-15 | Technologist | C-STORE → Storage Commitment acknowledgment | **< 60 s** for a complete series set |
| PAC-SL-16 | PACS Admin | QIDO-RS study query | **< 500 ms** p95 |
| PAC-SL-17 | All | WADO-RS metadata retrieval | **< 1 s** p95 |

## 3. Clinical Workflow SLAs

| ID | Metric | SLA Target | Owner |
| :--- | :--- | :--- | :--- |
| PAC-SL-20 | **Study ingestion → index & retrievable** | **< 5 min** after C-STORE completes | PACS |
| PAC-SL-21 | **Storage Commitment accuracy** | 100% of committed studies verifiable; 0 silent purges | PACS |
| PAC-SL-22 | **Orphan/exception rate** (studies failing auto-validation) | **< 0.5%** of studies; 100% of orphans worked within 24 h | PACS Admin |
| PAC-SL-23 | **Interface message delivery** (DICOM/HL7/MPPS) | **> 99.9%** delivered; 0 silent drops; 100% failures alert within 5 min | Ops |
| PAC-SL-24 | **Prior availability** at read time | **≥ 95%** of exams have priors prefetched or retrievable on demand < 10 s | Prefetch engine |
| PAC-SL-25 | **Cross-tenant prior access** (IDN/teleradiology) | Authorization decision **< 1 s**; 100% audited | Platform |

## 4. Department KPIs (reported to Radiology Director / Steering)

| ID | Metric | Target (typical benchmark) | Notes |
| :--- | :--- | :--- | :--- |
| PAC-SL-30 | **Report turnaround time (TAT)** — STAT/ED | **< 30–60 min** (study complete → final signed) | ED dashboard |
| PAC-SL-31 | **TAT — Inpatient** | **< 2–4 h** | |
| PAC-SL-32 | **TAT — Outpatient** | **24–48 h** | |
| PAC-SL-33 | **Modality uptime** (CT/MR/XR assets feeding the platform) | **99.5–99.9%** | Operational, tenant-side |
| PAC-SL-34 | **% MWL without manual entry** | **≥ 98%** of exams | Technologist efficiency |
| PAC-SL-35 | **Image repeat/reject rate** | **< 5%** | QC KPI |
| PAC-SL-36 | **Radiologist productivity** | studies read / FTE / day (per department target) | Analytics |
| PAC-SL-37 | **Retrieval success rate** (all retrieval requests) | **≥ 99.5%** | Archive health |

## 5. Storage & ILM SLAs

| ID | Metric | Target |
| :--- | :--- | :--- |
| PAC-SL-40 | Tier1 hot (0–30 d) retrieval | < 2 s (edge/SSD) |
| PAC-SL-41 | Tier2 warm (1–12 mo) retrieval | < 10 s (cloud standard) |
| PAC-SL-42 | Tier3 deep archive (5–30+ yr) retrieval | < 60 s (cold/Glacier-class) |
| PAC-SL-43 | Retention policy enforcement | 100% compliant purges; legal-hold overrides honored and audited; **0 accidental purges** |
| PAC-SL-44 | Storage durability | 99.999999999% (11 nines) object store; WORM/immutable enabled |
| PAC-SL-45 | Quota alerts | Notify tenant admin at 75% & 90% of storage quota; hard-stop configurable |

## 6. Billing & Metering Metrics (SaaS)

| ID | Metric | Target |
| :--- | :--- | :--- |
| PAC-SL-50 | Metering accuracy (studies stored, WADO bytes, API calls) | 100% of events captured; monthly invoice variance audit = 0 unresolved |
| PAC-SL-51 | Tenant provisioning time | < 15 min to READY for shared-schema; < 24 h for schema-per-tenant escape hatch |
| PAC-SL-52 | Invoice delivery | On schedule (period-end + 5 business days); disputes resolved ≤ 5 business days |

## 7. Security & Audit SLAs

| ID | Metric | Target |
| :--- | :--- | :--- |
| PAC-SL-60 | Audit completeness | 100% of view/retrieve/export/delete/share/access events logged (HIPAA) |
| PAC-SL-61 | Cross-tenant isolation assurance | 0 cross-tenant PHI incidents; quarterly RLS policy audit; DRR evidence |
| PAC-SL-62 | Encryption | TLS 1.2+ in transit; AES-256 at rest; keys per tenant option |
| PAC-SL-63 | Vulnerability patching | Critical CVEs patched ≤ 72 h; monthly scan cadence; SOC 2 Type II report available |

---

## SLA ownership summary

| SLA family | Owned by | Monitor |
| :--- | :--- | :--- |
| System availability / incident response (PAC-SL-01…05) | Platform ops | `v_tenant_billable`, uptime dashboards |
| Performance (PAC-SL-10…17) | Engineering / SRE | APM + WADO/QIDO latency metrics |
| Clinical workflow (PAC-SL-20…25) | Product + Integration | Interface health dashboards |
| Department KPIs (PAC-SL-30…37) | Tenant (radiology dept) | KPI dashboard (`pacs-ris-kpi-dashboard`) |
| Storage/ILM (PAC-SL-40…45) | Platform + Tenant admin | Storage dashboard |
| Billing (PAC-SL-50…52) | Platform ops | `tenant_invoices` |
| Security/audit (PAC-SL-60…63) | Security | Audit log tooling |
