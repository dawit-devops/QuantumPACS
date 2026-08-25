# UI/UX Redesign TDD Plan — §2.10 Super Admin / Tenant Admin & §2.11 Nursing

Round 5 of the per-role implementation review of `docs/ui-ux-redesign-spec.md`
(follows Front Desk §2.1, Technologist §2.3, Radiologist/Resident §2.4-2.5,
Billing/Coder & Care Coordinator §2.6-2.7 rounds on `feature/ris-integration`).

## Audit method

Three parallel read-only audits (frontend / backend / platform-inheritance),
gaps refined through the platform-inheritance rule: when this branch merges to
`v3-dev` QuantumPACS and the integrated RIS ship as ONE platform, so anything
the merged platform already provides is inherited, not rebuilt. Special
attention this round: the two prior feature-review cycles
(`docs/user-feature-review/super-admin`, `-tenant-admin`) already shipped most
of §2.10 on merged branches, and migration 037 created the entire R11 nursing
DB substrate with zero API/UI consumers.

## Verdict summary

### §2.10 Super Admin / Tenant Admin (~90% INHERIT)

| # | Feature | Verdict |
|---|---------|---------|
| ADM-01 | Configurable dashboard | PARTIAL → AdminDashboard fixed-layout exists (`dashboard/AdminDashboard.tsx`); widget-registry/configurable layouts stay under the standing platform-ADR deferral (rounds 3-4) |
| ADM-02 | Users CRUD | PARTIAL → CRUD/role-assign/deactivate/bulk CSV import exist (`users/Users.tsx`, `BulkImport.tsx`); bulk activate/deactivate missing → **AD1** |
| ADM-03 | Roles CRUD + matrix editor | INHERIT-FULL (`roles/Roles.tsx`: grouped searchable permission checkboxes, membership modal, built-in tier immutability via authoritative `modifiable` field) |
| ADM-04 | Tenants mgmt | INHERIT-FULL (`tenants/Tenants.tsx`: provision/suspend/quarantine/decommission, health dots, usage drawer; "impersonate tenant admin" satisfied by the cross-tenant switcher + `can_access_tenant` admin bypass — no shadow impersonation mechanism) |
| ADM-05 | Metrics dashboard | INHERIT-FULL (`/metrics` METRICS_READ\|ANALYTICS_READ alias; trends on AdminDashboard) |
| ADM-06 | Audit logs | INHERIT-FULL (filters event/user/tenant/date, expandable JSON payload Logs.tsx, server-side export-all CSV from the super-admin review round) |
| ADM-07 | HL7 dashboard | INHERIT-FULL (`hl7/*` console + InterfaceDashboard exception queue with retry) |
| ADM-08 | DICOMweb admin | INHERIT-FULL (`dicomweb/DicomWebAdmin.tsx`: Endpoints / Search Parameters / Modalities / Metrics / Requests tabs) |
| ADM-09 | FHIR config & monitoring | INHERIT (FhirConfig/FhirMonitoring/FhirDocs, SYSTEM_ADMIN) |
| ADM-10 | Maintenance mode | INHERIT-FULL (toggle+reason+duration, 503 write-gate middleware, banner, audit) |
| ADM-11 | Backup/restore UI | INHERIT (registry + verify/download/restore-confirm; real pg_dump engine = documented infra deferral) |
| ADM-12 | System config editor | INHERIT (whitelisted keys, masked secrets, restart-required tags, audited writes) |
| ADM-13 | Notification preferences | INHERIT-FULL (prefs page + server-side fan-out gating, admin-scoped role defaults) |
| ADM-14 | Tenant usage history | PARTIAL → backend DONE (`MeteringUsageHandler` returns `usage_daily[]` + totals); frontend renders a table only, no trend charts → **AD3** |
| ADM-15 | API key rotation | INHERIT (`/service-keys`: create/revoke/expiry/last-used/one-time secret; rotation = revoke + reissue) |
| ADM-16 | SSO/OIDC config | INHERIT for P2 (Integrations.tsx OAuth provider CRUD incl. jwks_uri/auto-provision; test-connection + group-mapping → backlog) |
| ADM-17 | Storage quotas | PARTIAL → `storage_pct` already computed by `db/tenants.get_stats`; no 80/90/100 alerts, no audited quota override justification → **AD2** |

### §2.11 Nursing — 0% built; substrate 100% inherited

Migration 037 (R11 Nursing FR-R11-01..10) created `vitals`, `prep_checklists`,
`safety_confirmations`, `contrast_records`, `reaction_escalations`,
`sedation_records`, `recovery_records`, `mar_records` — none reachable: zero
API/db-layer/UI consumers. Grants `NURSING_READ/WRITE` exist in the catalog
but NO role holds them; the legacy v2 `nurse` slug was deleted by migration
052 (users remapped → care_coordinator). The kiosk consent flow
(`CheckIn.tsx` canvas signature → base64 PNG → `record_consent`) is the
proven capture pattern.

| # | Feature | Verdict |
|---|---------|---------|
| N-01 | Vitals entry (BP/HR/temp/SpO2/wt/ht, timestamped, exam-linked) | GAP → NS2/NS3 (`vitals` table ready; weight/height columns added in migration 100) |
| N-02 | Pre-procedure checklist (required items must be checked) | GAP → NS2/NS3 (`prep_checklists` items JSONB + confirmed_by/at ready; 5 spec'd default items seeded) |
| N-03 | Contrast consent form (signature capture, stored as document) | GAP → NS2/NS3 (new `contrast_consents` table — frontdesk `consent_documents` is visit-scoped file-attach tracking, wrong shape; kiosk signature UX reused) |
| N-04 | Nurse notes visible to technologist and radiologist | GAP → NS2/NS3 (new `exam_notes` table; visibility via approved any-of read gate) |

## Permission review (directive #4) — G3, RESOLVED with human approval

Current holdings: NURSING_READ/NURSING_WRITE held by NO role (dead grants
since 052). Two decisions were put to human review and approved this session:

1. **G3 (approved): add `NURSING_READ` + `NURSING_WRITE` to
   `MATRIX_B_COORD` (care_coordinator)** — formalizing migration 052's
   nurse→care_coordinator remap direction instead of recreating a standalone
   `nurse` role or widening MATRIX_A_TECH. Application mirrors migration 095:
   idempotent jsonb-append + `token_version` bump for role holders.
2. **Read visibility (approved): nursing-record GETs gate any-of
   `[NURSING_READ, EXAM_READ]`** so technologist/radiologist see vitals/
   checklist/notes through existing EXAM_READ (spec N-04) with zero further
   matrix edits and no re-minted tokens for those roles; all writes remain
   strictly NURSING_WRITE.

No other grants required: AD1 gates on USER_DELETE (super/pacs admins hold
it; matches the destructive single-user deactivate), AD2 on TENANT_WRITE,
AD3 consumes existing TENANT_READ/METERING_READ endpoints unchanged.

## Implementation slices (TDD, RED→GREEN, one commit each)

Endpoint conventions cloned from `api/encounters.py`; db module from
`db/encounters.py`; tests from the conftest fake-auth harness
(`tests/test_encounters.py`). Deliberate improvement over the encounters
pattern: timestamps are parsed by Pydantic (`datetime | None`) rather than
raw strings passed to `$::timestamptz` (garbage input there surfaces as a
500, not a 422).

### Admin
- **AD1 — ADM-02 bulk user ops**: `POST /users/batch-status`
  `{user_ids[≤200], target_status active|deactivated}` gated USER_DELETE;
  reuses `Users.deactivate()` per id (last-active-admin lockout intact) plus
  new `Users.activate()` primitive; self-deactivation rejected; one audited
  `user.batch_status_changed` event with per-id outcomes; partial failure
  reported per id without aborting. FE: Users.tsx rowSelection + bulk bar
  (Activate/Deactivate Popconfirm) keyed on USER_DELETE.
- **AD2 — ADM-17 quota alerts + audited override**: threshold rendering on
  `storage_pct` (≥80 warning Tag, ≥90 Alert, ≥100 error) on Tenants cards +
  AdminDashboard tenant panel; `PUT /tenants/{id}` gains optional
  `quota_justification`, required-by-contract when the quota changes, emitting
  `tenant.quota_changed` {old, new, justification}.
- **AD3 — ADM-14 usage history chart**: Usage Drawer gains a chart.js Line
  over `usage_daily` (api_calls / storage GB / active_users series toggles);
  table stays beneath.

### Nursing
- **NS1 — Substrate + G3**: permissions.py matrix change; migration
  `100_nursing_surfaces.py` (grant append + token bump; `vitals` += weight_kg/
  height_cm + tenant_id tag columns on the used 037 tables; new
  `contrast_consents` + `exam_notes` tables with tenant_id + indexes);
  `db/nursing.py` module.
- **NS2 — N-01..N-04 endpoints** (`api/nursing.py`):
  `GET|POST /exams/{exam_id}/vitals` (GET any-of [NURSING_READ, EXAM_READ];
  POST NURSING_WRITE; Pydantic physiological range validation),
  `GET|PUT /exams/{exam_id}/pre-procedure-checklist` (confirm rejected until
  every required item checked; defaults seeded on first GET),
  `GET|POST /exams/{exam_id}/consent` (base64 PNG cap ~200 KB; accepted or
  declined+reason), `GET|POST /exams/{exam_id}/nurse-notes` (≤4000 chars),
  `GET /nursing/prep-list` (today's exams LEFT JOIN checklist state — thin
  read over existing exam rows, not a second worklist model).
- **NS3 — ExamConsole NursingPanel**: Card under "Safety Checks (pre-contrast)"
  visible with NURSING_READ; Tabs Vitals | Checklist | Consent | Notes;
  writes behind RequirePermission('NURSING_WRITE'); signature canvas cloned
  from kiosk CheckIn; read-only console behavior untouched.
- **NS4 — /nursing prep list + navigation**: route `/nursing` (NURSING_READ),
  Sidebar Coordination item "Nursing Prep", `/exams`(+/:id) gates become
  any-of [EXAM_READ, NURSING_READ], LANDING_STEPS acquisition step gains
  NURSING_READ as fallback-only landing.

## Test strategy

Per spec §8 within the standing round convention: pytest async integration
per slice (conftest fake-auth harness), Vitest + RTL per surface with axe
serious-violations scans on new pages, tsc + ruff + prettier gates, FULL
backend/frontend suites before every commit, one commit per feature.
Playwright E2E critical paths (E7 multi-tenant isolation, E10 role-based
access), k6 load and visual regression remain deferred as in every prior
round (documented backlog).

## Deferred backlog

1. Configurable widget framework (platform ADR — unchanged since round 3).
2. Real backup/restore engine (pg_dump integration) — infra decision.
3. OIDC test-connection + group-to-role mapping (ADM-16 remainder, P2).
4. Settings diff-view (ADM-12 nicety).
5. Sedation/recovery/reaction/MAR surfaces (remaining 037 tables beyond
   spec §2.11 scope) + contrast administration logging UI.
