# Delta — Other Hospital Staff (R19) — 2026-08-03

## Summary
- **Trigger**: re-verification after v3-dev merge 4d136e0 (exams/QA/reports routes shipped)
- **Version change**: 1.1.1 → 1.1.2 (PATCH)
- **Stakeholder**: PACS requirements architect

## Changed Requirements
none; re-verification only

Verified against post-merge codebase (4d136e0):
- In-app notification bell + WS push exists (`broadcast_to_user` → `{'type':'notifications'}`), but `report.signed` notifications fan out to the `qa` role only (`notify_role(conn, 'qa', ...)` in `reports.py`) — no hospital-staff care-team fan-out and no email service. **FR-R19-04 stays GATED** (shared in-app infra exists; the role-specific delivery does not).
- `GET /reports/{exam_id}` exists behind REPORT_READ (radiologist/admin roles) — no scoped hospital-staff report access. **FR-R19-02 stays GATED**.
- `PermissionRoute` enforces role-based access at the URL boundary for authenticated routes.
- Portal shell, care-team scope model, order-awareness view, follow-up primitive still absent — FR-R19-01/03/06/07/08/10 remain GATED; FR-R19-05/09 partial unchanged.

## Impact on Existing Artifacts
| Artifact | Changed? | Summary |
|----------|----------|---------|
| README.md | Yes | Post-merge re-verification note; version 1.1.1 → 1.1.2 |
| 01-user-requirements.md | No | Statuses unchanged |
| 06-acceptance-criteria.md | No | No GATED markers; unchanged |
| 07-traceability.md | No | Statuses unchanged |
| 08-implementation-roadmap.md | No | Statuses unchanged |
| CHANGELOG.md | Yes | Added 1.1.2 entry |
| DELTA.md | Yes | This file |
