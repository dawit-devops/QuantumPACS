# Sprint MVP-04 Detail — MWL SCP + MPPS Consumer (E-RIS-06) & Tracking Board (E-RIS-07)

**Version:** 1.0 · **Date:** 2026-08-18 · **Source:** `ris-integration-spec.md` §9.1; `RELEASE_PLAN.md` E-RIS-06, E-RIS-07; `02_end_to_end_workflows.md` RIS-WF1; `04_uiux_requirements.md` RIS-UI-07…12
**Cadence:** two 2-week sprints (S6–S7) · **Squads:** RIS-MVP — two backend, two frontend, part-time integration engineer, QA

---

## 1. Sprint Goal

> **"The modality pulls a worklist from the RIS, performs the exam, and the tracking board updates live in under 5 seconds — while the technologist never re-types patient data at the scanner console."**

**Scope in:** MWL SCP (DICOM C-FIND) serving scheduled entries, MPPS N-CREATE/N-SET consumer → tracking status + PACS echo, worklist search/filters/pagination + station AE endpoint, live tracking board, status progress indicator, KPI strip, filters, row actions with status guards.

**Scope out:** Reporting (S8–S9), critical results (S10), billing (S11).

---

## 2. Team Capacity (two 10-day sprints)

| Role | FTE | Available dev-days (×2) | Notes |
| :--- | :-: | :-: | :--- |
| Backend engineer ×2 | 2.0 | 40 | MWL SCP service, MPPS consumer, tracking API, status updates |
| Frontend engineer ×2 | 2.0 | 40 | Tracking board UI, KPI strip, filters, row actions |
| Integration engineer | 0.5 | 10 | DICOM MWL/MPPS conformance testing, PACS echo |
| QA | 1.0 | 20 | MWL/MPPS E2E, tracking board E2E, performance |
| **Total** | **5.5** | **~110** | Total task estimate below: **~50 dev-days** (BE 18.0 · FE 18.0 · INT 5.0 · QA 9.0) — ~60 days slack |

---

## 3. Task Board

### 3.1 MWL SCP (DICOM C-FIND) — E-RIS-06 #1
**Source:** `RELEASE_PLAN.md` E-RIS-06 #1; `ris-integration-spec.md` §5.3; `06_acceptance_criteria.md` RIS-AC-P02-01.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S4-01 | MWL SCP DICOM service: pynetdicom AE on port 11113 (`QPACS_MWL`); C-FIND handler queries `worklist_entries` WHERE status IN ('scheduled','arrived') | BE | 3.0 | S3-13 | Scanner query returns MWL entries; RIS-AC-P02-01 |
| S4-02 | MWL query filters: station_ae_title, patient_name, patient_id, accession_number, modality; DICOM wildcard matching (%, _) | BE | 1.5 | S4-01 | All filter combinations work; ≥ 98% auto-fill (RIS-SL-33) |
| S4-03 | Station AE endpoint: `GET /api/ris/worklist/station-aes` — list active station AEs from worklist entries | BE | 0.5 | S4-01 | Station AEs listed; UI can filter by station |
| S4-04 | MWL conformance test set: C-FIND requests with various filters; verify response datasets match DICOM MWL IOD | INT | 2.0 | S4-01 | Repeatable test scripts; ≥ 95% conformance |
| S4-05 | MWL REST API: extend existing `api/worklist.py` to serve MWL entries with RIS filters (status, modality, station_ae, date range) + pagination + server `total` | BE | 1.5 | S4-01 | `GET /api/worklist` returns filtered, paginated results |

**Epic exit contribution:** E-RIS-06 #1 (MWL SCP).

### 3.2 MPPS Consumer (N-CREATE/N-SET) — E-RIS-06 #2
**Source:** `RELEASE_PLAN.md` E-RIS-06 #2; `ris-integration-spec.md` §5.4; `06_acceptance_criteria.md` RIS-AC-P02-02.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S4-06 | MPPS consumer DICOM service: pynetdicom AE on port 11114 (`QPACS_MPPS`); N-CREATE handler → IN_PROGRESS on tracking; N-SET handler → COMPLETED on tracking | BE | 3.0 | S4-01 | MPPS events drive status; RIS-AC-P02-02 |
| S4-07 | `ris_mpps_events` table + Alembic migration (Migration 2 partial); event audit trail (event_type, mpps_status, raw_message, timestamps) | BE | 1.0 | — | Table created; events logged |
| S4-08 | PACS echo: MPPS N-CREATE/N-SET → echo study status to PACS (existing `dcm_server.py` C-STORE path or DICOMweb) | INT | 2.0 | S4-06 | PACS receives MPPS echo; study status updated |
| S4-09 | MPPS conformance test set: N-CREATE with IN_PROGRESS, N-SET with COMPLETED/DISCONTINUED; verify status updates + PACS echo | INT | 1.5 | S4-06 | Repeatable test scripts; ≥ 95% conformance |
| S4-10 | MPPS → tracking latency instrumented: `ris_mpps_event_duration_seconds` histogram; target < 5s (RIS-SL-22) | BE | 0.5 | S4-06 | Metric queryable; dashboard data |

**Epic exit contribution:** E-RIS-06 #2 (MPPS consumer + PACS echo).

### 3.3 Tracking Board — E-RIS-07 #1/2/3/4
**Source:** `RELEASE_PLAN.md` E-RIS-07 #1–4; `ris-integration-spec.md` §4.1; `04_uiux_requirements.md` RIS-UI-07…12.

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S4-11 | Tracking board API: `GET /api/ris/tracking` — live exam list with patient (masked per policy), accession, modality, procedure, scheduled time, room, technologist, status, priority, prior-auth flag; server-side pagination + filters | BE | 2.5 | S3-01 | RIS-UI-07 parity; live updates |
| S4-12 | KPI strip API: `GET /api/ris/tracking/kpi` — today's volume, in progress, awaiting read, overdue, STAT queue; live counts | BE | 1.0 | S4-11 | RIS-UI-12 parity; live counts |
| S4-13 | Status update API: `PUT /api/ris/tracking/{id}/status` — manual status update with guard validation + audit; row actions (check-in, mark arrived, reassign, reschedule, cancel) | BE | 1.5 | S3-03 | Guards enforced; audited; RIS-UI-10 |
| S4-14 | Status timeline API: `GET /api/ris/tracking/{id}/timeline` — ordered → scheduled → arrived → in_progress → completed → read → signed | BE | 0.5 | S4-11 | Status lifecycle visible |
| S4-15 | Tracking board UI: new `frontend/src/worklist/TrackingBoard.tsx` — live board of all exams with status lifecycle progress indicator, color-coded status, priority badge, prior-auth flag | FE | 5.0 | S4-11 | RIS-UI-07/08 parity; WCAG 2.1 AA; live updates ≤ 30s (RIS-SL-15) |
| S4-16 | KPI strip UI: new `frontend/src/worklist/KpiStrip.tsx` — today's volume, in progress, awaiting read, overdue, STAT queue; live counts | FE | 2.0 | S4-12 | RIS-UI-12 parity |
| S4-17 | Filters + search: modality, site, room, status, priority, date range; search by patient/accession; server-side pagination with `total` | FE | 3.0 | S4-15 | RIS-UI-09 parity |
| S4-18 | Row actions: check-in, mark arrived, reassign, reschedule, cancel — with status guards disabling invalid transitions | FE | 2.5 | S4-13 | RIS-UI-10 parity; guards enforced in UI |
| S4-19 | Critical-result alerts: persistent badges on tracking board until acknowledged; acknowledged time visible | FE | 1.0 | S4-15 | RIS-UI-11 parity (badge only; full workflow in S10) |

**Epic exit contribution:** E-RIS-07 #1–4 (tracking board).

### 3.4 Cross-cutting: E2E & Performance

| ID | Task | Owner | Est. | Dep | Acceptance check |
| :-: | :--- | :-: | :-: | :-: | :--- |
| S4-20 | MWL E2E: book appointment → MWL entry created → modality C-FIND query → entries returned → MPPS N-CREATE → IN_PROGRESS → MPPS N-SET → COMPLETED → tracking board updates | QA | 2.0 | S4-01…19 | RIS-AC-P02-01/02; RIS-SL-22 |
| S4-21 | Tracking board E2E: filter by modality/status/priority → row actions → status update → KPI strip updates; 50 concurrent updates → < 5s latency | QA | 1.5 | S4-15 | RIS-UI-07…12; RIS-SL-15 |
| S4-22 | MPPS → tracking latency: measure N-CREATE → board update latency; assert < 5s p95 | QA | 1.0 | S4-06 | RIS-SL-22 |
| S4-23 | RLS on tracking: cross-facility tracking denied; home-facility tracking works | QA | 0.5 | S4-11 | PAC-SL-61 |

---

## 4. Sprint Milestones

| Milestone | Target | Evidence |
| :--- | :--- | :--- |
| **Day 3 (S6)** | MWL SCP scaffold; MPPS consumer started; tracking API started | S4-01/06/11 started |
| **Day 8 (S6)** | MWL + MPPS conformance green; PACS echo; tracking API complete; tracking board UI started | S4-04/09, S4-08, S4-11…14 closed; S4-15 started |
| **Day 5 (S7)** | Tracking board UI complete; KPI strip; filters; row actions | S4-15…19 closed |
| **Day 10 (S7, demo)** | MWL + tracking E2E green; demo: book → MWL → modality → MPPS → tracking board live | S4-20…23; sprint review |

---

## 5. Sprint Definition of Done

| # | Check | Verifies | Method |
| :-: | :--- | :--- | :--- |
| D1 | MWL ≥ 98% auto-fill; scanner query returns entries without manual entry | RIS-AC-P02-01, RIS-SL-33 | S4-04/20 |
| D2 | MPPS → tracking < 5s; PACS echo successful | RIS-AC-P02-02, RIS-SL-22 | S4-22 |
| D3 | Tracking board: live updates ≤ 30s; status lifecycle; KPI strip; filters; row actions with guards | RIS-UI-07…12 | S4-21 |
| D4 | Engineering DoD: `tsc --noEmit` + `vite build` clean; unit tests green; migrations reviewed | release-plan §6 | CI gate |
| D5 | No P0/P1 open defects | release-plan §6 | Defect triage |

---

## 6. Risks & Watch Items

| Risk | Watch indicator | Mitigation |
| :--- | :--- | :--- |
| DICOM MWL conformance variance (real scanner differences) | S4-04 test set | Common scanner profiles tested; exception queue for unknown C-FIND queries |
| MPPS → PACS echo latency | S4-22 | Echo runs async; tracking board updates independently; PACS echo is best-effort |
| Tracking board performance with 500+ concurrent exams | S4-21 | Server-side pagination; polling interval configurable; WebSocket upgrade in v1.1 |
| pynetdicom port conflicts with existing DICOM services | Port allocation | MWL on 11113, MPPS on 11114, existing C-STORE on 11112; documented in config |

---

## Traceability

| Source work item | Tasks |
| :--- | :--- |
| E-RIS-06 #1 (MWL SCP) | S4-01…05 |
| E-RIS-06 #2 (MPPS consumer) | S4-06…10 |
| E-RIS-07 #1 (tracking board live) | S4-11…15 |
| E-RIS-07 #2 (status indicator) | S4-14 |
| E-RIS-07 #3 (filters/pagination) | S4-17 |
| E-RIS-07 #4 (row actions) | S4-13/18 |
| Cross-cutting (MWL E2E, tracking E2E, perf, RLS) | S4-20…23 |
