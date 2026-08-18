# 06 — E2E Report (tenant_admin)

Phase 4 of `user-feature-review tenant-admin` — Playwright verification of the
hand-off acceptance criteria against a **real backend** (seeded
`test.tenant_admin` / `Test@123456`, migration 061 applied live).

**Spec:** `frontend/e2e/tenant-admin.spec.ts` (5 tests, serial mode)
**Result:** **5/5 passed** · **10/10 under `--repeat-each=2`** · zero console
errors · zero failed network requests

---

## Pass/fail traceability

| Hand-off item | E2E test | ACs covered | Result |
|---|---|---|---|
| **P1-1** dead dashboard "Open" buttons | `P1-1: dashboard never offers an Open button for a route the role cannot open` | AC1 (render only when permission passes), AC2 (status line, no button), AC3 (`/replicas` still works), AC4 (no console error), AC5 (assertion) | ✅ |
| **P1-2** interface grants reconciled (direction a) | `P1-2: interface grants are real — HL7, Routing, DICOMweb reachable from the sidebar` | AC1 (grant direction applied), AC4 (every grant maps to a gate), AC5 (sidebar reflects reality) | ✅ |
| **P2-1** real tenant card counts | `P2-1: tenant card shows real user/study counts, never '?'` | AC1 (real counts), AC3 (`last_activity` when present), AC4 (never "? users") | ✅ |
| **P2-2** tenant-scoped user directory | `P2-2: users directory shows a tenant column and is tenant-scoped` | AC1 (tenant column), AC2 (backend scoping consistent), AC3 (filter to `default`), AC4 (super_admin unaffected — regression probe) | ✅ |
| **P2-3** Roles immutability hints | `P2-3: immutable built-in roles show a locked (disabled) Edit action` | AC1 (lock indicator), AC2 (disabled affordances), AC3 (super_admin unchanged — regression probe) | ✅ |
| **P2-4** notification defaults for admin roles | covered by backend tests + live prefs probe (regression script) | AC1 (all admin-scoped roles muted), AC2 (copy updated), AC3 (backend test) | ✅ |
| **P2-5** Files search-degraded state | covered by `test_files_search_degraded.py` (unit) + live probe | AC1 (distinguishable notice), AC2 (upload unaffected), AC3 (unit test) | ✅ |

---

## Evidence

### E2E spec (`tenant-admin.spec.ts`)

```
$ npx playwright test tenant-admin.spec.ts --repeat-each=2
  10 passed (serial, real backend)
```

Notable assertions:

- **P1-1** — locates the Interfaces panel FHIR row and asserts **zero** "Open"
  buttons (`expect(count).toBe(0)`); clicks HL7's Open and asserts the URL
  becomes `/hl7` (not a bounce back to `/admin`); clicks the Storage pill
  (`button[aria-label='Open Storage dashboard']`) and asserts `/replicas`.
- **P1-2** — sidebar `menuitem` role checks for HL7/Routing/DICOMweb; `/hl7`
  renders its Messages tab with no "Missing permission"; `/dicomweb` renders a
  non-empty body.
- **P2-1** — asserts `"? users"` / `"? studies"` never render, and the card
  text matches `/\d+ users/` (real counts, not the loading em-dash).
- **P2-2** — asserts the `Tenant` column header; API-check on
  `GET /api/v2/users?limit=50` returns **only** `tenant=default` rows for
  `test.tenant_admin`.
- **P2-3** — asserts **disabled** Edit for EMR Admin / PACS Administrator /
  Patient (immutable anchors, matched on the role-name cell to avoid the
  "View patient chart" false positive) and an **enabled** Edit for Cashier
  (facility-editable built-in).

### Regression probe (`evidence/regress-superadmin.cjs`)

`test.super_admin` re-walked every shared surface touched by this branch —
**the guard must never hide a legitimate affordance**:

| Check | Result |
|---|---|
| Login → `/admin` | ✅ |
| Dashboard interface Opens (all grants held → all render, none hidden) | ✅ 3/3 present |
| Open navigates off `/admin` (no bounce) | ✅ |
| Users Tenant column renders; cross-tenant admins show "—", scoped users show tenant name | ✅ `[—, hf, —]` |
| Roles immutable anchors show disabled Edit | ✅ 3 disabled |
| `/account/notifications` loads, 12 toggles render | ✅ |
| Console/page errors | ✅ none (only pre-existing antd v6 deprecation warnings) |

### Live smoke (`evidence/40–44-*.png`)

- `40-dashboard-fixed.png` — dashboard with FHIR Open absent, HL7/DICOM real
- `41-tenants-counts.png` — card shows "23 users / 17 studies / 20 files"
- `42-users-tenant.png` — Users table with Tenant column
- `43-roles-lock.png` — immutable anchors with disabled Edit
- `44-account-grouped.png` — Account page grouped permission families

---

## Definition of Done check

| DoD item | Status |
|---|---|
| Backend `pytest` passes (tenant scoping, grant-reconciliation, notification defaults, search-degraded tests) | ✅ 1680 passed · 4 xfailed |
| Frontend `tsc` + `npm run build` pass; ruff/prettier clean | ✅ |
| No schema change ships without an Alembic migration | ✅ grant-only migration **061** (059 pattern, idempotent, token bump) |
| Every new endpoint permission-gated and validated with `parse_body()` | ✅ no new endpoints (list enrichment + scoping on existing routes) |
| `scripts/dev.sh status` healthy; smoke-login walks Admin with zero dead "Open" buttons | ✅ live-verified |
| E2E covers dashboard dead-end fix (P1-1), tenant card counts (P2-1), users tenant filter (P2-2) | ✅ all three in spec |

## Known limitations

- P2-4/P2-5 are covered by backend unit tests + live probes rather than E2E
  (P2-4's default-muting is a DB-level default; P2-5's degraded branch needs
  ES down, which isn't reproducible on demand while ES is healthy in this env).
- The pre-existing `roles.spec.ts`/`a11y.spec.ts`/`navigation.spec.ts` login
  failures (admin/`pa55w0rd` vs this dev DB's random `superadmin_pass`) are an
  environmental credential mismatch unrelated to this branch (CI exports
  `E2E_ADMIN_PASS`).

## Verdict

**All hand-off items verified.** The tenant-admin workflow ships with zero dead
ends, real data on the Tenants page, a tenant-scoped user directory, honest
permission accounting (Account page groups + roadmap tags), and a clear
search-degraded state — with the interface grants reconciled so every listed
permission maps to a reachable surface.
