---
name: role-walk
description: |
  Supervised, interactive end-to-end role walkthrough for QuantumPACS — audit and
  refine ONE inbuilt platform role (super_admin, radiologist, technologist, …)
  across the whole stack in 6 phases: (1) role scope from source of truth,
  (2) ADR/docs-vs-code gap analysis, (3) best-practice recommendations
  (iam-audit / multi-tenant-saas), (4) walk plan, (5) unsupervised backend/API
  walk + backend feature inventory, then supervised browser walk with the human
  user + frontend feature inventory, (6) role-specific user guide
  (docs/user-guides/{role}.md). Every code change is decision-gated
  (FIX/UPDATE-DOCS/DEFER/REJECT/REDESIGN) before it is made; accepted
  recommendations not fixed during the walk become separate feature work.
  Artifacts in docs/role-walk/{role}/: SCOPE, GAP-ANALYSIS, RECOMMENDATIONS,
  PLAN (carries walk results inline), BACKEND-INVENTORY, FRONTEND-INVENTORY.

  Roles are parameterized from BUILT_IN_ROLES (backend/api/permissions.py).
  Use this skill whenever the user mentions role walks, role audits, per-role
  UI/UX reviews, feature inventories, role user guides, or wearing a role's
  hat — even if they don't say "role walk" explicitly.

  Triggers:
  - "role walk as <role>" / "per-role walk" / "supervised role walk"
  - "walk through each frontend UI function for <role>"
  - "<role> e2e role walk" / "interactive UAT walk for <role>"
  - "refine <role> across front/back/route/api/db"
  - "role scope audit for <role>"
  - "backend feature inventory" / "frontend feature inventory"
  - "user guide for <role>" / "user manual for <role>"
  - "which skills apply to <role>" / "load skills for <role>" / "role skill map"
  - "user feature review and critic" / "user-feature-review <role>" (legacy alias)
  - "wear the test.user hat for <role>" / "review the UI/UX for <role>"
  - "walk through the <role> experience" / "critique the current UI for <role>"
  - "what would a <role> want that's missing?"

metadata:
  author: quantumrad
  version: "3.0.0"
  changelog: |
    v3.0.0 — 2026-08-28 (Claude Code port; supersedes user-feature-review v1.0.0):
    - Lineage: v1 user-feature-review (4-phase: walkthrough → ui-ux-pro-max design
      → fullstack-guardian implementation → playwright E2E, artifacts in
      docs/user-feature-review/{role}/) → v2.x supervised-role-walk (opencode,
      6-phase, docs/role-walk/{role}/) → v3 role-walk.
    - LEDGER.md removed: walk results fold into PLAN.md (Results columns + Findings
      & decisions section). Intentional divergence from opencode v2.4.0.
    - No state.json: resume from PLAN.md pending rows + git log of docs(walk) commits.
    - Credentials resolved at runtime: acme.<role> (seed_uat.py, tenant acme)
      preferred; test.<role> (seed_test_users.py) fallback and the only option for
      roles not seeded in the acme tenant. Login POST /api/v2/login.
    - ui-ux-pro-max design phase and the implementation phase removed — accepted
      recommendations become separate feature work; decision-gated fixes during the
      walk itself are still in scope.
    - ROLE & FEATURE SKILL MAP corrected to skills that actually exist;
      user-feature-review removed (deleted); file-fallback tier added for
      hipaa-compliance / multi-tenant-saas / rest-api-design / prd.
  depends_on:
    - frontend/src/navigator.ts        # workspace → route → permission gate map
    - frontend/src/common/Sidebar.tsx  # navigable surfaces per role
    - backend/api/permissions.py       # Permission enum + BUILT_IN_ROLES grant source
    - backend/api/routes.py            # ALL registered routes (Phase 5a inventory source)
    - frontend/src/index.tsx           # ALL frontend routes (Phase 5b inventory source)
    - frontend/src/api/*.ts            # frontend→backend API call map (Phase 5b source)
    - backend/seed_uat.py              # acme.<role> / Test@123456 (tenant acme) — preferred
    - backend/seed_test_users.py       # test.<role> / Test@123456 (platform-side) — fallback
    - docs/BROWSER_TEST_PLAN.md        # UAT checklist (role section at the end)
    - docs/iam-audit.md                # prior IAM audit findings (Phase 2 input)
    - docs/decisions/ADR-017-oauth-oidc-rbac-auth.md               # RBAC design intent
    - docs/decisions/ADR-016-database-per-tenant-multi-tenancy.md  # tenant isolation
    - docs/decisions/ADR-026-tenant-data-plane-wiring.md
    - docs/decisions/ADR-029-tenant-read-isolation-pool-separation.md
    - ~/.agents/skills/iam-audit/SKILL.md           # Phase 3 reference (read file if not skill-listed)
    - ~/.agents/skills/multi-tenant-saas/SKILL.md   # Phase 3 reference (read file if not skill-listed)
---

# Role Walk (Supervised E2E + Full-Stack Refinement)

Audit and refine ONE inbuilt platform role end-to-end: what it is INTENDED to do
(docs/ADRs), what it ACTUALLY does (code), what industry practice says it SHOULD
do (iam-audit / multi-tenant-saas); exercise every UI function live in the
browser with the human user; inventory backend↔frontend coverage in both
directions; produce a role-specific user manual. Fix any layer only after the
user decides.

## Invocation Map

| Trigger | Action |
|---------|--------|
| "role walk as \<role\>" (or any full-walk trigger) | Run the full 6-phase pipeline for that role |
| "wear the test.user hat for \<role\>", "review the UI/UX for \<role\>", "user feature review and critic" | Same full walk (legacy v1 aliases — credentials are resolved at runtime, not forced to test.*) |
| "backend feature inventory for \<role\>" | Jump to Phase 5a (route enumeration + orphan triage), then decision gate |
| "frontend feature inventory for \<role\>" | Jump to Phase 5b triage for existing PLAN.md rows (or plan first if none) |
| "user guide for \<role\>" / "user manual for \<role\>" | Run Phase 6 only (requires SCOPE.md + walk results to exist) |
| "role skill map for \<role\>" | Print the mapped skills (Role table) and load them |
| "resume" / "continue" | Resume from PLAN.md pending rows (see Resumption) |

**Rule:** Each phase writes its artifact to `docs/role-walk/{role}/` BEFORE the
next phase starts. Read prior artifacts — never rely on conversation memory
across phases.

## Core Principles

1. **Supervised, not autonomous.** The browser half of the walk is a checkpoint
   conversation: the agent drives, the user observes/steers.
2. **Decision gate before EVERY code change.** No change to any layer — frontend
   component, route gate, permission matrix, backend handler, API schema, DB
   migration, docs — is made until the user has seen the finding + recommendation
   and decided (AskUserQuestion: FIX / UPDATE-DOCS / DEFER / REJECT / REDESIGN).
   This applies to ALL phases.
3. **Every layer is in scope.** Per UI function capture/refine: design → role
   scope & permissions → route/gate → frontend component → backend handler →
   API contract → DB schema.
4. **Source-of-truth first.** Resolve role scope from `navigator.ts` and
   `permissions.py` — never guess.
5. **Docs/ADR are the contract, code is the truth.** A divergence is a finding
   (fix the code, or update the ADR — decide with the user).
6. **Compact + commit early.** Session budget can end abruptly (402s). Commit
   after each logical group. The `docs/role-walk` deliverable IS a deliverable —
   commit it (`docs(walk): {role} Phase N — …`).
7. **Facts over screenshots.** Use `take_snapshot` (a11y tree) for navigating and
   acting; screenshots only when visual layout is the question. Always
   `list_pages` first (browser restarts change page ids).

## ROLE PROFILE CARD (fill once per role; keep visible all session)

| Field | Value |
|---|---|
| Role slug | `super_admin` (example) |
| Workspace | `platform` (from ROLE_WORKSPACE) |
| Scope class | admin-scoped / clinical-scoped |
| Landing route | from LANDING_STEPS / DASHBOARD_STEP |
| Grant set | permission list from permissions.py |
| Excluded from | surfaces the role cannot open (ClinicalRoute / NON_ADMIN_WORKSPACES) |
| Tenant model | platform owner vs tenant-bound vs clinical data-plane |
| Credential used | filled at runtime (Credential Resolution) |
| Relevant skills | role-level skills from the Skill Map (load in Phase 1) |

## Credential Resolution (runtime)

Resolve the role's login at walk time; record the outcome in the PROFILE CARD
and the PLAN.md header.

1. **Try `acme.<role>` / `Test@123456` first** — the UAT convention created by
   `backend/seed_uat.py` (tenant `acme`, with demo patients/studies). Seeded
   roles: super_admin, cashier, technologist, radiologist, care_coordinator,
   receptionist, patient.
2. If that 401s/404s, **try `test.<role>` / `Test@123456`** — platform-side
   users from `backend/seed_test_users.py` (every BUILT_IN_ROLES slug; only
   `test.tenant_admin` is tenant-scoped). Roles outside seed_uat's list
   (resident, physician, teleradiologist, tenant_admin, pacs_admin, …) exist
   only as test.* — go straight there.
3. If both are missing, seed: `backend/venv/bin/python backend/seed_uat.py`
   (preferred — includes acme demo data) or `…/seed_test_users.py`.
4. Login endpoint: `POST /api/v2/login` (NOT `/api/v2/auth/login` — wrong path
   401s). The frontend sends `tenant: acme` from the tenant selector.
5. **Tenant-context skew:** test.* users are platform-side (tenant NULL), so
   tenant-scoped surfaces may show empty data and the user legitimately sees
   cross-tenant platform data — do not flag that as a leak. acme.* users give
   realistic tenant-scoped walks.
6. Re-login fresh after backend restarts (tokens expire; service restarts
   invalidate).

## Walk Artifacts

One directory per role, committed as a deliverable:

```
docs/role-walk/{role}/
  SCOPE.md              ← Phase 1: intended scope (from source of truth)
  GAP-ANALYSIS.md       ← Phase 2: ADR/docs vs code discrepancies
  RECOMMENDATIONS.md    ← Phase 3: best-practice scoring + proposed changes
  PLAN.md               ← Phases 4–5: walk plan AND results inline (see template)
  BACKEND-INVENTORY.md  ← Phase 5a: orphaned/unsurfaced backend handlers
  FRONTEND-INVENTORY.md ← Phase 5b: frontend feature triage (wire/omit/refine)
docs/user-guides/{role}.md ← Phase 6: capability-complete user manual
```

There is **no LEDGER.md and no state.json** in this pipeline. PLAN.md's walk
table IS the progress record: one row per surface, `Status` PENDING until
walked. Do not resurrect LEDGER.md because legacy walk dirs (radiologist,
super_admin) contain one — those predate v3.

---

# ROLE & FEATURE SKILL MAP (invoke recommended skills at the point of use)

Load the skills relevant to the role and to each feature/layer you touch —
BEFORE or WHILE working on that surface — so domain guidance is applied when
needed, not as a separate pass. Add a `Skills invoked: …` line to each phase doc.

**Three-tier loading:** (1) invoke via the `skill` tool by name; (2) if the
skill is not offered in this session, read its SKILL.md directly from
`~/.agents/skills/<name>/` (this is how `hipaa-compliance`, `multi-tenant-saas`,
`rest-api-design`, `prd` are reached — real files, not skill-tool-registered);
(3) if neither exists, proceed with its principles from context and note the
miss in the phase doc. `ui-ux-pro-max` does not exist in this environment —
design judgment comes from `frontend-design` / `web-design-guidelines` instead.

## Role → Skills (load in Phase 1; record in the PROFILE CARD)

| Role | Recommended skills |
|---|---|
| super_admin | iam-audit, multi-tenant-saas†, hipaa-compliance†, security-fastapi, postgres, documentation-writer |
| tenant_admin | iam-audit, multi-tenant-saas†, postgres |
| radiologist | cornerstone3d-viewer, dicom-web-query, pacs-workflow, pydicom, hipaa-compliance† |
| technologist | pacs-workflow, dicom-web-query, pydicom, hipaa-compliance† |
| physician / resident / referring_physician | pacs-workflow, dicom-web-query, fhir-developer-skill, hipaa-compliance† |
| care_coordinator | pacs-workflow, fullstack-guardian, hipaa-compliance† |
| receptionist / cashier | fullstack-guardian, hipaa-compliance† |
| patient | hipaa-compliance†, frontend-design |

† = file-fallback tier (read from `~/.agents/skills/<name>/SKILL.md`).

## Feature / Layer → Skills (load lazily in Phase 5 before touching that surface)

| Layer / concern | Recommended skills |
|---|---|
| Backend API handler / schema | python-backend, security-fastapi, rest-api-design†, python-testing-patterns |
| DB schema / migration / query | postgres, postgresql-table-design |
| Auth / RBAC / permissions / gates | iam-audit, security-fastapi |
| Multi-tenant isolation / provisioning | multi-tenant-saas† |
| PHI / compliance (any clinical or billing surface) | hipaa-compliance† |
| DICOM query / retrieve / worklists | dicom-web-query, pacs-workflow |
| DICOM file / pixel processing | pydicom |
| Viewer (Cornerstone3D) | cornerstone3d-viewer |
| FHIR endpoints / resources | fhir-developer-skill |
| Frontend component / UI / UX | antd, frontend-react-best-practices, frontend-design, web-design-guidelines |
| Frontend types / review | typescript-react-reviewer |
| Frontend tests | vitest, frontend-testing |
| E2E / browser automation | playwright-e2e-testing, e2e-testing-patterns, webapp-testing |
| Requirements / user stories | prd-to-spec, prd† |
| Docs / ADRs | documentation-and-adrs, documentation-writer |
| XSS / output encoding | xss-prevention |

## Invocation rules

1. Phase 1: load the role-level skills; record them in the PROFILE CARD.
2. Phase 5a/5b: for each surface exercised or refined, load the layer skills
   that match the layer(s) you will touch (antd before a UI change, postgres
   before a schema decision, hipaa-compliance before any clinical/billing
   surface). Load lazily — only what that surface needs.
3. Add a `Skills invoked: …` line to each phase doc where a skill influenced
   the work.
4. If a mapped skill is unavailable, proceed with its principles and note the
   miss in the phase doc.

---

# PHASE 1 — Role Selection & Scope Enumeration

## Steps
1. Pick an inbuilt role (from `BUILT_IN_ROLES` in `backend/api/permissions.py`).
   Confirm the pick with the user (AskUserQuestion) when not specified.
2. Read `frontend/src/navigator.ts`: `ADMIN_SCOPED_ROLES` / `CLINICAL_SCOPED_ROLES`,
   `ROLE_WORKSPACE[role]`, `LANDING_STEPS` + `DASHBOARD_STEP`,
   `ADMIN_DASHBOARD_PERMISSIONS`.
3. Read `backend/api/permissions.py`: the role's grant set and the `Permission` enum.
4. Read `frontend/src/common/Sidebar.tsx`: enumerate every nav item the role can
   see (filter by `permissions`, `adminOnly`).
5. Fill the ROLE PROFILE CARD and write `SCOPE.md`.
6. Load role-level skills (Skill Map); add `Skills invoked` to SCOPE.md.

## SCOPE.md template
```markdown
# {role} — Intended Scope (Phase 1)
Date: YYYY-MM-DD
Sources: navigator.ts, permissions.py, Sidebar.tsx (commits {hash})

## Role Profile
{ROLE PROFILE CARD table}

## Reachable Surfaces
| # | Section | UI Function | Route | Gate (permissions) | Intended (one line) |
|---|---|---|---|---|---|

## Not reachable (by design)
- {surfaces the role cannot open, with the reason}
```

## Completion criteria
- [ ] Role profile card filled from source of truth.
- [ ] SCOPE.md lists every reachable route with gate + intended behavior.
- [ ] User confirmed the role selection.

---

# PHASE 2 — Gap Analysis (Documentation/ADR vs Codebase)

## Steps
1. Read the design docs: ADR-017 (role model), ADR-016 + ADR-026 + ADR-029
   (tenant scoping), `docs/iam-audit.md` (prior findings — re-check status).
2. Verify each documented claim in code:
   - Permission enum + role→permission map match the ADR.
   - Route gates enforce what the docs say.
   - Tenant scoping applied on every data-plane call the role makes.
   - No dead/legacy bypass paths (`users.admin`, wildcard `*`).
3. Write `GAP-ANALYSIS.md`; run the decision gate on findings.

## GAP-ANALYSIS.md template
```markdown
| # | Surface | Documented (ADR/spec) | Actual (code) | Severity | Evidence (file:line) | Notes |
|---|---|---|---|---|---|---|
```
Severity: CRITICAL > HIGH > MEDIUM > LOW.

## Completion criteria
- [ ] Every SCOPE.md surface has a gap row (or explicit "no gap").
- [ ] Severity assigned; evidence cited with file:line.
- [ ] Decision gate: findings presented; user decision recorded.

---

# PHASE 3 — Best-Practice Recommendations (iam-audit / multi-tenant-saas)

## Steps
1. Load `iam-audit` (Mode 1 "Application authorization": least privilege, role
   isolation per tenant, centralized `can()` checks, admin separation, logged
   permission checks, role explosion / shadow admin) and `multi-tenant-saas`
   (database-per-tenant vs shared-schema pitfalls, tenant-aware middleware,
   per-tenant data-plane routing, cross-tenant read isolation) — via the skill
   tool or the `~/.agents/skills/` files.
2. For each gap write a recommendation row (principle → change → layer →
   effort → priority).
3. **Decision gate (mandatory):** present gap + recommendation per surface; get
   FIX / UPDATE-DOCS / DEFER / REJECT / REDESIGN per item. Do NOT apply
   security/permission/tenant changes without sign-off.
4. Accepted-but-not-fixed-now items become **separate feature work outside this
   skill** — record the decision + a pointer (commit/issue/backlog note) in the
   row; do not implement them here.

## RECOMMENDATIONS.md template
```markdown
| # | Gap | Best-practice principle | Recommended change (layer) | Effort | Priority | User decision |
|---|---|---|---|---|---|---|
```

## Completion criteria
- [ ] Every gap maps to a recommendation with a layer + priority.
- [ ] User decision recorded for each.
- [ ] Accepted changes either queued (outside skill) or queued for the walk.

---

# PHASE 4 — Plan the Supervised Walk (wear the role's hat)

Write `PLAN.md`: the ordered list of UI functions the role will exercise, in
sidebar order, each with route + gate, intended behavior, expected API calls,
and acceptance. **This same file records walk results in Phase 5** — that is
why its columns 7–10 start empty. Commit the all-PENDING PLAN.md before the
walk starts so the results diff stays clean and resumption works.

## PLAN.md template
```markdown
# {role} — Walk Plan & Results (Phases 4–5)
Date: YYYY-MM-DD | Credential used: {from Credential Resolution} | Baseline commit: {hash}

## Walk order (planned; sidebar order; one line of exercise detail each)
1. {Surface} `{route}` — {what to exercise: filters, pagination, primary actions, error paths}
2. …

## Walk table (Phase 4 fills cols 1–6 all PENDING; Phase 5 fills 7–10 in place)
| # | UI Function | Route | Gate | Intended | Expected API (method+path→status) | Status | Actual (vs intended) | Fix (layer) | Commit |
|---|---|---|---|---|---|---|---|---|---|

## Excluded routes (planned Phase 4; verified in 5a)
| Route | Expected | Actual | Verdict |
|---|---|---|---|

## Findings & decisions (cross-cutting; appended in ANY phase)
| # | Phase | Finding | Evidence (file:line) | Recommendation | Decision | Commit |
|---|---|---|---|---|---|---|
```

Status vocabulary: `PENDING → PASS | PASS-AFTER-FIX | REFINE | BLOCKED |
DEFERRED(reason)`.

Bookkeeping rules (these replace the old LEDGER):
- One row per surface is the single source of truth. Per-surface results, fixes,
  and their commits live in the walk table.
- Cross-cutting findings (security, tenant leaks, ADR drift, inventory items that
  became fixes) live in Findings & decisions, cross-referenced by walk-table `#`
  where applicable.
- Keep cells terse; long notes go to Findings & decisions or the inventory docs.
- `Skills invoked` is a per-phase doc line, not a table column.

## Completion criteria
- [ ] Plan covers every SCOPE.md surface, in sidebar order.
- [ ] Expected API calls + status codes written per function.
- [ ] PLAN.md committed with every Status = PENDING.
- [ ] User approves the plan (or edits it).

---

# PHASE 5 — Execute the Walk (inventories included)

## Interaction protocol (pause vs proceed)
- **PAUSE** for user sign-off before ANY code change (all layers, all phases) —
  the Decision Gate Protocol below.
- **PROCEED** without pausing for: read-only exploration, curl checks, snapshots,
  test runs, doc drafting (uncommitted), commit-per-group housekeeping of
  already-approved changes.

## 5a. Unsupervised backend/API walk + Backend Feature Inventory

1. Login via Credential Resolution; get a bearer token.
2. Load the layer skills for the endpoints you will walk (Skill Map).
3. For every Expected API cell in the walk table, `curl` with the token:
   - Expected 2xx for permitted routes; 403/404 for excluded ones.
   - Verify tenant scoping (no cross-tenant leak — critical for platform roles;
     mind the test.* platform-side skew).
   - Verify response shape matches the frontend's expected DTO.
   **Write each touched row's Status/Actual into PLAN.md immediately.**
4. Verify the Excluded routes table → fill Actual/Verdict.
5. **Backend feature inventory** — find backend capabilities with no frontend UI:
   a. Enumerate ALL registered routes from `backend/api/routes.py` (method +
      path + handler class).
   b. For each route, determine if any frontend code calls it: grep
      `frontend/src/api/*.ts` and component files for the path. Watch for
      prefix mismatches (e.g. frontend `ris/report-templates` vs backend
      `/reports/templates`).
   c. Categorize uncalled routes:
      - **ORPHANED (should surface)**: production-intent handler in the role's
        scope with no UI → recommend a frontend surface (decision gate).
      - **INTERNAL**: service-to-service / DICOMweb / FHIR / share-key / health
        routes that legitimately have no UI → no action.
      - **DEAD**: handler + route exist but no caller anywhere → recommend
        removal or wiring (decision gate).
   d. Record in BACKEND-INVENTORY.md. Decision gate per ORPHANED/DEAD item
      (batch related items into one AskUserQuestion).
6. Commit: `docs(walk): {role} Phase 5a — backend walk + inventory`.

### BACKEND-INVENTORY.md template
```markdown
# {role} — Backend Inventory (Phase 5a)
Skills invoked: …

## Route coverage
| # | Backend route (method) | Handler | Called by frontend? | Tenant-scoped? | Gate | Notes |
|---|---|---|---|---|---|---|

## ORPHANED (should surface)
| # | Route | Handler | Why surface | Recommendation | Decision |
|---|---|---|---|---|---|

## INTERNAL (no UI by design)
…

## DEAD (removal/wiring candidates)
| # | Route | Handler | Why | Recommendation | Decision |
|---|---|---|---|---|---|
```

## 5b. Supervised interactive browser walk + Frontend Feature Inventory

For each walk-table row, in order, live with the user (chrome-devtools or
playwright MCP):

1. **State** — `list_pages`; ensure one tab at the function's route.
2. **Load layer skills** for this surface (Skill Map).
3. **Discuss intent** — state the Intended row; confirm/redirect with the user
   before interacting on design-sensitive surfaces.
4. **Exercise** — navigate → `take_snapshot` → interact (`fill_form`, `click`,
   `wait_for`). Watch `list_console_messages` + `list_network_requests` for
   500s / failed API calls.
5. **Record actual** — rendered output, API statuses, console errors. **Write
   the row's Status/Actual into PLAN.md before moving to the next surface.**
6. **User steers** — capture design/behavior change requests.
7. **Frontend feature triage** — as you walk each page, bucket it into
   FRONTEND-INVENTORY.md:
   - **A — wire**: page renders but its primary data call 404s/500s/returns a
     shape the UI can't consume → needs backend wiring.
   - **B — omit/reduce**: duplicated surfaces, near-empty pages duplicating a
     broader page, or dead nav targets.
   - **C — refine**: functional but with UX gaps (empty states, no loading,
     missing pagination, misaligned gates, stale copy) or data-quality issues.
8. **Decision gate** — before ANY refinement, present the finding +
   recommended fix; get the user's choice.
9. **Refine/fix** (on FIX decisions) across layers as decided. Run gates:
   backend `pytest` + `ruff` from `backend/`; frontend `npx vitest run` +
   `tsc` + `prettier`. Commit code (Conventional Commits), then fill the row's
   Fix (layer) + Commit columns.
10. **Commit** plan/inventory updates in logical groups. Never cross a commit
    boundary with a decided gate un-recorded.

### FRONTEND-INVENTORY.md template
```markdown
# {role} — Frontend Inventory (Phase 5b)
Skills invoked: …

## A. Needs backend wiring (UI exists, backend missing/incomplete)
| # | Page | Route | API calls | Missing/incomplete backend | Recommendation | Decision |
|---|---|---|---|---|---|---|

## B. Better omitted / reduced (overlaps, noise, unmaintained)
| # | Page | Route | Why reduce/omit | Recommendation | Decision |
|---|---|---|---|---|---|

## C. Needs refinement (works but has gaps)
| # | Page | Route | Gap (UX/perf/data) | Recommendation | Decision |
|---|---|---|---|---|---|
```

---

# PHASE 6 — Role-Specific User Guide (capability-complete user manual)

## Purpose
Produce a comprehensive, role-specific manual that documents EVERY capability
the role has (from SCOPE.md + walked PLAN.md results), how to operate each
surface, and what to expect — written for a human user of the app. Load
`documentation-writer` for this phase.

## Steps
1. Sources: SCOPE.md (reachable surfaces), PLAN.md (intended + actual behavior,
   fixes), BACKEND/FRONTEND-INVENTORY.md (what's wired/omitted/refined).
2. Write `docs/user-guides/{role}.md` — **update in place if it already exists**
   (do not fork a -v2 file). Cover every reachable surface; mark surfaces
   broken/pending with a status.
3. Include practical workflow walkthroughs ("how to X"), not just surface lists.
4. After the guide, ask the user whether any documented behavior should change
   (that becomes a decision-gated refinement back in Phase 5).

## USER-GUIDE template
```markdown
# {Role} User Guide — QuantumPACS
Version: {app version or commit} | Role: {role} | Applies to: {tenant model}

## 1. About this role
{What the role is, workspace, landing page, scope summary}

## 2. Signing in
{Login flow, tenant selection, session, password reset, security notes}

## 3. Getting around
{Landing page + sidebar map: every section/route the role can reach, one line each}

## 4. Surface-by-surface guide
### 4.1 {Surface} ({route})
- Purpose: …
- How to: step-by-step
- Fields/controls: …
- Status: {PASS / BETA / BROKEN-pending-fix}
- Notes: …

## 5. Common workflows (walkthroughs)
### 5.1 {Workflow}
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

---

# DECISION GATE PROTOCOL (applies to ALL phases)

Before ANY code/document change:

1. **State the finding** — what diverges from intent, where (file:line), severity.
2. **State the recommendation** — the change you propose, at which layer(s), with
   rationale (ADR, audit finding, or best-practice principle).
3. **Ask the user** — AskUserQuestion with options:
   - FIX — apply the recommended change
   - UPDATE-DOCS — fix the ADR/spec instead of the code
   - REDESIGN — different approach (capture the user's direction)
   - DEFER — record as open item with priority
   - REJECT — leave as-is, record rationale
4. **Record the decision** in the governing doc: RECOMMENDATIONS row, inventory
   row, or PLAN.md Findings & decisions.
5. Only after sign-off: make the change, run gates, commit.

Batch related findings into ONE AskUserQuestion call to reduce interruption,
but each change still needs an explicit decision. If the user's steer conflicts
with an ADR or audit finding, surface the conflict and recommend UPDATE-DOCS
(docs are the contract).

---

# SESSION STATE / RESUMPTION

- **PLAN.md is the progress record.** Resume at the first walk-table row with
  Status PENDING (or empty Actual); fill rows in place as you re-walk.
- Phase position: each doc's completion checkboxes + `git log --oneline --grep
  'docs(walk): {role}'` tell you where the walk stopped.
- Inventories are resumable from their last categorized row.
- The Phase 6 guide is resumable from the guide file (mark incomplete surfaces).
- Re-login fresh (tokens expire; backend may have restarted) and re-run
  Credential Resolution. Re-load role-level and layer skills — skills are
  per-session and do not persist.
- **Never resume from legacy `docs/user-feature-review/{role}/` artifacts**
  (the retired v1 pipeline with state.json) — they are history, not state.

---

# Gotchas (QuantumPACS)

## Backend / DB refinement
- Schema changes need **new Alembic files** in `backend/migrations/versions/`;
  sync the dev DB via `sync_db()` self-heal or careful raw DDL — do NOT blindly
  `alembic upgrade head` (version-table drift).
- Pool via `backend/db/database.py` `get_database().acquire()`; responses via
  `api/response.py` `ok()/created()/not_found()`; validation via
  `api/validate.py` `parse_body()` with Pydantic v2 `api/schemas/`.
- pypika: `Field` has no `.desc()` (use `Order.desc`), no `.in_()` (use `.isin()`).
- Route ordering: static routes before parameterized (`{id}`) routes.
- asyncpg: pass `date`/`datetime` objects, not ISO strings, for date columns.
- Restart `quantumpacs-backend.service` after backend edits; re-login for a
  fresh token.
- Keep throwaway session files out of commits; commit the docs/role-walk
  deliverable.

## Chrome-devtools MCP conventions
- `list_pages` FIRST in every action batch (page ids change on browser restart).
- Prefer `take_snapshot` over screenshots for navigating/interacting (uid targets).
- `wait_for` takes an ARRAY of texts: `wait_for(text=["..."])`, not a string.
- Admin roles land on `/admin`; clinical roles land on their own workspaces.
- Backend API walk: `curl` with `Authorization: Bearer <token>` from
  `POST /api/v2/login` (NOT `/api/v2/auth/login`).

## Test gates
- Backend `pytest` + `ruff` run from `backend/`.
- Frontend `npx vitest run` + `tsc` + `prettier` (pre-commit gates).

---

# Exit criteria

- SCOPE, GAP-ANALYSIS, RECOMMENDATIONS, PLAN, BACKEND-INVENTORY (5a),
  FRONTEND-INVENTORY (5b) docs exist and are current.
- Every PLAN.md walk-table row has Status ≠ PENDING; every excluded route
  verified.
- Every gap maps to a recommendation; every finding and inventory item has a
  user decision recorded.
- Role-level skills loaded in Phase 1, layer skills loaded per surface in
  Phase 5 (each recorded in `Skills invoked`); unavailability noted.
- Role-specific user guide written/updated at docs/user-guides/{role}.md.
- All backend pytest + frontend vitest/tsc pass.
