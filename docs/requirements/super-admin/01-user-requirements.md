# User Requirements — Super Admin (R01)

## Functional Requirements

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-R01-01 | The system SHALL allow the super admin to list, create, update, and delete tenants, with tenant provisioning creating the tenant database, admin user, and storage quota. | Must | `GET/POST /tenants`, `GET/PUT/DELETE /tenants/{id}`; provisioning creates a real alembic-migrated tenant DB, a registry admin user (`users.tenant = slug`, main DB), plan, and storage quota; status lifecycle provisioning/active/suspended/quarantined/decommissioned (ADR-026) |
| FR-R01-02 | The system SHALL allow the super admin to switch tenant context from a tenant switcher and scope all subsequent admin views to the selected tenant. | Must | Tenant switcher functional end-to-end: JWT `tenant` claim / `X-Tenant-ID` header resolution (admin override) with contextvar-routed tenant DB connections via `get_conn()` (ADR-026) |
| FR-R01-03 | The system SHALL allow the super admin to manage users: list, create, deactivate, reset passwords, and change roles. | Must | `GET/POST /users`, `POST /users/deactivate`, `POST /users/new_password`, `POST /users/role` |
| FR-R01-04 | The system SHALL allow the super admin to bulk-import users from CSV with validation report before commit. | Should | Existing `BulkImport.tsx` screen |
| FR-R01-05 | The system SHALL allow the super admin to manage RBAC roles: list, create, edit, delete, view role users, and assign fine-grained permissions from the permission catalog. | Must | `GET/POST /roles`, `GET/PUT/DELETE /roles/{id}`, `GET /roles/{id}/users`, `GET /permissions` |
| FR-R01-06 | The system SHALL allow the super admin to manage storage replicas: add, edit, delete, and view replication status. | Must | `GET/POST /replicas`, `GET/PUT/DELETE /replicas/{id}` |
| FR-R01-07 | The system SHALL allow the super admin to manage DICOM routing rules with a rule-condition builder (modality, AE title, destination). | Must | `GET/POST /routing`, `GET/PUT/DELETE /routing/{id}`; `RuleConditionBuilder.tsx` |
| FR-R01-08 | The system SHALL allow the super admin to manage service API keys: create, rotate, revoke, and see last-used metadata. | Must | `GET/POST /api-keys`, `GET/PUT/DELETE /api-keys/{id}` |
| FR-R01-09 | The system SHALL allow the super admin to manage integration webhooks: create, edit, delete, and send test deliveries. | Must | `GET/POST /webhooks`, `GET/PUT/DELETE /webhooks/{id}`, `POST /webhooks/test` |
| FR-R01-10 | The system SHALL allow the super admin to review audit logs with filters by event type, actor, resource, and date range, with event-type and actor facets. | Must | `GET /logs`, `GET /logs/event-types`, `GET /logs/actors` |
| FR-R01-11 | The system SHALL allow the super admin to view system metrics: platform, DICOM-web, HL7, and FHIR integration dashboards. | Must | `GET /metrics`, `GET /dashboard/metrics`, `/dicomweb/admin/metrics`, `/hl7/admin/metrics`, `/fhir/admin/metrics` |
| FR-R01-12 | The system SHALL allow the super admin to manage DICOMweb station AE titles (modality worklist stations). | Must | `GET/POST /dicomweb/admin` |
| FR-R01-13 | The system SHALL allow the super admin to configure FHIR: server config, OAuth clients, test requests, and review recent requests. | Must | `/fhir/admin/config`, `/fhir/admin/clients`, `/fhir/admin/test`, `/fhir/admin/requests` |
| FR-R01-14 | The system SHALL allow the super admin to configure HL7: connection config, status, message history, and per-message detail. | Must | `/hl7/admin/config`, `/hl7/admin/status`, `/hl7/admin/messages`, `/hl7/admin/messages/{id}` |
| FR-R01-15 | The system SHALL allow the super admin to manage OAuth/SSO providers: list, create, edit, delete, enable. | Must | `GET/POST /oauth/providers`, `GET/PUT/DELETE /oauth/providers/{id}` |
| FR-R01-16 | The system SHALL allow the super admin to receive in-app notifications for admin events (tenant provisioned, replica failure, integration outages) with unread-count badge. | Should | `GET /notifications`, `GET /notifications/unread-count` |
| FR-R01-17 | The system SHALL allow the super admin to view a global system health summary (aggregate of storage, integrations, DICOM, auth) on a dashboard. | Should | `GET /v2/dashboard/health` (METRICS_READ) — aggregates db, es, redis, storage, dicom_listener, ingestion_service, hl7, fhir, auth |
| FR-R01-18 | The system SHALL allow the super admin to trigger backup of the full system state (DB + files) and restore from backup. | Could | GAP: not implemented (Roadmap) — backlog |
| FR-R01-19 | The system SHALL log every super admin mutation (tenant, user, role, routing, key, webhook, integration) to the audit log with actor and timestamp. | Must | `AuditLog.log_event` exists; e.g. `tenant.provisioned` |
| FR-R01-20 | The system SHALL deny access to every admin endpoint without the corresponding permission (`Permission.*`), returning 403 for unauthorized actors. | Must | `@requires_permission` decorators |

## Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-R01-01 | Admin pages load within budget (LCP) | LCP ≤ 2.5s on desktop, 4G | Lighthouse CI / RUM |
| NFR-R01-02 | Admin list interactions respond within budget (INP) | INP ≤ 200ms | RUM / Lighthouse |
| NFR-R01-03 | Audit log query returns first page | ≤ 2s for 90th percentile on 1M rows | Synthetic probe with seeded volume |
| NFR-R01-04 | Users/roles/tenants list pagination | Server-side; page size 20–100; no full-table client payloads | Response size test |
| NFR-R01-05 | All admin mutations are audit-logged | 100% of mutating endpoints emit `AuditLog` entries | Audit coverage test |
| NFR-R01-06 | No PHI in URLs, logs, or analytics events | Zero PHI fields in client-side telemetry | Static scan + log inspection |
| NFR-R01-07 | All admin screens keyboard-operable | WCAG 2.1 AA | axe-core + manual keyboard pass |
| NFR-R01-08 | Admin UI accessible via screen reader | WCAG 2.1 AA (labels, landmarks, ARIA) | axe-core, RTL a11y tests |
| NFR-R01-09 | Tenant switch reflected app-wide | ≤ 1s from click to scoped view | Performance test |
| NFR-R01-10 | Integration test delivery (webhook) returns result | ≤ 5s with clear success/failure detail | `POST /webhooks/test` probe |
| NFR-R01-11 | System remains usable when ES is down | Admin search degrades gracefully, non-search admin functions unaffected | Failure-injection test |
| NFR-R01-12 | Concurrent admin sessions | Support ≥ 10 concurrent super-admin sessions | Load test |
| NFR-R01-13 | Session timeout for admin console | Idle timeout ≤ 30 min with re-auth prompt | Config test |
| NFR-R01-14 | Audit log retention | ≥ 1 year searchable; archive policy configurable | Storage policy test |

## Assumptions & Constraints

- **PHI**: R01 has full data access; HIPAA minimum necessary requires auditability of all R01 actions, not reduced access.
- **Integration contracts**: HL7 (ADT/ORM/ORU), FHIR (Patient, ImagingStudy, DocumentReference), DICOM (MWL/MPPS/C-STORE) — failure semantics per `02-workflow-maps.md`.
- **Device**: desktop-first admin console; no mobile requirement, but must be responsive at ≥ 1280px comfortably and usable at 1024px.
- **Offline**: admin console is online-only; must show clear error/retry states on connectivity loss.
- **Multi-tenant**: every admin view is tenant-scoped except super-admin-only views (tenants, global replicas, system health).
- **Search**: Elasticsearch may be absent in this environment — search must degrade gracefully (existing requirement in `docs/User-Stories.md:206`).
