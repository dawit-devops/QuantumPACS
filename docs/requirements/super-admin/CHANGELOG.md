# Changelog — R01 Super Admin (PACS Admin)

All notable changes to this requirements package follow
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.

## [1.4.0] — 2026-08-06
### Added
- ADR-026 (Tenant Data-Plane Wiring) closes the dormant DB-per-tenant architecture: contextvar-routed `get_conn()`, JWT claim → `X-Tenant-ID` → platform resolution precedence, `default` tenant seed, status lifecycle gating (403/404), quota enforcement (`QUOTA_EXCEEDED` + 90% breach notification), `tenant_usage_daily` metering, per-tenant backup, tenant health endpoint; external billing explicitly out of scope (backlog)
- Integration roundtrip (`backend/tests/integration/test_tenant_lifecycle.py`): provision → registry row + tenant DB + admin, JWT tenant claim login, routed-request isolation, suspend/decommission gating, metering, health
- Playwright coverage for the one-time admin password panel, provisioned card grid, and lifecycle status updates (`frontend/e2e/tenant-provisioning.spec.ts`)
### Changed
- README Flagged Gaps: storage tiering / quota enforcement UI resolved (metering + health feed the usage dashboard); per-tenant backup noted; external billing listed as explicit out-of-scope backlog
- Artifacts 01/06: FR-R01-01 (real DB + registry admin + status lifecycle) and FR-R01-02 (switcher functional end-to-end via routed connections) notes; AC-R01-01/02/04 verification methods updated
- FR-R01-18 (backup/restore of full system state) remains GATED / backlog — AC-R01-38 untouched

## [1.3.0] — 2026-08-05
### Added
- FR-R01-17 closed: `GET /v2/dashboard/health` (METRICS_READ) aggregates db, es, redis, storage, dicom_listener, ingestion_service, hl7, fhir, auth component status
- /metrics System Health rows are drill-down links to area dashboards (replicas/dicomweb/hl7/fhir) with time-scope passthrough; per-panel "metrics unavailable" + retry (panel isolation)
### Changed
- Artifacts 01/04/06/07/08 updated: FR-R01-17 GATED → Implemented; AC-R01-37 Pass (achieved 36 → 37 of 41; 3 partial, 1 gated)
- Excluded-scope note for the aggregate health endpoint removed from artifact 06
- FR-R01-18 (backup/restore) remains GATED / backlog — AC-R01-38 untouched

## [1.2.1] — 2026-08-03
### Changed
- Re-verified against post-merge codebase (4d136e0): no new admin endpoints affect R01 FRs; FR-R01-17/18 remain GATED
- Role-based access now enforced at route level via `PermissionRoute` (`frontend/src/auth/PermissionRoute.tsx`) — positive confirmation of the presentation-layer claim
- New built-in roles (`technologist`, `radiologist`, `qa_team`) and permission groups (`Exams`, `Reports`, `Peer Review`, `QA`) now visible in `/roles` permission catalog

## [1.2.0] — 2026-08-03
### Added
- Artifact 04: Role-Based Routing & Navigation (Presentation Layer) section — verified route/sidebar/permission mapping from `frontend/src/auth/`, `Sidebar.tsx`, `index.tsx`
- README: Codebase Alignment section (verified 2026-08-03) with implemented vs GATED status

## [1.1.0] — 2026-08-02
### Added
- Artifact 07 (Traceability Matrix): FR/NFR → AC traceability, cross-artifact dependencies, cross-role dependencies, integration contracts
- Artifact 08 (Implementation Roadmap): dependency-ordered implementation plan with status (done/partial/missing), blocking dependencies, and next steps
- GATED ACs identified: AC-R01-37 (health dashboard, blocked on backend aggregate endpoint), AC-R01-38 (backup/restore, no implementation)

## [1.0.0] — 2026-08-01
### Added
- Initial requirements package for Super Admin (PACS Admin) role
- FR-R01-01 through FR-R01-20: tenant provisioning, user/role RBAC,
  storage replicas, DICOM routing, service keys, webhooks, audit logs,
  metrics dashboards, FHIR/HL7 admin, OAuth providers, notifications
- NFR-R01-01 through NFR-R01-14: performance, accessibility, audit,
  session, and retention targets
- All 6 artifacts (01–06) with validator-gated acceptance criteria