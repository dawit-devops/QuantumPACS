# R04 — Radiology & Service Coordinator Requirements Package

| Field | Value |
|-------|-------|
| **Version** | 1.1.0 |
| **Status** | draft |
| **Generated** | 2026-08-03 |
| **Changelog** | [CHANGELOG.md](CHANGELOG.md) |

## Codebase Alignment (verified 2026-08-03)

**Presentation layer**: role-based; see artifact 04 — "Role-Based Routing &
Navigation": coordinators today use the Worklist (admin item, `WORKLIST_READ`) with
calendar view, batch operations, search, date-range + station filters.

**Implemented**: worklist CRUD/calendar/batch (FR-R04 worklist slice). **GATED**:
schedule board, exam assignment, staffing rosters, utilization, shift handoff report
— no routes/endpoints exist; flagged to backend.

---

## Role Profile

| Attribute | Detail |
|-----------|--------|
| **ID** | R04 |
| **Role** | Radiology & Service Coordinator (Chief Radiology Technologist) |
| **Persona** | Department scheduler and resource coordinator responsible for modality scheduling, exam assignment, resource utilization tracking, staffing rosters, and worklist management. Works from a central desk; manages multiple technologists and modalities simultaneously; reacts to STAT exams and scheduling conflicts. |
| **Access Tier** | Department scheduler (read/write scheduling, no clinical reading) |
| **Top Tasks (by frequency)** | 1. Modality scheduling (daily) — drag-and-drop exam blocks on the schedule board<br>2. Exam assignment & triage (daily) — assign exams to technologists, prioritize STAT<br>3. Resource utilization review (daily/weekly) — check dashboard for capacity<br>4. Staffing roster management (weekly) — adjust shifts, handle call-ins<br>5. Worklist management (continuous) — filter, bulk reassign, cancel exams |
| **Pain Points** | • No visual schedule board — spreadsheets or paper-based scheduling<br>• Manual exam assignment via email/phone to technologists<br>• No real-time conflict detection — double-bookings discovered at exam time<br>• No utilization dashboard — capacity decisions are guesswork<br>• Shift handoff is verbal/informal — no structured report<br>• STAT triage is manual — STAT exams get buried in routine queue |
| **Devices** | Desktop workstation (primary), tablet for rounding; dual-monitor standard for schedule board + worklist side-by-side |
| **Working Patterns** | Batch operations (morning scheduling), continuous monitoring (STAT triage), reactive (override/reassign for call-ins), weekly (roster management) |
| **PHI Exposure**: Patient initials only on schedule board; full PHI accessible via exam detail modal per HIPAA minimum necessary |

---

## Artifact Index

| # | File | Description | v3.0 Status |
|---|------|-------------|-------------|
| 01 | `01-user-requirements.md` | Functional (FR-R04-NN) & Non-Functional (NFR-R04-NN) requirements, MoSCoW prioritized | **Complete (v3.0 Must — 10 FRs)** |
| 02 | `02-workflow-maps.md` | 5 end-to-end workflow maps as Mermaid sequenceDiagrams with R06/R07/R05 integration touchpoints | **Complete** |
| 03 | `03-user-stories.md` | User stories (US-R04-NN) with Given/When/Then AC, WCAG 2.2 AA, performance targets | **Complete (10 v3.0 stories)** |
| 04 | `04-ui-ux-requirements.md` | Screen inventory (6 screens), component state matrix, design token references (existing + 5 proposed), a11y, responsive | **Complete** |
| 05 | `05-metrics-slas.md` | Quantified KPIs (M-R04-NN) with targets, measurement methods, frequency, owners; SLA tiers | **Complete (10 KPIs)** |
| 06 | `06-acceptance-criteria.md` | Validator-gated AC matrix mapped to FR/NFR IDs; verification methods; out-of-scope | **Complete (~40 v3.0 ACs)** |
| 07 | `07-traceability.md` | FR/NFR → AC traceability, cross-artifact dependencies, cross-role dependencies, integration contracts | **Complete** |
| 08 | `08-implementation-roadmap.md` | Dependency-ordered implementation plan with status (done/partial/missing) per artifact | **Complete** |

---

## v3.0 vs v3.1 Scope Split

### v3.0 (Must Priority — This Package)
- FR-R04-01: Modality Scheduling Board (drag-and-drop, time slots, priority badges)
- FR-R04-02: Exam Assignment (drag-and-drop or dropdown, WebSocket push)
- FR-R04-03: Stat/Priority Triage (auto-sort, auto-promotion)
- FR-R04-04: Resource Utilization Dashboard (capacity bar chart, utilization trend)
- FR-R04-05: Staffing Roster Management (shift assignment, status tracking)
- FR-R04-06: Worklist Management (filterable, paginated, bulk actions)
- FR-R04-07: Exam Override & Reassignment (bulk reassignment, confirmation)
- FR-R04-08: Schedule Conflict Detection (real-time, technologist + modality)
- FR-R04-09: Shift Handoff Report (PDF export, clipboard copy)
- FR-R04-10: Modality Calendar View (day/week/month toggle)

### v3.1 (Should/Could — Deferred)
- FR-R04-09: Shift handoff report PDF formatting enhancements
- FR-R04-10: Calendar view advanced features (drag-to-reschedule in calendar)
- FR-R04-11: Automated shift recommendations based on historical utilization
- FR-R04-12: Integration with HR system for real-time availability data

---

## Cross-Role Dependencies

| Dependency | Source Role | Integration | Field Mapping / API Contract |
|------------|-------------|-------------|------------------------------|
| **Exam Assignment Push** | R04 → R06/R07 | WebSocket (LISTEN/NOTIFY) | R04 assigns exam → R06/R07 worklist updates in ≤5s |
| **Utilization Data** | R04 → R03 Service Director | Dashboard read | R04 dashboard provides utilization metrics → R03 reads for capacity planning |
| **Incident/Retake Data** | R04 → R05 QA Team | `incidents` table | R04 logs incidents → R05 QA review queue |
| **Patient Demographics** | R16 EMR → R04 | HL7 ADT | R16 sends patient demographics → R04 shows initials on board |
| **Scheduled Exam Feed** | R15 RIS → R04 | HL7 ORM | R15 sends scheduled orders → R04 board auto-populates |
| **Study Lookup** | R04 → R17 PACS | DICOM C-FIND | R04 queries R17 for study details when scheduling |

---

## New API Endpoints Required (v3.0)

| Endpoint | Method | Purpose | Permission |
|----------|--------|---------|------------|
| `/api/v2/schedule/board` | GET | Fetch schedule board data (exams, slots, technologists) | `SCHEDULE_READ` |
| `/api/v2/schedule/exam` | POST | Schedule a new exam on the board | `SCHEDULE_WRITE` |
| `/api/v2/schedule/move` | POST | Move an exam to a different time slot | `SCHEDULE_WRITE` |
| `/api/v2/schedule/assign` | POST | Assign an exam to a technologist | `SCHEDULE_WRITE` |
| `/api/v2/schedule/bulk-reassign` | POST | Bulk reassign exams (override) | `SCHEDULE_WRITE` |
| `/api/v2/schedule/roster` | GET | Fetch staffing roster data | `SCHEDULE_READ` |
| `/api/v2/schedule/roster/{user_id}` | PUT | Update shift assignment for a technologist | `SCHEDULE_WRITE` |
| `/api/v2/schedule/utilization` | GET | Fetch utilization dashboard data | `SCHEDULE_READ` |
| `/api/v2/schedule/handoff-report` | POST | Generate shift handoff report (PDF/clipboard) | `SCHEDULE_READ` |
| `/api/v2/schedule/worklist` | GET | Fetch department-wide worklist | `SCHEDULE_READ` |

---

## New Permission Slugs Required

```python
# In backend/api/permissions.py
SCHEDULE_READ = 'SCHEDULE_READ'
SCHEDULE_WRITE = 'SCHEDULE_WRITE'

# Add to PERMISSION_GROUPS
PERMISSION_GROUPS['SCHEDULE'] = [
    'SCHEDULE_READ', 'SCHEDULE_WRITE'
]

# New built-in role or extend existing
BUILT_IN_ROLES['service_coordinator'] = [
    Permission.FILE_READ.value,
    Permission.STUDY_READ.value,
    'SCHEDULE_READ',
    'SCHEDULE_WRITE',
]
```

---

## Database Schema Extensions (1 New Table)

### New for R04

```sql
CREATE TABLE shift_assignments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) NOT NULL,
    shift_date      DATE NOT NULL,
    shift_type      VARCHAR(20) NOT NULL, -- 'morning', 'evening', 'night'
    start_time      TIME NOT NULL,
    end_time        TIME NOT NULL,
    status          VARCHAR(20) DEFAULT 'scheduled', -- 'scheduled', 'confirmed', 'swapped', 'cancelled'
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, shift_date, shift_type)
);

CREATE INDEX idx_shift_assignments_user ON shift_assignments(user_id, shift_date);
CREATE INDEX idx_shift_assignments_date ON shift_assignments(shift_date);
```

---

## Design System Extensions (5 New Semantic Tokens)

| Semantic Token | Primitive Ref / Value | Description |
|----------------|----------------------|-------------|
| `scheduler-stat-bg` | `rgba(239, 68, 68, 0.1)` | Background for STAT exam blocks on schedule board |
| `scheduler-urgent-bg` | `rgba(245, 158, 11, 0.1)` | Background for urgent exam blocks |
| `scheduler-routine-bg` | `rgba(209, 213, 219, 0.1)` | Background for routine exam blocks |
| `scheduler-conflict-border` | `#EF4444` | Border color for conflict indicators |
| `scheduler-assigned-bg` | `#D1FAE5` | Background for assigned exam blocks |

---

## New Component Specs (Add to `component-specs.md`)

| Component | States | Key Tokens | Behavior |
|-----------|--------|-----------|----------|
| **ScheduleBoard** | loading, empty, populated, conflict | `--bg-surface`, `--color-danger`, scheduler tokens | KanbanBoard variant with modality columns, 30-min time slots, drag-and-drop exam blocks, priority color coding |
| **ExamBlock** | default, stat, urgent, routine, assigned, conflict | scheduler-stat-bg, scheduler-urgent-bg, scheduler-routine-bg, scheduler-conflict-border | Draggable block showing patient initials, modality icon, priority badge; color-coded by priority; conflict state shows red border |
| **AssignDropdown** | idle, open, loading, error | `--color-primary`, `--bg-surface` | Dropdown showing available technologists with load indicator and modality tags; keyboard-navigable |
| **OverrideModal** | idle, loading, error | `--bg-surface`, `--color-danger` | Confirmation modal listing affected exams with priority and time; Confirm/Cancel buttons |
| **UtilizationDashboard** | loading, empty, error, populated | `--color-danger`, `--color-warning`, `--color-success` | Bar chart (capacity) + line chart (trend) with date range filter; color-coded by utilization threshold |
| **StaffingRoster** | loading, empty, error, populated | `--bg-surface`, status badge colors | Table with technologist roster; drag-and-drop shift assignment; overflow warnings |
| **HandoffReportModal** | loading, empty, error, populated | `--bg-surface` | Modal with report preview; Export PDF and Copy to Clipboard buttons |
| **CalendarView** | loading, empty, error, populated | scheduler tokens | Calendar with exam blocks color-coded by priority; day/week/month views; drill-down on day click |

---

## Quality Gate Checklist

- [x] All 8 files exist with correct ID prefixes (FR-R04, NFR-R04, US-R04, AC-R04, M-R04)
- [x] Every FR has ≥1 AC; every AC links to FR/NFR
- [x] All 4 states (loading/empty/error/success) specified per component
- [x] Performance targets quantified (LCP ≤2s, assign ≤500ms, conflict ≤200ms)
- [x] 10 API endpoints flagged with request/response shapes
- [x] WCAG 2.2 AA ACs concrete (keyboard, focus, contrast, ARIA, inline validation)
- [x] 5 Mermaid workflow diagrams (W1-W5, including handoff report)
- [x] R06/R07/R05 integration stubs documented (API contracts)
- [x] Design tokens: 5 proposed semantic tokens + existing references
- [x] Validator gate: every AC observable/measurable; reverse validation noted
- [x] Cross-role deps matrix (R06, R07, R05, R03, R15, R16, R17)
- [x] Out-of-scope explicitly listed

---

## Out of Scope (Explicit)

- Radiologist reading workflow (R12/R18) — coordinator assigns exams, radiologist interprets
- Technologist exam acquisition (R06/R07) — coordinator schedules, technologist performs
- Patient registration (R08) — coordinator does not register patients
- Billing/payment (R09) — outside coordinator scope
- System administration (R01/R02) — tenant config, user management, DICOM AE setup
- QA/protocol management (R05) — separate role with its own requirements package
- DICOM image viewing/measurement (R12/R18) — coordinator references studies, does not view images
- AI/CAD integration (v3.2+ roadmap) — not in v3.0 scope
- Mobile native app — PWA only; mobile view is responsive adaptation

---

*Generated by pacs-requirements-architect skill pipeline. See `CLAUDE.md` Section 8 for methodology.*