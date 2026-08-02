# User Requirements — Hospital IT / Tenant Admin (R02)

## Functional Requirements

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-R02-01 | The system SHALL scope every R02 view and action to the active tenant; cross-tenant access SHALL be denied (403) with no data leakage. | Must | `X-Tenant-ID` + `can_access_tenant` (tenant_middleware.py) |
| FR-R02-02 | The system SHALL allow the tenant admin to manage tenant users: list, create, deactivate, reset passwords, change roles — restricted to the tenant. | Must | `GET/POST /users`, `/users/deactivate`, `/users/new_password`, `/users/role` |
| FR-R02-03 | The system SHALL allow the tenant admin to bulk-import tenant users from CSV with validation report. | Should | `BulkImport.tsx` (tenant-scoped) |
| FR-R02-04 | The system SHALL allow the tenant admin to manage modality worklists: view, create, edit, and complete worklist entries (station AEs). | Must | `GET/PUT /worklist`, `GET/PUT /worklist/{id}`, `GET /worklist/station-aes` |
| FR-R02-05 | The system SHALL allow the tenant admin to register and manage station AE titles for modalities (DR, CR, CT, MRI, etc.). | Must | `GET/POST /dicomweb/admin`, `GET /worklist/station-aes` |
| FR-R02-06 | The system SHALL allow the tenant admin to manage DICOM routing rules within the tenant (condition builder: modality, AE, keywords, destination). | Must | `GET/POST /routing`, `GET/PUT/DELETE /routing/{id}` |
| FR-R02-07 | The system SHALL allow the tenant admin to manage service API keys for tenant integrations. | Must | `GET/POST /api-keys`, `GET/PUT/DELETE /api-keys/{id}` |
| FR-R02-08 | The system SHALL allow the tenant admin to manage tenant-scoped storage replicas and view replication status. | Must | `GET/POST /replicas`, `GET/PUT/DELETE /replicas/{id}` |
| FR-R02-09 | The system SHALL allow the tenant admin to configure the HL7 interface for the tenant (config, status, message history, per-message detail). | Must | `/hl7/admin/config`, `/hl7/admin/status`, `/hl7/admin/messages`, `/hl7/admin/messages/{id}` |
| FR-R02-10 | The system SHALL allow the tenant admin to configure the FHIR server, OAuth clients, and run integration tests for the tenant. | Must | `/fhir/admin/config`, `/fhir/admin/clients`, `/fhir/admin/test`, `/fhir/admin/requests` |
| FR-R02-11 | The system SHALL allow the tenant admin to review tenant audit logs with event-type/actor/date filters. | Must | `GET /logs`, `GET /logs/event-types`, `GET /logs/actors` (tenant-scoped) |
| FR-R02-12 | The system SHALL allow the tenant admin to view tenant-scoped metrics (platform + integration dashboards). | Must | `GET /metrics`, `GET /dashboard/metrics` (tenant-scoped) |
| FR-R02-13 | The system SHALL allow the tenant admin to receive tenant notifications (replica failure, integration outage) with unread badge. | Should | `GET /notifications`, `GET /notifications/unread-count` |
| FR-R02-14 | The system SHALL NOT expose global/super-admin items (other tenants, global replicas, global RBAC) to the tenant admin UI. | Must | Permission-driven menu (component-specs.md pattern) |
| FR-R02-15 | The system SHALL allow the tenant admin to view tenant storage usage against the provisioned quota. | Should | GAP: usage dashboard endpoint needed |
| FR-R02-16 | The system SHALL log every R02 mutation to the tenant audit log with actor, action, resource, timestamp, request_id. | Must | `AuditLog.log_event` with tenant context |

## Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-R02-01 | Tenant admin pages load (LCP) | ≤ 2.5s p75 desktop 4G | Lighthouse CI / RUM |
| NFR-R02-02 | Admin interactions respond (INP) | ≤ 200ms p75 | RUM / Lighthouse |
| NFR-R02-03 | Cross-tenant access denied | 100% of cross-tenant attempts return 403 and are logged | API test matrix (2 tenants) |
| NFR-R02-04 | Tenant audit queries first page | ≤ 2s p90 (tenant data volume) | Synthetic probe |
| NFR-R02-05 | Worklist/station list freshness | ≤ 30s staleness | Synthetic probe |
| NFR-R02-06 | No PHI in URLs, logs, analytics | Zero PHI fields in telemetry | Static scan |
| NFR-R02-07 | WCAG 2.1 AA for all admin screens | Zero serious axe violations | axe-core |
| NFR-R02-08 | Tenant switch context retained | ≤ 1s scoped view load | Performance test |
| NFR-R02-09 | Tenant isolation under load | 10 concurrent tenant admins without cross-tenant data mixing | Load test |
| NFR-R02-10 | Session idle timeout | ≤ 30 min with re-auth | Config test |

## Assumptions & Constraints

- **Tenant scope is security-critical**: R02 requirements inherit NFR-R02-03 as the top invariant — one tenant's data must never appear in another tenant's view.
- **No tenant provisioning**: R02 cannot create tenants; that is R01-only. UI must hide/disable tenant CRUD for R02.
- **Integration contracts**: HL7/FHIR endpoints are tenant-scoped; secrets encrypted and shown once.
- **Devices**: desktop-first; responsive ≥ 1024px; mobile not required.
- **Offline**: admin console online-only with clear error/retry states.
- **Search**: ES may be absent — degrade gracefully.
