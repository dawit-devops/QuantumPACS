# RIS — Metrics & SLAs

**Document:** 05 of 06 · **Version:** 1.0 · **Date:** 2026-08-04

SLAs and KPIs for the RIS surface. System-level SLAs shared with PACS (availability, incident response, DR) are defined in `PACS/05_metrics_and_slas.md` and referenced here; RIS adds workflow- and revenue-focused metrics. Metering feeds `usage_metering` / `tenant_invoices` (`pacs-ris-multitenancy.md` §7).

---

## 1. System-Level SLAs (shared platform)

| ID | Metric | Target |
| :--- | :--- | :--- |
| RIS-SL-01 | Availability | **99.9%** monthly; 99.95% premium tier (same as PAC-SL-01) |
| RIS-SL-02 | Incident response | P1 ≤ 15 min initial response 24/7; P2 ≤ 30 min; P3 next business day |
| RIS-SL-03 | RTO / RPO | RTO ≤ 4 h; RPO ≤ 60 min |
| RIS-SL-04 | Planned downtime | ≤ 4 h/quarter, ≥ 7 days notice; zero-downtime patching desired |

## 2. Performance SLAs (per-persona experience)

| ID | Persona | Metric | Target |
| :--- | :--- | :--- | :--- |
| RIS-SL-10 | Technologist | MWL query served to modality console | **< 1 s** p95 |
| RIS-SL-11 | Scheduler | Booking slot search & save | **< 1.5 s** p95 |
| RIS-SL-12 | Front Desk | Registration/check-in screen transitions | **< 1 s** p95 |
| RIS-SL-13 | Radiologist | Worklist load with filters | **< 1 s** p95 |
| RIS-SL-14 | Radiologist | Report save/draft autosave | **< 1 s** perceived (async) |
| RIS-SL-15 | All | Tracking board live-update latency | **≤ 30 s** (v1 polling); real-time later |

## 3. Workflow & Interface SLAs

| ID | Metric | Target | Owner |
| :--- | :--- | :--- | :--- |
| RIS-SL-20 | **Order intake → accessible for scheduling** | **< 1 min** after HL7 ORM/FHIR receipt | Integration |
| RIS-SL-21 | **Scheduled order → on MWL** | Immediately at schedule; 100% of scheduled exams served | RIS |
| RIS-SL-22 | **MPPS → tracking board update** | **< 5 s** after receipt; 100% echo to PACS | Integration |
| RIS-SL-23 | **Interface message delivery** (HL7/DICOM) | **> 99.9%** delivered; 0 silent drops; failures alerted ≤ 5 min | Ops |
| RIS-SL-24 | **Signed report → EMR delivery** (ORU/FHIR) | **< 5 min** after sign-off; 100% delivered | Integration |
| RIS-SL-25 | **Critical-results acknowledgment** | 100% notified; unacknowledged escalated per policy (e.g., 15 min); acknowledgment documented | RIS |

## 4. Department KPIs (reported to Radiology Director / Steering)

| ID | Metric | Target (typical benchmark) | Notes |
| :--- | :--- | :--- | :--- |
| RIS-SL-30 | **Report TAT — STAT/ED** | **< 30–60 min** | study complete → final signed |
| RIS-SL-31 | **Report TAT — Inpatient** | **< 2–4 h** | |
| RIS-SL-32 | **Report TAT — Outpatient** | **24–48 h** | |
| RIS-SL-33 | **% orders via MWL without manual entry** | **≥ 98%** | technologist efficiency |
| RIS-SL-34 | **Scheduling conflict rate** | **0 conflicts** (system-enforced); override rate < 1% (audited) | |
| RIS-SL-35 | **No-show rate** | Reduction ≥ 20% vs. baseline with reminders | |
| RIS-SL-36 | **Prior-auth approval before exam** | **≥ 95%** of required exams authorized pre-scan | |
| RIS-SL-37 | **Duplicate MRN rate** | **< 1%** new-registration duplicate rate | MPI health |

## 5. Billing & Revenue Cycle KPIs

| ID | Metric | Target | Notes |
| :--- | :--- | :--- | :--- |
| RIS-SL-40 | **Charge capture rate** | **≥ 98%** of signed exams billed | revenue integrity |
| RIS-SL-41 | **Unbilled aging** | **$0** older than 5 business days (actionable backlog) | |
| RIS-SL-42 | **Claim denial rate** | **< 10%** (baseline-dependent), with reason-code analysis | |
| RIS-SL-43 | **Coding accuracy** | ≥ 95% first-pass clean claims | |
| RIS-SL-44 | **Charge drop latency** | **< 24 h** from report sign-off to charge drop | |

## 6. SaaS Business Metrics (platform)

| ID | Metric | Target |
| :--- | :--- | :--- |
| RIS-SL-50 | Metering accuracy (MWL queries, API calls, notifications) | 100% events captured; invoice variance audit = 0 unresolved |
| RIS-SL-51 | Tenant provisioning time | < 15 min to READY (shared schema) |
| RIS-SL-52 | Tenant admin time-to-value | ≤ 1 business day to configure sites/rooms/schedules for a new tenant |

## 7. Security & Audit SLAs

| ID | Metric | Target |
| :--- | :--- | :--- |
| RIS-SL-60 | Audit completeness | 100% of order/schedule/report/access/export events logged (HIPAA) |
| RIS-SL-61 | Isolation assurance | 0 cross-tenant PHI incidents; quarterly RLS policy audit |
| RIS-SL-62 | Encryption / patching | TLS 1.2+, AES-256; critical CVEs ≤ 72 h; SOC 2 Type II available |

---

## SLA ownership summary

| SLA family | Owned by | Monitor |
| :--- | :--- | :--- |
| System (RIS-SL-01…04) | Platform ops | uptime dashboards |
| Performance (RIS-SL-10…15) | Engineering/SRE | APM |
| Workflow & interfaces (RIS-SL-20…25) | Integration team | interface dashboards, exception queue |
| Department KPIs (RIS-SL-30…37) | Tenant (radiology dept) | KPI dashboard |
| Billing (RIS-SL-40…44) | Tenant (billing) + platform | billing workspace |
| SaaS business (RIS-SL-50…52) | Platform ops | `tenant_invoices`, `v_tenant_billable` |
| Security (RIS-SL-60…62) | Security | audit tooling |
