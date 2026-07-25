# ADR-022: Git Branching Strategy — Phased Git Flow for v3

## Status
Accepted

## Date
2026-07-25

## Context

QuantumPACS v3.0 is developed across 8 phases over ~9 months (July 2026 – June 2027), with v3.1 and v3.2 following. The current topology has three production-like branches (`main`, `v3-dev`, `phase2-ingestion-service`) with no formal lifecycle — feature branches linger after merge, `v3-dev` has no documented promotion path to `main`, and Dependabot creates orphan branches against `main` (v2.x) while v3 work happens on `v3-dev`.

Key constraints:
- **Scheduled releases** (v3.0 GA June 2027, quarterly patches, v3.1 Q4 2027, v3.2 Q1 2028) — rules out trunk-based or pure GitHub Flow
- **Phased delivery** — each Phase (1–8) is a multi-week effort with its own feature branch; these must not block each other
- **Production maintenance** — v2.0.x needs security patches while v3 is under development
- **Single developer** — heavy process (formal Git Flow with `develop` + `release`) is overhead; need a lightweight version
- **CI must gate everything** — tests, lint, security scan on every push to any active branch

## Decision

Adopt **Phased Git Flow**, a simplified Git Flow variant tailored to the v3 roadmap:

```
main ───●────────────●────────────────●────  (production, always deployable)
        │            │                │
        │   release/v3.0  release/v3.1│
        │   ┌──●──●────┘              │
        │   │                         │
v3-dev ──●──●──●──●──●───●───●───●─────  (v3 integration)
         │  │  │  │      │   │
         │  │  │  │      │   └── phase/6  (parallel feature branches)
         │  │  │  │      └────── phase/5
         │  │  │  └───────────── phase/3
         │  └──┴──────────────── phase/2
         └────────────────────── phase/1
```

### Branch Types

| Branch | Source | Merges To | Lifecycle | Purpose |
|--------|--------|-----------|-----------|---------|
| `main` | — | — | Permanent | Production releases. Always deployable. Only merge via `release/*` or `fix/*` PRs. |
| `v3-dev` | `main` | `release/*` | Permanent | v3 integration branch. All phases merge here. CI runs full suite. |
| `phase/N` | `v3-dev` | `v3-dev` | Per-Phase | Feature branch for one Phase (e.g. `phase/2`). Named `phase/<N>-<descriptor>`. Deleted after merge. |
| `release/v3.N` | `v3-dev` | `main`, `v3-dev` | Per-Release | Release candidate branch. Patch-only after branched. Version bump, changelog, final hardening. |
| `fix/*` | `main` | `main`, `v3-dev` | Per-Fix | Emergency hotfix for production v2.x. Cherry-picked to `v3-dev`. |
| `dependabot/*` | (auto) | (auto) | Per-PR | Dependabot auto-PRs against `main`. Merged into `main`, then backported to `v3-dev` as needed. |

### Lifecycle Rules

1. **Feature branches (`phase/N`)**:
   - Created from `v3-dev`: `git checkout -b phase/3-dicomweb v3-dev`
   - Merge commits only (no squash) — preserve atomic commit history for bisection
   - Deleted after merging: `git branch -d phase/3-dicomweb && git push origin --delete phase/3-dicomweb`
   - Multiple phase branches may coexist (non-overlapping code areas)
   - Keep rebased on `v3-dev` weekly to avoid drift

2. **Release branches (`release/v3.N`)**:
   - Created when `v3-dev` reaches feature-complete for a milestone
   - Only bug fixes, docs, version bumps allowed (no new features)
   - Merged to `main` via signed, rebased PR — `git merge --ff-only`
   - Merged back to `v3-dev` immediately after release

3. **Hotfix branches (`fix/*`)**:
   - Branch from `main`: `git checkout -b fix/security-regression main`
   - PR to `main`, then cherry-pick to `v3-dev`
   - Tagged as patch version bump: `v2.0.1`

4. **Dependabot**:
   - Target `main` (legacy v2.x dependency bumps)
   - Security-critical backports to `v3-dev` done manually

### Commit Conventions

Enforce [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.

Breaking changes: `feat!:` or `fix!:` with `BREAKING CHANGE:` in footer.

Branch naming:
- `phase/2-ingestion-service` — phase feature branch
- `release/v3.0` — release candidate
- `fix/2.0.1-cve-2024-1234` — hotfix

### CI/CD Integration

Update CI triggers to run on all active branches:

```yaml
on:
  push:
    branches: [main, v3-dev, phase/**]
  pull_request:
    branches: [main, v3-dev]
```

Branch protection rules:
- `main`: requires signed commits, 1 approval, CI green, conversation resolution
- `v3-dev`: requires CI green, conversation resolution (single-dev exception: self-merge OK)
- `phase/*`: CI green (no approval gate)

### Pre-commit Hooks

The existing hooks (ruff, prettier, tsc, pytest) run on every `git commit`. Extend to prevent direct pushes to protected branches:

```yaml
- id: no-direct-push-to-main
  name: Prevent direct push to main/v3-dev
  entry: sh -c '! git rev-parse --abbrev-ref HEAD | grep -E "^(main|v3-dev)$"' 2>/dev/null
  language: system
  pass_filenames: false
  always_run: true
```

## Alternatives Considered

### Pure Git Flow (with `develop` + `release` + `hotfix`)
- Pros: Well-known, documented, tooling (`git flow` CLI)
- Cons: Three permanent branches (`main` + `develop` + `v3-dev`) is redundant; `develop` adds ceremony without value for single-dev team
- Rejected: `v3-dev` replaces `develop`; `release/*` and `fix/*` retained

### GitHub Flow (feature branches off `main`)
- Pros: Simplest, least ceremony
- Cons: Cannot maintain v2.x production fixes alongside v3 development; `main` is always v2.x until v3.0 GA, making v3 PRs unmergeable
- Rejected: Conflict between v2 maintenance and v3 development requires isolation

### Trunk-Based Development
- Pros: Fastest integration, least merge debt
- Cons: Requires feature flags for incomplete v3 features; high test coverage prerequisite not yet met; v3 phases span weeks, too long for trunk-based branches
- Rejected: Immature test suite + long-lived phases incompatible

## Consequences

- `v3-dev` becomes the single source of truth for all v3 development — unambiguous base for phase branches
- `main` stays at v2.0.x until v3.0 GA, receiving security patches via `fix/*` branches
- Phase branches are short-lived (weeks) by roadmap design; merge conflicts minimised by phase-scoped code
- Dependabot branches target `main` (v2.x); v3 dependency bumps managed separately
- CI runs on all active branches, ensuring regressions caught early across parallel phases
- After v3.0 GA, the strategy simplifies: `v3-dev` is deleted, `main` becomes the sole integration branch, and v3.1+ follows GitHub Flow

## Migration Path

```bash
# 1. Rename current feature branch to phase/2 convention
git branch -m phase2-ingestion-service phase/2-ingestion-service
git push origin -u phase/2-ingestion-service
git push origin --delete phase2-ingestion-service

# 2. Update CI triggers for phase/** pattern
# 3. Add pre-commit hook to protect main/v3-dev
# 4. Communicate strategy to contributors
```

## References

- ADR-014: Modular Monolith with Deferred Microservices (v3 architecture)
- ADR-016: Database-per-Tenant Multi-Tenancy
- ADR-017: OAuth/OIDC + RBAC Authentication
- ROADMAP-v3.md: Release cadence and phase schedule
- IMPLEMENTATION_PLAN-v3.md: Phase dependency graph
