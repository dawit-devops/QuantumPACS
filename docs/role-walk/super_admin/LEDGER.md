# super_admin — Walk Ledger (Phase 5)

Date: 2026-08-27

| # | UI Function | Route | Permissions | Intended | Actual | Status | Refinement (layer) | Commit |
|---|---|---|---|---|---|---|---|---|
| 1 | Admin Dashboard | `/admin` | ADMIN_DASHBOARD_PERMISSIONS | Platform health + metrics home | API walk: health/admin-status 200 | PASS | — | — |
| 2 | RIS Dashboard | `/admin/ris-dashboard` | REPORT_READ | TAT/utilization/volume KPIs | API: ris-kpi 200 | PASS | — | — |
| 3 | Staff Schedule | `/admin/staff-schedule` | SCHEDULE_READ/WRITE | Shift assignments, time-off, coverage | API: staff-time-off 200, staff-schedule 200 (was 500 + CROSS-TENANT LEAK) | REFINE | **CRITICAL: DeptStaffScheduleHandler GET had no tenant filter (returned all tenants' worklist); POST trusted body.tenant_id. Fixed + date param coercion.** | `d90b911` |
| 4 | Report Templates | `/admin/report-templates` | REPORT_WRITE | Template library CRUD | API: GET /ris/report-templates was 404 | REFINE | **List route missing — registered ReportTemplatesHandler at /ris/report-templates** | `d90b911` |
| 5 | Replicas | `/replicas` | REPLICA_READ | Replica sync state | API: 200 | PASS | — | — |
| 6 | Tenants | `/tenants` | TENANT_READ/ADMIN | Multi-tenant registry + quota | API: 200 (was 500 Decimal — fixed earlier) | PASS | Decimal serialization fixed (ad536ba) | `ad536ba` |
| 7 | Users | `/users` | USER_READ | Platform user management | API: 200 | PASS | — | — |
| 8 | Roles | `/roles` | ROLE_READ | Permission matrix | API: 200 | PASS | — | — |
| 9 | Logs | `/logs` | LOG_READ/AUDIT_READ | Audit + app logs | API: 200 | PASS | — | — |
| 10 | Service Keys | `/service-keys` | SERVICE_KEY_READ | API keys | (pending browser) | — | — | — |
| 11 | Routing | `/routing` | ROUTING_READ | AE routing table | API: 200 | PASS | — | — |
| 12 | FHIR | `/fhir/*` | SYSTEM_ADMIN | FHIR config/monitoring | API: fhir-config 200 | PASS | — | — |
| 13 | Integrations | `/integrations` | SYSTEM_ADMIN | Integration registry | (pending browser) | — | — | — |
| 14 | HL7 | `/hl7` | HL7_READ | Interface console | API: hl7-status 200 | PASS | — | — |
| 15 | Interface Health | `/admin/interfaces` | HL7_READ | Endpoint monitor | API: interfaces 200 | PASS | — | — |
| 16 | Maintenance | `/admin/maintenance` | SYSTEM_ADMIN | Maintenance mode | API: POST-only (405 on GET — expected) | PASS | — | — |
| 17 | Backups | `/admin/backups` | SYSTEM_ADMIN | Backup registry | API: 200 | PASS | — | — |
| 18 | Settings | `/admin/settings` | SYSTEM_ADMIN | Config overrides | (pending browser) | — | — | — |
| 19 | DICOMweb | `/dicomweb*` | DICOMWEB_READ | Server/STOW/browser | API: dicomweb-metrics 200 | PASS | — | — |
| 20 | Metrics | `/metrics` | METRICS_READ | Analytics dashboards | API: 200 | PASS | — | — |
| 21 | Files | `/` | FILE_READ/STUDY_READ | File browser | (pending browser) | — | — | — |
| 22 | Tenant scoping (G7) | all data-plane | — | No cross-tenant leak | FOUND + FIXED in staff-schedule; others verified scoped | REFINE | See #3 | `d90b911` |

## Open items (Phase 3 recommendations, pending user decision)
- G1 (MEDIUM): `users.admin` parallel super-admin path — converge on SYSTEM_ADMIN permission
- G2 (LOW): ADR-017 documents `auditor` role not in code — update ADR or add role
- G3 (HIGH): no MFA (H-1), localStorage access token (H-2), token in login body (M-5)
- G6 (MEDIUM): tenant create doesn't provision a real per-tenant DB in dev (shared DB)

## Browser walk status (Phase 5b)
Not yet started — awaiting user to join the interactive session.
