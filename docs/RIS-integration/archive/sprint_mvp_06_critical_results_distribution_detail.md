# Sprint MVP-06 Detail — Critical Results (E-RIS-09) & Results Distribution (E-RIS-10)

**Version:** 1.0 · **Date:** 2026-08-18 · **Source:** `ris-integration-spec.md` §9.1; `RELEASE_PLAN.md` E-RIS-09, E-RIS-10; `02_end_to_end_workflows.md` RIS-WF4/WF5; `06_acceptance_criteria.md` RIS-AC-P01-03, RIS-AC-P08-02
**Cadence:** one 2-week sprint (S10) · **Squads:** RIS-MVP — two backend, one frontend, part-time integration engineer, QA

---

## 1. Sprint Goal

> **"A radiologist flags a critical finding with one action; the referring physician is notified immediately with tracked acknowledgment; unacknowledged results escalate per policy; and signed reports are delivered to the EMR within 5 minutes — 100% delivered, 0 silent failures."**

**Scope in:** Critical result flagging (one action), recipient selection, tracked notification (EHR_ALERT/MESSAGING/PAGE/PHONE), acknowledgment + escalation, critical flag in ORU payload, signed report → ORU/FHIR → EMR delivery (< 5 min), delivery status/retry, portal/SMS/email notifications.

**Scope out:** Billing (S11), hardening (S12).

---

## 2. Team Capacity (one 10-day sprint)

| Role | FTE | Available dev-days | Notes |
| :--- | :-: | :-: | :--- |
| Backend engineer ×2 | 2.0 | 20 | Critical results service, escalation, ORU distribution, delivery retry |
| Frontend engineer ×1 | 1.0 | 10 | Critical results UX, recipient selection, ack UI |
| Integration engineer | 0.5 | 5 | ORU distribution conformance, notification providers |
| QA | 1.0 | 10 | Critical results E2E, distribution E2E, escalation |
| **Total** | **4.5** | **~45** | Total task estimate below: **~32 dev-days** (BE 12.0 · FE 5.0 · INT 4.0 · QA 7.0) — ~13 days slack |

---

## 3. Task Board

### 3.1 Critical Results — E-RIS-09 #1/2/3/4
**Source:** `RELEASE_PLAN.md` E-RIS-09 #1–4; `ris-integration-spec.md` §3.2 Migration 3; `06_acceptance_criteria.md` RIS-AC-P01-03.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S6-01 | `ris_critical_results` table + Alembic migration (Migration 3 partial); flag_description, notification_channel, recipient, escalation_level, status | BE | 1.0 | — | Table created |
| S6-02 | Critical flag API: `POST /api/ris/critical-results` — one-action flag with recipient selection; creates notification; embeds flag in report | BE | 2.0 | S5-11 | RIS-AC-P01-03; one action |
| S6-03 | Acknowledgment API: `POST /api/ris/critical-results/{id}/acknowledge` — recipient ack with timestamp; escalation timer reset | BE | 1.5 | S6-02 | 100% ack tracked; RIS-SL-25 |
| S6-04 | Escalation policy config: configurable escalation rules (e.g., 15 min → page, 30 min → phone); background task checks unacknowledged | BE | 2.0 | S6-03 | Escalates on timeout; RIS-SL-25 |
| S6-05 | Critical flag in ORU payload: signed report ORU carries critical flag; embedded in HL7 OBX segment | BE | 1.0 | S6-02, S5-12 | ORU payload carries critical flag |
| S6-06 | Critical results UI: extend `frontend/src/radiologist/ReportPanel.tsx` — one-click flag button, recipient selection dialog, ack receipt, escalation status visible | FE | 3.0 | S6-02 | RIS-UI-27 parity; WCAG 2.1 AA |
| S6-07 | Critical results list: `GET /api/ris/critical-results` — list all critical results for facility with status (pending/acknowledged/escalated) | BE | 1.0 | S6-02 | List works; filters by status |
| S6-08 | Critical results list UI: new `frontend/src/radiologist/CriticalResults.tsx` — list with persistent badges until acknowledged; acknowledged time visible | FE | 2.0 | S6-07 | RIS-UI-11 parity |

**Epic exit contribution:** E-RIS-09 #1–4 (critical results loop).

### 3.2 Results Distribution — E-RIS-10 #1/2
**Source:** `RELEASE_PLAN.md` E-RIS-10 #1/2; `ris-integration-spec.md` §2.2; `06_acceptance_criteria.md` RIS-AC-P08-02.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S6-09 | ORU distribution engine: signed report → HL7 ORU^R01 message → EMR endpoint (from `ris_interface_endpoints` config); delivery status tracking | BE | 2.5 | S5-12 | Signed report → ORU delivered < 5 min (RIS-SL-24); 0 silent failures |
| S6-10 | Delivery retry: failed ORU delivery → retry queue (configurable max_retries); exception handling; delivery status visible | BE | 1.5 | S6-09 | 0 silent failures; retry works |
| S6-11 | Portal/SMS/email result-availability notifications: signed report → notification to patient (opt-out honored) | INT | 2.0 | S6-09 | RIS-AC-P08-02; opt-out honored |
| S6-12 | Delivery status API: `GET /api/ris/reports/{exam_id}/delivery` — delivery status per recipient (EMR, patient portal) | BE | 1.0 | S6-09 | Status visible; retry available |

**Epic exit contribution:** E-RIS-10 #1/2 (results distribution).

### 3.3 Cross-cutting: E2E

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S6-13 | Critical results E2E: flag critical → recipient notified → ack → escalation timer → unacknowledged escalation → ack clears escalation | QA | 2.0 | S6-01…08 | RIS-AC-P01-03; RIS-SL-25 |
| S6-14 | Distribution E2E: sign report → ORU generated → delivered to EMR endpoint → delivery status → retry on failure → patient notification → opt-out honored | QA | 2.0 | S6-09…12 | RIS-AC-P08-02; RIS-SL-24 |
| S6-15 | RLS on critical results: cross-facility critical results denied | QA | 0.5 | S6-02 | PAC-SL-61 |

---

## 4. Sprint Milestones

| Milestone | Target | Evidence |
| :--- | :--- | :--- |
| **Day 3** | Critical results table + flag API + ack API; ORU distribution scaffold | S6-01/02/03, S6-09 started |
| **Day 5** | Escalation policy; critical flag in ORU; critical results UI; delivery retry | S6-04/05/06, S6-10 closed |
| **Day 8** | Critical results list + UI; ORU distribution live; portal notifications | S6-07/08, S6-09/11, S6-12 closed |
| **Day 10 (demo)** | Critical results + distribution E2E green; demo: flag → ack → escalate → ORU → delivery → notification | S6-13…15; sprint review |

---

## 5. Sprint Definition of Done

| # | Check | Verifies | Method |
| :-: | :--- | :--- | :--- |
| D1 | Critical results: one-action flag, tracked ack, escalation; 100% ack; RIS-SL-25 | RIS-AC-P01-03 | S6-13 |
| D2 | Distribution: signed report → ORU < 5 min; 0 silent failures; retry works; RIS-SL-24 | RIS-AC-P08-02 | S6-14 |
| D3 | Patient notifications: opt-out honored; every send logged | RIS-SL-60 | S6-14 |
| D4 | Engineering DoD: `tsc --noEmit` + `vite build` clean; unit tests green; migrations reviewed | release-plan §6 | CI gate |
| D5 | No P0/P1 open defects | release-plan §6 | Defect triage |

---

## 6. Risks & Watch Items

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| Escalation timer precision (background task vs. real-time) | S6-04 | pg_cron for escalation checks; timer granularity 1 min; documented |
| EMR ORU endpoint availability (test vs. real) | S6-09 | Mock EMR endpoint for dev/test; real endpoint configurable per tenant |
| Notification provider reliability (SMS/email) | S6-11 | Retry + exception queue; provider redundancy; ≤ 5-min failure alerting |
| Critical result acknowledgment tracking accuracy | S6-13 | Every ack timestamped; escalation timer reset on ack; audit trail |

---

## Traceability

| Source work item | Tasks |
| :--- | :--- |
| E-RIS-09 #1 (flag + recipient) | S6-01/02 |
| E-RIS-09 #2 (ack + escalation) | S6-03/04 |
| E-RIS-09 #3 (escalation config) | S6-04 |
| E-RIS-09 #4 (critical in ORU) | S6-05 |
| E-RIS-10 #1 (ORU distribution) | S6-09/10/12 |
| E-RIS-10 #2 (delivery retry) | S6-10 |
| E-RIS-10 #3 (portal notifications) | S6-11 |
| Cross-cutting (critical results E2E, distribution E2E, RLS) | S6-13…15 |
