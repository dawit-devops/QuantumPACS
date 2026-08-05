# Delta — Radiology & Service Coordinator (R04) — 2026-08-03

## Summary
- **Trigger**: v3-dev merge 4d136e0 (2026-08-03) shipped R04 schedule board (frontend over worklist API)
- **Version change**: 1.1.0 → 1.2.0 (MINOR)
- **Stakeholder**: PACS requirements architect

## Changed Requirements
| ID | Field Changed | Old Value | New Value | Rationale |
|----|---------------|-----------|-----------|-----------|
| FR-R04-01 | Status | GATED | Implemented | `ScheduleBoard.tsx` at `/schedule-board` shipped — frontend view over `GET /worklist` (date filters, per_page 500); drag-and-drop rescheduling not implemented |
| FR-R04-06 | Status | Implemented | Implemented (confirmed) | `/worklist` CRUD + batch + calendar confirmed against routes.py/frontend |
| FR-R04-10 | Status | GATED | Implemented (partial) | Worklist table/calendar toggle (`CalendarView.tsx`) shipped; week/month views + drill-down remain GATED |
| FR-R04-02 | Status | GATED | GATED (unchanged) | No `/schedule/assign` endpoint; no WebSocket push |
| FR-R04-03..05, 07..09 | Status | GATED | GATED (unchanged) | No `/schedule/*` backend endpoints exist |

## Impact on Existing Artifacts
| Artifact | Changed? | Summary |
|----------|----------|---------|
| 01 User Requirements | Yes | Codebase Status section rewritten (board implemented; assignment/triage/utilization/rosters/handoff GATED) |
| 04 UI/UX Requirements | Yes | Route table: `/schedule-board` accessible (WORKLIST_READ); staffing/utilization/handoff remain GATED |
| 06 Acceptance Criteria | Yes | Implementation status note added; board/calendar ACs verifiable via visual evidence / component test |
| 07 Traceability | Yes | Per-FR statuses updated (Covered/GATED) with accurate blocking dependencies |
| 08 Roadmap | Yes | FR-R04-01/06/10 moved to Implemented (Passing ACs); phases + blocking deps updated |
| README | Yes | Codebase Alignment rewritten; API-endpoint table annotated with current status |
| CHANGELOG | Yes | 1.2.0 entry added |
