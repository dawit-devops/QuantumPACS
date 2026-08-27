---
---
name: supervised-role-walk
description: |
  Supervised, interactive end-to-end role walkthrough for QuantumPACS/QuantumRAD —
  a reusable, step-by-step methodology that audits ONE inbuilt platform role
  (e.g. super_admin, radiologist, cashier) and refines it across the WHOLE stack.

  Phases:
    1. ROLE SELECT — pick an inbuilt platform role; enumerate intended scope from
       source of truth (navigator.ts, permissions.py, Sidebar.tsx).
    2. GAP ANALYSIS — diff the role's documented intent (ADRs / RBAC spec /
       docs/iam-audit.md) against the actual codebase.
    3. RECOMMEND — score each gap against industry best practice (iam-audit /
       multi-tenant-saas skills); discuss with the user; decide.
    4. PLAN THE WALK — lay out every UI function the role can reach with expected
       behavior.
    5. EXECUTE — (a) unsupervised backend/API walk **+ backend feature
       inventory** (find orphaned handlers that SHOULD be surfaced on the
       frontend), then (b) supervised interactive browser walk with the human
       user (chrome-devtools / playwright) **+ frontend feature inventory**
       (triage each page into needs-backend-wiring / omit-reduce / refine).
    6. USER GUIDE — generate a comprehensive, capability-complete ROLE-SPECIFIC
        user manual (docs/user-guides/{role}.md) from the walked surfaces.

  Every phase ends with a user DECISION GATE: no code change of any kind is made
  until the user has been presented the finding + the agent's recommendation and
  has chosen (fix / update docs / defer / reject / redesign).

  Each phase produces a committed document under docs/role-walk/{role}/; the user
  guide is a standalone deliverable.

  Triggers:
  - "per-role walk"
  - "role walk as <role>"
  - "walk through each frontend UI function for <role>"
  - "super_admin e2e role walk"
  - "refine <role> across front/back/route/api/db"
  - "interactive UAT walk for <role>"
  - "supervised role walk"
  - "role scope audit for <role>"
  - "backend feature inventory"
  - "frontend feature inventory"
  - "user manual for <role>"
  - "user guide for <role>"

metadata:
  author: quantumrad
  version: "2.3.0"
  changelog: |
    v2.3.0 — 2026-08-27:
    - Phase 6 (BACKEND INVENTORY) merged into Phase 5a (backend walk).
    - Phase 7 (FRONTEND INVENTORY) merged into Phase 5b (frontend walk).
    - Phase 8 renumbered to Phase 6 (USER GUIDE).
    - Decision gate now applies inline during the walk at each inventory finding.
    v2.2.0 — 2026-08-27:
    - Phase 6 (BACKEND INVENTORY): enumerate implemented backend handlers and
      find orphaned endpoints that should be surfaced on the frontend.
    - Phase 7 (FRONTEND INVENTORY): triage every frontend feature into
      (a) needs backend wiring, (b) better omitted/reduced, (c) needs refinement.
    - Phase 8 (USER GUIDE): capability-complete role-specific user manual
      (docs/user-guides/{role}.md) derived from the walked surfaces.
    - Strengthened DECISION GATE: the user is asked (with the agent's
      recommendation) BEFORE ANY CODE CHANGE, at every phase — not only Phase 3.
    v2.1.0 — 2026-08-27:
    - Added document TEMPLATES for every phase output; ROLE PROFILE CARD;
      explicit INTERACTION PROTOCOL (pause-vs-proceed, question tool, escalation);
      per-phase COMPLETION CRITERIA; SESSION STATE / resumption from LEDGER.md;
      multi-tenant SaaS emphasis (tenant-leak and per-tenant data-plane checks).
    v2.0.0 — 2026-08-27:
    - Restructured into the 5-phase methodology; Phase 2 compares ADR/docs vs code;
      Phase 3 wires iam-audit + multi-tenant-saas; Phase 5 splits unsupervised
      backend/API walk and supervised browser walk.
    v1.0.0 — 2026-08-27:
    - Initial release: interactive supervised role-walk with full-stack refinement.
  depends_on:
    - frontend/src/navigator.ts       # workspace → route → permission gate map
    - frontend/src/common/Sidebar.tsx # navigable surfaces per role
    - backend/api/permissions.py      # Permission enum + role grant source of truth
    - backend/api/routes.py           # ALL registered routes (Phase 5a inventory source)
    - backend/api/*.py                # handler classes (Phase 5a inventory source)
    - frontend/src/index.tsx          # ALL frontend routes (Phase 5b inventory source)
    - frontend/src/api/*.ts           # frontend→backend API call map (Phase 5b source)
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
do (iam-audit / multi-tenant-saas), exercise every UI function live in the browser
with the human user, inventory backend↔frontend coverage in both directions, and
produce a role-specific user manual. Fix any layer only after the user decides.

## When to Use

- User says "per-role walk", "role walk as X", "walk through each frontend UI
  function for X", "e2e super_admin walk", "refine X across front/back/route/api/db",
  "supervised role walk", "role scope audit for X", "backend feature inventory",
  "frontend feature inventory", "user manual for X".

## Core Principles

1. **Supervised, not autonomous.** The browser half of the walk is a checkpoint
   conversation: the agent drives, the user observes/steers.
2. **Decision gate before EVERY code change.** No change to any layer — frontend
   component, route gate, permission matrix, backend handler, API schema, DB
   migration, docs — is made until the user has seen the finding + the agent's
   recommendation and decided. Use the `question` tool with explicit options
   (FIX / UPDATE-DOCS / DEFER / REJECT / REDESIGN). This applies to ALL phases.
3. **Every layer is in scope.** Per UI function capture/refine: **design → role
   scope & permissions → route/gate → frontend component → backend handler → API
   contract → DB schema**.
4. **Source-of-truth first.** Resolve role scope from `navigator.ts` and
   `permissions.py` — never guess.
5. **Docs/ADR are the contract, code is the truth.** A divergence is a finding
   (fix the code, or update the ADR — decide with the user).
6. **Compact + commit early.** 402 budget errors end sessions. Commit after each
   logical group. Commit the docs/role-walk deliverable — it IS a deliverable.
7. **Facts over screenshots.** Use `take_snapshot` (a11y tree) for actions;
   `take_screenshot` only when visual layout is the question. Always `list_pages`
   first (browser restarts change page ids).

## ROLE PROFILE CARD (fill once per role; keep visible all session)

| Field | Value |
|---|---|
| Role slug | `super_admin` (example) |
| Workspace | `platform` (from ROLE_WORKSPACE) |
| Scope class | admin-scoped / clinical-scoped |
| Landing route | `/admin` (or the role's LANDING_STEPS first pass) |
| Grant set | permission set from permissions.py |
| Excluded from | surfaces the role cannot open (ClinicalRoute / NON_ADMIN_WORKSPACES) |
| Tenant model | platform owner vs tenant-bound vs clinical data-plane |
| Seeded login | `acme.<role>` / `Test@123456` |

## Walk Artifacts

One directory per role, committed as a deliverable:

```
docs/role-walk/{role}/
  SCOPE.md           ← Phase 1: intended scope (from source of truth)
  GAP-ANALYSIS.md    ← Phase 2: ADR/docs vs code discrepancies
  RECOMMENDATIONS.md ← Phase 3: best-practice scoring + proposed changes
  PLAN.md            ← Phase 4: walk plan (expected behavior per UI function)
  LEDGER.md          ← Phase 5: Expected/Actual/Refinement/Commit per function
  BACKEND-INVENTORY.md ← Phase 5a: orphaned/unsurfaced backend handlers
  FRONTEND-INVENTORY.md ← Phase 5b: frontend feature triage (wire/omit/refine)
  {function-slug}.md ← one design+refinement note per UI function (optional)
docs/user-guides/{role}.md ← Phase 6: capability-complete user manual
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
5. Fill the ROLE PROFILE CARD and write SCOPE.md.

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

## Not reachable (by design)
- {clinical/admin surfaces the role cannot open}
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
   - Route gates enforce what the docs say.
   - Tenant scoping applied on every data-plane call the role makes.
   - No dead/legacy bypass paths (`users.admin`, wildcard `*`).
3. Write GAP-ANALYSIS.md.

## GAP-ANALYSIS.md template
```markdown
| # | Surface | Documented (ADR/spec) | Actual (code) | Severity | Evidence (file:line) | Notes |
|---|---|---|---|---|---|---|
```
Severity: CRITICAL > HIGH > MEDIUM > LOW.

## Completion criteria
- [ ] Every SCOPE.md surface has a gap row (or explicit "no gap").
- [ ] Severity assigned; evidence cited with file:line.
- [ ] **Decision gate**: findings presented to user; user acknowledged (fix/defer/reject recorded).

---

# PHASE 3 — Best-Practice Recommendations (iam-audit / multi-tenant-saas)

## Steps
1. Load `~/.agents/skills/iam-audit/SKILL.md` — Mode 1 "Application authorization":
   least privilege, role isolation per tenant, centralized `can()` checks, admin
   separation, permission checks logged, role explosion / accretion / shadow admin.
2. Load `~/.agents/skills/multi-tenant-saas/SKILL.md` — tenant isolation:
   database-per-tenant (ADR-016) vs shared-schema pitfalls, tenant-aware middleware,
   per-tenant data-plane routing, cross-tenant read isolation (ADR-029).
3. For each gap write a recommendation row.
4. **Decision gate** (mandatory): present gap + recommendation per surface; ask the
   user for a decision (FIX / UPDATE-DOCS / DEFER / REJECT / REDESIGN) via the
   `question` tool. Do NOT apply security/permission/tenant changes without sign-off.

## RECOMMENDATIONS.md template
```markdown
| # | Gap | Best-practice principle | Recommended change (layer) | Effort | Priority | User decision |
|---|---|---|---|---|---|---|
```

## Completion criteria
- [ ] Every gap maps to a recommendation with a layer + priority.
- [ ] User decision recorded for each (FIX/UPDATE-DOCS/DEFER/REJECT/REDESIGN).
- [ ] Accepted changes queued as concrete tasks.

---

# PHASE 4 — Plan the Supervised Walk (wear the role's hat)

Write PLAN.md: the ordered list of UI functions the role will exercise, in
sidebar order, each with route + gate, intended behavior, exercise steps, expected
API calls (method + path + status), and acceptance.

## PLAN.md template
```markdown
| # | UI Function | Route | Gate | Intended | Steps | Expected API | Accept |
|---|---|---|---|---|---|---|---|
```

## Completion criteria
- [ ] Plan covers every SCOPE.md surface, in order.
- [ ] Expected API calls + status codes written per function.
- [ ] User approves the plan (or edits it).

---

# PHASE 5 — Execute the Walk (includes the backend & frontend inventories)

## 5a. Unsupervised backend/API walk + Backend Feature Inventory
1. Login `acme.<role>` / `Test@123456` → `POST /api/v2/login` with `{"tenant":"acme"}`.
2. For every endpoint the role's surfaces call, `curl` with the bearer token:
   - Expected 2xx for permitted routes; 403/404 for excluded ones.
   - Verify tenant scoping (no cross-tenant leak — critical for platform roles).
   - Verify response shape matches the frontend's expected DTO.
3. **Backend feature inventory** — find backend capabilities that exist (handlers
   + routes) but have no frontend UI:
   a. Enumerate ALL registered routes from `backend/api/routes.py` (method + path
      + handler class). This is the backend surface.
   b. For each route, determine if any frontend code calls it: grep
      `frontend/src/api/*.ts` and component files for the path. Watch for prefix
      mismatches (e.g. frontend `ris/report-templates` vs backend `/reports/templates`).
   c. Categorize uncalled routes:
      - **ORPHANED (should surface)**: production-intent handler in the role's
        scope with no UI reaching it → recommend a frontend surface (decision gate).
      - **INTERNAL**: service-to-service / DICOMweb / FHIR / share-key / health
        routes that legitimately have no UI → no action.
      - **DEAD**: handler + route exist but no caller anywhere (backend or
        frontend) → recommend removal or wiring (decision gate).
   d. Record results in BACKEND-INVENTORY.md (below). **Decision gate** per
      orphaned/dead item (wire / remove / defer).
4. Record endpoint walk results in LEDGER.md.

### BACKEND-INVENTORY.md template
```markdown
| # | Backend route (method) | Handler | Called by frontend? | Tenant-scoped? | Gate | Notes |
|---|---|---|---|---|---|---|
```
Plus a categorized list of ORPHANED / INTERNAL / DEAD routes with a recommendation
each and the user decision recorded.

## 5b. Supervised interactive browser walk + Frontend Feature Inventory
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
6. **Frontend feature inventory** — as you walk each page, triage it into one bucket:
   - **A — wire**: page renders but its primary data call 404s/500s/returns a
     shape the UI can't consume → needs backend wiring.
   - **B — omit/reduce**: duplicated surfaces (two list pages for the same data),
     near-empty pages duplicating a broader page, or dead nav targets.
   - **C — refine**: functional but with UX gaps (empty states, no loading,
     missing pagination, misaligned gates, stale copy) or data-quality issues
     (seeded placeholder rows showing to users).
   Record each in FRONTEND-INVENTORY.md. **Decision gate** per item
   (wire / omit / refine / defer / reject).
7. **Decision gate** — before ANY refinement, present the finding + recommended
   fix to the user; get their choice.
8. **Refine/fix** across layers as decided. Run gates: backend `pytest`+`ruff`
   from `backend/`; frontend `npx vitest run`+`tsc`+`prettier`.
9. **Commit** (logical groups). Update LEDGER.md row.

### FRONTEND-INVENTORY.md template
```markdown
# {role} — Frontend Inventory (Phase 5b)

## A. Needs backend wiring (UI exists, backend missing/incomplete)
| # | Page | Route | API calls | Missing/incomplete backend | Recommendation |
|---|---|---|---|---|---|

## B. Better omitted / reduced (feature adds noise, overlaps, or is unmaintained)
| # | Page | Route | Why reduce/omit | Recommendation |
|---|---|---|---|---|

## C. Needs refinement (works but has gaps)
| # | Page | Route | Gap (UX/perf/data) | Recommendation |
|---|---|---|---|---|
```

## LEDGER.md template
```markdown
| # | UI Function | Route | Permissions | Intended | Actual | Status | Refinement (layer) | Commit |
|---|---|---|---|---|---|---|---|---|
```
Status: PASS | REFINE | BLOCKED | DEFERRED (with reason).

## 5c. Interaction protocol (pause vs proceed)
- PAUSE for user sign-off before ANY code change (all layers, all phases).
- PROCEED without pausing for: read-only exploration, curl checks, snapshots,
  test runs, doc drafting (non-committed), commit-per-group housekeeping of
  already-approved changes.
- Escalation: if the user's steer conflicts with an ADR or audit finding, surface
  the conflict and recommend updating the ADR (docs are the contract).

---

# PHASE 6 — Role-Specific User Guide (capability-complete user manual)

## Purpose
Produce a comprehensive, role-specific user manual that documents EVERY capability
the role has (from SCOPE.md + walked LEDGER), how to operate each surface, and what
to expect — written for a human user of the app.

## Steps
1. Source: SCOPE.md (reachable surfaces), PLAN.md (intended behavior), LEDGER.md
   (actual behavior + fixes), FRONTEND-INVENTORY.md (what's wired/omitted/refined).
2. Write `docs/user-guides/{role}.md` following the template below. Cover every
   reachable surface; mark surfaces that are broken/pending with a status.
3. Include practical workflow walkthroughs ("how to X"), not just surface lists.
4. After the guide, ask the user whether any surface's documented behavior should
   be changed (that becomes a Phase 3/5 decision-gated refinement).

## USER-GUIDE template
```markdown
# {Role} User Guide — QuantumPACS
Version: {app version or commit} | Role: {role} | Applies to: {tenant model}

## 1. About this role
{What the role is, workspace, landing page, scope summary}

## 2. Signing in
{Login flow, tenant selection, session, password reset, security notes (MFA if any)}

## 3. Getting around
{Landing page + sidebar map: every section/route the role can reach, one line each}

## 4. Surface-by-surface guide
### 4.1 {Surface}  ({route})
- Purpose: ...
- How to: step-by-step
- Fields/controls: ...
- Status: {PASS / BETA / BROKEN-pending-fix}
- Notes: ...
(repeat for every surface)

## 5. Common workflows (walkthroughs)
### 5.1 {Workflow} — e.g. "Provision a new tenant"
{step-by-step from login to completion}

## 6. Permissions summary
{What the role can/cannot do at the permission level}

## 7. Troubleshooting & known limits
{Common errors, known limitations (ES offline, shared dev DB, etc.)}
```

## Completion criteria
- [ ] Guide covers every reachable surface from SCOPE.md.
- [ ] Every surface has a status (PASS/BETA/BROKEN).
- [ ] At least one practical workflow walkthrough per major workspace.
- [ ] Guide committed under docs/user-guides/.
```

---

# DECISION GATE PROTOCOL (applies to ALL phases)

Before ANY code/document change, run this loop:

1. **State the finding** — what diverges from intent, where (file:line), severity.
2. **State the recommendation** — the change you propose, at which layer(s), with
   the rationale (ADR, audit finding, or best-practice principle).
3. **Ask the user** — use the `question` tool with options:
   - FIX — apply the recommended change
   - UPDATE-DOCS — fix the ADR/spec instead of the code
   - REDESIGN — user wants a different approach (capture their direction)
   - DEFER — record as open item with priority
   - REJECT — leave as-is, record rationale
4. **Record the decision** in the phase doc / LEDGER.
5. Only after sign-off, make the change, run gates, and commit.

If multiple findings are related, batch them into ONE question call (up to the tool
limit) to reduce interruption; but each change still needs an explicit decision.

---

# SESSION STATE / RESUMPTION

- LEDGER.md is the single source of walk progress. To resume: read LEDGER.md, find
  the last row without a Commit, continue from there.
- If the session ended mid-phase: the phase's completion checkboxes + the last
  written doc tell you where to restart.
- Phase 5 inventories (backend in 5a, frontend in 5b) are resumable from their
  markdown (last categorized row).
- Phase 6 guide is resumable from the guide file (mark incomplete surfaces).
- Always re-login fresh (tokens expire; backend may have restarted).

---

# Backend / DB refinement gotchas (QuantumPACS)

- Migrations must be **new Alembic files** for schema changes; sync the dev DB via
  `sync_db()` self-heal or apply raw with care — do NOT blindly `alembic upgrade head`
  (drift; migration 112 already applied via raw ALTER).
- Use `backend/db/database.py` `Database` pool via `get_database().acquire()`.
- Response helpers `api/response.py` `ok()/created()/not_found()`; validation
  `api/validate.py` `parse_body()` with Pydantic v2 `api/schemas/`.
- pypika: `Field` has no `.desc()` (use `Order.desc`), no `.in_()` (use `.isin()`).
- Route ordering: static routes before parameterized (`{id}`) routes.
- asyncpg: pass `date`/`datetime` objects, not ISO strings, for date-typed columns.
- Restart `quantumpacs-backend.service` after backend edits and re-login for fresh token.
- Keep throwaway session files out of commits; commit the docs/role-walk deliverable.

# Chrome-devtools MCP conventions

- `list_pages` FIRST every action batch (page ids change on browser restart).
- Prefer `take_snapshot` over screenshots for navigating/interacting (uid targets).
- `wait_for` takes an ARRAY of texts: `wait_for(text=["..."])`, not a string.
- Log in per role: `acme.<role>` / `Test@123456`; the frontend sends `tenant: acme`
  from the tenant selector automatically. Admin roles land on `/admin`; clinical
  roles land on their own workspaces.
- Backend API walk uses `curl` with `Authorization: Bearer <token>` from
  `POST /api/v2/login` (NOT `/api/v2/auth/login` — wrong path; it 401s).

# Exit criteria

- SCOPE, GAP-ANALYSIS, RECOMMENDATIONS, PLAN, LEDGER, BACKEND-INVENTORY (from 5a),
  FRONTEND-INVENTORY (from 5b) docs exist and are current.
- Every enumerated UI function has a ledger row; every gap maps to a recommendation;
  every backend route and frontend page is inventoried.
- Each REFINE/BLOCKED/ORPHANED/WIRE-ITEM has a user decision recorded.
- Role-specific user guide written to docs/user-guides/{role}.md.
- All backend pytest + frontend vitest/tsc pass.
