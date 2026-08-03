# Delta — Referring Clinician (R14) — 2026-08-03

## Summary
- **Trigger**: re-verification after v3-dev merge 4d136e0 (exams/QA/reports routes shipped)
- **Version change**: 1.2.0 → 1.2.1 (PATCH)
- **Stakeholder**: PACS requirements architect

## Changed Requirements
none; re-verification only

Verified against post-merge codebase (4d136e0):
- `GET /reports/{exam_id}` (ExamReportHandler) now exists, gated by REPORT_READ. The `radiologist` built-in role has REPORT_READ; the `physician` built-in role does **not** (FILE_READ/PATIENT_READ/STUDY_READ/DICOMWEB_READ), and the share-link path cannot call it — `ShareView` merely stores the key and redirects to Files with no report tab. **FR-R14-04 stays GATED** (a route behind a permission this role lacks is not implementation for the role).
- In-app notification infra exists (bell badge + WS push `{'type':'notifications'}`), but `report.signed` notifications fan out to the `qa` role only; no referring-clinician routing and no email service. **FR-R14-06 stays GATED** (in-app half of the FR exists as shared infra, delivery to the role does not).
- OAuth providers admin (`/oauth/providers`) and share-link viewer (`/view/:key`) re-confirmed — FR-R14-01/03 implemented, FR-R14-02 partial unchanged.
- `PermissionRoute` enforces role-based access at the URL boundary for authenticated routes.

## Impact on Existing Artifacts
| Artifact | Changed? | Summary |
|----------|----------|---------|
| README.md | Yes | Post-merge re-verification note; version 1.2.0 → 1.2.1 |
| 01-user-requirements.md | Yes | Codebase Status: re-verification note appended (no status change) |
| 06-acceptance-criteria.md | No | No GATED markers; unchanged |
| 07-traceability.md | Yes | FR-R14-04/06 GATED blocking-dependency notes updated (statuses unchanged) |
| 08-implementation-roadmap.md | Yes | FR-R14-04 blocking-dependency note updated (status unchanged) |
| CHANGELOG.md | Yes | Added 1.2.1 entry |
| DELTA.md | Yes | This file |
