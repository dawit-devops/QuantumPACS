# super_admin — Walk Plan (Phase 4)

Date: 2026-08-27
Order: Sidebar order (Admin section first, then Metrics)

## Walk order
1. Admin Dashboard `/admin` — landing page, health/metrics tiles
2. RIS Dashboard `/admin/ris-dashboard` — TAT, utilization, volume
3. Staff Schedule `/admin/staff-schedule` — Scheduled Exams + Time Off & Coverage
4. Report Templates `/admin/report-templates` — template library
5. Replicas `/replicas` — replica sync state
6. Tenants `/tenants` — multi-tenant registry (CRUD, storage, quota)
7. Users `/users` — platform user management
8. Roles `/roles` — permission matrix
9. Logs `/logs` — audit + app log stream
10. Service Keys `/service-keys` — API keys
11. Routing `/routing` — AE title routing table
12. FHIR `/fhir/config`, `/fhir/monitoring`, `/fhir/docs` — SYSTEM_ADMIN
13. Integrations `/integrations` — SYSTEM_ADMIN
14. HL7 `/hl7` — interface console
15. Interface Health `/admin/interfaces` — endpoint monitor
16. Maintenance `/admin/maintenance` — SYSTEM_ADMIN
17. Backups `/admin/backups` — SYSTEM_ADMIN
18. Settings `/admin/settings` — SYSTEM_ADMIN
19. DICOMweb `/dicomweb`, `/dicomweb/store`, `/dicomweb/browser`
20. Metrics `/metrics` — analytics dashboards
21. Files `/` — file/study browser

## Execution
**Phase 5a**: Unsupervised backend walk — curl each endpoint, verify 2xx + tenant scoping
**Phase 5b**: Supervised browser walk — navigate each route, snapshot, interact, record