# Delta — Front Desk (R08) — 2026-08-03

## Summary
- **Trigger**: re-verification after v3-dev merge 4d136e0 (exams/QA/reports routes shipped)
- **Version change**: 1.1.1 → 1.1.2 (PATCH)
- **Stakeholder**: PACS requirements architect

## Changed Requirements
none; re-verification only

Verified against post-merge codebase (4d136e0):
- Worklist CRUD/calendar/create-entry frontends exist (`Worklist.tsx`, `CalendarView.tsx`, `CreateEntry.tsx`); `/worklist`, `/schedule-board` routes gated by `PermissionRoute` (WORKLIST_READ).
- `/schedule-board` is an R04 worklist-derived read view — not an appointment-scheduling API; FR-R08-04 remains GATED.
- Patient search exists via Files/patient pages (`/patients/{id}`, `Patient.tsx`) — FR-R08-01 partial status unchanged.
- `backend/api/hl7.py` `Hl7Receiver` is inbound-only (`POST /hl7`); no outbound ADT sender — FR-R08-02 remains GATED.
- `PermissionRoute` (frontend) enforces role-based access at the URL boundary; in-app notification bell refreshes via WS push — neither unblocks front-desk FRs.

## Impact on Existing Artifacts
| Artifact | Changed? | Summary |
|----------|----------|---------|
| README.md | Yes | Post-merge re-verification note; version 1.1.1 → 1.1.2 |
| 01-user-requirements.md | No | Statuses unchanged |
| 06-acceptance-criteria.md | No | No GATED markers; unchanged |
| 07-traceability.md | No | FR-R08-01 partial / FR-R08-02..10 GATED unchanged |
| 08-implementation-roadmap.md | No | Statuses unchanged |
| CHANGELOG.md | Yes | Added 1.1.2 entry |
| DELTA.md | Yes | This file |
