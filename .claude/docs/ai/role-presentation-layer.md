# Role-Based Presentation Layer — Codebase Ground Truth

> Verified against `frontend/src/` (current branch + `v3-dev`) and `backend/api/` on
> 2026-08-03. This is the source of truth for revising `docs/requirements/<role>/`
> packages: role-based UI routing, navigation, and functionality.

## Auth Model

- `AuthContext.tsx` exposes `{ user, isAuthenticated, hasPermission, signIn, signOut,
  activeTenant, setActiveTenant }`. `AuthUser` = `{ id, username, admin, role,
  permissions: string[], tenant_id? }`.
- `hasPermission(p)` = `user.admin || user.permissions.includes(p)`. Persisted to
  localStorage on sign-in (`permissions` JSON array, `admin`, `role`, `tenant_id`).
- `RequirePermission` component (`frontend/src/auth/RequirePermission.tsx`): renders
  children only when `hasPermission(permission)` is true, else `null`.
- `PermissionRoute` component (`frontend/src/auth/PermissionRoute.tsx`): route-level
  gate — unauthenticated → `/login`; authenticated without the required permission →
  `/` (Files); authenticated + permission → renders children. Applied to every admin
  route in `index.tsx` (same permission matrix as Sidebar.tsx) to close the
  deep-link gap.
- `ProtectedRoute`: gates routes on auth (userId or tempKey share-link). Share-link
  mode (`tempKey`) bypasses normal auth and hides the entire sidebar.
- Session tokens: access + refresh via `helpers.ts` (`setTokens`, `startRefreshTimer`).

## Navigation Model (Sidebar.tsx)

**Always visible to any authenticated user**: Files (`/`), Metrics (`/metrics`),
Account (`/account`), Notifications (bell), theme toggle, Logout.

**Admin submenu** is visible when `hasAnyAdminPermission()` — true if `user.admin`
OR any of `USER_READ | REPLICA_READ | TENANT_READ | ROLE_READ | LOG_READ |
SERVICE_KEY_READ | WORKLIST_READ | HL7_READ`. Items inside are individually gated:

| Sidebar item | Route | Requires permission |
|--------------|-------|---------------------|
| Replicas | `/replicas` | `REPLICA_READ` |
| Users | `/users` | `USER_READ` |
| Tenants | `/tenants` | `TENANT_READ` |
| Roles | `/roles` | `ROLE_READ` |
| Logs | `/logs` | `LOG_READ` |
| Worklist | `/worklist` | `WORKLIST_READ` |
| Service Keys | `/service-keys` | `SERVICE_KEY_READ` |
| Routing | `/routing` | `ROUTING_READ` |
| FHIR submenu | `/fhir/config`, `/fhir/monitoring`, `/fhir/docs` | `SYSTEM_ADMIN` |
| HL7 | `/hl7` | `HL7_READ` |
| DICOMweb | `/dicomweb` | `DICOMWEB_READ` |
| Integrations | `/integrations` | `SYSTEM_ADMIN` |

**Mobile**: `<lg` breakpoint collapses sidebar to a hamburger drawer; pagination
limit drops to 5.

## Frontend Routes (index.tsx)

`/login`, `/account`, `/replicas`, `/users`, `/roles`, `/tenants`, `/metrics`,
`/logs`, `/worklist`, `/service-keys`, `/routing`, `/fhir/config`,
`/fhir/monitoring`, `/fhir/docs`, `/hl7`, `/dicomweb`, `/integrations`,
`/patients/:id`, `/view/:key` (share view, unauthenticated), `/files/:id`
(viewer), `/` (Files/search), `*` (NotFound).

## Backend API Surface (routes.py — verified)

Auth/account: `/login`, `/auth/refresh`, `/auth/logout`, `/auth/revoke`,
`/oauth/login`, `/oauth/callback`, `/.well-known/openid-configuration`,
`/oauth/token`, `/change_password`, `/account/profile`.

Admin: `/users` (+ `/deactivate`, `/new_password`, `/role`), `/roles` (+`/{id}`,
`/{id}/users`, `/permissions`), `/tenants` (+`/{id}`, `/{id}/stats`),
`/replicas`(+`/{id}`), `/routing`(+`/{id}`), `/api-keys`(+`/{id}`),
`/webhooks`(+`/{id}`, `/webhooks/test`), `/logs`(+`/event-types`, `/actors`),
`/metrics`, `/dashboard/metrics`, `/notifications`(+`/unread-count`, `/read-all`,
`/{id}`), `/oauth/providers`(+`/{id}`).

Files/clinical: `/patients/{id}`, `/files`(+`/{id}`, `/{id}/changes`,
`/{id}/share`, `/{id}/shares`, `/{id}/data`, `/{id}/thumbnail`), `/files/upload`,
`/files/download.zip`, `/files/download.csv`, `/files/download_token`.

Integrations: `/dicomweb/studies` (+ series/instance drill-down, `/wado`),
`/dicomweb/admin`(+`/metrics`), `/fhir/metadata`, `/fhir/Patient`,
`/fhir/ImagingStudy`, `/fhir/DocumentReference`, `/fhir/admin/config|clients|metrics|requests|test`,
`/hl7`, `/hl7/admin/messages`(+`/{id}`), `/hl7/admin/metrics|config|status`.

Worklist: `/worklist`, `/worklist/{id}`, `/worklist/station-aes`.
Realtime: `/ws_token`, WebSocket `/ws` (LISTEN/NOTIFY push: notifications,
annotation sync).

## Permission Catalog (backend/api/permissions.py — 34 slugs)

`FILE_READ, FILE_WRITE, FILE_DELETE, PATIENT_READ, PATIENT_WRITE, STUDY_READ,
STUDY_WRITE, USER_READ, USER_WRITE, USER_DELETE, USER_ADMIN, REPLICA_READ,
REPLICA_WRITE, REPLICA_DELETE, LOG_READ, TENANT_READ, TENANT_WRITE, TENANT_ADMIN,
ROLE_READ, ROLE_WRITE, ROLE_DELETE, SERVICE_KEY_READ, SERVICE_KEY_WRITE,
SERVICE_KEY_DELETE, WORKLIST_READ, WORKLIST_WRITE, DICOMWEB_READ, DICOMWEB_WRITE,
ROUTING_READ, ROUTING_WRITE, METRICS_READ, SYSTEM_ADMIN` (plus `EXAM_*` family in
R06/R07 package proposals — NOT in codebase).

**Not in codebase** (aspirational, mark GATED): `EXAM_READ/EXAM_WRITE`,
`ANALYTICS_READ`, `ANALYTICS_EXPORT`, `REPORT_BUILD`, `REPORT_SCHEDULE`,
`ALERT_MANAGE`, QA/incident permissions, billing permissions, nursing permissions,
registration/scheduling permissions, equipment permissions.

## Role → Presentation Reality (what each persona can actually see today)

| Role | Routes/navigation available in current codebase | Implemented functionality |
|------|------------------------------------------------|---------------------------|
| R01 Super Admin | All admin items + Files/Metrics/Account | All admin CRUD, RBAC, integrations config, logs, metrics, worklist |
| R02 Tenant Admin | Admin subset gated by their permissions (no Tenants provisioning) | Same screens, tenant-scoped; provisioning is R01-only |
| R03 Service Director | Metrics + Files (read); no analytics dashboards | `GET /metrics`, `/dashboard/metrics` only — KPIs/reporting GATED |
| R04 Service Coordinator | Worklist (admin item, WORKLIST_READ) | Worklist CRUD, calendar, batch ops — scheduling board GATED |
| R05 QI/QA Team | Files + Metrics (read); no QA tools | No QA-specific screens — QA dashboards/peer review GATED |
| R06 Technologist | Files + Worklist (if granted) | Study browser, viewer (QA via viewer), worklist — acquisition workflow GATED |
| R07 Technician | Same as R06 | Same; fluoroscopy/mammo-specific flows GATED |
| R08 Front Desk | Files (read) only | No registration/scheduling screens — GATED |
| R09 Cashier | Files (read) only | No billing screens — GATED |
| R10 Biomedical Engineer | Files (read) only | No equipment registry — GATED |
| R11 Nursing | Files (read) only | No nursing worklist — GATED |
| R12 Staff Radiologist | Files, Patient, Viewer, Metrics | Viewer, annotations, shares, audit, patient page — reporting GATED |
| R13 Resident | Files, Patient, Viewer | Same as R12 (no role distinction) — supervised flows GATED |
| R14 Referring Clinician | `/view/:key` share link (viewer only, no sidebar) | Share-link viewer, annotation viewing — report/order GATED |
| R15 External RIS | API only (HL7, DICOM MWL/MPPS, FHIR ServiceRequest) | `/worklist*`, `/hl7`, `/dicomweb*`, `/fhir/*` — full order cycle partial |
| R16 External EMR | API only (HL7 ADT/ORM/ORU, FHIR Patient) | `/fhir/Patient`, `/hl7` — demographics + results |
| R17 External PACS | API only (DICOM C-FIND/C-MOVE/C-STORE, DICOMweb) | `/dicomweb/studies*`, `/wado` — query/retrieve/store |
| R18 Teleradiologist | Same as R12 (remote) | Viewer/annotation — telerad-specific (offline packages, prelim routing) GATED |
| R19 Hospital Staff | Files (read) or share link | Viewer/study browser — limited-scope portal GATED |

## Skill-Convention Items to Enforce in Revision

- IDs zero-padded `FR-RXX-NN` / `NFR-RXX-NN` / `US-RXX-NN` / `AC-RXX-NN` / `M-RXX-NN`.
- Every FR/NFR → ≥1 AC in artifact 06; traceability matrix 07 covers all.
- Artifact 08 roadmap: `done` / `partial` / `missing` statuses per artifact + blocking
  deps + next-steps.
- Aspirational FRs (no codebase support) keep their text but get `GATED` in the
  traceability status and roadmap `Missing` sections with blocking dependency.
- README: API surface table must cite real endpoints from the table above; flagged
  gaps = the GATED list.
- `version` bump + CHANGELOG entry per package revision (SemVer).
