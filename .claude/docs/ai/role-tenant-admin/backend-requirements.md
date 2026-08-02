# Backend Requirements: R02 Hospital IT / Tenant Admin

## Context

The Tenant Admin operates **one** hospital/department tenant inside the
QuantumPACS instance. Everything is a tenant-scoped subset of R01 Super Admin —
the same screens, the same actions, but strictly limited to their own tenant.
They CANNOT manage other tenants, CANNOT provision tenants, and CANNOT change
global/DICOM system configuration. The frontend must enforce these boundaries
visually (hide global items entirely) **and** the backend must reject cross-tenant
access (the UI depends on that guarantee).

**Screens (tenant-scoped subsets of existing frontend screens)**: Users, Roles,
Worklist, Routing Rules, Service Keys, Replicas, Logs, Metrics, HL7 Admin, FHIR
Admin, DICOMweb Admin (station AEs), Notifications. Most map to existing feature
docs — see `users/`, `roles/`, `worklist/`, `routing-rules/`,
`service-keys/`, `replicas/`, `audit-logs/`, `metrics/`, `hl7-adt-orm/`,
`fhir-r4-api/`, `dicomweb/`, `notifications/`.

**Personas**: P4 (PACS Admin, tenant-scoped). **Access tier**: `TENANT_*` +
tenant-scoped `USER_*`, `WORKLIST_*`, `ROUTING_*`, `SERVICE_KEY_*`, `REPLICA_*`,
`LOG_READ`, `METRICS_READ`.

## Screens/Components

### Tenant-Scoped Admin Screens (same components as R01)

**Purpose**: Manage users, roles, worklist, routing, service keys, replicas,
logs, metrics, and integration configs for the tenant only.

**Data I need to display**:
- Users/roles/permission catalog — identical to R01 but only this tenant's data.
- Worklist entries, station AE titles, routing rules, API keys, replicas, logs,
  and metrics **scoped to the tenant** (no other-tenant rows must ever appear).
- Integration configs (HL7/FHIR/DICOMweb) for the tenant.

**Actions**: same CRUD actions as R01 within the tenant scope (create user,
assign role, manage worklist, configure routing, manage keys, view logs/metrics).

**States to handle**: loading/empty/error; one-time password display; quota
warnings on any tenant-scoped usage view.

**Business rules affecting UI**:
- The sidebar/menu must be permission-driven so global items (provision tenant,
  global config) never render for this role.
- Any action that would touch another tenant must be impossible in the UI and
  rejected by the backend (403).

### Worklist & Station Configuration

**Purpose**: Configure and maintain the tenant's modality worklist.

**Data I need**: worklist entries with statuses, station AE titles (the
authoritative list for the tenant), scheduling metadata.

**Actions**: create/edit/cancel worklist entries, mark performed, manage station
AE titles.

## Uncertainties
- [ ] No dedicated department/modality registry endpoint exists — modalities are
  implied by worklist station AEs. Confirm with backend before sprint
  commitment.
- [ ] Tenant-scoped quota/usage dashboard is missing — only provisioning accepts
  a quota. Is a tenant usage aggregate available?
- [ ] Backup/restore (tenant scope) is a roadmap item, not available.
- [ ] The "no global items" menu pattern is documented in component-specs but
  must be enforced end-to-end (frontend + backend).

## Questions for Backend
- Is there a tenant-scoped aggregate for storage usage/quota the tenant admin can
  view?
- For station AE management, is the list per-tenant or global, and who is
  allowed to add/remove entries?
- Should the tenant admin be able to create their own API keys, or is that
  restricted to R01?

## Discussion Log

_(pending backend review)_
