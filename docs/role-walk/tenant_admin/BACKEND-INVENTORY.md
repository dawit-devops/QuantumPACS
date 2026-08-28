# tenant_admin — Backend Inventory (Phase 5a)
Date: 2026-08-28 | Credential: test.tenant_admin (35 perms, tenant 'default') | Skills invoked: iam-audit, dicom-web-query

## Route coverage (tenant_admin scope; read endpoints curl-verified 200, write paths 403 as gated)
| # | Backend route (method) | Handler | Called by frontend? | Tenant-scoped? | Gate | Notes |
|---|---|---|---|---|---|---|
| 1 | /ris/report-templates (GET) | ReportTemplatesHandler | Yes (ris.ts) | yes | REPORT_TEMPLATE_ADMIN | 214 templates; publish/rollback/versions all 200 |
| 2 | /v2/dashboard/health (GET) | DashboardHealth | Yes (admin.ts) | yes | dashboard union | 200 |
| 3 | /v2/dashboard/metrics (GET) | DashboardMetrics | Yes (admin.ts) | yes | METRICS_READ/ANALYTICS_READ | 200 |
| 4 | /ris/dashboard/kpi (GET) | RisDashboardKPI | Yes (ris.ts) | yes | REPORT_READ | 200 |
| 5 | /replicas (GET) | ReplicasHandler | Yes (replicas.ts) | yes | REPLICA_READ | 200; POST/PUT/DELETE 403 (REPLICA_WRITE not granted to tenant_admin) |
| 6 | /users (GET/POST) | UsersHandler | Yes (users.ts) | yes | USER_READ/USER_WRITE | GET 200; POST needs CSRF; USER_WRITE granted |
| 7 | /tenants (GET) | TenantsHandler | Yes (tenants.ts) | yes | TENANT_READ | 200, no db_* fields; POST/DELETE 403 (platform-only) |
| 8 | /tenants/health (GET) | TenantHealthHandler | Yes (tenants.ts) | yes | METERING_READ | 200 |
| 9 | /tenants/{id}/usage (GET) | MeteringUsageHandler | Yes (tenants.ts) | yes | METERING_READ | 200 |
| 10 | /roles (GET/POST) | RolesHandler | Yes (roles.ts) | yes | ROLE_READ/ROLE_WRITE | 200; ROLE_DELETE granted |
| 11 | /logs (GET) | LogsHandler | Yes (logs.ts) | yes | LOG_READ/AUDIT_READ | 200; CSV + actors + event-types OK |
| 12 | /api-keys (GET/POST) | ApiKeysHandler | Yes (servicekeys.ts) | yes (H-3 tenant-bound) | SERVICE_KEY_READ/WRITE | **FIXED (migration 114)** created_by UUID→BIGINT; create/delete verified |
| 13 | /routing (GET) | RoutingHandler | Yes (routing.ts) | yes | ROUTING_READ | 200; writes 403 (no ROUTING_WRITE) |
| 14 | /hl7/admin/messages|config|metrics|status (GET) | Hl7AdminHandler etc. | Yes (hl7.ts) | yes | HL7_READ | 200; PUT config 403 (HL7_WRITE) |
| 15 | /ris/interfaces (GET) | RisInterfacesHandler | Yes (interfaces.ts) | yes | INTERFACE_MONITOR | 200 |
| 16 | /ris/interfaces/{id}/messages|metrics (GET) | (interface msg/metrics) | Yes | yes | INTERFACE_MONITOR | 200 |
| 17 | /ris/interfaces/exceptions (GET) | RisInterfaceExceptionsHandler | Yes | yes | INTERFACE_MONITOR | 200 |
| 18 | /ris/interfaces/exceptions/{id}/retry (POST) | RisInterfaceExceptionRetryHandler | Yes (interfaces.ts) | yes | **HL7_WRITE** (NOT INTERFACE_ADMIN) | 403 for tenant_admin — see F4; INTERFACE_ADMIN is monitor-only |
| 19 | /dicomweb/admin (GET) | DicomwebAdmin | Yes (dicomweb.ts) | yes | DICOMWEB_READ | 200 |
| 20 | /dicomweb/admin/metrics, /requests (GET) | admin metrics/requests | Yes | yes | DICOMWEB_READ | 200 |
| 21 | /dicomweb/studies (QIDO) | DICOMweb QIDO | Yes (dicomweb.ts) | yes | DICOMWEB_READ | 200, DICOM JSON |
| 22 | /dicomweb/studies/{uid}/series|instances (WADO) | WADO-RS | Yes (viewer) | yes | DICOMWEB_READ | viewer loads |
| 23 | /dicomweb/studies (POST STOW) | STOW | No (store page disabled) | — | DICOMWEB_WRITE | 403 for tenant_admin (not granted) |
| 24 | /ris/billing/queue (GET) | RisBillingQueueHandler | Yes (billing-ris.ts) | yes | BILLING_READ | 200 |
| 25 | /ris/billing/claims (GET) + /{id}/history | RisClaimsHandler | Yes | yes | BILLING_READ | 200 |
| 26 | /ris/billing/revenue (GET) | RisRevenueHandler | Yes | yes | BILLING_READ | **FIXED (billing.py:1212)** paid_amount; 200 now |
| 27 | /ris/billing/unbilled (GET) | RisUnbilledHandler | Yes | yes | BILLING_READ | 200 |
| 28 | /ris/billing/denials (GET) | RisDenialQueueHandler | Yes | yes | BILLING_READ | 200; import/rework 403 (BILLING_WRITE) |
| 29 | /ris/billing/fee-schedule + contracts (GET) | fee schedule/contracts | Yes | yes | BILLING_READ | 200; edits 403 |
| 30 | /ris/billing/reconciliation (GET) | RisReconciliationHandler | Yes | yes | BILLING_READ | 200 |
| 31 | /metrics (GET) | MetricsHandler | Yes (dashboard) | yes | METRICS_READ | 200 |
| 32 | /v2/oauth/providers (GET/POST/PUT/DELETE) | OAuthProvidersHandler | Yes but **page gated SYSTEM_ADMIN** | yes | TENANT_ADMIN | **ORPHANED surface** — backend grants, frontend `/integrations` gate blocks (see O1) |
| 33 | /usage (GET) | PlatformUsageHandler | ? (usage panel) | yes | METERING_READ | 200 (usage panel on /tenants) |

## ORPHANED (should surface)
| # | Route | Handler | Why surface | Recommendation | Decision |
|---|---|---|---|---|---|
| O1 | /v2/oauth/providers (GET/POST/PUT/DELETE) | OAuthProvidersHandler | tenant_admin holds TENANT_ADMIN (granted) and the backend returns 200, but the only UI that calls it (Integrations page, `frontend/src/integrations/Integrations.tsx:77`) is gated `SYSTEM_ADMIN` in `frontend/src/index.tsx:831-835`. A granted, tenant-scoped capability (OIDC provider CRUD + test-connection) has no reachable surface for the role that holds it. | Widen the `/integrations` route gate to `["SYSTEM_ADMIN","TENANT_ADMIN"]` AND the nav item (`frontend/src/common/Sidebar.tsx:587`), hiding the Webhooks tab (SYSTEM_ADMIN-gated backend) from non-SYSTEM_ADMIN. | FIXED (commit below) |
| O2 | STORAGE_ADMIN, CDS_ADMIN grants | — | `STORAGE_ADMIN` and `CDS_ADMIN` appear in tenant_admin's grant set but no route gates on either (`grep STORAGE_ADMIN/CDS_ADMIN backend/api/*.py` → only permissions.py). These are dead grants — nothing in the backend is unlocked by them. | Trim from MATRIX_C_TENANT_ADMIN or gate a real surface on them (storage usage/reporting, CDS rules admin). Dead grants violate least-privilege least-surface. | KEPT (recorded; decision: leave grants as-is) |

## INTERNAL (no UI by design)
- `/dicomweb/studies/{uid}/series/{sid}/instances/{iid}` WADO-RS frames/metadata, `/archive` ZIP — viewer/Weasis direct loads.
- `/oauth/login`, `/oauth/callback`, `/oauth/jwks`, `/oauth/token` — auth flow, not tenant_admin scope.
- `/fhir/*` — FHIR API (SYSTEM_ADMIN UI gate; FHIR is a service surface).
- `/hl7`, `/hl7/admin/*` message endpoints — called by the /hl7 console page.
- `/replicas/{id}`, `/logs/actors`, `/logs/event-types` — sub-resources of listed pages.
- `/qa/tech-metrics`, `/qa/reject-analysis`, `/qa/dose-tracking` — QA analytics, QA_ANALYTICS_READ (not granted to tenant_admin → 403; QA is technologist/QA lead scope).

## DEAD (removal/wiring candidates)
| # | Route | Handler | Why | Recommendation | Decision |
|---|---|---|---|---|---|
| D1 | (see O2) | — | STORAGE_ADMIN / CDS_ADMIN grants have zero gate sites — the permissions are dead in the backend for every role, not just tenant_admin. | Remove from grant sets (migration) or wire to a real surface. | PENDING |

## Notes
- CSRF double-submit applies to all POST/PUT/DELETE (header `X-CSRF-Token` + cookie) — curl checks used the cookie flow; this is expected behavior, not a bug.
- SPA routes (`/reading`, `/admin/...`, `/patients/...`) return 500 on the backend in dev because `./static/index.html` doesn't exist; frontend is served by Vite on :5173. Redirect/block verdicts are browser-walk (5b) items, not curl.
