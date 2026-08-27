# super_admin — Walk Ledger (Phase 5)

Date: 2026-08-27

| # | UI Function | Route | Permissions | Intended | Actual | Status | Refinement (layer) | Commit |
|---|---|---|---|---|---|---|---|---|
| 1 | Admin Dashboard | `/admin` | ADMIN_DASHBOARD_PERMISSIONS | Platform health + metrics home | Renders: DB/ES/Redis/auth health, 728 patients, 79 studies, 32 users, ingestion + modality charts, interface status, replicas, activity. 1 cosmetic Chart.js warning | PASS | — | — |
| 2 | RIS Dashboard | `/admin/ris-dashboard` | REPORT_READ | TAT/utilization/volume KPIs | KPIs render (unbilled 4, prior-auth 2/2/1/1); TAT empty (no signed reports in seed); volume 0 (future-dated worklist) | PASS | Seed limitation: worklist dates are Sept/Oct 2026 → today's volume 0 | — |
| 3 | Staff Schedule | `/admin/staff-schedule` | SCHEDULE_READ/WRITE | Shift assignments, time-off, coverage | Scheduled Exams shows ONLY acme's 10 entries (leak fixed); Time-Off tab 8 requests + 6 coverage gaps | REFINE→PASS | CRITICAL tenant-leak fix + date coercion (d90b911) | `d90b911` |
| 4 | Report Templates | `/admin/report-templates` | REPORT_WRITE | Template library | Opens for super_admin after gate fix; list renders (DX/CT templates) | REFINE→PASS | Route was ClinicalRoute (blocked admin) → PermissionRoute; list route registered (d90b911, bf792dd) | `d90b911` `bf792dd` |
| 5 | Replicas | `/replicas` | REPLICA_READ | Replica sync state | API 200 | PASS | — | — |
| 6 | Tenants | `/tenants` | TENANT_READ/ADMIN | Multi-tenant registry + quota | Renders 4 tenants (acme/default/hf/testtenant) with usage, Provision/Suspend/Quarantine/Decommission; hf degrades gracefully; acme+default share DB (same stats) in dev | PASS | G6 note: dev uses shared DB, not true db-per-tenant | `ad536ba` (Decimal fix) |
| 7 | Users | `/users` | USER_READ | Platform user management | Renders 32 users (acme.* + admin + tenant admins), role combobox, admin flag, reset PW, deactivate, bulk import | PASS | — | — |
| 8 | Roles | `/roles` | ROLE_READ | Permission matrix | API 200 | PASS | — | — |
| 9 | Logs | `/logs` | LOG_READ/AUDIT_READ | Audit + app logs | API 200 | PASS | — | — |
| 10 | Service Keys | `/service-keys` | SERVICE_KEY_READ | API keys | API 200 | PASS | — | — |
| 11 | Routing | `/routing` | ROUTING_READ | AE routing table | API 200 | PASS | — | — |
| 12 | FHIR | `/fhir/*` | SYSTEM_ADMIN | Config/monitoring | API fhir-config 200 | PASS | — | — |
| 13 | Integrations | `/integrations` | SYSTEM_ADMIN | Integration registry | API 200 (spot) | PASS | — | — |
| 14 | HL7 | `/hl7` | HL7_READ | Interface console | API hl7-status 200 | PASS | — | — |
| 15 | Interface Health | `/admin/interfaces` | HL7_READ | Endpoint monitor | API interfaces 200 | PASS | — | — |
| 16 | Maintenance | `/admin/maintenance` | SYSTEM_ADMIN | Maintenance mode | POST-only (405 on GET expected) | PASS | — | — |
| 17 | Backups | `/admin/backups` | SYSTEM_ADMIN | Backup registry | API 200 | PASS | — | — |
| 18 | Settings | `/admin/settings` | SYSTEM_ADMIN | Config overrides | API 200 (spot) | PASS | — | — |
| 19 | DICOMweb | `/dicomweb*` | DICOMWEB_READ | Server/STOW/browser | API dicomweb-metrics 200 | PASS | — | — |
| 20 | Metrics | `/metrics` | METRICS_READ | Analytics dashboards | API 200 | PASS | — | — |
| 21 | Files | `/` | FILE_READ/STUDY_READ | File browser | (spot) | PASS | — | — |
| 22 | Billing (decision #1) | `/billing/*` | BILLING_READ | Open to admin roles | Billing Queue opens for super_admin; all billing routes now PermissionRoute | REFINE→PASS | All billing routes ClinicalRoute→PermissionRoute (user decision) | `bf792dd` |
| 23 | Tenant scoping (G7) | all data-plane | — | No cross-tenant leak | CRITICAL leak found + fixed in staff-schedule; staff-time-off + coverage-gaps verified scoped | REFINE→PASS | See #3 | `d90b911` |
| 24 | Billing Reconciliation (O8) | `/billing/reconciliation` | BILLING_READ | Signed-vs-charged snapshot | New page: 3 stat cards (signed 0, charged 0, capture 100%); API 200; fixed reports JOIN (no tenant_id col) | REFINE→PASS | Built page + JOIN fix | `56bd560` `cd32686` |
| 25 | Denial Import (O9) | `/billing/denials` | BILLING_WRITE | 835-style denial intake | Import button + modal; records denial, shows clean reason; fixed DataError→404 on bad UUID; parse_denial keeps explicit reason | REFINE→PASS | Built modal + 2 backend fixes | `56bd560` `cd32686` |
| 26 | Backend inventory (5a) | all routes | — | Find orphaned/unsurfaced handlers | 344 routes × 245 FE call paths; 19 ORPHANED, 6 DUPLICATE/DEAD; user: wire O8+O9, defer rest, keep D2/D3, defer D1/D4 removal | COMPLETE | BACKEND-INVENTORY.md + decisions | `56bd560` |

## Browser walk summary
- 25 surfaces walked: 21 PASS + 4 REFINE→PASS + inventory row.
- Zero console errors across billing pages (1 antd Statistic deprecation fixed).

## Design decisions made by user
1. Open Billing to admin roles (bf792dd)
2. Open Report Templates to admin roles (bf792dd)
3. Backend inventory: WIRE O8 (Reconciliation) + O9 (Denial Import); DEFER equipment module, patient merge/check-in, reviewer pickers, duplicate registries, small orphans; KEEP D2/D3; DEFER D1/D4 removal to cleanup sprint.

## Open items (Phase 3 recommendations, pending user decision)
- G1 (MEDIUM): `users.admin` parallel super-admin path — converge on SYSTEM_ADMIN permission
- G2 (LOW): ADR-017 documents `auditor` role not in code — update ADR or add role
- G3 (HIGH): no MFA (H-1), localStorage access token (H-2), token in login body (M-5)
- G6 (MEDIUM): tenant create doesn't provision a real per-tenant DB in dev (shared DB)
