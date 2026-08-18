# RIS — UI/UX Requirements

**Document:** 04 of 06 · **Version:** 1.0 · **Date:** 2026-08-04

Requirements apply to the **tracking board**, **scheduling**, **registration/intake**, **reading worklist & reporting**, **billing workspace**, and **admin consoles**. IDs: `RIS-UI-…`. Priorities: M/D/O. Baseline: `docs/specs/worklist_design.md`, `docs/design-tokens.json`.

---

## 1. Cross-Cutting UX Principles

| ID | Requirement | Pri |
| :--- | :--- | :-: |
| RIS-UI-01 | **Sub-second responsiveness** for list/tracking interactions (p95 < 1 s); async loading indicators for slower operations. | M |
| RIS-UI-02 | **Live updates** on the tracking board (polling now, pub-sub later per `notifications_design.md`); no manual refresh to see status changes. | M |
| RIS-UI-03 | **Keyboard-first** for schedulers & front desk (fast booking, check-in via shortcuts); full mouse alternative. | M |
| RIS-UI-04 | **Consistent design tokens, status color semantics, and error patterns** across RIS screens and the wider platform. | M |
| RIS-UI-05 | **Accessibility WCAG 2.1 AA**; status never conveyed by color alone (badge + label + icon). | M |
| RIS-UI-06 | **Session resilience** — open tabs keep filters/sort and WIP (report drafts) across reconnects. | D |

## 2. Tracking Board (Technologist · Scheduler · Manager)

| ID | Requirement | Pri |
| :--- | :--- | :-: |
| RIS-UI-07 | Live board of all exams: patient (masked per policy), accession, modality, procedure, scheduled time, room, technologist, status, priority badge, prior-auth flag, AI flag. | M |
| RIS-UI-08 | Status lifecycle rendered as a progress indicator: Ordered → Scheduled → Arrived → In Progress → Completed → Read → Signed; transitions animate and are color-coded. | M |
| RIS-UI-09 | Filters: modality, site, room, status, priority, date range; search by patient/accession (server-side pagination with `total`). | M |
| RIS-UI-10 | Views: table + board/card + calendar; row actions (check-in, mark arrived, reassign, reschedule, cancel) with status guards disabling invalid transitions. | M |
| RIS-UI-11 | Critical-result alerts appear as persistent badges until acknowledged; acknowledged time visible. | M |
| RIS-UI-12 | KPI strip: today's volume, in progress, awaiting read, overdue, STAT queue — live counts. | D |

## 3. Scheduling (Scheduler)

| ID | Requirement | Pri |
| :--- | :--- | :-: |
| RIS-UI-13 | Calendar grid per room/modality with slot availability; drag-to-book and click-to-book; visual conflict prevention (red/disabled when double-book or contraindicated). | M |
| RIS-UI-14 | Booking form: patient (search + MPI hint), procedure (triggers prep/contrast rules), priority, site/room/technologist, time; shows prep instructions & contrast warnings inline. | M |
| RIS-UI-15 | Rule feedback: contraindications (contrast allergy, renal function), duplicate-exam rules, prior-auth requirement — surfaced before save with override path (logged). | M |
| RIS-UI-16 | Prior-auth panel: status, expiry, CPT linkage; expired/none → warning badge and blocked booking unless overridden. | D |
| RIS-UI-17 | Reminder management: per-order reminder config (channel: SMS/email/phone, time), template, opt-out. | D |
| RIS-UI-18 | Multi-site search & book (IDN): availability across sites shown side-by-side; site selection recorded. | D |
| RIS-UI-19 | Reschedule/cancel flow: reason capture, slot release, patient notification triggered, audit logged. | M |

## 4. Registration & Intake (Front Desk)

| ID | Requirement | Pri |
| :--- | :--- | :-: |
| RIS-UI-20 | Registration form with demographics + insurance; inline MPI duplicate-match warnings (probable match) with merge/review link. | M |
| RIS-UI-21 | Insurance eligibility check action with status result (active/inactive/needs verification) displayed inline. | D |
| RIS-UI-22 | Check-in one-click from schedule: sets Arrived, prints/QR labels, collects consents (signature capture), shows wait time. | M |
| RIS-UI-23 | Pre-registration support: portal-submitted data visible for completion before arrival. | D |

## 5. Reading Worklist & Reporting (Radiologist)

| ID | Requirement | Pri |
| :--- | :--- | :-: |
| RIS-UI-24 | Reading worklist: priority-sorted, filters (modality/site/status/date), unread toggle, AI-flag badge; row click → PACS viewer launch with study context (RIS-UI-26). | M |
| RIS-UI-25 | Report editor: structured template library (searchable), sections, smart fields, speech-recognition inline transcription with verification highlight, measurement/image linking (key images). | M |
| RIS-UI-26 | **Launch PACS viewer in context** from the worklist (deep link with StudyInstanceUID); return-to-RIS returns to the same worklist state. | M |
| RIS-UI-27 | Critical-results flow: one-click flag → confirm dialog with recipient selection → notification sent with timestamp; acknowledgment + escalation status visible; logged. | M |
| RIS-UI-28 | Sign & route: sign dialog shows completeness warnings (missing required sections); signed reports show status; auto-routing indicator to EMR/billing. | M |
| RIS-UI-29 | WIP draft list: auto-saved drafts restorable; no duplicate reports on re-entry. | D |

## 6. Billing Workspace (Billing Coder)

| ID | Requirement | Pri |
| :--- | :--- | :-: |
| RIS-UI-30 | Billing queue of signed-but-unbilled exams: suggested CPT/ICD-10 from procedure + report; coder confirms/adjusts; charge drop action. | M |
| RIS-UI-31 | Unbilled aging report with drill-down (by date, site, payer). | M |
| RIS-UI-32 | Denial/rework queue: reason code, original claim, correction workflow, resubmit; status history visible. | M |
| RIS-UI-33 | Prior-auth linkage visible on claim line; missing auth highlighted. | D |

## 7. Admin & Config (RIS Admin · Tenant Admin)

| ID | Requirement | Pri |
| :--- | :--- | :-: |
| RIS-UI-34 | Scheduling template editor: room/modality availability matrices, staff assignment rules, default durations per procedure. | D |
| RIS-UI-35 | Procedure/CPT/ICD map manager: searchable, versioned, bulk import/export; validation against duplicates. | M |
| RIS-UI-36 | Report template manager: template tree, version history, publish/rollback, permissions. | D |
| RIS-UI-37 | Interface health dashboard: per-interface message counts, errors, latency, last-message times; alert rules config; exception queue with retry/reconcile. | M |
| RIS-UI-38 | MPI maintenance: duplicate candidate list, merge wizard with undo, audit trail. | D |
| RIS-UI-39 | User/role management per tenant with permission matrix and audit (per `roles_design.md`). | M |

## 8. Tenant & Ops Dashboards (Tenant Admin · Super Admin)

| ID | Requirement | Pri |
| :--- | :--- | :-: |
| RIS-UI-40 | Usage metering (MWL queries, API calls, notifications sent) and invoice view with drill-down; export CSV. | M |
| RIS-UI-41 | Tenant card grid with status lifecycle & provisioning spinner (per `tenants_design.md`). | M |
| RIS-UI-42 | KPI dashboards (TAT, utilization, patient flow, unbilled) with time-series + drill-down. | D |

## Acceptance linkage

`RIS-UI-*` requirements map to acceptance criteria in `06_acceptance_criteria.md` (e.g., RIS-UI-07…12 → RIS-AC-P02-02/P07-01; RIS-UI-13…19 → RIS-AC-P03-*; RIS-UI-24…29 → RIS-AC-P01-*; RIS-UI-30…33 → RIS-AC-P05-*).
