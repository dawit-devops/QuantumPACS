---
name: user-feature-review
description: |
  User feature review and critic skill. Wears the test.user hat: walks through
  and reviews the UI/UX and features actually implemented in the codebase for a
  given role, constructs hypothetical role-scoped flows missing from the current
  implementation, critiques the current UI/UX against the role's expectations,
  and hands off a prioritized improvement list to the dev team. Then drives the
  full pipeline: ui-ux-pro-max proposes the design, fullstack-guardian
  implements it, and playwright E2E-tests the complete role flow via
  chrome-devtools + playwright MCP.

  Roles are parameterized: "user-feature-review patient", "user-feature-review
  radiologist", etc. — any slug from BUILT_IN_ROLES (backend/api/permissions.py),
  which maps to the seeded login test.<role> / Test@123456. Defaults to the
  generic end-user persona when no role is given.

  Triggers:
  - "user feature review and critic"
  - "wear the test.user hat"
  - "review the UI/UX for <role>"
  - "walk through the <role> experience"
  - "what would a <role> want that's missing?"
  - "critique the current UI for <role>"
  - "hand off UI/UX improvements to the dev team"
  - "user-feature-review <role>"

metadata:
  author: quantumrad
  version: "1.0.0"
  changelog: |
    v1.0.0 — 2026-08-14:
    - Initial release: 4-phase pipeline (test-user walkthrough → ui-ux-pro-max
      design → fullstack-guardian implementation → playwright E2E verification)
    - Role parameterization from BUILT_IN_ROLES with seeded test.<role> logins
    - Checkpoint gates between phases; artifacts under docs/user-feature-review/{role}/
  depends_on:
    - backend/api/permissions.py  # BUILT_IN_ROLES source of truth for role slugs
    - frontend/src/navigator.ts    # workspace → route → permission gate map
    - backend/seed_test_users.py   # seeded test.<role> / Test@123456 logins
  delegates:
    - ui-ux-pro-max  # Phase 2 — design proposal from hand-off
    - fullstack-guardian  # Phase 3 — implement the design
    - playwright     # Phase 4 — E2E test the full flow
---

# User Feature Review & Critic

A reusable pipeline that reviews the UI/UX of a role as that role's user
(not as a developer), imagines what is missing, critiques what exists, hands
the findings to the dev team, and then sees the improvement through design →
implementation → E2E verification.

## Section 0: Invocation Map

| Trigger | Action |
|---------|--------|
| `user-feature-review <role>` | Run the full 4-phase pipeline for that role |
| "wear the test.user hat for <role>" | Run Phase 1 only (review + critique + hand-off) |
| "design the hand-off for <role>" | Run Phase 2 only (ui-ux-pro-max design) |
| "implement the hand-off for <role>" | Run Phase 3 only (fullstack-guardian implementation) |
| "test the <role> flow end to end" | Run Phase 4 only (playwright E2E) |
| "resume" / "continue" | Continue from the last checkpoint in state |

**Rule:** Each phase writes its artifact to `docs/user-feature-review/{role}/`
BEFORE the next phase starts. Read prior phase artifacts — never rely on
conversation memory across phases.

## Section 1: Role Resolution

1. Parse `$ARGUMENTS` for the role slug (first positional token). If absent,
   default to the generic end-user persona (cross-role common surfaces:
   login, dashboard, account, portal).
2. Validate the slug against `BUILT_IN_ROLES` in `backend/api/permissions.py`.
   If unknown, list valid slugs and ask the user which role to use — do NOT
   guess.
3. Resolve the seeded credentials: username `test.<slug>`, password
   `Test@123456` (see `backend/seed_test_users.py`). Confirm the user is
   seeded/active via the login flow, or run the seeder if missing:
   ```bash
   backend/venv/bin/python backend/seed_test_users.py
   ```
4. Build the role's permission set (from `BUILT_IN_ROLES[slug]`) and its
   reachable surfaces (from `frontend/src/navigator.ts` workspace→route map +
   `PermissionRoute`/`RequirePermission` gates in `frontend/src/auth/`).

## Section 2: Artifacts & State

All artifacts live in `docs/user-feature-review/{role}/`:

| # | File | Phase | Contents |
|---|------|-------|----------|
| 0 | `00-inventory.md` | 1 | Actually-implemented surfaces: routes, pages, permissions, live walkthrough evidence (screenshots/snapshots) |
| 1 | `01-hypothetical-flows.md` | 1 | Flows the role expects but the app lacks (user stories, step-by-step scenarios) |
| 2 | `02-critique.md` | 1 | Experience critique vs expectations (severity-rated) |
| 3 | `03-handoff.md` | 1 | Prioritized improvement list (P0/P1/P2) for the dev team — each with user story + acceptance criteria |
| 4 | `04-design.md` | 2 | ui-ux-pro-max design proposal from the hand-off |
| 5 | `05-implementation.md` | 3 | fullstack-guardian changes: specs, branch, commits, files touched |
| 6 | `06-e2e-report.md` | 4 | playwright E2E results vs acceptance criteria (pass/fail table) |
| 7 | `state.json` | all | Current phase, checkpoints passed, timestamps (resume support) |

Create the directory and `state.json` at start; update `state.json` after
every phase.

## Section 3: Phase 1 — Test User Walkthrough (review + critique + hand-off)

**Mood: the agent wears the test.user hat. All findings are framed as what the
user experiences, wants, or is blocked by — never as developer opinions.**

### Step 1.1: Inventory the actual implementation (read-only)

- Extract the role's permissions from `backend/api/permissions.py`
  (`BUILT_IN_ROLES[slug]`) and read the matching `MATRIX_*` groups if the role
  is canonical.
- Map the reachable UI: read `frontend/src/navigator.ts` (workspace→route→
  permission), then list each page under `frontend/src/{workspace}/` and the
  API endpoints they call (grep `fetch(`/`apiClient` in those pages).
- Note role-specific gating: `PermissionRoute`/`RequirePermission` usage.

### Step 1.2: Live walkthrough (chrome-devtools)

The app runs at `http://localhost:5173` (dev) — verify it is up first
(`curl -s -o /dev/null -w "%{http_code}" http://localhost:5173`).

1. Navigate to the app, log in as `test.{slug}` / `Test@123456`.
2. For EVERY reachable surface (per Step 1.1):
   - navigate, take a snapshot (a11y tree) and a screenshot
   - exercise the primary actions available (click each nav item, button,
     menu; submit each form with valid + invalid input)
   - record console messages and failed network requests
3. Save screenshots under `docs/user-feature-review/{role}/evidence/` and
   reference them from `00-inventory.md`.

### Step 1.3: Construct hypothetical flows (what is MISSING)

Ask "what does a {role} need to do end-to-end that the app cannot do today?"
Build 3–8 concrete hypothetical flows, each with:

- **User story**: "As a {role}, I want … so that …"
- **Step-by-step scenario**: numbered interaction path with expected UI
  responses (compare against current behavior; mark each step exists/missing)
- **Data/API impact**: what endpoints or fields would be required

### Step 1.4: Critique the current implementation

Rate each inventory item and each hypothetical flow on:

| Dimension | Question |
|-----------|----------|
| Discoverability | Can the user find this without training? |
| Efficiency | Minimum clicks/keypresses to complete the task? |
| Feedback | Loading, success, error states present and clear? |
| Consistency | Matches patterns used elsewhere in the app? |
| Trust | Data displayed accurately, actions reversible? |
| Accessibility | Keyboard nav, contrast, labels (WCAG 2.1 AA)? |

Severity: **Critical** (blocks the task entirely) / **High** (major friction)
/ **Medium** (annoyance) / **Low** (polish).

### Step 1.5: Hand off to the dev team

Write `03-handoff.md`: a prioritized improvement list. Every item must have a
**user story**, **acceptance criteria** (testable, numbered), **affected
files/areas**, and a **priority**. End with a "Definition of Done" checklist
the dev team must satisfy.

**PHASE CHECKPOINT 1** — stop and summarize for the user:
- surfaces inventoried (count), hypothetical flows (count), critique findings
  (breakdown by severity), hand-off items (P0/P1/P2 counts)
- Ask: proceed to design (Phase 2), adjust the hand-off, or stop.

---

## Section 4: Phase 2 — Design Proposal (ui-ux-pro-max)

Invoke the registered **ui-ux-pro-max** skill with the hand-off as input:

1. Read `03-handoff.md` (and `01-hypothetical-flows.md` for context).
2. Use ui-ux-pro-max's workflow:
   - Product type: healthcare/PACS (SaaS clinical tool)
   - Stack: detect from `frontend/package.json` (React + Ant Design + Vite)
   - Run its search tool against the design decisions needed per hand-off item.
     Resolve the script path in this order (first that exists):
     ```bash
     python "${CLAUDE_PLUGIN_ROOT}/.claude/skills/ui-ux-pro-max/scripts/search.py" "<query>" --domain <domain>
     python ".agents/skills/ui-ux-pro-max/scripts/search.py" "<query>" --domain <domain>
     python "$HOME/.agents/skills/ui-ux-pro-max/scripts/search.py" "<query>" --domain <domain>
     ```
     (fall back to `python3`; domains: `style`, `color`, `typography`, `ux`,
     `chart`, `product`, `gsap`)
   - Generate the design system recommendations: tokens, colors, typography,
     spacing, component choices (Ant Design components), interaction patterns,
     accessibility conformance.
3. Map each hand-off item → concrete design decision (component, layout,
   states, motion, responsive behavior).
4. Write `04-design.md`: design proposal with rationale, plus a short
   "conflicts with existing patterns" section flagging anything that would
   fight the current Ant Design implementation.

**PHASE CHECKPOINT 2** — stop and summarize the design for the user; ask to
proceed to implementation (Phase 3), revise the design, or stop.

---

## Section 5: Phase 3 — Implementation (fullstack-guardian)

Invoke the registered **fullstack-guardian** skill with `04-design.md` as the
feature spec:

1. Follow fullstack-guardian's core workflow:
   - Gather requirements from the design + hand-off acceptance criteria
   - Write the technical design doc under `specs/user-feature-review-{role}.md`
   - Run the security checkpoint (`references/security-checklist.md`) BEFORE
     writing code — auth, authz, input validation, output encoding
   - Implement incrementally, frontend + backend together
2. Follow repo conventions (CLAUDE.md):
   - Backend: Starlette endpoints with `parse_body()` validation, `ok()`/
     `created()` helpers, asyncpg via `get_database().acquire()`, JWT via
     `api/tokens.py`, Alembic migration for any schema change
   - Frontend: Ant Design components, component-local state + context, plain
     CSS per component, ambient types in `src/types.d.ts`
3. Branch + commit:
   ```bash
   git checkout -b phase/user-feature-review-{slug}
   ```
   Conventional Commits (`feat(role): …`).
4. Verify: backend `pytest`, frontend `tsc`/`npm run build`, `ruff` lint.
5. Write `05-implementation.md`: branch, commits, files touched, tests run,
   any deviations from the design (with reasons).

**PHASE CHECKPOINT 3** — stop and summarize the implementation for the user;
ask to proceed to E2E testing (Phase 4) or stop.

---

## Section 6: Phase 4 — E2E Test (playwright + chrome-devtools)

Invoke the registered **playwright** skill to test the full `test.{slug}`
flow end-to-end:

1. Extract the acceptance criteria from `03-handoff.md` (source of truth for
   what "done" means) and the flows from `01-hypothetical-flows.md`.
2. Test every scenario via the browser tooling:
   - chrome-devtools MCP (navigate, snapshot, fill, click, screenshot,
     console/network inspection) for exploratory verification
   - playwright MCP (or `@playwright/test` specs if the repo has a
     `frontend/e2e` setup — check first) for the scripted end-to-end run
3. Cover the FULL flow: login as `test.{slug}` → every pre-existing reachable
   surface → every newly implemented feature → logout. Include error paths
   (invalid input, permissions denied) and edge cases from the critique.
4. Record evidence: screenshots per step, console messages, network requests.
5. Write `06-e2e-report.md`:
   - pass/fail table keyed by acceptance criteria ID
   - evidence links (`docs/user-feature-review/{role}/evidence/`)
   - regressions found in pre-existing surfaces
   - follow-up fixes requested (if any) with severity
6. If failures exist, report them and offer to either re-open Phase 3 for a
   fix loop or file the failures as follow-up items in the hand-off.

**PHASE CHECKPOINT 4** — final summary: pipeline complete, artifacts listed,
remaining work (if any), and recommended next role to review.

---

## Section 7: Quality Gates

| Gate | When | Check |
|------|------|-------|
| Role valid | Phase 1 start | Slug ∈ BUILT_IN_ROLES |
| App reachable | Phase 1 | `http://localhost:5173` responds |
| Login works | Phase 1 | `test.{slug}` / `Test@123456` authenticates |
| Artifacts written | Phase end | `00`–`06` files exist before next phase starts |
| Acceptance criteria testable | Phase 1 | Every hand-off item has numbered, verifiable criteria |
| Design conflicts flagged | Phase 2 | "Conflicts with existing patterns" section present |
| Security checkpoint | Phase 3 | Auth/authz/validation/output-encoding confirmed per fullstack-guardian checklist |
| Build green | Phase 3 | `pytest`, `tsc`, `ruff` pass |
| E2E evidence | Phase 4 | Screenshots + console + network per scenario |
| Traceability | Phase 4 | Every hand-off item maps to ≥1 test result |

## Section 8: Reusability Notes

- The skill is intentionally role-agnostic: swap the slug and re-run. Prefer
  running it per role (one branch per role) so findings stay scoped.
- Phase 1 is read-only — safe to run on any branch.
- Phases 2–4 write to the repo (specs, code, branch). Always checkpoint with
  the user before crossing from review (Phase 1) into design/implementation.
- If a registered skill is unavailable at invocation time, do the work
  manually using the repo's existing patterns and note the substitution in
  the artifact.
