# tenant_admin — Frontend Inventory (Phase 5b)
Date: 2026-08-28 | Credential: test.tenant_admin / Test@123456 via browser login | Skills invoked: iam-audit

## Browser-verified surfaces (Phase 5b walk, sidemenu → page order)
| # | UI Function | Route | Browser Verdict | Issues Found | Gate (frontend route) |
|---|---|---|---|---|---|
| 1 | Report Templates | /admin/report-templates | PASS | Versions dialog shows "No data" (template has no versions — empty state correct) | PermissionRoute + adminOnly |
| 2 | Dashboard | /admin | PASS | Health strip, KPI cards, replicas, activity, quick links all render | PermissionRoute + adminOnly (ADMIN_DASHBOARD_PERMISSIONS) |
| 3 | RIS Dashboard | /admin/ris-dashboard | PASS-AFTER-FIX | F5: Workload tab 500'd (fixed); Equipment tab graceful degradation (EQUIPMENT_READ not granted) | PermissionRoute + adminOnly (REPORT_READ) |
| 4 | Replicas | /replicas | PASS-AFTER-FIX | F6: Page crashed `id.slice is not a function` (fixed); 1 Master replica renders | PermissionRoute (REPLICA_READ) |
| 5 | Users | /users | PASS | List, role dropdown, reset/deactivate actions | PermissionRoute (USER_READ) |
| 6 | Tenants | /tenants | PASS | Tenant card, Edit/Usage/Suspend/Quarantine/Decommission buttons | PermissionRoute (TENANT_READ) |
| 7 | Roles | /roles | PASS | All built-in roles listed, edit buttons, user counts, pagination | PermissionRoute (ROLE_READ) |
| 8 | Logs | /logs | PASS | 87 events, event-type filters, date range, tenant filter, actor filter, live toggle, CSV export, pagination | PermissionRoute (LOG_READ, AUDIT_READ) |
| 9 | Service Keys | /service-keys | PASS-AFTER-FIX | F3: create/revoke verified end-to-end in browser | PermissionRoute (SERVICE_KEY_READ) |
| 10 | Routing | /routing | PASS | Empty state "No routing rules configured" | PermissionRoute (ROUTING_READ) |
| 11 | HL7 | /hl7 | PASS | 1108 messages, filters (type/status/patient/facility), tabs (Messages/Analytics/Configuration), pagination | PermissionRoute (HL7_READ) |
| 12 | Interface Health | /admin/interfaces | PASS | 2 interfaces, message metrics, latency, exception queue (50 awaiting retry, Retry buttons visible) | PermissionRoute + adminOnly (HL7_READ) |
| 13 | DICOMweb Server | /dicomweb | PASS | Server info, QIDO/WADO/STOW status, 6 tabs (Endpoints/Search/Metrics/Requests/Missing) | PermissionRoute (DICOMWEB_READ) |
| 14 | DICOMweb Store | /dicomweb/store | PASS (curl) | Upload button — 403 expected (no DICOMWEB_WRITE) | PermissionRoute (DICOMWEB_READ) |
| 15 | DICOMweb Study Browser | /dicomweb/browser | PASS (curl) | Search, expand, WADO-RS, archive, Weasis launch | PermissionRoute (DICOMWEB_READ) |
| 16 | Billing Queue | /billing/queue | PASS (curl) | Paginated queue, CPT suggestions, patient responsibility | PermissionRoute (BILLING_READ) |
| 17 | Claims | /billing/claims | PASS (curl) | Claim list, history drawer | PermissionRoute (BILLING_READ) |
| 18 | Revenue | /billing/revenue | PASS-AFTER-FIX | F2: fixed `charge_amount` → `paid_amount`; renders revenue cards + tables | PermissionRoute (BILLING_READ) |
| 19 | Unbilled Aging | /billing/unbilled | PASS (curl) | Aging report with grouping | PermissionRoute (BILLING_READ) |
| 20 | Denial Rework | /billing/denials | PASS (curl) | Denial list, history | PermissionRoute (BILLING_READ) |
| 21 | Fee Schedule | /billing/fee-schedule | PASS (curl) | Fee schedule list/search, payer contracts, comparison | PermissionRoute (BILLING_READ) |
| 22 | Reconciliation | /billing/reconciliation | PASS (curl) | Signed-vs-charged snapshot | PermissionRoute (BILLING_READ) |
| 23 | Metrics | /metrics | PASS (curl) | Totals, charts, system health | PermissionRoute (METRICS_READ, ANALYTICS_READ) |
| 24 | Integrations | /integrations | PASS-AFTER-FIX | O1: OAuth providers tab renders (0 providers), Webhooks tab hidden (SYSTEM_ADMIN only) | PermissionRoute [SYSTEM_ADMIN, TENANT_ADMIN] |

## Nav items visible in sidebar (tenant_admin)
| Nav Item | Path | Permission Gate | Visible? |
|---|---|---|---|
| Files | / | VIEWER_ROUTE_PERMISSIONS | Yes |
| Account | /account | None | Yes |
| Billing (submenu) | /billing/* | BILLING_READ | Yes |
| Report Templates | /admin/report-templates | REPORT_TEMPLATE_ADMIN | Yes |
| Dashboard | /admin | adminOnly | Yes |
| RIS Dashboard | /admin/ris-dashboard | adminOnly (REPORT_READ) | Yes |
| Replicas | /replicas | REPLICA_READ | Yes |
| Users | /users | USER_READ | Yes |
| Tenants | /tenants | TENANT_READ | Yes |
| Roles | /roles | ROLE_READ | Yes |
| Logs | /logs | LOG_READ | Yes |
| Service Keys | /service-keys | SERVICE_KEY_READ | Yes |
| Routing | /routing | ROUTING_READ | Yes |
| Integrations | /integrations | SYSTEM_ADMIN, TENANT_ADMIN | Yes (O1 fix) |
| HL7 | /hl7 | HL7_READ | Yes |
| Interface Health | /admin/interfaces | HL7_READ | Yes |
| DICOMweb (submenu) | /dicomweb/* | DICOMWEB_READ | Yes |
| Metrics | /metrics | METRICS_READ | Yes |

## Inaccessible surfaces (blocked for tenant_admin)
| Surface | Route | Gate | Reason |
|---|---|---|---|
| Maintenance | /admin/maintenance | SYSTEM_ADMIN | Not granted |
| Backups | /admin/backups | SYSTEM_ADMIN | Not granted |
| Settings | /admin/settings | SYSTEM_ADMIN | Not granted |
| FHIR Config | /fhir/config | SYSTEM_ADMIN | Not granted |
| FHIR Monitoring | /fhir/monitoring | SYSTEM_ADMIN | Not granted |
| FHIR Docs | /fhir/docs | SYSTEM_ADMIN | Not granted |
| Staff Schedule | /admin/staff-schedule | SCHEDULE_READ + excludedRoles | Clinical route excluded |
| All clinical routes | /patients, /reading, /worklist, /exams, /schedule, /orders, /qa/*, /frontdesk/*, /portal | ClinicalRoute excludedRoles | Redirect to /admin for admin-scoped roles |