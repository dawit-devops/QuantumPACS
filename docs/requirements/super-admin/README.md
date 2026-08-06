# Requirements Package — R01 Super Admin (PACS Admin)

| Field | Value |
|-------|-------|
| **Version** | 1.3.0 |
| **Status** | approved |
| **Generated** | 2026-08-03 |
| **Changelog** | [CHANGELOG.md](CHANGELOG.md) |

## Codebase Alignment (verified 2026-08-03; re-verified post-merge 4d136e0)

**Presentation layer**: fully role-based. See artifact 04
(`04-ui-ux-requirements.md`) — "Role-Based Routing & Navigation" for the verified
route/sidebar/permission mapping (`frontend/src/auth/`, `Sidebar.tsx`, `index.tsx`).
Since the v3-dev merge (`4d136e0`), `PermissionRoute` (`frontend/src/auth/PermissionRoute.tsx`)
enforces the same permission gates at the URL boundary (deep links redirect to `/`
when the permission is missing) — strengthening the role-based claim; new built-in
roles (`technologist`, `radiologist`, `qa_team`) and new permission groups (`Exams`,
`Reports`, `Peer Review`, `QA` incl. `PROTOCOL_MANAGE`) now appear in the `/roles`
permission catalog managed by this role.

**Implemented**: all FR-R01-01..17, FR-R01-19/20 (admin CRUD, RBAC, integrations,
logs, metrics, worklist, global health aggregate `GET /v2/dashboard/health` with
storage/DICOM/HL7/FHIR/auth components + dashboard drill-down links).
**GATED** (kept as v3.0 spec): FR-R01-18 (backup/restore — no API; only
`scripts/backup_db.sh`).

## Role Summary

**Persona**: Senior systems administrator owning the entire QuantumPACS instance and all tenants.
**Access tier**: Full system + tenant configuration (`SYSTEM_ADMIN` and all permission groups).
**Context**: Manages multiple tenants, DICOM infrastructure, integrations, storage, RBAC, and audit.
Works from an ops/IT office; reacts to incidents; rarely uses the clinical viewer.

## Artifact Index

| # | Artifact | File |
|---|----------|------|
| 01 | User Requirements | `01-user-requirements.md` |
| 02 | End-to-End Workflow Maps | `02-workflow-maps.md` |
| 03 | User Stories | `03-user-stories.md` |
| 04 | UI/UX Requirements | `04-ui-ux-requirements.md` |
| 05 | Metrics & SLAs | `05-metrics-slas.md` |
| 06 | Acceptance Criteria (validator-gated) | `06-acceptance-criteria.md` |
| 07 | Traceability Matrix | `07-traceability.md` |
| 08 | Implementation Roadmap | `08-implementation-roadmap.md` |

## Cross-Role Dependencies

- **R02 Hospital IT / Tenant Admin** — tenant-scoped subset of R01 capabilities; R01 provisions the tenant, R02 operates it.
- **R15/R16/R17 External RIS/EMR/PACS** — integrations (HL7, FHIR, DICOM, webhooks) configured by R01.
- **R03 Service Director / R05 QI/QA** — consume `Metrics & SLAs` reporting; R01 owns infrastructure SLOs, R03 owns clinical KPIs.
- **R12/R18 Radiologists** — depend on storage/replica health, routing rules, and worklist availability guaranteed by R01.

## Grounding Sources

- Frontend screens (existing): `/tenants`, `/users`, `/roles`, `/routing`, `/service-keys`, `/integrations`, `/replicas`, `/logs`, `/metrics`, `/dicomweb`, `/fhir/config`, `/fhir/monitoring`, `/hl7`, `/notifications`
- Backend API (existing): `backend/api/routes.py` — full admin endpoint inventory (Section: API Surface)
- Permission model: `backend/api/permissions.py` (`Permission.SYSTEM_ADMIN`, `TENANT_*`, `USER_*`, `ROLE_*`, `REPLICA_*`, `ROUTING_*`, `SERVICE_KEY_*`, `LOG_READ`, `METRICS_READ`, etc.)
- Prior docs: `docs/User-Stories.md` (Epic E7 Administration), `docs/UX-Functionality.md` (§2.3, §2.6, Flows 7–10), `docs/IMPLEMENTATION_PLAN-v3.md` (F2.5, F6.1c, F6.2), `docs/PRD-v3.md`, `docs/design-tokens.json`, `docs/component-specs.md`

## API Surface (verified against `backend/api/routes.py`)

| Area | Endpoints (all under `/api/v2`) |
|------|---------------------------------|
| Tenants | `GET/POST /tenants`, `GET/PUT/DELETE /tenants/{id}` |
| Users | `GET/POST /users`, `POST /users/deactivate`, `POST /users/new_password`, `POST /users/role` |
| Roles | `GET/POST /roles`, `GET/PUT/DELETE /roles/{id}`, `GET /roles/{id}/users`, `GET /permissions` |
| Replicas | `GET/POST /replicas`, `GET/PUT/DELETE /replicas/{id}` |
| Routing | `GET/POST /routing`, `GET/PUT/DELETE /routing/{id}` |
| Service keys | `GET/POST /api-keys`, `GET/PUT/DELETE /api-keys/{id}` |
| Webhooks | `GET/POST /webhooks`, `GET/PUT/DELETE /webhooks/{id}`, `POST /webhooks/test` |
| Logs | `GET /logs`, `GET /logs/event-types`, `GET /logs/actors` |
| Metrics | `GET /metrics`, `GET /dashboard/metrics`, `GET /v2/dashboard/health`, `GET /dicomweb/admin/metrics`, `GET /hl7/admin/metrics`, `GET /fhir/admin/metrics` |
| DICOM admin | `GET/POST /dicomweb/admin` (station AEs) |
| FHIR admin | `GET/PUT /fhir/admin/config`, `GET/POST /fhir/admin/clients`, `GET/PUT/DELETE /fhir/admin/clients/{id}`, `GET /fhir/admin/requests`, `POST /fhir/admin/test` |
| HL7 admin | `GET /hl7/admin/messages`, `GET /hl7/admin/messages/{id}`, `GET /hl7/admin/metrics`, `GET/PUT /hl7/admin/config`, `GET /hl7/admin/status` |
| Worklist | `GET /worklist`, `GET/PUT /worklist/{id}`, `GET /worklist/station-aes` |
| OAuth | `GET/POST /oauth/providers`, `GET/PUT/DELETE /oauth/providers/{id}` |
| Notifications | `GET /notifications`, `GET /notifications/unread-count` |

## Flagged Gaps (not yet in API surface — must be raised with backend)

- Backup & restore of full system state (DB + files) — roadmap feature, not yet implemented (FR-R01-18); per-tenant DB backup via `pg_dump` exists (ADR-026, `scripts/backup_db.sh`)
- Global notification preferences administration (only per-user bell exists)
- External subscription billing (Stripe etc.) — explicitly out of scope for v3.0 (ADR-026); per-tenant usage metering (`tenant_usage_daily`) is the foundation billing will consume

Resolved 2026-08-06 (ADR-026): storage tiering / quota enforcement UI — storage
quota is enforced on upload (`QUOTA_EXCEEDED`, 90% breach notification), and the
per-tenant usage dashboard is fed by `tenant_usage_daily` metering plus the
tenant health endpoint (`GET /v2/tenants/health`).
