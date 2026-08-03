# Delta — Staff Radiologist (R12) — 2026-08-03

## Summary
- **Trigger**: v3-dev merge 4d136e0 (2026-08-03) shipped reading/reporting/peer-review/presets
- **Version change**: 1.2.0 → 1.3.0 (MINOR)
- **Stakeholder**: PACS requirements architect

## Changed Requirements

| ID | Field Changed | Old Value | New Value | Rationale |
|----|---------------|-----------|-----------|-----------|
| FR-R12-01 | Notes (endpoint) | `GET /worklist` (WORKLIST_READ) | `GET /reports/reading-list` (REPORT_READ), fed by exam handoff (R06) | Reading worklist endpoint shipped; radiologist role grants REPORT_READ |
| FR-R12-09 | Status (GATED → Implemented); Notes | GAP: no reporting endpoints | `GET/PUT /reports/{exam_id}` (draft → preliminary → final), `POST /reports/{exam_id}/sign`, `GET /reports/templates` | Structured reporting + templates + sign shipped in `api/reports.py` + `ReportEditor.tsx` |
| FR-R12-10 | Status (unchanged GATED) | GATED — no escalation endpoint | GATED — no escalation endpoint; sign notifies QA role only | No escalation endpoint exists in codebase |
| FR-R12-12 | Status (GATED → Partial); Notes | R13 dependency; reporting gap | `/peer-reviews*` covers final signed reports; resident-draft attending-review queue not built | Peer-review workflow shipped; draft co-sign/supervision workflow still missing |
| FR-R12-14 | Status (GATED → Implemented); Notes | Notification bell pattern; backend event wiring | `exam.completed` role notification + `/ws` push (NotificationBell) | Exam handoff notification + WebSocket shipped |
| FR-R12-15 | Status (GATED → Implemented); Notes | Viewport preset feature | `/reading-presets` + `/reading-presets/{id}` CRUD (window_level + layout per modality) | Reading presets shipped end-to-end (commit 38bc04c) |
| NFR-R12-10 | Status (GATED → Implemented) | Blocked on reporting | Autosave flush + dirty-retry (zero lost drafts) | Report autosave loop shipped in `ReportEditor.tsx` |

## Impact on Existing Artifacts

| Artifact | Changed? | Summary |
|----------|----------|---------|
| 01-user-requirements.md | Yes | Notes column updated for FR-R12-01/09/12/14/15; Codebase Status + Assumptions rewritten |
| 03-user-stories.md | Yes | US-R12-06 (reporting) and US-R12-12 (presets) marked Implemented with endpoints; US-R12-08 (draft review) marked Partial |
| 06-acceptance-criteria.md | Yes | AC-R12-20/21/27/29 un-gated with real verification methods; AC-R12-30 (templates) and AC-R12-31 (peer review) added; AC-R12-22 gate note updated; verdict + excluded-scope rewritten |
| 07-traceability.md | Yes | FR-R12-09/12 AC links extended; GATED table now holds FR-R12-06/10/12 only |
| 08-implementation-roadmap.md | Yes | FR-R12-09/14/15 + NFR-R12-10 moved to Implemented; FR-R12-12 to Partially Implemented; blocking deps + next steps updated |
| README.md | Yes | Codebase Alignment rewritten with real routes/pages/permissions; version 1.3.0; flagged gaps updated |
| CHANGELOG.md | Yes | [1.3.0] entry added |
