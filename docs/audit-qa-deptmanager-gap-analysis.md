# Audit: QA Manager (2.8) & Department Manager (2.9) — Gap Analysis

**Date:** 2026-08-24  
**Branch:** feature/ris-integration  
**Spec:** docs/ui-ux-redesign-spec.md §2.8–2.9

---

## 1. Implementation vs Spec — Feature-by-Feature Audit

### 2.8 QA Manager

| # | Feature | Spec Priority | Backend API | Backend Exists? | Frontend Exists? | Status |
|---|---------|--------------|-------------|-----------------|------------------|--------|
| QA-01 | QA Queue | P0 | `GET /api/qa/queue` | ✅ `qa.py:QAQueueHandler` | ✅ `qa/QAQueue.tsx` | **IMPLEMENTED** |
| QA-02 | Reject Analysis Dashboard | P1 | `GET /api/qa/reject-analysis` | ❌ No endpoint | ❌ No component | **GAP — P1** |
| QA-03 | Dose Tracking Report | P1 | `GET /api/qa/dose-tracking` | ❌ No endpoint | ❌ No component | **GAP — P1** |
| QA-04 | Image Quality Scoring | P2 | `POST /api/qa/reviews/{id}/score` | ⚠️ Embedded in QAReviewHandler.post (score is part of qa_scores) | ✅ `qa/QAReviewForm.tsx` (includes scoring UI) | **PARTIAL — score saved via existing endpoint** |
| QA-05 | Technologist Performance Metrics | P1 | `GET /api/qa/tech-metrics` | ❌ No endpoint | ❌ No component | **GAP — P1** |
| QA-06 | Protocol Compliance Rate | P1 | `GET /api/qa/protocol-compliance` | ❌ No endpoint | ❌ No component | **GAP — P1** |
| QA-07 | Trending Graphs | P1 | `GET /api/qa/trends` | ❌ No endpoint | ❌ No component | **GAP — P1** |
| QA-08 | QA Export (CSV/PDF) | P2 | `GET /api/qa/export` | ❌ No endpoint | ❌ No component | **GAP — P2** |
| QA-09 | Protocol Registry CRUD | P0 | `GET/POST /api/qa/protocols` + PUT/DELETE | ✅ `qa.py:QAProtocolsHandler` + `QAProtocolHandler` | ✅ `qa/ProtocolRegistry.tsx` | **IMPLEMENTED** |
| QA-10 | Incidents Log | P0 | `GET /api/qa/incidents` | ✅ `qa.py:QAIncidentsHandler` | ✅ `qa/Incidents.tsx` | **IMPLEMENTED** |
| QA-11 | Corrective Actions | P0 | `GET /api/qa/corrective-actions` | ✅ `qa.py:QACorrectiveActionsHandler` | ✅ `qa/CorrectiveActions.tsx` | **IMPLEMENTED** |

**QA Summary:** 4 of 11 features implemented. All P0 features are done. Gaps are P1/P2 analytics features (QA-02, QA-03, QA-05, QA-06, QA-07) and export (QA-08).

### 2.9 Department Manager

| # | Feature | Spec Priority | Backend API | Backend Exists? | Frontend Exists? | Status |
|---|---------|--------------|-------------|-----------------|------------------|--------|
| DM-01 | Department Workload Distribution | P0 | `GET /api/ris/tracking` (aggregated) | ⚠️ `worklist.py:TrackingHandler` exists (raw), no aggregated workload endpoint | ❌ No component | **GAP — P0** |
| DM-02 | Turnaround Time Drill-Down | P1 | `GET /api/ris/analytics/turnaround` | ❌ No endpoint (ris_dashboard.py has TAT p95 but no drill-down per provider) | ⚠️ RISDashboard.tsx shows TAT by priority only | **GAP — P1** |
| DM-03 | Volume Forecast | P2 | `GET /api/ris/analytics/forecast` | ❌ No endpoint | ❌ No component | **GAP — P2** |
| DM-04 | Equipment Utilization Report | P1 | `GET /api/ris/analytics/equipment` | ⚠️ `equipment.py` has equipment CRUD + downtime but no utilization % endpoint | ❌ No component | **GAP — P1** |
| DM-05 | Patient Satisfaction Metrics | P2 | `GET /api/ris/analytics/satisfaction` | ❌ No endpoint | ❌ No component | **GAP — P2** |
| DM-06 | Department Budget Tracking | P2 | `GET /api/ris/analytics/budget` | ❌ No endpoint | ❌ No component | **GAP — P2** |
| DM-07 | Staff Schedule Management | P1 | `GET/POST /api/ris/staff-schedule` | ❌ No endpoint (scheduling.py handles resources/appointments, not staff schedules) | ❌ No component | **GAP — P1** |
| DM-08 | Staffing Model Optimizer | P2 | `GET /api/ris/analytics/staffing-model` | ❌ No endpoint | ❌ No component | **GAP — P2** |

**DM Summary:** 0 of 8 features fully implemented. The existing `ris_dashboard.py` provides some overlapping KPIs (TAT, utilization, unbilled, volume, prior-auth, chargeback, denial rate) but does NOT match the spec's DM-01 through DM-08 feature set.

---

## 2. Cross-Check: Platform Inheritance (PACS vs RIS-Gap Refinement)

After analyzing the codebase, the following gaps are **not real concerns** for the integrated platform because they either:
- Overlap with existing QuantumPACS functionality that will be inherited
- Are already partially covered by existing endpoints
- Are P2 (deferred by spec phase plan)

### Refinement: Gaps That Are NOT Real Concerns

| Gap | Reason to Drop/Defer |
|-----|---------------------|
| DM-03 (Volume Forecast) | P2 only. Requires ML/historical data pipeline. Not critical for initial RIS launch. Defer. |
| DM-05 (Patient Satisfaction) | P2 only. Requires external survey integration. Defer. |
| DM-06 (Department Budget) | P2 only. Requires finance system integration. Defer. |
| DM-08 (Staffing Model Optimizer) | P2 only. Complex ML feature. Defer. |
| QA-08 (QA Export CSV/PDF) | P2 only. Can be built on top of existing analytics endpoints once they exist. Defer. |

### Real Gaps to Implement Now (P0/P1)

| Gap | Priority | Why It's a Real Concern |
|-----|----------|------------------------|
| **QA-02** Reject Analysis | P1 | QA manager cannot track reject rates — core QA function |
| **QA-03** Dose Tracking Report | P1 | Regulatory compliance (ACR) — must track dose exceedances |
| **QA-05** Tech Performance Metrics | P1 | QA manager needs per-tech scores for training/coaching |
| **QA-06** Protocol Compliance Rate | P1 | Core QA metric — feeds R03 Service Director dashboard |
| **QA-07** Trending Graphs | P1 | All QA metrics need trends for operational visibility |
| **DM-01** Workload Distribution | P0 | Dept manager's primary operational view |
| **DM-02** TAT Drill-Down | P1 | Existing ris_dashboard has p95 but no per-provider drill-down |
| **DM-04** Equipment Utilization | P1 | Equipment.py has CRUD but no utilization analytics |
| **DM-07** Staff Schedule Mgmt | P1 | No staff scheduling surface exists in RIS |

---

## 3. Existing Backend API & DB Mapping

### Existing QA Backend

| Endpoint | Handler | DB Tables | Permissions |
|----------|---------|-----------|-------------|
| `GET /api/qa/queue` | `QAQueueHandler` | `exams`, `qa_scores` | `QA_READ` |
| `GET/POST /api/qa/reviews/{exam_id}` | `QAReviewHandler` | `qa_scores`, `protocols` | `QA_READ`/`QA_WRITE` |
| `GET/POST /api/qa/protocols` | `QAProtocolsHandler` | `protocols` | `QA_READ`/`PROTOCOL_MANAGE` |
| `PUT/DELETE /api/qa/protocols/{id}` | `QAProtocolHandler` | `protocols` | `PROTOCOL_MANAGE` |
| `GET/POST /api/qa/incidents` | `QAIncidentsHandler` | `incidents` | `QA_READ`/`QA_WRITE` |
| `POST /api/qa/incidents/{id}/resolve` | `QAIncidentHandler` | `incidents` | `QA_WRITE` |
| `GET/POST /api/qa/corrective-actions` | `QACorrectiveActionsHandler` | `corrective_actions` | `QA_READ`/`QA_WRITE` |
| `POST /api/qa/corrective-actions/{id}/resolve` | `QACorrectiveActionHandler` | `corrective_actions` | `QA_WRITE` |
| `GET /api/qa/dashboard` | `QADashboardHandler` | `qa_scores`, `corrective_actions`, `incidents` | `QA_READ` |

### Existing Department Manager Backend

| Endpoint | Handler | DB Tables | Permissions |
|----------|---------|-----------|-------------|
| `GET /api/ris/dashboard/kpi` | `RisDashboardKpiHandler` | `reports`, `exams`, `ris_appointments`, `ris_charges`, `worklist_entries`, `ris_prior_auth_requests`, `ris_claims` | `REPORT_READ` |

### Existing Equipment Backend

| Endpoint | Handler | DB Tables | Permissions |
|----------|---------|-----------|-------------|
| `GET/POST /api/equipment` | `EquipmentHandler` | `equipment` | `EQUIPMENT_READ`/`EQUIPMENT_WRITE` |
| `GET/POST /api/equipment/{id}/downtime` | `DowntimeEventsHandler` | `equipment_downtime` | `EQUIPMENT_READ` |

### Existing Tracking Backend

| Endpoint | Handler | DB Tables | Permissions |
|----------|---------|-----------|-------------|
| `GET /api/ris/tracking` | `TrackingHandler` | `worklist_entries`, `exams` | `WORKLIST_READ` |
| `GET /api/ris/tracking/kpi` | `TrackingKpiHandler` | `worklist_entries` | `WORKLIST_READ` |

---

## 4. Permission Requirements & Grant Analysis

### Current Permissions Used

| Permission | Current Holders (Matrix) | Used By |
|------------|-------------------------|---------|
| `QA_READ` | QA Manager role (not in Matrix A/B/C explicitly — inherited from legacy) | QA Queue, Reviews GET, Protocols GET, Incidents GET, Corrective Actions GET, Dashboard |
| `QA_WRITE` | QA Manager role (legacy) | QA Reviews POST, Incidents POST/resolve, Corrective Actions POST/resolve |
| `PROTOCOL_MANAGE` | QA Manager role (legacy) | Protocol CRUD |
| `ANALYTICS_READ` | Matrix C: dept_manager, service_director | RIS Dashboard KPI (overlaps with REPORT_READ) |
| `EQUIPMENT_READ` | Biomedical Engineer (legacy) | Equipment CRUD |
| `WORKLIST_READ` | Matrix A: radiologist, tech, scheduler, referring; Matrix B: physician, resident, coordinator | Tracking Board |

### New Permissions Required

**For QA Analytics (QA-02, QA-03, QA-05, QA-06, QA-07):**

No new permissions needed. All analytics endpoints should be gated on `QA_READ` — the QA Manager already holds this, and the analytics are QA-team-specific views of existing data.

**For Department Manager (DM-01, DM-02, DM-04, DM-07):**

| New Endpoint | Suggested Gate | Notes |
|-------------|----------------|-------|
| `GET /api/ris/analytics/workload` | `REPORT_READ` + `ANALYTICS_READ` | Dept manager already holds both via `MATRIX_C_DEPTMGR` |
| `GET /api/ris/analytics/tat-drilldown` | `REPORT_READ` + `ANALYTICS_READ` | Extends existing ris_dashboard |
| `GET /api/ris/analytics/equipment-util` | `EQUIPMENT_READ` + `ANALYTICS_READ` | **NEW GRANT NEEDED**: dept_manager needs `EQUIPMENT_READ` |
| `GET/POST /api/ris/staff-schedule` | `SCHEDULE_READ` + `SCHEDULE_WRITE` | Dept manager already holds `SCHEDULE_READ` via `MATRIX_C_DEPTMGR`; **needs `SCHEDULE_WRITE` for staff schedule edits** |

### Permission Grant Requests for Human Review

**REQUEST 1: Add `EQUIPMENT_READ` to `MATRIX_C_DEPTMGR`**
- **Current `MATRIX_C_DEPTMGR`:** `{PATIENT_READ, ORDER_READ, SCHEDULE_READ, PRIOR_AUTH_READ, WORKLIST_READ, REPORT_READ, BILLING_READ, ANALYTICS_READ, METRICS_READ, CHART_READ, RESULTS_READ, AUDIT_READ}`
- **Proposed addition:** `EQUIPMENT_READ`
- **Justification:** DM-04 (Equipment Utilization Report) requires reading equipment status and downtime data. The dept manager oversees modality operations and needs equipment visibility.
- **Risk:** Low. Read-only access to equipment metadata. No mutation capability.

**REQUEST 2: Add `SCHEDULE_WRITE` to `MATRIX_C_DEPTMGR`**
- **Proposed addition:** `SCHEDULE_WRITE`
- **Justification:** DM-07 (Staff Schedule Management) requires creating/editing staff schedules. Without SCHEDULE_WRITE, the dept manager can only view schedules.
- **Risk:** Medium. SCHEDULE_WRITE also enables appointment booking. However, the dept manager is a senior role that should have scheduling authority. The endpoint-level guard can further restrict to staff-schedule-only operations.
- **Alternative:** Create a new `STAFF_SCHEDULE_WRITE` permission for finer granularity. This is cleaner but requires a new enum member + migration.

**REQUEST 3: No new permission for QA analytics**
- All QA analytics (QA-02 through QA-07) are gated on existing `QA_READ`.
- Justification: These are read-only aggregations of data the QA manager already has access to.

---

## 5. Implementation Plan — TDD Pipeline

### Phase 1: QA Analytics Dashboard (QA-02, QA-03, QA-05, QA-06, QA-07)

**Strategy:** Single new endpoint `GET /api/qa/analytics` that returns all QA analytics in one response, plus dedicated drill-down endpoints for reject analysis and tech metrics.

#### Step 1: Backend — QA Analytics Endpoints (TDD)

**Tests first:**
1. `test_qa_analytics_reject_analysis.py` — Reject rate by modality, tech, protocol, reason
2. `test_qa_analytics_dose_tracking.py` — Dose metrics by modality/protocol/tech vs ACR benchmarks
3. `test_qa_analytics_tech_metrics.py` — Per-tech: reject rate, dose compliance, protocol adherence
4. `test_qa_analytics_protocol_compliance.py` — Protocol adherence % by protocol, trending
5. `test_qa_analytics_trends.py` — Trend data for all metrics (daily/weekly/monthly)

**Implementation:**
1. Add handlers to `backend/api/qa.py`:
   - `QARejectAnalysisHandler` — `GET /api/qa/reject-analysis`
   - `QADoseTrackingHandler` — `GET /api/qa/dose-tracking`
   - `QATechMetricsHandler` — `GET /api/qa/tech-metrics`
   - `QAProtocolComplianceHandler` — `GET /api/qa/protocol-compliance`
   - `QATrendsHandler` — `GET /api/qa/trends`
2. Add SQL queries to `backend/db/qa.py`:
   - `reject_analysis(modality, tech, date_range)` — aggregate qa_scores WHERE pass_fail='fail'
   - `dose_tracking(modality, protocol, date_range)` — aggregate dose fields from qa_scores + protocols ACR benchmarks
   - `tech_metrics(tech_id, date_range)` — per-technologist aggregations
   - `protocol_compliance(protocol_id, date_range)` — sequence_compliance stats
   - `trends(metric, granularity, date_range)` — time-series aggregations
3. Register routes in `backend/api/routes.py`

#### Step 2: Frontend — QA Analytics Dashboard (TDD)

**Tests first:**
1. `test/QAAnalyticsDashboard.test.tsx` — Renders KPI cards, trend charts, tables
2. `test/QARejectAnalysis.test.tsx` — Reject rate table with modality/tech/protocol breakdown
3. `test/QADoseTracking.test.tsx` — Dose metrics with ACR benchmark comparison bars
4. `test/QATechMetrics.test.tsx` — Tech performance comparison table
5. `test/QAProtocolCompliance.test.tsx` — Compliance % per protocol

**Implementation:**
1. Add API client: `frontend/src/api/qa-analytics.ts`
2. Create components:
   - `frontend/src/qa/QAAnalyticsDashboard.tsx` — Main analytics view with tabbed sub-views
   - `frontend/src/qa/QAAnalyticsDashboard.css`
3. Add route in `index.tsx`: `/qa/analytics` → `QAAnalyticsDashboard`
4. Add sidebar item in `Sidebar.tsx`: "QA Analytics" under QA section
5. Add navigation in `getKey()` for `/qa/analytics`

#### Step 3: Integration Tests

- Test QA Manager role can access all QA analytics endpoints
- Test non-QA roles are blocked from QA analytics

---

### Phase 2: Department Manager Dashboard Enhancement (DM-01, DM-02, DM-04, DM-07)

**Strategy:** Enhance the existing `ris_dashboard.py` with additional drill-down endpoints, and add new workload distribution and staff schedule endpoints.

#### Step 1: Backend — Dept Manager Endpoints (TDD)

**Tests first:**
1. `test_deptmanager_workload.py` — Workload distribution by provider/room/modality
2. `test_deptmanager_tat_drilldown.py` — TAT by provider with drill-down
3. `test_deptmanager_equipment_util.py` — Equipment utilization % with downtime overlay
4. `test_deptmanager_staff_schedule.py` — Staff schedule CRUD

**Implementation:**
1. Add handlers to `backend/api/ris_dashboard.py` or new `backend/api/dept_manager.py`:
   - `DeptWorkloadHandler` — `GET /api/ris/analytics/workload`
   - `DeptTatDrilldownHandler` — `GET /api/ris/analytics/tat-drilldown`
   - `DeptEquipmentUtilHandler` — `GET /api/ris/analytics/equipment-util`
   - `DeptStaffScheduleHandler` — `GET/POST /api/ris/staff-schedule`
2. Register routes in `backend/api/routes.py`
3. Apply permission grants (after human review of REQUEST 1 & 2)

#### Step 2: Frontend — Enhanced Dept Manager Dashboard (TDD)

**Tests first:**
1. `test/DeptManagerDashboard.test.tsx` — Enhanced dashboard with workload heatmap, TAT drill-down, equipment cards
2. `test/WorkloadDistribution.test.tsx` — Heatmap or table of provider/room utilization
3. `test/StaffSchedule.test.tsx` — Schedule management view

**Implementation:**
1. Enhance `frontend/src/admin/RISDashboard.tsx`:
   - Add workload distribution panel (heatmap or card grid)
   - Add TAT drill-down table (per-provider)
   - Add equipment utilization cards
2. Create `frontend/src/admin/StaffSchedule.tsx` — Staff schedule management
3. Add route in `index.tsx`: `/admin/staff-schedule` → `StaffSchedule`
4. Add sidebar items in `Sidebar.tsx` under Admin section

#### Step 3: Integration Tests

- Test dept_manager role can access all new endpoints
- Test non-dept_manager roles are blocked

---

## 6. Test Strategy (per §8 of spec)

### 8.1 E2E Critical Path Flows

| Flow | Relevance |
|------|-----------|
| E1: Order Lifecycle | QA analytics depend on completed exams flowing through the pipeline |
| E10: Role-Based Access | QA Manager and Dept Manager role isolation |

### 8.2 Accessibility (axe-core)

- QA Analytics Dashboard: WCAG 2.1 AA audit
- Dept Manager Dashboard: WCAG 2.1 AA audit

### 8.3 Load Testing (k6)

- QA analytics queries with 10k+ qa_scores rows
- Dept manager dashboard with 100+ concurrent users

### 8.4 Visual Regression

- Playwright screenshots of QA Analytics Dashboard at 1080p, 1440p
- Playwright screenshots of enhanced Dept Manager Dashboard at 1080p, 1440p

---

## 7. Commit Strategy

Following repo pre-commit gates:
1. **Commit 1:** Backend QA analytics endpoints + tests (format, typecheck, pytest pass)
2. **Commit 2:** Frontend QA Analytics Dashboard + tests (prettier, tsc, vitest pass)
3. **Commit 3:** Backend Dept Manager endpoints + tests
4. **Commit 4:** Frontend enhanced Dept Manager + tests

Each commit passes: formatting → typecheck → full test suite → build.
