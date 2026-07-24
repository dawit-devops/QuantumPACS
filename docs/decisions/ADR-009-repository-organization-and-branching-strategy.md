# ADR-009: Repository Organization and Branching Strategy

## Status
Accepted

## Date
2026-07-23

## Context
QuantumPACS is a monorepo containing a Python/Starlette backend, a React SPA frontend, Docker infrastructure, and documentation. As more engineers contribute and the feature set grows (RIS integration, HL7/FHIR gateways, AI/ML pipelines), the repository needs a clear organization and branching model that supports:

- Multiple features in parallel without stepping on each other
- Versioned releases for PACS deployments (hospitals pin versions)
- Emergency hotfixes for production (medical software uptime)
- HIPAA-compliant audit trail — every change traceable to a ticket
- CI/CD with automated quality gates
- The strangler fig pattern already in use (incremental modernization)

The current setup has a single `dev` branch with direct commits. This does not scale.

## Decision

### Repository Structure

```
quantumpacs/
├── .github/
│   ├── workflows/               # CI/CD (lint, test, build, deploy)
│   ├── dependabot.yml
│   └── PULL_REQUEST_TEMPLATE.md
├── backend/                     # Python/Starlette API
│   ├── api/                     # HTTP route handlers
│   ├── db/                      # Database layer (asyncpg + migrations)
│   ├── dcm/                     # DICOM processing
│   ├── es/                      # Elasticsearch integration
│   ├── tests/                   # pytest suite
│   ├── migrations/              # Alembic
│   ├── app.py
│   └── config.py
├── frontend/                    # React SPA
│   ├── src/
│   │   ├── detail/              # DICOM viewer
│   │   ├── files/               # File browser
│   │   ├── patient/             # Patient records
│   │   └── ...                  # Per-feature module
│   ├── package.json
│   └── vite.config.js
├── docs/
│   ├── decisions/               # ADRs (this file)
│   ├── api/                     # API reference
│   └── operations/              # Runbooks
├── scripts/                     # Dev tooling
├── docker/                      # Service Dockerfiles
├── infra/                       # Terraform / Ansible (future)
├── tools/                       # Internal CLI tools (future)
├── docker-compose.yaml
├── Dockerfile
└── CLAUDE.md
```

Key principles:
- **Monorepo with bounded contexts** — backend/ and frontend/ are independent deploy units within a single repo. No shared code across them (they communicate via HTTP API).
- **Per-feature modules** — new features add a directory under `backend/api/` or `frontend/src/` rather than scattering across existing files.
- **ADR index** — a running numbered list in `docs/decisions/README.md` as the entry point.
- **Runbooks** in `docs/operations/` for deployment, backup, incident response.

### Branching Strategy: GitHub Flow with Release Branches

```
main  ──●────●────●────●────────●───────────●──── release tags (v2.0.0, v2.1.0)
         │    │    │    │        │           │
         │    │    │    │        │           └── feature/new-feature
         │    │    │    │        └── release/2.1.0
         │    │    │    └── release/2.0.0
         │    │    └── fix/crash-on-null
         │    └── feature/study-browser
         └── feature/DICOM-SR
```

| Branch | Purpose | Lifecycle | Created From | Merges To |
|--------|---------|-----------|--------------|-----------|
| `main` | Production — always deployable | Permanent | — | — |
| `feature/*` | Feature work, bug fixes | Days | `main` | `main` via PR |
| `fix/*` | Bug fixes (same as feature) | Days | `main` | `main` via PR |
| `release/*` | Release stabilization, version bumps | Weeks | `main` | `main` via PR |
| `hotfix/*` | Emergency production fix | Hours | `main` (tagged release) | `main` via PR |

**Rules:**

1. **`main` is always deployable.** Every commit to main must pass lint, test, and build.
2. **Feature branches branch from `main`** and merge back via PR with at least one approval.
3. **Release branches** (`release/v2.x`) are cut before a production deployment for final validation. Bug fixes on a release branch are cherry-picked to `main`.
4. **Hotfix branches** branch from the release tag (`v2.0.0`), fix the issue, and merge to `main` and the release branch.
5. **Conventional commits** — `<type>(scope): <description>` — enforced by CI. Types: `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`.
6. **Signed commits** — all commits GPG/SSH signed for HIPAA audit trail.
7. **No direct pushes to `main`** — only PR merges.
8. **Atomic commits preserved** — no squash unless asked. Rebase + merge commit is the default.

### Commit Convention

```
<type>(<scope>): <description>

[optional body]

Signed-off-by: Name <email>
```

Scope maps to the bounded context: `backend`, `frontend`, `infra`, `docs`. Examples:

```
feat(backend): add DICOM SR parsing endpoint
fix(frontend): handle null window center in viewer
docs: add ADR-009 repository organization
ci: add lint workflow for backend
```

### CI/CD Pipeline

```
push/PR → lint → test → build → (deploy staging) → (deploy prod on tag)
```

Required checks before merge:
- Backend lint (ruff) + test (pytest)
- Frontend lint (eslint) + test (vitest) + build (vite)
- DCO sign-off on every commit
- No unresolved review threads

### Release Process

```bash
git checkout main && git pull
git checkout -b release/v2.1.0
# bump version in pyproject.toml, package.json
# add CHANGELOG entry
git commit -m "chore: bump version to 2.1.0"
git push -u origin release/v2.1.0
# PR → review → merge to main
git tag v2.1.0
git push origin v2.1.0
```

### Hotfix Process

```bash
git checkout v2.0.0   # detached HEAD or create branch
git checkout -b hotfix/2.0.1-crash-fix
# fix + commit
git commit -m "fix(backend): null pointer in study query"
git push -u origin hotfix/2.0.1-crash-fix
# PR targeting main → review → merge
git tag v2.0.1
git push origin v2.0.1
# cherry-pick to release branch if active
```

## Alternatives Considered

### Git Flow (develop + main)
- Pros: Clear separation between integration and production
- Cons: Overhead of `develop` branch creates extra merge steps; `develop` and `main` constantly drift; the medical release cadence (weeks/months) doesn't need a permanent integration branch — PRs serve that role.

### Trunk-Based Development
- Pros: Simplest model, works for CI/CD
- Cons: Requires feature flags for incomplete work. PACS/RIS features often span multiple PRs and take weeks; feature flags add complexity to a medical codebase where hiding incomplete UI paths has safety implications.

### GitLab Flow (environment branches)
- Pros: Natural staging/production promotion
- Cons: Adds branch-per-environment management. Our deployment is a single Docker stack; environment promotion is handled by the CI/CD pipeline, not branches.

## Consequences

**Positive:**
- Release branches isolate stabilization work from new development
- Hotfix branches allow emergency patches without pulling in unreleased changes
- Conventional commits enable automated CHANGELOG generation
- Monorepo with bounded contexts keeps the codebase navigable as it grows
- Signed commits provide HIPAA audit trail

**Negative:**
- Release branch merges create merge commits on main (accepted — atomic commits are worth the history)
- Contributors must learn the commit convention (enforced by CI)
- Feature branches that live longer than a week need regular rebasing
