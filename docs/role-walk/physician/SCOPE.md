# physician — Intended Scope (Phase 1)
Date: 2026-08-28
Sources: navigator.ts, permissions.py (PHYSICIAN_PERMISSIONS = LEGACY_PHYSICIAN | MATRIX_B_PHYS), Sidebar.tsx, RBAC_matrix_spec.md §5 (Matrix B)
Skills invoked: iam-audit, hipaa-compliance

## Role Profile

| Field | Value |
|---|---|
| Role slug | `physician` |
| Workspace | `clinical` (from ROLE_WORKSPACE) |
| Scope class | clinical-scoped (`CLINICAL_SCOPED_ROLES`) |
| Landing route | `/reading` (REPORT_READ passes — reading worklist) |
| Grant set | LEGACY_PHYSICIAN ∪ MATRIX_B_PHYS (19 grants) |
| Excluded from | Admin console surfaces (DASHBOARD_STEP, adminOnly items) — but DICOMweb is NOT adminOnly and is reachable |
| Tenant model | acme.physician is tenant-scoped (seed_uat has `acme.pacs_admin`? No — need to check. Actually seed_uat doesn't list physician. Let me check) |
| Credential used | `acme.physician` / `Test@123456` (tenant-scoped, acme tenant) |
| Relevant skills | iam-audit, hipaa-compliance, pacs-workflow, dicom-web-query, fhir-developer-skill |

## Reachable Surfaces (sidebar-visible)

| # | Section | UI Function | Route | Gate (permissions) | Intended (one line) |
|---|---|---|---|---|---|
| 1 | — | Files | `/` | FILE_READ, STUDY_READ, VIEWER_READ | Browse/upload/view DICOM files |
| 2 | Reading | Reading Worklist | `/reading` | REPORT_READ | Clinical reading worklist — unread/reported exams |
| 3 | Reading | Teaching Library | `/teaching` | REPORT_READ | Curated teaching cases |
| 4 | Reading | Critical Results | `/critical` | REPORT_READ | Critical results monitoring |
| 5 | Acquisition | Modality Worklist | `/worklist` | WORKLIST_READ | DICOM modality worklist |
| 6 | Acquisition | Tracking Board | `/tracking` | WORKLIST_READ | Live exam tracking board |
| 7 | Acquisition | Schedule Board | `/schedule-board` | WORKLIST_READ, SCHEDULE_READ | Day schedule with capacity |
| 8 | Acquisition | Calendar | `/schedule` | SCHEDULE_READ | Resource calendar |
| 9 | Acquisition | Resources | `/schedule/resources` | SCHEDULE_READ | Resource definitions |
| 10 | Coordination | Orders | `/orders` | ORDER_READ | Order list |
| 11 | Coordination | Prior Auth | `/prior-auth` | PRIOR_AUTH_READ | Prior authorization management |
| 12 | Coordination | Reminders | `/reminders` | PRIOR_AUTH_READ | Reminder config/delivery log |
| 13 | Coordination | Care Plans | `/care-plans` | PATIENT_READ | Care plan board |
| 14 | Coordination | Communications | `/communications` | PATIENT_READ | Patient communication log |
| 15 | Admin | DICOMweb Server | `/dicomweb` | DICOMWEB_READ (legacy, not adminOnly) | DICOMweb server info/metrics |
| 16 | Admin | DICOMweb Store | `/dicomweb/store` | DICOMWEB_READ | STOW-RS upload |
| 17 | Admin | DICOMweb Study Browser | `/dicomweb/browser` | DICOMWEB_READ | Study search/series/instances |
| 18 | Front Desk | Today's Schedule | `/frontdesk/schedule` | SCHEDULE_READ | Today's visit schedule |
| 19 | Front Desk | Patient Search | (action) | PATIENT_READ | Global patient search overlay |

## Not reachable (by design — clinical-scoped, no admin surfaces)

| Surface | Route | Reason |
|---|---|---|
| Admin Dashboard | `/admin` | adminOnly; clinical-scoped role |
| RIS Dashboard | `/admin/ris-dashboard` | adminOnly |
| Staff Schedule | `/admin/staff-schedule` | adminOnly |
| Interface Health | `/admin/interfaces` | adminOnly + HL7_READ not held |
| Replicas, Users, Tenants, Roles, Logs, Service Keys, Routing, FHIR, Integrations, HL7, Maintenance, Backups, Settings | various | PermissionRoute gates — no admin perms (USER_READ, TENANT_READ, etc.) |
| QA Queue, Protocols, Incidents, Corrective Actions, Analytics | various | QA_READ not held |
| Billing (all) | /billing/* | BILLING_READ not held |
| Portal | /portal/* | PORTAL_READ not held |
| Report Templates | /admin/report-templates | REPORT_WRITE/REPORT_TEMPLATE_ADMIN not held |
| Metrics | /metrics | METRICS_READ/ANALYTICS_READ not held |

## Key observations (Phase 2 candidates)

1. **Front Desk visible**: physician holds SCHEDULE_READ + PATIENT_READ, which unlocks the "Today's Schedule" and "Patient Search" items in the Front Desk section. The navigator excludes frontdesk from clinical landing, but the sidebar section filter allows it for non-admin-scoped roles. This may be a gap — a clinical physician should not see front-desk nav.
2. **DICOMweb reachable**: physician holds DICOMWEB_READ via legacy grant. The DICOMweb submenu is not adminOnly (user decision 2026-08-27), so the DICOMweb console is reachable for physician. Whether a physician should operate the DICOMweb server/STOW/browser is a product question.
3. **Physician has EMR write power**: ENCOUNTER_WRITE, NOTE_SIGN, MED_ORDER_WRITE, ORDER_WRITE, CARE_PLAN_WRITE — this is the full clinical writer role. The spec Matrix B PHYS row matches.
4. **No REPORT_WRITE**: physician can read reports but NOT write/sign them. That's the radiologist's domain (spec Matrix A). Physician is a clinical reader and EMR writer.
5. **No REPORT_SIGN**: only radiologist/teleradiologist have this.