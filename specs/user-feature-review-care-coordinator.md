# user-feature-review: care_coordinator — Implementation Spec

Branch: `phase/user-feature-review-care-coordinator` · Source: `docs/user-feature-review/care-coordinator/03-handoff.md` + `04-design.md`

## Scope

| Item | Work | AC source |
|---|---|---|
| P0-1 | Grant read-only `WORKLIST_READ` to `MATRIX_B_COORD` + `MATRIX_B_PHYS`; migration 063; matrix tests; physician schedule verified | 03 P0-1 (1–5) |
| P1-1 | Grant read-only `FILE_READ` to `MATRIX_B_COORD` (Files dead end) | 03 P1-1 (1–3) |
| P0-2 | `GET /api/v2/orders` (ORDER_READ) + read-only Orders page `/orders` + Coordination sidebar section | 03 P0-2 (1–4) |
| P1-2 | care_coordinator lands on `/orders` (coordination workspace); other roles unchanged | 03 P1-2 (1–3) |
| P2-1 | Patient payload gains `reports`; Patient page Reports & Results card (REPORT_READ-gated) | 03 P2-1 (1–3) |
| P2-2 | ErrorDisplay hides Retry on permission failures, names the missing grant, offers home | 03 P2-2 (1–2) |

## Backend

### permissions.py
- `MATRIX_B_PHYS` += `WORKLIST_READ`, `FILE_READ` (comment mirrors the R13 rationale; the R13 comment already asserted physician holds FILE_READ — the matrix never granted it).
- `MATRIX_B_COORD` += `WORKLIST_READ`, `FILE_READ` (read-only only).

### Migration 063 (`063_add_coordination_read_grants.py`)
- Appends each grant with `permissions || '["X"]'::jsonb ... AND NOT permissions ? 'X'` — **targeted append**, preserves facility edits to other grants (unlike 062's whole-set restore).
- Downgrade no-op (data repair). Tests assert grants == matrix and no write tiers.

### db/orders.py (new)
- `Orders.list_for_coordinator()`: `visit_orders` LEFT JOIN patients (by MRN) + LATERAL latest worklist entry / exam / report per patient. Returns `patient_db_id` (numeric patients.id) for the patient route key.

### api/orders.py (new)
- `OrdersHandler.get` gated `ORDER_READ`; `_row_dict` serialization (date/time/uuid → str).

### routes.py
- `v2(Route('/orders', endpoint=OrdersHandler))` + import.

### db/patient.py
- `get_extra` gains `reports`: reports JOIN exams by `exams.patient_id = patients.patient_id` (MRN; guarded when the caller's patient row lacks it — exam-detail callers).

## Frontend

### navigator.ts
- `Workspace` union += `"coordination"`; `NON_ADMIN_WORKSPACES` += `"coordination"` (admin-scoped roles never land on/see it).
- `LANDING_STEPS` += `{ route: "/orders", workspace: "coordination", permissions: ["ORDER_READ"] }` (before the clinical step).
- `ROLE_WORKSPACE["care_coordinator"] = "coordination"` (was "clinical"). Physician/referring keep "clinical" → landing unchanged.

### Sidebar.tsx
- New `coordination` section, icon `ScheduleOutlined`, item Orders (`ORDER_READ`).
- `SECTION_OF_KEY["orders"] = "coordination"`.

### index.tsx
- Lazy `Orders`; route `/orders` with `ClinicalRoute permission="ORDER_READ"`.

### coordinator/Orders.tsx (new)
- Read-only coordination worklist: summary Alert ("N open · M waiting >24h · K reported today"), filters with aria ids (`#orders-status-filter` etc.), Table with derived status Tag (requested/scheduled/in progress/performed/reported/cancelled), age chip (>24h orange, >72h red), report link to `/reading/:examId`, row click → `/patients/{patient_db_id}`.
- Empty state: guidance + "Open Schedule Board" button.
- `derivedOrderStatus`/`ageDays` exported for tests.

### patient/Patient.tsx
- `Reports & Results` card (gated `hasPermission("REPORT_READ")`), status Tags mirroring reading-worklist colors, empty state "No reports yet".
- `api/patient.ts` `PatientSummary` += `reports`.

### common/ErrorDisplay.tsx
- Detects `/missing permission/i` → hides Retry (can never succeed), names the grant, `role="alert"`, "Go to home" button via `landingRouteFor(user)`.

## Tests
- `tests/test_orders_api.py` (new): ORDER_READ gate, payload shape, empty list.
- `tests/test_rbac_matrix.py`: care_coordinator + physician schedule/file read grants, no write tiers.
- `tests/test_migrations.py`: 063 exists, grants match matrix, read-only only.

## Verification (live, `test.care_coordinator` / `test.physician`)
- Worklist/files/orders all 200 with the fresh 15-grant token.
- Browser: landing `/orders`, sidebar Coordination+Schedule+Files, schedule board loads (care_coordinator AND physician), Files list loads, Reports card renders, Orders row renders + row-click, other roles' landings unchanged.
- `1700 passed` pytest · ruff clean · `tsc` + build green.

## Deviations / notes
- `FILE_READ` granted to physician too (P1-1 was scoped to care_coordinator; the R13 comment asserted physician holds it, and physician had the identical Files 403). Scope addition documented in 05.
- Tenant-selector 403 (`/v2/tenants`) is pre-existing, silently handled, invisible (selector renders only when >1 tenant) — out of scope.
- Orders write actions (ORDER_WRITE status updates, tabs drawer) deferred — read-only surface per design conflict #1.
