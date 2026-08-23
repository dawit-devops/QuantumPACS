# UI/UX Redesign & Integration Spec — PACS+RIS v3

**Version:** 2.0  
**Date:** 2026-08-23  
**Status:** Draft  
**Scope:** Frontend UI/UX overhaul to surface the full RIS-integrated PACS+RIS v3 platform  
**Platform:** QuantumPACS v3-dev (React/Vite + Ant Design v6 + Cornerstone3D)

---

## 1. Executive Summary

### 1.1 Problem Statement

The PACS+RIS v3 backend is feature-complete with 33+ user stories, 12 RIS epics, and 10+ backend services. However, the **frontend does not reflect this richness**:

- User-feature-review audits found **2 Critical + 2 High** dead-end surfaces
- No role-specific home pages — every user sees the same sidebar and lands on the same surfaces
- Existing pages are basic tables without the operational dashboards modern RIS systems require
- The radiologist reading experience lacks immersive mode
- No automated E2E, accessibility, or load testing covers the new RIS surfaces

### 1.2 Goals

1. **Each role sees a purpose-built interface** with maximum feature richness
2. **Full RIS lifecycle visibility** — Kanban, scheduling, billing, critical results
3. **Immersive clinical reading** — dark, distraction-free mode
4. **Production-grade testing** — Playwright E2E, axe, k6, visual regression
5. **Fix all critical/high feature-review findings**

---

## 2. Per-Role Feature Catalog

### 2.1 Front Desk / Receptionist

**Landing:** `/frontdesk/registration`  
**Sidebar:** Registration, Today's Schedule, Waiting Queue, Patient Search

#### Features

| # | Feature | Description | Priority | Backend API |
|---|---------|-------------|----------|-------------|
| FD-01 | **Patient Demographics Form (MPI-aware)** | Full registration form: name, DOB, sex, address, phone, MRN, insurance, emergency contact. MPI dedup check on submit (alerts if similar patient exists) | P0 | `POST /api/ris/patients` |
| FD-02 | **Insurance Eligibility Check** | Real-time eligibility verification against payer. Shows coverage status, copay, deductible remaining. Pre-populates insurance fields | P0 | `POST /api/ris/patients/{id}/insurance` |
| FD-03 | **Walk-in Scheduling** | Book walk-in patients directly from registration. Shows available slots for the next 2 hours. Conflict-free (scheduling engine) | P0 | `POST /api/ris/appointments` |
| FD-04 | **Appointment Check-in (One-Click)** | Click check-in on any scheduled appointment. Status transitions: SCHEDULED → ARRIVED. Updates tracking board in real-time | P0 | `POST /api/ris/appointments/{id}/check-in` |
| FD-05 | **Waiting Queue** | Live queue of checked-in patients. Shows wait time (minutes since check-in), assigned modality/room, priority. Color-coded by wait time (green <15m, yellow 15-30m, red >30m) | P0 | `GET /api/ris/tracking` (filtered by status=arrived) |
| FD-06 | **Today's Appointment Timeline** | Chronological view of all today's appointments. Shows patient, time, modality, room, status. Quick-filter by modality and status | P1 | `GET /api/ris/appointments` (today filter) |
| FD-07 | **Patient Quick Search** | Global patient search bar (overlay/modal). Searches by name, MRN, DOB, phone. Shows recent searches. Click to open patient detail | P1 | `GET /api/ris/patients/search` |
| FD-08 | **Registration Status Badge** | Visual badge on each registration: New / Returning / Needs Update / Insurance Required | P2 | Client-side derivation |
| FD-09 | **Print Registration Summary** | Printable registration summary for patient. Includes demographics, insurance, appointment details | P2 | Client-side template |
| FD-10 | **Co-pay Collection Prompt** | After check-in, prompt for co-pay collection. Records payment status for billing | P2 | `POST /api/ris/patients/{id}/payment` |

#### Dashboard Widgets (Configurable)

| Widget | Description |
|--------|-------------|
| `kpi-today-checkins` | Today's check-in count vs scheduled |
| `kpi-waiting-count` | Current waiting queue size |
| `kpi-overdue-wait` | Patients waiting >30 min |
| `today-timeline` | Chronological appointment list |
| `patient-search` | Quick patient lookup |
| `quick-actions` | New Registration, Check-in, Walk-in Book |

---

### 2.2 Scheduler

**Landing:** `/schedule`  
**Sidebar:** Calendar, Orders, Tracking Board, Resources, Prior Auth

#### Features

| # | Feature | Description | Priority | Backend API |
|---|---------|-------------|----------|-------------|
| S-01 | **Drag-to-Book on Calendar** | Drag appointment cards between time slots and rooms. Visual conflict highlighting (red overlap). Drop to create/rebook | P0 | `POST /api/ris/appointments` |
| S-02 | **Conflict Visualization** | Red overlapping blocks when room/tech double-booked. Hover tooltip showing conflicting appointment details. Resolution: auto-suggest alternative slot | P0 | Client-side + `GET /api/ris/appointments/availability` |
| S-03 | **Week/Month Views** | Toggle between day/week/month calendar views. Week shows 7 columns (Mon-Sun). Month shows monthly grid with appointment dots | P0 | `GET /api/ris/appointments/calendar` |
| S-04 | **Room Utilization Heatmap** | Color-coded heatmap of room usage (green=available, yellow=partial, red=full). Click to see details. Per-room and per-day breakdown | P1 | `GET /api/ris/resources` + appointments aggregation |
| S-05 | **Provider Schedule Templates** | Save/load recurring schedule templates (e.g., "Dr. Smith MWF 8am-4pm"). Apply template to date range. Override individual slots | P1 | `POST /api/ris/resources` (with schedule metadata) |
| S-06 | **Batch Booking** | Book multiple appointments at once (e.g., "Book 3 CT slots on Tuesday"). Shows all available slots, user picks 3, confirms batch | P1 | `POST /api/ris/appointments` (batch) |
| S-07 | **Appointment Reminders Config** | Configure reminder rules: SMS/email/phone, timing (24h before, 2h before), opt-out management. View reminder delivery log | P1 | `POST /api/ris/reminders/config` |
| S-08 | **Waitlist Management** | Maintain a waitlist for cancelled slots. Auto-notify waitlisted patients when slot opens. Priority-based (STAT > urgent > routine) | P2 | `POST /api/ris/appointments/waitlist` |
| S-09 | **Order-to-Schedule Link** | From order list, click "Schedule" to open booking form pre-filled with order details (modality, procedure, urgency, patient) | P0 | `GET /api/ris/orders/{id}` + booking form |
| S-10 | **Prior Auth Check Before Booking** | Before confirming appointment, check prior auth status. Warn if auth required but not obtained. Allow override with reason | P0 | `GET /api/ris/prior-auth` (by order) |
| S-11 | **Resource Calendar Filter** | Filter calendar by room, modality, or technologist. Show only selected resource's schedule | P1 | `GET /api/ris/appointments` (resource filter) |
| S-12 | **Appointment Reschedule** | One-click reschedule with conflict check. Shows alternative slots. Maintains appointment history (original vs rescheduled) | P0 | `PUT /api/ris/appointments/{id}` |
| S-13 | **No-Show Tracking** | Mark patients as no-show. Track no-show rate per patient/provider/modality. Configurable no-show threshold for auto-cancellation | P2 | `PUT /api/ris/appointments/{id}` (status=no_show) |
| S-14 | **Multi-Day View** | Gantt-style view showing room/tech availability across multiple days. Helps with long-range scheduling (week-ahead, month-ahead) | P2 | `GET /api/ris/appointments` (date range) |

#### Dashboard Widgets (Configurable)

| Widget | Description |
|--------|-------------|
| `kpi-today-bookings` | Today's total bookings |
| `kpi-available-slots` | Available slots for today/next 3 days |
| `kpi-conflicts` | Active scheduling conflicts |
| `kpi-no-show-rate` | No-show rate (7-day rolling) |
| `room-utilization` | Room utilization heatmap |
| `prior-auth-alerts` | Orders needing auth before booking |
| `today-timeline` | Chronological appointment list |

---

### 2.3 Technologist

**Landing:** `/exams`  
**Sidebar:** My Exams, Modality Worklist, Tracking Board, Schedule

#### Features

| # | Feature | Description | Priority | Backend API |
|---|---------|-------------|----------|-------------|
| T-01 | **"My Exams" Filter (Assigned Only)** | Default filter: `assigned_technologist = current_user`. Toggle to show unassigned pool. Clear ownership visibility | P0 | `GET /api/exams` (assigned filter) |
| T-02 | **Claim/Unclaim Exams** | One-click claim on unassigned exams. One-click unclaim (release back to pool). Visual indicator of "mine" vs "unclaimed" | P0 | `POST /api/exams/{id}/claim` |
| T-03 | **Next-Patient Indicator** | On exam console, show "Next: [Patient] — [Modality] — [Priority]" with ETA. Eliminates tabbing back to worklist mid-scan | P0 | `GET /api/exams` (next in queue) |
| T-04 | **Prior Contrast Reaction History** | Before contrast administration, show patient's prior contrast reactions (if any). Red warning badge if documented reaction exists | P1 | `GET /api/patients/{id}/history` |
| T-05 | **MWL Sync Status** | Visual indicator: "MWL Synced ✓" or "MWL Pending ⏳". Shows last sync time. Manual sync trigger button | P1 | `GET /api/worklist` (sync status) |
| T-06 | **Protocol Library Browser** | Browse available protocols by modality. Filter by body part, clinical indication. Favorite protocols for quick access | P1 | `GET /api/protocols` |
| T-07 | **Image Quality Preview Thumbnails** | After acquisition, show thumbnail preview of each series. Quality score (simulated for now). Accept/reject with reason | P2 | `GET /api/exams/{id}/acquisitions` |
| T-08 | **Dose Comparison to ACR Benchmarks** | Real-time dose tracking with ACR reference range comparison. Visual progress bar (green/yellow/red). Warning when approaching or exceeding benchmark | P1 | `GET /api/exams/{id}/dose` |
| T-09 | **Critical Result Flagging** | "Flag Critical Finding" button on exam console (after scan). Captures description, notification channel, recipient. Triggers critical results workflow | P0 | `POST /api/ris/critical-results` |
| T-10 | **Modality Worklist (DICOM MWL)** | DICOM-standard MWL view (table with PatientName, PatientID, AccessionNumber, ScheduledDate, Modality). Refresh button to pull latest from SCP | P0 | `GET /api/worklist` |
| T-11 | **Exam Console 5-Step Flow** | Identity confirm → Protocol selection → Image acquisition (with dose ledger) → Safety checks → Complete. Each step has validation | P0 | `POST /api/exams/{id}/*` |
| T-12 | **Incident Logging** | Log incidents (patient motion, equipment malfunction, contrast reaction, positioning error). Link to rejected acquisition. Required for QA | P0 | `POST /api/qa/incidents` |
| T-13 | **Elapsed Time in Queue** | Color-coded time indicator: green <15m, yellow 15-30m, red >30m. Helps prioritize oldest waiting patients | P1 | Client-side derivation |
| T-14 | **Radiation Warning on Pregnancy Check** | Visual radiation warning icon when pregnancy safety check is involved. Required acknowledgment before proceeding | P0 | Client-side UI |
| T-15 | **Ctrl+Shift+W Worklist Shortcut** | Keyboard shortcut to jump back to worklist from exam console. Prevents browser tab close | P0 | Client-side |

#### Dashboard Widgets (Configurable)

| Widget | Description |
|--------|-------------|
| `kpi-ready-exams` | Ready (unclaimed) exams for my modalities |
| `kpi-in-progress` | Currently scanning |
| `kpi-completed-today` | Completed today |
| `kpi-dose-alerts` | Exams approaching ACR dose limits |
| `next-patient` | Next patient in queue |
| `protocol-library` | Quick protocol lookup |
| `activity-feed` | Recent exam events |

---

### 2.4 Radiologist

**Landing:** `/reading`  
**Sidebar:** Reading Worklist, Peer Review, Critical Results, Tracking Board, My Reports

#### Features

| # | Feature | Description | Priority | Backend API |
|---|---------|-------------|----------|-------------|
| R-01 | **Priority-Sorted Reading Queue** | STAT → Urgent → Routine, FIFO within tier. Unread toggle. Filter by modality, status, physician | P0 | `GET /api/reports/reading-list` |
| R-02 | **Reading Console (Viewer + Report)** | Split pane: Cornerstone3D viewer (left) + Report panel (right). Resizable split. Collapsible report panel with `[`/`]` | P0 | `GET /api/exams/{id}` + `GET /api/reports/{exam_id}` |
| R-03 | **Report Templates** | Apply structured report templates (findings, impression, recommendations). Template selector in report panel. Template management via admin | P0 | `GET /api/reports/templates` |
| R-04 | **Autosave (3s cadence)** | Draft auto-saves every 3 seconds. Never lose work. Visual indicator: "Draft saved at HH:MM" or "Unsaved changes" | P0 | `PUT /api/reports/{exam_id}` |
| R-05 | **Report Sign/Submit/Return** | Radiologist: Sign (final) → distributes to EMR. Resident: Submit → goes to attending for co-sign. Attending: Sign or Return with feedback | P0 | `POST /api/reports/{exam_id}/sign` |
| R-06 | **Report Versioning & Comparison** | View all versions of a report. Diff view between versions (highlighted changes). Restore previous version | P1 | `GET /api/reports/{exam_id}/versions` |
| R-07 | **Prior Report Quick-View** | Sidebar panel showing patient's prior reports for same modality/body part. Quick comparison without leaving console | P1 | `GET /api/reports` (patient + modality filter) |
| R-08 | **Study Bookmarks / Case Collection** | Bookmark studies for teaching, research, or follow-up. Create named collections. Share collections with colleagues | P2 | `POST /api/studies/{id}/bookmark` |
| R-09 | **Dictation Integration Hooks** | API hooks for speech-to-text services (Nuance, M*Modal). "Start Dictation" button → sends audio stream, receives text into report fields | P2 | WebSocket to dictation service |
| R-10 | **AI-Assisted Findings Suggestions** | Panel showing AI-generated findings suggestions (from CAD/ML pipeline). Radiologist accepts/rejects/modifies each suggestion | P2 | `GET /api/exams/{id}/ai-suggestions` |
| R-11 | **Teaching File Submission** | From reading console, submit case to teaching file library. Add annotations, teaching points, differential diagnosis | P1 | `POST /api/teaching-files` |
| R-12 | **Multi-Study Comparison View** | Side-by-side comparison of current study with prior study. Synced scrolling, window/level. Layout: 2x1, 2x2 | P1 | `GET /api/dicomweb/studies/{uid}` |
| R-13 | **Peer Review Inbox** | List of exams assigned for peer review. Accept/reject review. Add comments. Track review status | P0 | `GET /api/peer-review` |
| R-14 | **Critical Results Workflow** | Flag critical findings. Notify referring physician (EHR alert/page/phone). Track acknowledgment. Escalation timer (15 min) | P0 | `POST /api/ris/critical-results` |
| R-15 | **Sign & Next** | One-click sign current report + jump to next unread exam. Preserves worklist filters. Shows "Signed ✓ — Next: [Patient]" | P0 | `POST /api/reports/{exam_id}/sign` + queue navigation |
| R-16 | **Report Feedback Loop** | After signing, show "Report distributed to [EMR/Physician]" confirmation. Track report receipt status | P1 | `GET /api/reports/{exam_id}/distribution` |
| R-17 | **Reading Statistics** | Personal reading stats: reports signed today, avg turnaround, STAT compliance rate. Trends over time | P2 | `GET /api/reports/reading-stats` |

#### Dashboard Widgets (Configurable)

| Widget | Description |
|--------|-------------|
| `kpi-stat-queue` | STAT exams awaiting read |
| `kpi-in-progress` | Currently reading |
| `kpi-completed-today` | Reports signed today |
| `kpi-turnaround` | Avg turnaround time (STAT) |
| `kpi-overdue` | Studies >2h awaiting read |
| `pipeline-orders` | Order pipeline (completed → read → signed) |
| `activity-feed` | Recent report events |
| `alerts-panel` | Critical results, overdue studies |
| `patient-search` | Quick patient lookup |
| `reading-stats` | Personal performance metrics |

---

### 2.5 Resident

**Landing:** `/reading/home`  
**Sidebar:** Resident Home, Reading Worklist, Teaching Library, My Progress

#### Features

| # | Feature | Description | Priority | Backend API |
|---|---------|-------------|----------|-------------|
| RES-01 | **Resident Home Dashboard** | Queue counts (STAT/Urgent/Routine), claimed today count, feedback & progress, recent exams | P0 | `GET /api/reports/reading-list` |
| RES-02 | **Supervised Reading Queue** | Reports in draft → submitted → co-signed lifecycle. "Awaiting Review" filter for submitted reports. Return-to-resident with feedback | P0 | `GET /api/reports/reading-list` |
| RES-03 | **Teaching Library** | Browse curated teaching cases by modality/body part. Filter by diagnosis, difficulty level. View teaching points and annotations | P1 | `GET /api/teaching-files` |
| RES-04 | **My Progress** | Personal metrics: reports completed, avg turnaround, feedback received. Comparison to peer residents (anonymized). Progress over time chart | P1 | `GET /api/reports/reading-stats` |
| RES-05 | **Co-sign / Return Workflow** | Submit report → attending reviews → co-sign (final) or return with feedback. Feedback text visible in console and notifications | P0 | `POST /api/reports/{exam_id}/submit` / `POST /api/reports/{exam_id}/return` |
| RES-06 | **Notification: Report Returned** | Push notification when attending returns report. Includes feedback text. Click to open draft with feedback highlighted | P0 | WebSocket notification |
| RES-07 | **Revision Filter on Worklist** | Filter reading worklist by "returned for revision" status. Shows only exams needing rework | P1 | `GET /api/reports/reading-list` (status=returned) |
| RES-08 | **Claimed Today Counter** | Accurate "Claimed today" count (drafts started today, not total queue). Fixed from current bug | P0 | Backend `claimed_today` field |

#### Dashboard Widgets (Configurable)

| Widget | Description |
|--------|-------------|
| `kpi-my-queue` | My assigned exams (STAT/Urgent/Routine) |
| `kpi-claimed-today` | Claimed today count |
| `kpi-awaiting-review` | Reports awaiting attending review |
| `progress-chart` | Personal progress over time |
| `teaching-library` | Quick access to teaching files |
| `feedback-feed` | Recent feedback from attendings |

---

### 2.6 Billing / Coder

**Landing:** `/billing/queue`  
**Sidebar:** Billing Queue, Unbilled Aging, Denial Rework, Orders, Reports (read-only)

#### Features

| # | Feature | Description | Priority | Backend API |
|---|---------|-------------|----------|-------------|
| B-01 | **Billing Queue** | Signed-but-unbilled charges. CPT/ICD-10 suggestions from coding map. Confirm and drop charge. 30s auto-refresh | P0 | `GET /api/ris/billing/queue` |
| B-02 | **837 Claim Submission** | Submit claims electronically. Review claim details before submission. Batch submission support. Status tracking (submitted/acknowledged/paid/denied) | P1 | `POST /api/ris/billing/claims/{id}/submit` |
| B-03 | **Patient Responsibility View** | Show patient financial responsibility: copay, coinsurance, deductible. Insurance breakdown per charge. Patient statement generation | P1 | `GET /api/ris/billing/patients/{id}/responsibility` |
| B-04 | **Payment Posting (835 Remittance)** | Import and post ERA/835 remittance files. Auto-match to claims. Show paid/denied/adjusted amounts. Balance forwarding | P2 | `POST /api/ris/billing/payments` |
| B-05 | **Batch Charge Drop** | Select multiple signed reports → drop charges in bulk. Review CPT suggestions for each. Confirm batch | P1 | `POST /api/ris/billing/charges/batch` |
| B-06 | **Claim Status Tracking** | Dashboard showing claim lifecycle: Draft → Submitted → Acknowledged → Paid/Denied. Filter by payer, date, status. Drill into individual claim | P1 | `GET /api/ris/billing/claims` |
| B-07 | **Revenue Dashboard** | Revenue trends: daily/weekly/monthly collection. Revenue by modality, provider, payer. Outstanding AR aging. Visual charts | P1 | `GET /api/ris/billing/revenue` |
| B-08 | **Payer Contract Rates** | View contracted rates by payer/procedure. Compare actual charges to contract rates. Flag under/over-charges | P2 | `GET /api/ris/billing/contracts` |
| B-09 | **Procedure Fee Schedule** | Editable fee schedule by CPT code. Import from CMS fee schedule. Override per payer. Version history | P2 | `GET/PUT /api/ris/billing/fee-schedule` |
| B-10 | **Denial Rework** | Denied claims grouped by rejection reason code. Correct and resubmit. Claim history timeline. Batch rework by reason code | P0 | `GET /api/ris/billing/denials` |
| B-11 | **Unbilled Aging Dashboard** | Charges >5 days unbilled. Group by date/site/payer. Red indicator for aged charges. Export for reconciliation | P0 | `GET /api/ris/billing/unbilled` |
| B-12 | **CPT/ICD-10 Suggestions** | Auto-suggest CPT codes based on procedure description and modality. Suggest ICD-10 based on clinical indication. Confidence score | P0 | `GET /api/ris/billing/cpt-suggestions` |

#### Dashboard Widgets (Configurable)

| Widget | Description |
|--------|-------------|
| `kpi-unbilled` | Total unbilled amount |
| `kpi-claims-submitted` | Claims submitted this week |
| `kpi-revenue-today` | Today's revenue |
| `kpi-denials` | Active denials count |
| `chart-revenue` | Revenue trend (30d) |
| `chart-aging` | AR aging distribution |
| `alerts-panel` | Overdue claims, aging charges |
| `patient-search` | Quick patient lookup |

---

### 2.7 Care Coordinator

**Landing:** `/orders`  
**Sidebar:** Orders, Prior Auth, Schedule, Reminders, Patient Search

#### Features

| # | Feature | Description | Priority | Backend API |
|---|---------|-------------|----------|-------------|
| CC-01 | **Orders Lifecycle View** | Full order list with derived status (requested → scheduled → in progress → completed → reported). Age indicator (>24h amber, >72h red). Stuck-work signal | P0 | `GET /api/orders` |
| CC-02 | **Care Plan Management** | Create/edit care plans per patient. Tasks, follow-ups, responsible providers. Status tracking (active/completed/on-hold) | P1 | `POST /api/ris/care-plans` |
| CC-03 | **Encounter Tracking** | Track patient encounters (visits, calls, messages). Link to orders and reports. Timeline view of patient journey | P1 | `GET /api/ris/encounters` |
| CC-04 | **Patient Communication Log** | Log calls, messages, faxes with patients/providers. Categorize (appointment reminder, result notification, referral). Search by patient | P1 | `POST /api/ris/communications` |
| CC-05 | **Referral Tracking** | Track referrals from ordering provider to specialist. Status: pending → accepted → completed. Link to order and report | P2 | `GET /api/ris/referrals` |
| CC-06 | **Discharge Planning Checklist** | Pre-discharge checklist: follow-up appointments, medication reconciliation, patient education. Template-based. Status per item | P2 | `POST /api/ris/discharge-checklists` |
| CC-07 | **Medication Reconciliation View** | Read-only view of patient's current medications (from EMR/FHIR). Compare pre/post-procedure. Flag interactions | P2 | `GET /api/fhir/MedicationRequest` |
| CC-08 | **Handoff Notes** | Add/read handoff notes on patients. Visible to next coordinator who handles the patient. Priority flags | P2 | `POST /api/ris/handoff-notes` |
| CC-09 | **Read-Only Patient Chart** | Full patient chart view: demographics, orders, reports, encounters, medications, allergies. Tabbed interface | P0 | `GET /api/ris/patients/{id}` |
| CC-10 | **Report Summary on Patient Page** | When viewing patient, show signed report summaries (impression, recommendations). Click to open full report | P1 | `GET /api/reports` (patient filter) |
| CC-11 | **Prior Auth Management** | Create/track prior authorization requests. Status: required → pending → approved → denied. Expiry tracking. Override with reason | P0 | `GET/POST /api/ris/prior-auth` |
| CC-12 | **Appointment Reminders** | Configure and send reminders. View delivery log. Manual send. Opt-out management per patient | P1 | `POST /api/ris/reminders` |
| CC-13 | **Patient Quick Search** | Global patient search bar. Searches by name, MRN, DOB. Shows recent searches | P0 | `GET /api/ris/patients/search` |

#### Dashboard Widgets (Configurable)

| Widget | Description |
|--------|-------------|
| `kpi-open-orders` | Open orders requiring action |
| `kpi-waiting-prior-auth` | Orders awaiting prior auth |
| `kpi-stuck-orders` | Orders >24h without progress |
| `kpi-completed-today` | Orders completed today |
| `pipeline-orders` | Order lifecycle pipeline |
| `patient-search` | Quick patient lookup |
| `alerts-panel` | Expiring auths, overdue orders |
| `activity-feed` | Recent order events |

---

### 2.8 QA Manager

**Landing:** `/qa/queue`  
**Sidebar:** QA Queue, Protocols, Incidents, Corrective Actions, Tracking Board

#### Features

| # | Feature | Description | Priority | Backend API |
|---|---------|-------------|----------|-------------|
| QA-01 | **QA Queue** | Pending image quality reviews. Accept/reject with reason. Link to technologist and exam. Priority sorting | P0 | `GET /api/qa/queue` |
| QA-02 | **Reject Analysis Dashboard** | Reject rate by modality, technologist, protocol, reason. Trending graphs (daily/weekly/monthly). Drill-down to individual rejects | P1 | `GET /api/qa/reject-analysis` |
| QA-03 | **Dose Tracking Report** | Dose metrics by modality/protocol/technologist. ACR benchmark comparison. Flag exams exceeding reference levels. Trending over time | P1 | `GET /api/qa/dose-tracking` |
| QA-04 | **Image Quality Scoring** | Score image quality on a 1-5 scale. Track scores by technologist/modality/protocol. Identify training needs | P2 | `POST /api/qa/reviews/{id}/score` |
| QA-05 | **Technologist Performance Metrics** | Per-technologist: reject rate, dose compliance, protocol adherence, exam completion time. Comparison across team | P1 | `GET /api/qa/tech-metrics` |
| QA-06 | **Protocol Compliance Rate** | Track protocol adherence: correct sequences, contrast timing, positioning. Compliance % by protocol. Trending | P1 | `GET /api/qa/protocol-compliance` |
| QA-07 | **Trending Graphs** | All QA metrics with trend lines. Daily/weekly/monthly/quarterly views. Export as CSV/PDF | P1 | `GET /api/qa/trends` |
| QA-08 | **QA Export (CSV/PDF)** | Export any QA report as CSV or PDF. Scheduled export (weekly summary email) | P2 | `GET /api/qa/export` |
| QA-09 | **Protocol Registry** | CRUD for imaging protocols. Version control. Assign protocols to modalities. Set as default | P0 | `GET/POST /api/protocols` |
| QA-10 | **Incidents Log** | View all incidents (patient motion, equipment, contrast reaction, positioning). Link to rejected acquisition. Filter by type/severity | P0 | `GET /api/qa/incidents` |
| QA-11 | **Corrective Actions** | Track corrective actions from incidents. Assignee, due date, status. Link to incident. Escalation for overdue | P0 | `GET /api/qa/corrective-actions` |

#### Dashboard Widgets (Configurable)

| Widget | Description |
|--------|-------------|
| `kpi-pending-reviews` | Pending QA reviews |
| `kpi-reject-rate` | Current reject rate |
| `kpi-dose-alerts` | Dose limit exceedances |
| `chart-reject-trend` | Reject rate trend (30d) |
| `chart-dose-trend` | Dose trend by modality |
| `tech-performance` | Tech performance summary |
| `alerts-panel` | Overdue corrective actions |

---

### 2.9 Department Manager

**Landing:** `/admin/ris-dashboard` (department-scoped KPIs)  
**Sidebar:** Hybrid — Department sidebar for daily ops, Admin sidebar for staff management

#### Department Sidebar (Daily Ops)

| # | Feature | Description | Priority | Backend API |
|---|---------|-------------|----------|-------------|
| DM-01 | **Department Workload Distribution** | Real-time workload by provider/room/modality. Who's overloaded, who's available. Heatmap visualization | P0 | `GET /api/ris/tracking` (aggregated) |
| DM-02 | **Turnaround Time Drill-Down** | TAT by provider: ordered→scheduled, scheduled→completed, completed→signed. Drill into individual exams | P1 | `GET /api/ris/analytics/turnaround` |
| DM-03 | **Volume Forecast** | Predicted volume based on historical patterns. Staffing recommendations. Seasonal trends | P2 | `GET /api/ris/analytics/forecast` |
| DM-04 | **Equipment Utilization Report** | Modality utilization % (CT, MR, US, etc.). Downtime tracking. Maintenance schedule overlay | P1 | `GET /api/ris/analytics/equipment` |
| DM-05 | **Patient Satisfaction Metrics** | Patient satisfaction scores (if collected). Survey response rates. Trending over time | P2 | `GET /api/ris/analytics/satisfaction` |
| DM-06 | **Department Budget Tracking** | Budget vs actual: equipment costs, staffing costs, supply costs. Monthly trending. Variance alerts | P2 | `GET /api/ris/analytics/budget` |
| DM-07 | **Staff Schedule Management** | View/edit staff schedules. Assign shifts. Handle time-off requests. Coverage gaps alert | P1 | `GET/POST /api/ris/staff-schedule` |
| DM-08 | **Staffing Model Optimizer** | Based on volume forecast, suggest optimal staffing levels. What-if scenarios (add/remove staff) | P2 | `GET /api/ris/analytics/staffing-model` |

#### Admin Sidebar (Staff Management)

Accessed via toggle in department manager sidebar. Shows admin-scoped items for user/role management within the department.

#### Dashboard Widgets (Configurable)

| Widget | Description |
|--------|-------------|
| `kpi-dept-volume` | Department volume (today/week) |
| `kpi-turnaround` | Avg turnaround time |
| `kpi-staff-utilization` | Staff utilization % |
| `kpi-equipment-uptime` | Equipment uptime % |
| `chart-volume-trend` | Volume trend (30d) |
| `chart-turnaround-trend` | TAT trend (30d) |
| `workload-heatmap` | Provider workload distribution |
| `alerts-panel` | Overdue exams, equipment issues |

---

### 2.10 Super Admin / Tenant Admin

**Landing:** `/admin`  
**Sidebar:** Dashboard, Users, Roles, Tenants, Metrics, Audit Logs, Interfaces, Platform

#### Features

| # | Feature | Description | Priority | Backend API |
|---|---------|-------------|----------|-------------|
| ADM-01 | **Configurable Dashboard** | Widget-based dashboard with role-specific defaults. Users can rearrange widgets. Layout persists | P0 | `GET /api/dashboard/metrics` |
| ADM-02 | **Users CRUD** | Create/edit/delete users. Assign roles. Bulk operations (activate/deactivate). Import from CSV | P0 | `GET/POST/PUT/DELETE /api/users` |
| ADM-03 | **Roles CRUD** | Create/edit/delete roles. Permission matrix editor. Built-in role immutability tiers | P0 | `GET/POST/PUT/DELETE /api/roles` |
| ADM-04 | **Tenants Management** | Provision/decommission tenants. Per-tenant health, usage, storage. Impersonate tenant admin | P0 | `GET/POST/DELETE /api/v2/tenants` |
| ADM-05 | **Metrics Dashboard** | System metrics: API latency, error rates, storage usage, active connections. Historical charts | P0 | `GET /api/metrics` |
| ADM-06 | **Audit Logs** | Full audit trail. Filter by event type, user, tenant, date. Expandable JSON payloads. CSV export (full dataset) | P0 | `GET /api/logs` |
| ADM-07 | **HL7 Dashboard** | Interface health: message counts, error rates, latency. Exception queue with retry. Message drill-down | P0 | `GET /api/hl7/*` |
| ADM-08 | **DICOMweb Admin** | Endpoint management, search parameters, modality registry, request metrics. Conformance documentation | P0 | `GET /api/dicomweb/admin/*` |
| ADM-09 | **FHIR Config & Monitoring** | FHIR endpoint configuration, conformance statement, monitoring dashboard | P1 | `GET /api/fhir/*` |
| ADM-10 | **Maintenance Mode Toggle** | In-app toggle to enable/disable maintenance mode. Custom message for locked-out users. Audit-logged | P1 | `PUT /api/admin/maintenance` |
| ADM-11 | **Backup/Restore UI** | Trigger manual backup. View backup history. Restore from backup (with confirmation). Schedule backups | P1 | `POST /api/admin/backups` |
| ADM-12 | **System Config Editor** | View/edit YAML config in-app. Diff view (before/after). Restart required indicator. Validation before save | P1 | `GET/PUT /api/admin/config` |
| ADM-13 | **Notification Preferences** | Per-role notification type configuration. Mute specific event types. Channel preferences (bell/email/SMS) | P1 | `GET/PUT /api/notifications/preferences` |
| ADM-14 | **Tenant Usage History** | Charts showing tenant usage over time: storage, users, studies, API calls. Trend analysis | P1 | `GET /api/tenants/{id}/stats/history` |
| ADM-15 | **API Key Rotation** | Generate new API keys. Revoke old keys. Key expiration management. Usage tracking per key | P0 | `POST /api/service-keys` |
| ADM-16 | **SSO/OIDC Configuration** | Configure OAuth/OIDC providers. JWKS endpoint. Group-to-role mapping. Test connection | P2 | `GET/PUT /api/oauth/providers` |
| ADM-17 | **Storage Quota Management** | Set per-tenant storage quotas. Usage alerts at 80%/90%/100%. Quota override with justification | P1 | `PUT /api/tenants/{id}/quota` |

#### Dashboard Widgets (Configurable)

| Widget | Description |
|--------|-------------|
| `health-strip` | Service health indicators |
| `kpi-total-patients` | Total patients |
| `kpi-total-studies` | Total studies |
| `kpi-active-users` | Active users |
| `kpi-storage` | Storage usage |
| `chart-api-latency` | API latency trend |
| `chart-error-rates` | Error rate trend |
| `interface-health` | HL7/DICOM/FHIR status |
| `tenant-usage` | Per-tenant usage summary |
| `alerts-panel` | System alerts, quota warnings |

---

### 2.11 Nursing

**Landing:** `/nursing/patient/{id}` (context-specific, not a global dashboard)  
**Sidebar:** Minimal — linked from exam console, not a standalone workspace

#### Features

| # | Feature | Description | Priority | Backend API |
|---|---------|-------------|----------|-------------|
| N-01 | **Patient Vitals Entry Form** | Record vitals before procedure: BP, HR, temp, SpO2, weight, height. Timestamped. Linked to exam | P1 | `POST /api/exams/{id}/vitals` |
| N-02 | **Pre-Procedure Checklist** | Interactive checklist: allergy verification, medication review, NPO status, consent form, ID band verified. Required items must be checked | P1 | `POST /api/exams/{id}/pre-procedure-checklist` |
| N-03 | **Contrast Consent Form** | Digital consent form for contrast administration. Patient/signature capture. Risk acknowledgment. Stored as document | P1 | `POST /api/exams/{id}/consent` |
| N-04 | **Nurse Notes on Exam** | Free-text notes field on exam. Visible to technologist and radiologist. Timestamped, attributed | P1 | `POST /api/exams/{id}/nurse-notes` |

---

### 2.12 Patient Portal — Detailed Spec

**Landing:** `/portal`  
**Sidebar:** My Records, Appointments, Results, Follow-up  
**Auth:** Patient role (`PORTAL_READ`); scope-gated to own records only (HIPAA minimum necessary)  
**Scope model:** Patient sees only records where `patient_staff_scope` grants exist AND `patients.meta.consent_results = true`. Consent withdrawal revokes visibility instantly. HIM-held reports are blocked from portal display.

#### 2.12.1 Current State vs Target

| Aspect | Current (v2) | Target (v3 Enhanced) |
|--------|-------------|----------------------|
| Home page | Empty / demographics card only | Dashboard with cards: upcoming appointments, recent results, quick actions, imaging summary |
| Demographics | Read-only card (name, MRN, DOB, sex) | Read-only profile (no edit workflow). Name, DOB, sex, phone, email, MRN displayed |
| Orders | Basic table (procedure, urgency, status, date) | Enhanced table with status timeline, link to related appointment |
| Reports | Basic table (accession, modality, status, impression, signed date) | Report detail page with findings/impression/recommendations, signing radiologist info |
| Appointments | Not implemented | Upcoming + history views with prep instructions, room/tech info, linked reports |
| Follow-ups | Backend CRUD exists, no UI | Full follow-up request form + status tracking + notification on response |
| Notifications | None | In-app notification bell for new results, appointment reminders, follow-up responses |
| Consent | Backend gate exists, no UI | Consent management page (grant/withdraw consent for results sharing) |
| Kiosk | QR-token check-in (working) | Enhanced with prep instructions display, consent form, co-pay prompt |

#### 2.12.2 Portal Home Page Design

```
┌──────────────────────────────────────────────────────────────────┐
│  QuantumPACS Patient Portal                     [🔔 2] [👤 John] │
│  ─────────────────────────────────────────────────────────────── │
│                                                                  │
│  ┌─────────────────┐ ┌─────────────────┐ ┌──────────────────┐   │
│  │ 📅 Next Appt    │ │ 📋 New Results  │ │ ⚡ Quick Actions  │   │
│  │                 │ │                 │ │                  │   │
│  │ CT Chest        │ │ CT Chest —      │ │ [Request Follow] │   │
│  │ Aug 28, 10:30am │ │ Signed Aug 22   │ │ [View Records]   │   │
│  │ Room: CT-1      │ │ Dr. Smith       │ │ [Contact Us]     │   │
│  │                 │ │                 │ │                  │   │
│  │ [View Details]  │ │ [Read Report]   │ │                  │   │
│  └─────────────────┘ └─────────────────┘ └──────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 👤 Patient Info                                          │   │
│  │ Name: John Smith  MRN: 12345  DOB: 01/15/1980  Sex: M   │   │
│  │ Phone: (555) 123-4567  Email: john@example.com           │   │
│  │ [View Profile]  [Manage Consent]                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 📊 My Imaging Summary                                    │   │
│  │ Total Studies: 12  │  This Year: 3  │  Pending: 1        │   │
│  │ Modalities: CT(5) MR(4) US(2) DX(1)                     │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

#### 2.12.3 Feature Details

**P-01: Patient Profile (Read-Only Demographics)**

| Aspect | Detail |
|--------|--------|
| View | Read-only profile: name, DOB, sex, phone, email, MRN. No edit workflow — changes handled by front desk during registration |
| Insurance | NOT included in portal scope. Front desk manages insurance during check-in |
| Consent | Toggle consent for results sharing (`patients.meta.consent_results`). Withdraw consent revokes portal visibility of reports/orders |
| Audit | Every view/consent change is audit-logged (`portal.patient_view`, `portal.consent_changed`) |
| API | `GET /api/portal/patients/{id}` — returns demographics + consent status |

**P-02: Upcoming Appointments**

| Aspect | Detail |
|--------|--------|
| View | Chronological list of future appointments: date/time, modality, procedure name, room, facility, status (scheduled/confirmed) |
| Prep Instructions | Per-appointment prep text pulled from appointment metadata. Examples: "Fast 4 hours before CT", "No metal jewelry for MRI", "Finish bowel prep by 6am" |
| ICS Download | NOT included. Patients view appointments in-app only |
| Check-in Status | Shows if check-in is available (QR code for kiosk). "You're checked in ✓" badge if already arrived |
| Reminders | Visual indicator of upcoming reminders (SMS/email sent). Configurable per appointment |
| API | `GET /api/portal/patients/{id}/appointments` — future appointments. `GET /api/portal/patients/{id}/appointments?status=history` — past appointments |

**P-03: Appointment History**

| Aspect | Detail |
|--------|--------|
| View | Past appointments: date, modality, procedure, facility, outcome (completed/cancelled/no-show) |
| Linked Reports | Click any past appointment to jump to its signed report (if available) |
| Filter | Filter by modality, date range, facility |
| API | `GET /api/portal/patients/{id}/appointments?status=completed` |

**P-04: Results Notification & Report View**

| Aspect | Detail |
|--------|--------|
| Notification | In-app bell notification when signed report is available. Red badge count. Click to navigate to report |
| Report List | Table: accession number, modality, body part, status (signed/preliminary), signed date, signing radiologist name |
| Report Detail Page | Dedicated page (`/portal/reports/{reportId}`) with: full findings text, impression, recommendations, signing radiologist name + credentials, sign date/time |
| Plain Language | NOT included. Patients see the raw medical report as-is |
| Consent Gate | Reports only visible if `patients.meta.consent_results = true`. If consent withdrawn, reports disappear from list and detail pages return 404 |
| HIM Hold | If report is HIM-held (`release_status = 'held'`), it is excluded from portal list. Audit event `portal.report_hold_blocked` fires if patient attempts access |
| Download | NOT included. Reports viewed in-app only |
| Share | NOT included. Physicians access via their own portal login |
| API | `GET /api/portal/patients/{id}/reports` — list. `GET /api/portal/patients/{id}/reports/{reportId}` — detail |

**P-05: Follow-up Request**

| Aspect | Detail |
|--------|--------|
| Request Form | Patient selects: reason (result question, appointment request, referral status, other), preferred contact method (phone/email), preferred time window, free-text note |
| Linked Context | Optional: link to specific report or appointment (pre-fills context for coordinator) |
| Status Tracking | Request list with statuses: submitted → in-progress → completed. Visual timeline of each request |
| Notification | Patient receives notification when coordinator responds. Response visible in the request detail |
| Cancel | Patient can cancel a submitted request (before in-progress) |
| API | `POST /api/portal/follow-ups` — create (exists). `GET /api/portal/follow-ups` — list (exists). `PUT /api/portal/follow-ups/{id}` — update status/cancel (exists) |



#### 2.12.4 Portal Navigation Structure

```
/portal                    → Home dashboard (cards: appointments, results, actions, imaging summary)
/portal/profile            → Patient profile (read-only) + consent management
/portal/appointments       → Upcoming appointments with prep instructions
/portal/appointments?tab=history → Past appointments (with linked reports)
/portal/results            → Signed reports list
/portal/results/:reportId  → Full report detail page (findings, impression, recommendations)
/portal/follow-ups         → Follow-up requests (create + track)
```

#### 2.12.5 Portal UI Components

| Component | Path | Purpose |
|-----------|------|---------|
| `PortalHome.tsx` | `frontend/src/portal/PortalHome.tsx` | Dashboard with card widgets (replaces current Portal.tsx) |
| `PatientProfile.tsx` | `frontend/src/portal/PatientProfile.tsx` | Read-only profile view + consent toggle |
| `AppointmentList.tsx` | `frontend/src/portal/AppointmentList.tsx` | Upcoming + history appointments with prep instructions |
| `ReportList.tsx` | `frontend/src/portal/ReportList.tsx` | Signed reports table (enhanced from current) |
| `ReportDetail.tsx` | `frontend/src/portal/ReportDetail.tsx` | Full report page: findings, impression, recommendations |
| `FollowUpHub.tsx` | `frontend/src/portal/FollowUpHub.tsx` | Follow-up request form + status tracking timeline |
| `ConsentManager.tsx` | `frontend/src/portal/ConsentManager.tsx` | Consent grant/withdraw UI with explanation |

#### 2.12.6 Portal Styling

```css
/* frontend/src/portal/portal.css */

/* Portal uses a softer, patient-friendly palette — less clinical, more welcoming */
.portal-home {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.portal-card {
  border-radius: 12px;
  border: 1px solid var(--border-color);
  background: var(--bg-surface);
  transition: box-shadow 0.2s;
}

.portal-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.portal-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  font-weight: 600;
}

.portal-card-body {
  padding: 16px 20px;
}

/* Appointment card with prep instruction highlight */
.portal-appt-prep {
  background: #FFF7E6;
  border-left: 3px solid #FA8C16;
  padding: 8px 12px;
  border-radius: 0 6px 6px 0;
  margin-top: 8px;
  font-size: 13px;
}

/* Report result card — new results get a subtle pulse */
.portal-result-new {
  border-left: 3px solid #52C41A;
  animation: portal-pulse 2s ease-in-out 3;
}

@keyframes portal-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(82, 196, 26, 0.2); }
  50% { box-shadow: 0 0 0 4px rgba(82, 196, 26, 0.1); }
}

/* Follow-up status timeline */
.portal-followup-timeline {
  padding: 12px 0;
}

.portal-followup-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.portal-followup-status.submitted { background: #E6F7FF; color: #1890FF; }
.portal-followup-status.in-progress { background: #FFF7E6; color: #FA8C16; }
.portal-followup-status.completed { background: #F6FFED; color: #52C41A; }
.portal-followup-status.cancelled { background: #FFF1F0; color: #FF4D4F; }
```

#### 2.12.7 Portal Notifications

The portal integrates with the existing notification system (`api/notifications.py`). New notification types for patients:

| Event | Channel | Payload | Action |
|-------|---------|---------|--------|
| `portal.report_available` | In-app bell | Report accession, modality, signing radiologist | Navigate to `/portal/results/{reportId}` |
| `portal.appointment_reminder` | In-app bell | Appointment date/time, modality, prep summary | Navigate to `/portal/appointments` |
| `portal.follow_up_response` | In-app bell | Coordinator response text, request ID | Navigate to `/portal/follow-ups` |

Notification preferences per patient: `PUT /api/portal/notifications/preferences` — opt-in/out per event type.

#### 2.12.8 Consent Management

The portal includes a dedicated consent management page (`/portal/profile` → Consent section):

| Consent Type | Scope | Toggle |
|-------------|-------|--------|
| `consent_results` | Share signed reports in portal | On/Off (default: Off until patient grants) |
| `consent_appointments` | Show appointment details | On/Off (default: On for scheduled patients) |

When consent is withdrawn:
- Reports disappear from portal list within 30s (next poll cycle)
- Report detail pages return 404 (indistinguishable from "not found")
- Orders may still be visible (depends on order consent separately)
- Audit event `portal.consent_changed` fires with before/after state

#### 2.12.9 Security & Compliance

| Aspect | Implementation |
|--------|----------------|
| Authentication | Patient role JWT (same as staff, different role). Portal uses `PORTAL_READ` permission gate |
| Scope isolation | Every data query is scope-gated (`patient_staff_scope`). Patient can only see their own records |
| Consent gate | `patients.meta.consent_results` checked on every report/order query. No consent = empty results (not 403) |
| HIM hold | Reports with `release_status = 'held'` are excluded from portal queries. Audit event on attempted access |
| Audit trail | Every portal action (view, consent change) is audit-logged with event type, actor, timestamp |
| Rate limiting | Portal endpoints use the existing `RisRateLimitMiddleware` (120 req/min per tenant/IP) |
| PHI minimization | Kiosk check-in shows only display name + time (no MRN, no orders). Portal demographics exclude sensitive fields (SSN, full address) from URL params |

---

### 2.13 Kiosk Check-in — Detailed Spec

**Landing:** `/checkin?token={hmac-signed-token}` (public, no auth required)  
**No sidebar** — standalone kiosk mode, full-screen, touch-optimized  
**Auth:** HMAC-signed token IS the credential. Token embeds `tenant + appointment_id + expiry`. No login, no session.

#### 2.13.1 Kiosk Flow

```
┌──────────────────────────────────────────────┐
│                                              │
│          QuantumPACS Self Check-in           │
│                                              │
│   ┌──────────────────────────────────────┐   │
│   │                                      │   │
│   │   Welcome, John Smith                │   │
│   │                                      │   │
│   │   CT Chest with Contrast             │   │
│   │   Today at 10:30 AM                  │   │
│   │   Room: CT-1                         │   │
│   │                                      │   │
│   │   ┌──────────────────────────────┐   │   │
│   │   │  Prep Instructions:          │   │   │
│   │   │  • Fast for 4 hours before   │   │   │
│   │   │  • Bring insurance card      │   │   │
│   │   │  • Arrive 15 min early       │   │   │
│   │   └──────────────────────────────┘   │   │
│   │                                      │   │
│   │   [ ✅ I'm here — check me in ]      │   │
│   │                                      │   │
│   └──────────────────────────────────────┘   │
│                                              │
└──────────────────────────────────────────────┘
```

#### 2.13.2 Feature Details

**K-01: Token-Based Check-in (Existing — Enhanced)**

| Aspect | Detail |
|--------|--------|
| Token | HMAC-signed: `b64url(json{t: tenant, a: appointment_id, e: expiry}).<SHA256 signature>` |
| GET | Validates token → shows: patient display name, appointment time, status. Minimal PHI |
| POST | Confirms check-in: flips `SCHEDULED → ARRIVED`. Returns 409 if already checked in |
| Expiry | Token expires after 24h (configurable). Expired token shows "This check-in link has expired" |
| Security | Constant-time signature comparison. No RBAC — token possession = authorization |
| API | `GET /api/ris/checkin/{token}` — summary. `POST /api/ris/checkin/{token}` — confirm |

**K-02: Prep Instructions Display (New)**

| Aspect | Detail |
|--------|--------|
| Content | Prep instructions pulled from appointment metadata. Displayed in a highlighted box |
| Modality-specific | Different instructions per modality: CT (fasting, contrast), MR (no metal, gown), US (full bladder), etc. |
| Language | Instructions stored in English. Future: multi-language support via tenant config |
| Acknowledgment | "I understand" checkbox required before check-in button becomes active |

**K-03: Digital Consent Form (New)**

| Aspect | Detail |
|--------|--------|
| Display | Full consent text rendered on kiosk screen. Scrollable if long |
| Signature | Touchscreen signature pad (canvas element). Patient signs with finger/stylus |
| Storage | Signature image stored as base64 PNG. Linked to appointment record |
| Refusal | "I decline" button with mandatory reason field. Still allows check-in (consent refusal ≠ no show) |
| API | `POST /api/ris/checkin/{token}/consent` — submit consent with signature |

**K-04: Co-pay Collection (New)**

| Aspect | Detail |
|--------|--------|
| Prompt | After check-in, if co-pay is required (from insurance eligibility check), prompt for payment |
| Methods | Cash, credit card (if card reader integrated), insurance on file |
| Receipt | Print receipt option (thermal printer or PDF download) |
| Skip | "Pay later" option — co-pay remains outstanding, billing queue picks it up |
| API | `POST /api/ris/checkin/{token}/payment` — record payment method |


**K-05: Wait Time Display (New)**

| Aspect | Detail |
|--------|--------|
| After Check-in | After successful check-in, show estimated wait time based on current queue position |
| Queue Position | "You are #3 in the queue. Estimated wait: ~15 minutes" |
| Updates | Auto-refresh every 60s. Shows "Please have a seat" message |
| API | `GET /api/ris/checkin/{token}/queue-position` — queue position + ETA |

#### 2.13.3 Kiosk UI Components

| Component | Path | Purpose |
|-----------|------|---------|
| `CheckIn.tsx` | `frontend/src/kiosk/CheckIn.tsx` | Main kiosk page (existing, enhanced) |
| `PrepInstructions.tsx` | `frontend/src/kiosk/PrepInstructions.tsx` | Prep instructions display component |
| `ConsentForm.tsx` | `frontend/src/kiosk/ConsentForm.tsx` | Digital consent form with signature pad |
| `CoPayPrompt.tsx` | `frontend/src/kiosk/CoPayPrompt.tsx` | Co-pay collection form |
| `CoPayPrompt.tsx` | `frontend/src/kiosk/CoPayPrompt.tsx` | Co-pay collection form |
| `WaitTime.tsx` | `frontend/src/kiosk/WaitTime.tsx` | Post-check-in wait time display |
| `SignaturePad.tsx` | `frontend/src/common/SignaturePad.tsx` | Reusable touchscreen signature canvas |

#### 2.13.4 Kiosk Styling

```css
/* frontend/src/kiosk/CheckIn.css */

/* Kiosk: full-screen, touch-optimized, high contrast */
.kiosk-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 48px;
  background: #F0F5FF;
  font-size: 18px;
}

.kiosk-title {
  font-size: 32px;
  font-weight: 700;
  color: #1A1A2E;
  margin-bottom: 8px;
}

.kiosk-subtitle {
  font-size: 20px;
  color: #5A6072;
  margin-bottom: 32px;
}

.kiosk-card {
  background: white;
  border-radius: 16px;
  padding: 40px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
  max-width: 600px;
  width: 100%;
}

.kiosk-prep {
  background: #FFF7E6;
  border-left: 4px solid #FA8C16;
  padding: 16px 20px;
  border-radius: 0 12px 12px 0;
  margin: 24px 0;
  font-size: 16px;
  line-height: 1.6;
}

/* Touch-optimized button — large hit target for kiosk screens */
.kiosk-btn {
  min-height: 64px;
  font-size: 20px;
  font-weight: 600;
  border-radius: 12px;
  width: 100%;
}

/* Signature pad — full width, high contrast */
.kiosk-signature {
  border: 2px solid #C4C9D4;
  border-radius: 12px;
  background: white;
  width: 100%;
  height: 200px;
  touch-action: none;
}

/* Wait time display — calming green pulse */
.kiosk-wait {
  text-align: center;
  padding: 40px;
}

.kiosk-wait-number {
  font-size: 72px;
  font-weight: 700;
  color: #52C41A;
}

.kiosk-wait-label {
  font-size: 20px;
  color: #5A6072;
}

/* Co-pay prompt — prominent payment card */
.kiosk-copay {
  text-align: center;
  padding: 32px;
}

.kiosk-copay-amount {
  font-size: 48px;
  font-weight: 700;
  color: #1A1A2E;
  margin: 16px 0;
}

.kiosk-copay-methods {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin: 24px 0;
}

.kiosk-copay-method {
  min-width: 120px;
  min-height: 56px;
  border-radius: 12px;
  font-size: 16px;
}

.kiosk-copay-skip {
  margin-top: 16px;
  color: #8B949E;
  font-size: 14px;
}
```

---

## 3. Configurable Widget Dashboard

### 3.1 Widget Registry

```typescript
// frontend/src/dashboard/widgets/registry.ts
interface WidgetDef {
  id: string;
  title: string;
  icon: React.ReactNode;
  defaultSize: 'sm' | 'md' | 'lg';
  permissions: string[];
  roles?: string[];
  component: React.LazyExoticType<any>;
}

// All widgets from §2.1-2.12 are registered here.
// Each widget self-fetches its data via API hooks.
```

### 3.2 Role Default Layouts

Each role gets a curated default layout (see §2.1-2.12 Dashboard Widgets tables). Users can override and save their own arrangement.

### 3.3 User Override Persistence

Layout saved to `PUT /api/users/{id}/preferences` with `dashboard_layout` key. Reset-to-default button available.

### 3.4 Widget Implementation Pattern

Each widget is a self-contained React component with:
- Its own data-fetching hook (e.g., `useKpiTodayVolume()`)
- Loading/error/empty states via `PageState`
- Responsive sizing (sm=1 col, md=2 col, lg=3 col)
- Click-to-drill-down navigation where applicable

```typescript
// Example widget component
function KpiTodayVolume() {
  const { data, loading, error } = useKpiTodayVolume();
  return (
    <Card className="dashboard-widget size-sm">
      <Card.Header>Today's Volume</Card.Header>
      <Card.Body>
        <PageState loading={loading} error={error} empty={!data}>
          <Statistic value={data.count} prefix={<FundOutlined />} />
          <Text type="secondary">+{data.change}% vs yesterday</Text>
        </PageState>
      </Card.Body>
    </Card>
  );
}
```

### 3.5 Dashboard CSS Grid

```css
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  padding: 24px;
}

.dashboard-widget.size-sm { grid-column: span 1; }
.dashboard-widget.size-md { grid-column: span 2; }
.dashboard-widget.size-lg { grid-column: span 3; }

@media (max-width: 768px) {
  .dashboard-grid { grid-template-columns: 1fr; }
  .dashboard-widget.size-md,
  .dashboard-widget.size-lg { grid-column: span 1; }
}
```

---

## 4. Role-Based Navigation

### 4.1 Sidebar Per Role

Each role sees a completely different sidebar. See §2.1-2.12 "Sidebar" entries for each role's navigation structure.

### 4.2 Implementation

```typescript
// frontend/src/common/RoleSidebar.tsx
interface RoleNavConfig {
  role: string;
  sections: NavSectionDef[];
  landing: string;
}

const ROLE_NAV_REGISTRY: RoleNavConfig[] = [
  { role: 'receptionist',    sections: frontDeskNav,    landing: '/frontdesk/registration' },
  { role: 'scheduler',       sections: schedulerNav,    landing: '/schedule' },
  { role: 'technologist',    sections: techNav,         landing: '/exams' },
  { role: 'radiologist',     sections: readingNav,      landing: '/reading' },
  { role: 'resident',        sections: residentNav,     landing: '/reading/home' },
  { role: 'cashier',         sections: billingNav,      landing: '/billing/queue' },
  { role: 'care_coordinator', sections: coordNav,       landing: '/orders' },
  { role: 'qa_manager',      sections: qaNav,           landing: '/qa/queue' },
  { role: 'dept_manager',    sections: deptManagerNav,  landing: '/admin/ris-dashboard' },
  { role: '*',               sections: adminNav,        landing: '/admin' },
];

// Fallback: union of all role sidebars for multi-role users.
function RoleSidebar({ role, permissions }: Props) {
  const config = ROLE_NAV_REGISTRY.find(r => r.role === role)
    ?? ROLE_NAV_REGISTRY.find(r => r.role === '*');
  // Filter sections by permissions, render
}
```

### 4.3 Landing Route Priority

```typescript
// navigator.ts — LANDING_STEPS updated for RIS v3:
const LANDING_STEPS: LandingStep[] = [
  { route: '/admin',                    workspace: 'admin',       permissions: ['SYSTEM_ADMIN'] },
  { route: '/frontdesk/registration',   workspace: 'frontdesk',   permissions: ['REGISTRATION_READ'] },
  { route: '/schedule',                 workspace: 'acquisition', permissions: ['SCHEDULE_READ'] },
  { route: '/exams',                    workspace: 'acquisition', permissions: ['EXAM_READ'] },
  { route: '/reading',                  workspace: 'reading',     permissions: ['REPORT_READ'] },
  { route: '/reading/home',             workspace: 'reading',     permissions: ['REPORT_READ'], roles: ['resident'] },
  { route: '/billing/queue',            workspace: 'admin',       permissions: ['BILLING_READ'] },
  { route: '/orders',                   workspace: 'coordination', permissions: ['ORDER_READ'] },
  { route: '/qa/queue',                 workspace: 'qa',          permissions: ['QA_READ'] },
  { route: '/portal',                   workspace: 'portal',      permissions: ['PORTAL_READ'] },
  // ... fallbacks
];
```

---

## 5. Immersive Reader Mode

### 5.1 Features

- **Dark background** (#0a0a0a) — reduces eye strain in dark reading rooms
- **Sidebar collapses** to thin icon strip (48px width)
- **Report panel toggles** with `[`/`]` keyboard shortcuts
- **Keyboard shortcuts**: `Ctrl+S` save, `Ctrl+Enter` sign, `←`/`→` navigate queue
- **Status bar** shows available shortcuts at bottom of screen
- **Auto-enters** immersive mode when screen width >1920px (dual-monitor detection)
- **Manual toggle** via Space key or view menu

### 5.2 Keyboard Shortcuts Reference

| Shortcut | Action | Category |
|----------|--------|----------|
| `Space` | Toggle immersive mode | View |
| `[` / `]` | Toggle report panel | Navigation |
| `Ctrl+S` | Save draft | Report |
| `Ctrl+Enter` | Sign report | Report |
| `Ctrl+Shift+S` | Submit (resident) | Report |
| `←` / `→` | Previous/Next exam | Navigation |
| `Ctrl+Shift+W` | Jump to worklist | Navigation |
| `F1` | Show shortcuts help | Help |

### 5.3 CSS

```css
.reading-console.immersive {
  background: #0a0a0a;
  color: #e0e0e0;
}
.reading-console.immersive .page-header,
.reading-console.immersive .ant-layout-header {
  background: #111 !important;
  border-bottom-color: #333;
}
.reading-console.immersive .sidebar {
  width: 48px !important;
  overflow: hidden;
}
.reading-console.immersive .sidebar .nav-label {
  display: none;
}
.reading-console.immersive .report-panel {
  background: #111;
  border-left-color: #333;
}
.reading-console.immersive .report-panel textarea {
  background: #1a1a1a;
  color: #e0e0e0;
  border-color: #333;
}
.reading-console.immersive .status-bar {
  position: fixed;
  bottom: 0;
  left: 48px;
  right: 0;
  height: 28px;
  background: #111;
  border-top: 1px solid #333;
  font-size: 12px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 24px;
}
```

---

## 6. Tracking Board: Role-Configurable Kanban

### 6.1 Column Configurations

Each role sees only relevant columns:

| Role | Columns |
|------|--------|
| Admin/Scheduler | Ordered → Scheduled → Arrived → In Progress → Completed → Read → Signed |
| Scheduler | New Orders → Scheduled → Checked In → Scanning → Done |
| Technologist | Scheduled → Arrived → Scanning → Completed |
| Radiologist | Awaiting Read → Reading → Signed |
| Cashier | Ready to Bill → Billed |

### 6.2 Drag-and-Drop

Both modes supported:
- **Power users** (admin, scheduler): drag cards between columns with confirmation dialog
- **All others**: click status badge → dropdown to select next valid status
- Uses `@dnd-kit/core` for drag implementation

### 6.3 View Toggle

Kanban (default) ↔ Table view toggle. Table shows same data in spreadsheet format for users who prefer it.

---

## 7. Medical-Grade Theme

### 7.1 Design Tokens

```css
:root {
  --color-primary: #0066CC;     /* clinical blue */
  --color-success: #00A86B;     /* medical green */
  --color-warning: #E68A00;     /* amber */
  --color-error: #CC0000;       /* medical red */
  --color-info: #00838F;        /* teal */
}

[data-theme="dark"] {
  --bg-primary: #0D1117;
  --bg-surface: #161B22;
  --text-primary: #E6EDF3;
  --text-secondary: #8B949E;
  --border-color: #30363D;
}
```

### 7.2 Role Accent Colors

Subtle 3px left border on sidebar header per role:

```css
.sidebar-header[data-role="radiologist"]    { border-left-color: #0066CC; }
.sidebar-header[data-role="technologist"]   { border-left-color: #00A86B; }
.sidebar-header[data-role="receptionist"]   { border-left-color: #722ED1; }
.sidebar-header[data-role="scheduler"]      { border-left-color: #E68A00; }
.sidebar-header[data-role="cashier"]        { border-left-color: #CC0000; }
.sidebar-header[data-role="care_coordinator"] { border-left-color: #00838F; }
.sidebar-header[data-role="super_admin"]    { border-left-color: #52C41A; }
```

---

## 8. Testing Strategy

### 8.1 E2E Critical Path Flows

| # | Flow | Roles |
|---|------|-------|
| E1 | Order Lifecycle (Happy Path) | Front Desk → Scheduler → Tech → Radiologist → Billing |
| E2 | STAT Order | Scheduler → Tech → Radiologist |
| E3 | Critical Result | Radiologist → Technologist |
| E4 | Prior Auth Denial | Coordinator → Scheduler |
| E5 | MWL → MPPS Flow | Technologist |
| E6 | HL7 Interface | System → Admin |
| E7 | Multi-Tenant Isolation | Super Admin → Tenant Admin |
| E8 | Report Versioning | Resident → Radiologist |
| E9 | Billing Aging | Cashier |
| E10 | Role-Based Access | All roles |

### 8.2 Accessibility (axe-core)

WCAG 2.1 AA audit on every role's home page.

### 8.3 Load Testing (k6)

50 concurrent radiologists + 20 schedulers + 10 front-desk. p95 < 500ms.

### 8.4 Visual Regression

Playwright screenshots at 1080p, 1440p, 4K across all role home pages.

---

## 9. Implementation Phases

| Phase | Roles | Features | Sprint |
|-------|-------|----------|--------|
| **A** | Front Desk, Scheduler | Full front-desk suite, Full scheduling suite | 1-3 |
| **B** | Technologist | Full technologist console | 4-5 |
| **C** | Radiologist, Resident | Full reading suite, Resident features | 6-8 |
| **D** | Billing | Enhanced billing suite | 9-10 |
| **E** | Admin, Dept Manager | Full admin suite, Full dept management | 11-12 |
| **F** | Coordinator, QA | Full coordinator suite, Full QA suite | 13-14 |
| **G** | Nursing, Portal, Kiosk | Minimal nursing, Enhanced portal, Kiosk | 15-16 |

---

## 10. Dependencies

| Package | Purpose |
|---------|---------|
| `@dnd-kit/core` | Drag-and-drop for Kanban |
| `@dnd-kit/sortable` | Sortable containers |
| `@axe-core/playwright` | Accessibility audit |
| `playwright` | E2E testing |
| `k6` | Load testing (CLI) |

---

## 11. Risks

| Risk | Mitigation |
|------|------------|
| Role sidebar breaks multi-role users | Fallback: union of sidebars |
| Kanban accessibility | Click-to-transition as alternative |
| Immersive mode + Cornerstone resize | ResizeObserver for dynamic sizing |
| Widget bundle size | All widgets lazy-loaded |
| E2E flakiness | retries: 1, waitForLoadState |
| k6 needs realistic data | Seed script + setup.js |
