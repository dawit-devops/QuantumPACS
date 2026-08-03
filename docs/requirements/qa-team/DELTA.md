# Delta — QI/QA Team (R05) — 2026-08-03

## Summary
- **Trigger**: v3-dev merge 4d136e0 (2026-08-03) shipped the R05 QA module end-to-end (backend `api/qa.py` + frontend `frontend/src/qa/`)
- **Version change**: 1.2.0 → 1.3.0 (MINOR)
- **Stakeholder**: PACS requirements architect

## Changed Requirements
| ID | Field Changed | Old Value | New Value | Rationale |
|----|---------------|-----------|-----------|-----------|
| FR-R05-01 | Status | GATED | Implemented | `GET /qa/queue` + `QAQueue.tsx` at `/qa/queue` |
| FR-R05-02 | Status | GATED | Implemented | `GET/PUT /qa/reviews/{exam_id}`, `POST /qa/reviews` + `QAReviewForm.tsx` at `/qa/review/:examId` |
| FR-R05-03 | Status | GATED | Implemented | `/qa/protocols` CRUD + `ProtocolRegistry.tsx` at `/qa/protocols` |
| FR-R05-04 | Status | GATED | Implemented | `qa_scores` written via review submit |
| FR-R05-05 | Status | GATED | Implemented | `/qa/corrective-actions` + resolve + `CorrectiveActions.tsx` at `/qa/actions` |
| FR-R05-06 | Status | GATED | Implemented | `/qa/incidents` + resolve + `Incidents.tsx` at `/qa/incidents` |
| FR-R05-07 | Status | GATED | Implemented | `qa_team` built-in role + `QA_*`/`PROTOCOL_MANAGE` permissions shipped |
| FR-R05-10 | Status | GATED | Implemented | `/qa/reviewers`, `POST /peer-reviews`, `POST /peer-reviews/{id}/submit`; new AC-R05-153 added |
| FR-R05-08, 09 | Status | GATED | GATED (unchanged) | No rules engine or tag parser; v3.1 scope |
| FR-R05-11, 12 | Status | GATED | GATED (unchanged) | No phantom-analysis or reporting engine; v3.1 scope |
| FR-R05-13 | Status | GATED | GATED (unchanged) | No AI integration; v3.2 scope |

## Impact on Existing Artifacts
| Artifact | Changed? | Summary |
|----------|----------|---------|
| 01 User Requirements | Yes | Codebase Status rewritten: implemented QA module endpoints/pages/role vs GATED remainder |
| 04 UI/UX Requirements | Yes | Route table: `/qa/*` screens now accessible (`QA_READ`); gating section split implemented vs GATED |
| 06 Acceptance Criteria | Yes | AC-R05-153 added (FR-R05-10 peer review); implementation status note appended |
| 07 Traceability | Yes | FR-R05-10 + NFR rows fixed; per-FR statuses (Covered — implemented / GATED) with endpoint mapping |
| 08 Roadmap | Yes | FR-R05-01..07, 10 moved to Implemented (Passing ACs); GATED table + blocking deps narrowed |
| README | Yes | Codebase Alignment rewritten with actual routes/permissions/pages; endpoint/permission/schema sections annotated shipped |
| CHANGELOG | Yes | 1.3.0 entry added |
