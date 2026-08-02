# Requirements Package — R02 Hospital IT / Tenant Admin

| Field | Value |
|-------|-------|
| **Version** | 1.2.1 |
| **Status** | draft |
| **Generated** | 2026-08-03 |
| **Changelog** | [CHANGELOG.md](CHANGELOG.md) |

## Codebase Alignment (verified 2026-08-03)

**Presentation layer**: tenant-scoped role-based subset of R01. See artifact 04
— "Role-Based Routing & Navigation": the Tenants/provisioning item is R01-only and
never renders; every other admin item is permission-gated in `Sidebar.tsx`; backend
rejects cross-tenant access (403).

**Implemented**: tenant-scoped users/roles/worklist/routing/service-keys/replicas/
logs/metrics/HL7/FHIR/DICOMweb admin + notifications; tenant storage usage via
`GET /tenants/{id}/stats`. **GATED**: dedicated usage/quota dashboard UI,
department/modality registry, backup/restore.

## Role Summary

**Persona**: Tenant-level IT administrator operating one hospital/department tenant within the QuantumPACS instance.
**Access tier**: Tenant-wide admin — `TENANT_READ/TENANT_WRITE/TENANT_ADMIN` plus tenant-scoped `USER_*`, `WORKLIST_*`, `ROUTING_*`, `SERVICE_KEY_*`, `REPLICA_*`, `LOG_READ`, `METRICS_READ`, integration admin permissions.
**Boundaries**: CANNOT manage other tenants, CANNOT provision tenants (R01), CANNOT change global/DICOM system configuration (R01).

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

- **R01 Super Admin** — provisions this tenant (tenant DB, quota, admin user); R02 operates inside it.
- **R04 Service Coordinator** — consumes worklist/station configuration managed by R02.
- **R06/R07 Technologist/Technician** — modality worklists configured by R02.
- **R15/R16/R17 External RIS/EMR/PACS** — tenant-scoped integration endpoints managed by R02.
- **R05 QI/QA** — reads tenant audit data; R02 ensures audit capture.
- **R03 Service Director** — consumes tenant metrics; R02 owns tenant infra SLOs.

## Grounding Sources

- Tenant scoping: `backend/api/tenant_middleware.py` (`X-Tenant-ID` header, `TenantConnectionPool`, 403 on cross-tenant access)
- Permissions: `backend/api/permissions.py` (`TENANT_READ/WRITE/ADMIN`, `WORKLIST_READ/WRITE`, `ROUTING_*`, `USER_*`, `SERVICE_KEY_*`, `REPLICA_*`, `LOG_READ`, `METRICS_READ`)
- API surface: `backend/api/routes.py` (users, worklist, worklist/station-aes, routing, api-keys, replicas, logs, metrics, hl7/fhir/dicomweb admin, notifications)
- Prior docs: `docs/User-Stories.md` (Epic E7), `docs/UX-Functionality.md` (§2.3), `docs/IMPLEMENTATION_PLAN-v3.md` (F2.5 tenant admin UI), `docs/PRD-v3.md`
- R01 package (same conventions): `docs/requirements/super-admin/`

## Tenant-Scoped API Surface (subset of R01, scoped via `X-Tenant-ID`)

| Area | Endpoints (all under `/api/v2`, tenant-scoped) |
|------|---------------------------------|
| Users | `GET/POST /users`, `POST /users/deactivate`, `POST /users/new_password`, `POST /users/role` |
| Worklist | `GET /worklist`, `GET/PUT /worklist/{id}`, `GET /worklist/station-aes` |
| Routing | `GET/POST /routing`, `GET/PUT/DELETE /routing/{id}` |
| Service keys | `GET/POST /api-keys`, `GET/PUT/DELETE /api-keys/{id}` |
| Replicas | `GET/POST /replicas`, `GET/PUT/DELETE /replicas/{id}` (tenant-scoped) |
| Logs | `GET /logs`, `GET /logs/event-types`, `GET /logs/actors` (tenant-scoped) |
| Metrics | `GET /metrics`, `GET /dashboard/metrics` (tenant-scoped) |
| HL7 | `GET /hl7/admin/messages`, `GET /hl7/admin/messages/{id}`, `GET /hl7/admin/metrics`, `GET/PUT /hl7/admin/config`, `GET /hl7/admin/status` |
| FHIR | `GET/PUT /fhir/admin/config`, `GET/POST /fhir/admin/clients`, `GET/PUT/DELETE /fhir/admin/clients/{id}`, `GET /fhir/admin/requests`, `POST /fhir/admin/test` |
| DICOMweb | `GET/POST /dicomweb/admin` (station AEs) |
| Notifications | `GET /notifications`, `GET /notifications/unread-count` |

## Flagged Gaps

- **Backup/restore (tenant scope)** — no UI/endpoint; roadmap feature (shared with R01).
- **Department / modality registry** — no dedicated department CRUD endpoint; modalities are implied by worklist station AEs. Confirm with backend before sprint commitment.
- **Tenant-scoped quota/usage dashboard** — provisioning accepts `storage_quota_bytes` but no tenant usage view exists; needs backend aggregate.
- **Super-admin boundary enforcement UI** — tenant admin must not see global items; needs explicit permission-driven menu (exists as pattern in `component-specs.md`).
