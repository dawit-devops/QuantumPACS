# Changelog — Service Coordinator (R04)

All notable changes to this requirements package follow
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.

## [1.1.0] — 2026-08-03
### Added
- Artifact 04: Role-Based Routing & Navigation (Presentation Layer) section — worklist CRUD/calendar/batch implemented; scheduling board/staffing/utilization GATED
- README: Codebase Alignment section (verified 2026-08-03)

## [1.0.0] — 2026-08-02
### Added
- Initial requirements package for Service Coordinator role
- FR-R04-01: Modality Scheduling Board (drag-and-drop, time slots, priority badges)
- FR-R04-02: Exam Assignment (drag-and-drop or dropdown, WebSocket push)
- FR-R04-03: Stat/Priority Triage (auto-sort, auto-promotion at threshold)
- FR-R04-04: Resource Utilization Dashboard (capacity bar chart, utilization trend)
- FR-R04-05: Staffing Roster Management (shift assignment, status tracking)
- FR-R04-06: Worklist Management (filterable, paginated, bulk actions)
- FR-R04-07: Exam Override & Reassignment (bulk reassignment, confirmation)
- FR-R04-08: Schedule Conflict Detection (real-time, technologist + modality)
- FR-R04-09: Shift Handoff Report (PDF export, clipboard copy)
- FR-R04-10: Modality Calendar View (day/week/month toggle)
- All 8 artifacts (01-08) with complete traceability
- 10 API endpoints flagged for `frontend-to-backend-requirements` skill
- 5 new semantic design tokens for scheduler components
- Cross-role dependencies with R06, R07, R05, R03, R15, R16, R17