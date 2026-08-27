---
---
name: supervised-role-walk
description: |
  Supervised, interactive end-to-end role walkthrough for QuantumPACS/QuantumRAD —
  a reusable, step-by-step methodology that audits ONE inbuilt platform role
  (e.g. super_admin, radiologist, cashier) and refines it across the WHOLE stack.

  The 5 phases:
    1. ROLE SELECT — pick an inbuilt platform role and enumerate its intended scope
       from source of truth (navigator.ts, permissions.py, Sidebar.tsx).
    2. GAP ANALYSIS — diff the role's documented intent (ADRs / RBAC spec /
       docs/iam-audit.md) against the actual codebase to surface discrepancies.
    3. RECOMMEND — score each gap against industry best practice from the
       iam-audit and multi-tenant-saas skills; discuss with the user; decide.
    4. PLAN THE WALK — wearing the role's hat, lay out every UI function the role
       can reach (route → gate → handler → API → DB) with expected behavior.
    5. EXECUTE — (a) UNSUPERVISED backend/API walk (curl every endpoint; verify
       authz, tenant scoping, response shapes), then (b) SUPERVISED interactive
       in-browser walk with the human user via the chrome-devtools (or playwright)
       MCP — navigate, interact, record expected vs actual, and make codebase
       adjustments at ANY layer based on the user↔agent interaction.

  Each phase produces a committed document under docs/role-walk/{role}/ and ends
  with commits for accepted refinements.

  Triggers:
  - "per-role walk"
  - "role walk as <role>"
  - "walk through each frontend UI function for <role>"
  - "super_admin e2e role walk"
  - "refine <role> across front/back/route/api/db"
  - "interactive UAT walk for <role>"
  - "supervised role walk"
  - "role scope audit for <role>"

metadata:
  author: quantumrad
  version: "2.1.0"
  changelog: |
    v2.1.0 — 2026-08-27:
    - Added document TEMPLATES for every phase output (SCOPE/GAP/RECOMMEND/PLAN/LEDGER).
    - Added ROLE PROFILE CARD (one-screen role summary for the walk session).
    - Made the INTERACTION PROTOCOL explicit: mandatory checkpoints, the
      `question` tool usage, disagree/escalate flow, and "pause vs proceed" rules.
    - Added per-phase COMPLETION CRITERIA so each phase ends on an unambiguous signal.
    - Added SESSION STATE section: how to resume an interrupted walk from LEDGER.md.
    - Multi-tenant SaaS emphasis for platform roles: tenant-leak checks and
      per-tenant data-plane verification are now explicit checklist items.
    v2.0.0 — 2026-08-27:
    - Restructured into the 5-phase methodology (select → gap analysis →
      recommend → plan → execute).
    - Phase 2 (gap analysis) now compares ADR/RBAC-spec/docs vs actual code.
    - Phase 3 (recommend) now explicitly wires the iam-audit and multi-tenant-saas
      skills for best-practice scoring of each gap.
    - Phase 5 (execute) now splits the walk into (a) unsupervised backend/API
      walk and (b) supervised interactive browser walk with the human user.
    - Added the interaction contract: checkpoints where the agent must pause and
      discuss with the user before making design/permission changes.
    v1.0.0 — 2026-08-27:
    - Initial release: interactive supervised role-walk for multi-tenant SaaS
      platform roles (super_admin default), with full-stack refinement.
  depends_on:
    - frontend/src/navigator.ts       # workspace → route → permission gate map
    - frontend/src/common/Sidebar.tsx # navigable surfaces per role
    - backend/api/permissions.py      # Permission enum + role grant source of truth
    - backend/seed_uat.py             # acme.<role> / Test@123456 seeded logins
    - docs/BROWSER_TEST_PLAN.md       # 131-point UAT checklist (role last section)
    - docs/iam-audit.md               # prior IAM audit findings (Phase 2 input)
    - docs/decisions/ADR-017-oauth-oidc-rbac-auth.md  # RBAC design intent
    - docs/decisions/ADR-016-database-per-tenant-multi-tenancy.md # tenant isolation intent
    - docs/decisions/ADR-026-tenant-data-plane-wiring.md, ADR-029-tenant-read-isolation-pool-separation.md
    - ~/.agents/skills/iam-audit/SKILL.md           # Phase 3 reference: IAM best practice
    - ~/.agents/skills/multi-tenant-saas/SKILL.md   # Phase 3 reference: tenant isolation best practice
---

# Supervised Role Walk (Interactive E2E + Full-Stack Refinement)

Audit and refine ONE inbuilt platform role end-to-end: what it is INTENDED to do
(docs/ADRs), what it ACTUALLY does (code), what industry practice says it SHOULD
do (iam-audit / multi-tenant-saas), then exercise every UI function live in the
browser with the human user and fix any layer that diverges.

## When to Use

- User says "per-role walk", "role walk as X", "walk through each frontend UI
  function for X", "e2e super_admin walk", "refine X across front/back/route/api/db",
  "supervised role walk", "role scope audit for X".

## Core Principles

1. **Supervised, not autonomous.** The browser half of the walk is a checkpoint
   conversation: the agent drives, the user observes/steers. Pause and discuss
   with the user before any non-trivial design, permission, or schema change.
2. **Every layer is in scope.** Per UI function capture/refine: **design → role
   scope & permissions → route/gate → frontend component → backend handler → API
   contract → DB schema**. Fixes touch whichever layer diverges from intent.
3. **Source-of-truth first.** Resolve role scope from `navigator.ts`
   (`ADMIN_SCOPED_ROLES`, `CLINICAL_SCOPED_ROLES`, `LANDING_STEPS`, `ROLE_WORKSPACE`)
   and `permissions.py` (`Permission`, role map) — never guess.
4. **Docs/ADR are the contract, code is the truth.** A divergence between an ADR
   and the code is a finding (fix the code, or update the ADR — decide with the user).
5. **Compact + commit early.** 402 budget errors end sessions. Commit after each
   logical group of functions. Commit the docs/role-walk deliverable — it IS a
   deliverable — but exclude throwaway artifacts.
6. **Facts over screenshots.** Use `take_snapshot` (a11y tree) for actions; use
   `take_screenshot` only when visual layout is the question. Always `list_pages`
   first (browser restarts change page ids).

## ROLE PROFILE CARD (fill once per role; keep visible all session)

| Field | Value |
|---|---|
| Role slug | `super_admin` |
| Workspace | `platform` (from ROLE_WORKSPACE) |
| Scope class | admin-scoped (`ADMIN_SCOPED_ROLES`) |
| Landing route | `/admin` (DASHBOARD_STEP for admin-scoped roles) |
| Grant set | ALL permissions (`SUPER_ADMIN_PERMISSIONS = {p.value for p in Permission}`), `admin: true` bypass, `SYSTEM_ADMIN` |
| Excluded from | clinical pages (`ClinicalRoute` excludedRoles) |
| Tenant model | platform owner: sees all tenants (TENANT_ADMIN/CROSS_TENANT_READ); data-plane tenant-scoped |
| Seeded login | `acme.super_admin` / `Test@123456` |

## Walk Artifacts

One directory per role, committed as a deliverable:

```
docs/role-walk/{role}/
  SCOPE.md           ← Phase 1: intended scope (from source of truth)
  GAP-ANALYSIS.md    ← Phase 2: ADR/docs vs code discrepancies
  RECOMMENDATIONS.md ← Phase 3: best-practice scoring + proposed changes
  PLAN.md            ← Phase 4: walk plan (expected behavior per UI function)
  LEDGER.md          ← Phase 5: Expected/Actual/Refinement/Commit per function
  {function-slug}.md ← one design+refinement note per UI function (optional)
```

---

# PHASE 1 — Role Selection & Scope Enumeration

## Steps
1. Pick an inbuilt platform role (default `super_admin`). List candidates from
   `backend/api/permissions.py` role map. Confirm the pick with the user
   (use the `question` tool when the user hasn't specified).
2. Read `frontend/src/navigator.ts`: `ADMIN_SCOPED_ROLES` / `CLINICAL_SCOPED_ROLES`,
   `ROLE_WORKSPACE[role]`, `LANDING_STEPS` + `DASHBOARD_STEP`, `ADMIN_DASHBOARD_PERMISSIONS`.
3. Read `backend/api/permissions.py`: the role's grant set and the `Permission` enum.
4. Read `frontend/src/common/Sidebar.tsx`: enumerate every nav item the role can
   see (filter by `permissions`, `adminOnly`).
5. Fill the ROLE PROFILE CARD and write SCOPE.md (template below).

## SCOPE.md template
```markdown
# {role} — Intended Scope (Phase 1)
Date: YYYY-MM-DD
Sources: navigator.ts, permissions.py, Sidebar.tsx (commits {hash})

## Role Profile
{table card}

## Reachable Surfaces
| # | Section | UI Function | Route | Gate (permissions) | Intended (one line) |
|---|---|---|---|---|---|
| 1 | Platform | Users | /users | USER_READ/WRITE/DELETE/ADMIN | List/search users, create, assign role+tenant, reset PW, deactivate |
| ... |

## Not reachable (by design)
- Clinical surfaces (/reading, /qa, /billing/queue, ...) — excluded via ClinicalRoute.
```

## Completion criteria
- [ ] Role profile card filled from source of truth.
- [ ] SCOPE.md lists every reachable route with gate + intended behavior.
- [ ] User confirmed the role selection.

---

# PHASE 2 — Gap Analysis (Documentation/ADR vs Codebase)

## Steps
1. Read the RBAC/identity design docs: ADR-017 (role model), ADR-016 + ADR-026 +
   ADR-029 (tenant scoping), `docs/iam-audit.md` (prior findings — re-check status),
   ADR-004 (research baseline).
2. Verify each documented claim in code:
   - Permission enum + role→permission map match the ADR.
   - Route gates (`PermissionRoute`/`ClinicalRoute`/`AdminConsoleRoute`,
     `@requires_permission`) enforce what the docs say.
   - Tenant scoping (`effective_tenant`, `X-Tenant-ID`, tenant pool) is applied on
     every data-plane call the role makes.
   - No dead/legacy bypass paths (`users.admin` boolean, wildcard `*`).
3. Write GAP-ANALYSIS.md (template below).

## GAP-ANALYSIS.md template
```markdown
# {role} — Gap Analysis (Phase 2)
Date: YYYY-MM-DD
Docs reviewed: ADR-017, ADR-016, ADR-026, ADR-029, ADR-004, docs/iam-audit.md

| # | Surface | Documented (ADR/spec) | Actual (code) | Severity | Evidence (file:line) | Notes |
|---|---|---|---|---|---|---|

Severity: CRITICAL (authz/tenant-leak/500) > HIGH (feature broken/wrong) >
MEDIUM (UI/UX, missing validation) > LOW (cosmetic, docs drift).
```

## Completion criteria
- [ ] Every SCOPE.md surface has a gap row (or explicit "no gap").
- [ ] Severity assigned; evidence cited with file:line.
- [ ] Present findings to user; get acknowledgement.

---

# PHASE 3 — Best-Practice Recommendations (iam-audit / multi-tenant-saas)

## Steps
1. Load `~/.agents/skills/iam-audit/SKILL.md` — Mode 1 "Application authorization":
   least privilege, role isolation per tenant, centralized `can()` checks, admin
   separation, permission checks logged, role explosion / accretion / shadow admin.
2. Load `~/.agents/skills/multi-tenant-saas/SKILL.md` — tenant isolation:
   database-per-tenant (ADR-016) vs shared-schema pitfalls, tenant-aware
   middleware, per-tenant data-plane routing, cross-tenant read isolation (ADR-029).
3. For each gap in GAP-ANALYSIS.md write a recommendation row.
4. **Interactive discussion**: present gap + recommendation per surface; ask the
   user for a decision (fix code / update docs / defer / reject). Use the
   `question` tool with options. Do NOT auto-apply security/permission/tenant
   changes without sign-off.

## RECOMMENDATIONS.md template
```markdown
# {role} — Recommendations (Phase 3)
Date: YYYY-MM-DD
Reference skills: iam-audit (Mode 1), multi-tenant-saas

| # | Gap | Best-practice principle | Recommended change (layer) | Effort | Priority | User decision |
|---|---|---|---|---|---|---|
```

## Completion criteria
- [ ] Every gap maps to a recommendation with a layer + priority.
- [ ] User has decided each: FIX / UPDATE-DOCS / DEFER / REJECT (recorded).
- [ ] Accepted changes are queued as concrete tasks.

---

# PHASE 4 — Plan the Supervised Walk (wear the role's hat)

Write PLAN.md: the ordered list of UI functions the role will exercise, in
sidebar order, each with route + gate, intended behavior ("what wearing the role
means operationally"), exercise steps, expected API calls (method + path + status),
and acceptance.

## PLAN.md template
```markdown
# {role} — Walk Plan (Phase 4)
Date: YYYY-MM-DD
Order: sidebar order of the role's workspace sections

## 1. {Function}  ({route})
- Gate: {permissions}
- Intended: {operational behavior wearing the role}
- Steps: {navigate → snapshot → interact...}
- Expected API: {GET /api/... → 200; POST /api/... → 201}
- Accept: {what PASS means}
```

## Completion criteria
- [ ] Plan covers every SCOPE.md surface, in order.
- [ ] Expected API calls + status codes written per function.
- [ ] User approves the plan (or edits it).

---

# PHASE 5 — Execute the Walk

## 5a. Unsupervised backend/API walk
Without the browser, verify the role's backend contract:
1. Login `acme.<role>` / `Test@123456` → `POST /api/v2/login` with `{"tenant":"acme"}`.
2. For every endpoint the role's surfaces call, `curl` with the bearer token:
   - Expected 2xx for permitted routes; 403/404 for excluded ones.
   - Verify tenant scoping (rows only from acme tenant; no cross-tenant leak —
     especially important for platform roles that CAN see all tenants: confirm
     data-plane reads stay within the requested tenant).
   - Verify response shape matches the frontend's expected DTO.
3. Record results in LEDGER.md (they feed 5b).

## 5b. Supervised interactive browser walk
For each function in PLAN.md order, live with the user via chrome-devtools
(or playwright) MCP:
1. **State** — `list_pages`; ensure one tab at the function's route.
2. **Discuss intent** — state the Intended row; confirm/redirect with the user
   before interacting on design-sensitive surfaces.
3. **Exercise** — `navigate_page` → `take_snapshot` → interact (`fill_form`,
   `click`, `hover`, `wait_for`). Watch `list_console_messages` +
   `list_network_requests` for 500s / failed API calls.
4. **Record actual** — rendered output, API statuses, console errors.
5. **User steers** — capture design/behavior change requests.
6. **Refine/fix** across layers as needed (frontend component, route gate,
   permission, backend handler, API schema, DB migration). Run gates: backend
   `pytest`+`ruff` from `backend/`; frontend `npx vitest run`+`tsc`+`prettier`.
7. **Commit** (logical groups). Update LEDGER.md row.

## LEDGER.md template
```markdown
# {role} — Walk Ledger (Phase 5)
Date: YYYY-MM-DD

| # | UI Function | Route | Permissions | Intended | Actual | Status | Refinement (layer) | Commit |
|---|---|---|---|---|---|---|---|---|

Status: PASS | REFINE | BLOCKED | DEFERRED (with reason)
```

## 5c. Interaction protocol (pause vs proceed)
PAUSE for user sign-off before:
- Changing any permission matrix / role grant (Phase 3 decisions).
- Changing tenant-isolation / data-plane scoping behavior.
- Adding or dropping a DB column (new Alembic migration).
- Redesigning a UI surface beyond a bug fix.
PROCEED without pausing for: 500 fixes, clear bugs, response-shape corrections,
commit-per-group housekeeping.

Escalation: if the user's steer conflicts with an ADR or an audit finding, surface
the conflict and recommend updating the ADR (docs are the contract).

## Session state / resumption
- LEDGER.md is the single source of walk progress. To resume: read LEDGER.md,
  find the last row without a Commit, and continue from that function.
- If the session ended mid-phase: the phase's incomplete checkbox list + the last
  written doc tell you where to restart.
- Always re-login fresh (tokens expire; backend may have restarted).

# Backend / DB refinement gotchas (QuantumPACS)

- Migrations must be **new Alembic files** for schema changes; sync the dev DB via
  `sync_db()` self-heal or apply raw with care — do NOT blindly `alembic upgrade head`
  (drift; migration 112 already applied via raw ALTER).
- Use `backend/db/database.py` `Database` pool via `get_database().acquire()`.
- Response helpers `api/response.py` `ok()/created()/not_found()`; validation
  `api/validate.py` `parse_body()` with Pydantic v2 `api/schemas/`.
- pypika: `Field` has no `.desc()` (use `Order.desc`), no `.in_()` (use `.isin()`).
- Restart `quantumpacs-backend.service` after backend edits and re-login for fresh token.
- Keep throwaway session files out of commits; commit the docs/role-walk deliverable.

# Chrome-devtools MCP conventions

- `list_pages` FIRST every action batch (page ids change on browser restart).
- Prefer `take_snapshot` over screenshots for navigating/interacting (uid targets).
- `wait_for` takes an ARRAY of texts: `wait_for(text=["..."])`, not a string.
- Log in per role: `acme.<role>` / `Test@123456`; the frontend sends `tenant: acme`
  from the tenant selector automatically. Admin roles land on `/admin`; clinical
  roles land on their own workspaces. For clinical-route tests use clinical-role
  logins, not super_admin.
- Backend API walk uses `curl` with `Authorization: Bearer <token>` from
  `POST /api/v2/login` (NOT `/api/v2/auth/login` — wrong path; it 401s).

# Exit criteria

- SCOPE.md, GAP-ANALYSIS.md, RECOMMENDATIONS.md, PLAN.md, LEDGER.md exist and are current.
- Every enumerated UI function has a ledger row (Intended/Actual/Status).
- Each REFINE/BLOCKED function has a fix + commit (or an explicit user decision not to fix).
- Role scope table is current with `navigator.ts` + `permissions.py`; gap rows map to a recommendation.
- All backend pytest + frontend vitest/tsc pass.
