# 00 — Inventory: tenant_admin (what actually exists)

**Role:** `tenant_admin` — Matrix C, tenant-scoped platform operator (seeded `test.tenant_admin`, tenant=`default`). Lands on `/admin` Operations Dashboard (admin-scoped role). 32 grants.

## Reachable surfaces (walked live — 10)

| # | Route | Page | What works | Evidence |
|---|-------|------|------------|----------|
| 1 | `/admin` | Operations Dashboard | Health strip, KPIs (patients/studies/files/users/storage), Interfaces panel, replicas, recent activity | `10-admin.png` |
| 2 | `/users` | Users | List all users, Add user, Bulk Import, Reset password / Deactivate per row | `10-users.png` |
| 3 | `/tenants` | Tenants | Provision Tenant, per-tenant Edit / Usage / Suspend / Quarantine / Decommission, storage bar | `10-tenants.png`, `12-tenants.png` |
| 4 | `/roles` | Roles | Role list + Create/edit (ROLE_WRITE), membership modal | `10-roles.png` |
| 5 | `/logs` | Audit Log | Live audit stream, event chips, filters | `10-logs.png` |
| 6 | `/service-keys` | Service Keys | Generate/revoke (empty state present) | `10-service-keys.png` |
| 7 | `/replicas` | Replicas | Replica list + Add replica (REPLICA_WRITE) | `10-replicas.png` |
| 8 | `/` | Files | File search/upload (empty in dev — ES down) | `10-files.png` |
| 9 | `/metrics` | Metrics | Health + KPIs + charts (METRICS_READ) | `10-metrics.png` |
| 10 | `/account` | Account | Profile, role, tenant, raw permission list | `10-account.png` |

Notifications bell: renders, 0 unread in dev; prefs endpoint is FILE_READ-gated so the P1-1 prefs page is reachable.

## Denial probes (13 — all correctly bounced)

`/routing`, `/hl7`, `/dicomweb` (+store/browser), `/admin/maintenance`, `/admin/backups`, `/admin/settings`, `/fhir/*`, `/integrations`, `/reading`, `/exams`, `/qa/queue`, `/frontdesk/*`, `/portal` → all redirect to `/admin` (role-scope gates work; deep-link timing artifact on first probe run confirmed not a logout — isolated reruns land `/admin` with zero 4xx).

## Permission inventory (32)

```
AUDIT_READ BILLING_READ CDS_ADMIN CHART_READ FILE_READ FILE_WRITE
INTERFACE_ADMIN INTERFACE_MONITOR LOG_READ METERING_READ METRICS_READ
ORDER_READ PATIENT_READ REPLICA_READ REPLICA_WRITE REPORT_READ
REPORT_TEMPLATE_ADMIN RESULTS_READ ROLE_DELETE ROLE_READ ROLE_WRITE
SERVICE_KEY_DELETE SERVICE_KEY_READ SERVICE_KEY_WRITE STORAGE_ADMIN
STUDY_READ TENANT_ADMIN TENANT_READ USER_READ USER_WRITE VIEWER_READ
WORKLIST_READ
```

Notable: **holds** `INTERFACE_ADMIN`, `INTERFACE_MONITOR`, `STORAGE_ADMIN`, `METERING_READ`, `BILLING_READ`, `CDS_ADMIN`, `REPORT_TEMPLATE_ADMIN` — **lacks** `HL7_READ`, `ROUTING_READ`, `DICOMWEB_READ`, `SYSTEM_ADMIN`, any `NOTIFICATION_*`, any clinical-write grant.

## Live-verified behaviors

- Login + landing: ✅ `/admin` Operations Dashboard
- Users list: ✅ shows all users (no tenant column/filter)
- Tenants list: ✅ scoped to own tenant (`default`) — one card
- Usage drawer: ✅ opens with table (empty data in dev)
- Role membership modal: ✅ (P2-5 fix from super_admin review works here too)
- Maintenance/Backups/Settings nav items: ❌ hidden (SYSTEM_ADMIN) — correct
- Console: 0 page errors on all walked surfaces

## Evidence files

`evidence/` — `00-landing.png`, `10-*.png` (10 surfaces), `12-tenants.png`, `20-denied-*.png` (13), `30-interface-*.png`, `31-tenant-usage.png`, `32-usage-drawer.png`, `33-bell.png`, `walkthrough.log`.
