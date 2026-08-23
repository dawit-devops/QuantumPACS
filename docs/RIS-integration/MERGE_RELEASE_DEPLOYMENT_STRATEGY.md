# Merge, Release & Deployment Strategy

**Branch:** `feature/ris-integration` → `v3-dev` → `main`
**Scope:** Deploy the integrated PACS + RIS platform
**Date:** 2026-08-23
**Author:** Buffy (automated review)
**Companion docs:** `CUTOVER_RUNBOOK.md`, `S12_HARDENING_EVIDENCE.md`, `GAP_AUDIT_TDD_PIPELINE.md`

---

## 1. Branch Topology (Current State)

```
main ─────────────●──────────────────────────────  (v2.x production)
                  │
                  │  (no reverse commits — clean fast-forward)
                  │
v3-dev ────●──●──●──●───────────────────────────  (v3 integration, Phases 0–6)
           │  │  │  │
           │  │  │  └── feature/ris-integration (82 commits, 0 behind v3-dev)
           │  │  └──── phase/* branches (various)
           │  └─────── phase/* branches
           └────────── v3-dev head: 4796f09
```

### Key facts

| Metric | Value |
|--------|-------|
| Commits ahead of `v3-dev` | 82 |
| Commits behind `v3-dev` | 0 (clean fast-forward possible) |
| Merge conflicts | 0 (no files changed in both branches) |
| Files changed vs `v3-dev` | 425 (+53,403 / -1,125) |
| Alembic migrations | 88 (000→087), linear, no branching heads |
| Backend tests | 2523 passed, 2 skipped, 0 failed |
| Frontend tsc | 0 errors |

---

## 2. Merge Strategy (feature/ris-integration → v3-dev)

### 2.1 Why Fast-Forward

ADR-022 specifies *"merge commits only (no squash) — preserve atomic commit history for bisection."* Since `v3-dev` has zero drift (no new commits since the feature branch forked), a fast-forward merge satisfies this requirement while producing a perfectly linear history.

### 2.2 Pre-Merge Checklist

| # | Gate | Command | Pass condition |
|---|------|---------|----------------|
| 1 | Working tree clean | `git status --short` | No output (or only expected untracked) |
| 2 | Backend tests green | `cd backend && .venv/bin/python3 -m pytest tests/ -q` | 0 failed |
| 3 | Frontend tsc clean | `cd frontend && npx tsc --noEmit` | 0 errors |
| 4 | CI pipeline green on `feature/ris-integration` | GitHub Actions check run | All jobs pass |
| 5 | No regressions vs `v3-dev` HEAD | `git diff v3-dev...feature/ris-integration --stat` | Only additive RIS changes |
| 6 | Migration chain clean | `cd backend && .venv/bin/python3 -m alembic heads` | Single head (087) |

### 2.3 Merge Procedure

```bash
# 1. Ensure v3-dev is up to date
git checkout v3-dev
git pull origin v3-dev

# 2. Fast-forward merge
git merge --ff-only feature/ris-integration

# 3. Verify HEAD matches feature/ris-integration tip
git log --oneline -1   # should be 77cc389 or latest commit

# 4. Push v3-dev (triggers full CI pipeline)
git push origin v3-dev

# 5. Delete the feature branch (ADR-022: "deleted after merge")
git branch -d feature/ris-integration
git push origin --delete feature/ris-integration
```

### 2.4 Post-Merge Verification

After pushing `v3-dev`, the CI pipeline runs 12 jobs:

| Job | What it checks |
|-----|----------------|
| `lint-backend` | ruff (Python) |
| `lint-frontend` | prettier |
| `typecheck` | `tsc --noEmit` |
| `test-backend` | Full pytest with Postgres service + coverage floor |
| `test-frontend` | Full vitest with coverage |
| `e2e` | Playwright against real stack (Postgres + Redis + backend + frontend) |
| `build-gate` | Vite build + bundle size check + coverage |
| `docker-build` | Both images build cleanly |
| `docker-smoke` | Full compose stack boots, backend healthy |
| `prod-smoke` | `docker-compose.prod.yaml` boots, backend healthy, frontend serves |
| `vuln-scan` | Trivy CRITICAL/HIGH scan |
| `requirements-validate` | 19 role packages pass validation |

**All 12 gates must pass before `v3-dev` is considered release-ready.**

---

## 3. Release Plan (v3-dev → main)

### 3.1 When to Release to `main`

Per ADR-022, `main` stays at v2.x until **v3.0 GA** (roadmap target: June 2027). The RIS integration merging into `v3-dev` is a **v3.0 milestone**, not a v2.x patch.

| Decision | Rationale |
|----------|-----------|
| **Do NOT merge `v3-dev` → `main` immediately** | `main` is v2.x production; RIS is v3 scope |
| **Create `release/v3.0` when `v3-dev` is feature-complete** | Branch from `v3-dev` once all phases (1–8) land |
| **`release/v3.0` → `main` at GA** | After UAT sign-off, DR rehearsal, and go/no-go |

### 3.2 Release Branch Lifecycle

```
v3-dev ──●──●──●──●──●──●──●──●──●────  (all phases merged)
                     │
                     │  (feature-complete gate)
                     │
release/v3.0 ──●──●──●──●────────────  (patch-only: bugfixes, version bump, changelog)
                     │
                     │  (GA gate: UAT ✅, DR drill ✅, security audit ✅)
                     │
main ───────●─────────────────────────  (v3.0.0 production)
              │
              └── cherry-pick / merge back to v3-dev (§3.4)
```

### 3.3 Release Branch Procedure

```bash
# 1. Create release branch from v3-dev (when ALL phases are feature-complete)
git checkout -b release/v3.0 v3-dev

# 2. Version bump
#    - backend: update version in config.py or __init__.py
#    - frontend: update package.json version field

# 3. Generate CHANGELOG.md from conventional commits
git log --oneline v3-dev --since="2026-07-01" > CHANGELOG.md

# 4. Tag the release candidate
git tag -a v3.0.0-rc1 -m "Release candidate 1"
git push origin release/v3.0 --tags

# 5. Stabilisation (bugfixes ONLY on release/v3.0)
#    - No new features
#    - Bugfixes committed, tested, CI green
#    - Staging deployment validated

# 6. Final tag
git tag -a v3.0.0 -m "v3.0 GA"
git push origin release/v3.0 --tags
```

### 3.4 Post-Release: Merge Back to v3-dev

After `release/v3.0` merges to `main`:

```bash
# Merge release fixes back into v3-dev
git checkout v3-dev
git merge --no-ff release/v3.0 -m "Merge release/v3.0 back into v3-dev"

# Delete release branch (ADR-022: lifecycle ends after merge)
git branch -d release/v3.0
git push origin --delete release/v3.0
```

### 3.5 Hotfix Path (Post-GA)

For critical production fixes after v3.0 GA:

```bash
# Branch from main
git checkout -b fix/<description> main

# Fix, test, PR to main
# Then cherry-pick to v3-dev
git checkout v3-dev
git cherry-pick <commit-sha>
```

---

## 4. Pre-Production Deployment Strategy

### 4.1 Environment Progression

```
Development (localhost)  →  Staging (mirror-prod)  →  Production
       │                         │                        │
   docker compose up        docker-compose.prod      real infrastructure
   (dev services)           (IMAGE_TAG=staging)      (IMAGE_TAG=<sha>)
```

### 4.2 Staging Environment

**Purpose:** Validate the merged `v3-dev` in a production-like environment before cutting `release/v3.0`.

| Component | Staging Config |
|-----------|---------------|
| Postgres | `docker-compose.prod.yaml` with real volume, `quantumpacs-postgres:18` |
| Backend | Same image as prod, `IMAGE_TAG=staging-<sha>` |
| Frontend | Same image as prod, `IMAGE_TAG=staging-<sha>` |
| Data | Synthetic patient data (`scripts/seed_uat.py`) + de-identified real studies |
| DICOM | dcm4chee archive + MWL SCP running |
| HL7 | MLLP interface engine connected to test RIS |

**Staging Deployment Procedure:**

```bash
# 1. Build images from v3-dev HEAD
IMAGE_TAG=staging-$(git rev-parse --short HEAD) \
  docker compose -f docker-compose.prod.yaml build

# 2. Deploy to staging
IMAGE_TAG=staging-$(git rev-parse --short HEAD) \
  docker compose -f docker-compose.prod.yaml up -d

# 3. Verify backend health
curl -sf http://localhost:8080/api/health   # → 200

# 4. Run UAT scripts per persona
python scripts/seed_uat.py --persona radiologist --env staging
python scripts/seed_uat.py --persona technologist --env staging
python scripts/seed_uat.py --persona scheduler --env staging
python scripts/seed_uat.py --persona front-desk --env staging
python scripts/seed_uat.py --persona biller --env staging
python scripts/seed_uat.py --persona ris-admin --env staging
python scripts/seed_uat.py --persona manager --env staging

# 5. Run E2E tests against staging
cd frontend && npx playwright test --project=chromium

# 6. Smoke-test DICOM + HL7
# - C-FIND from a mapped station AE → MWL entries returned
# - Send test ORM → order appears in worklist
# - Sign report → charge appears in billing queue
```

### 4.3 Production Deployment (v3.0 GA)

Per the existing `CUTOVER_RUNBOOK.md`:

| Phase | Window | Actions |
|-------|--------|---------|
| **T-60 min (Preflight)** | 30 min | CI green, full test suite, fresh-DB migration replay, images buildable, backups current, secrets validated, comms sent |
| **T-0 (Deploy)** | 15 min | Maintenance mode → Postgres → Redis → Backend (auto-migrates) → Frontend → Optional ES |
| **T+10 (Verify)** | 10 min | 8-point smoke: health, login, MWL, tracking, sign-off, billing, background engines, tenant isolation |
| **T+40 (Post-deploy)** | 30 min | Disable maintenance, monitor error rate + p95, announce completion |
| **Rollback** | ≤ 15 min app-only, ≤ 60 min full | Maintenance mode → pinned images → optional schema downgrade → DB restore (last resort) |

### 4.4 Rollback Rehearsal (Pre-GO)

Before any production cutover, execute once on staging:

- [ ] Previous-tag backend/frontend images retained in the registry
- [ ] `alembic downgrade` exercised for the release's newest migration(s)
- [ ] Restore-from-dump rehearsed into a scratch DB
- [ ] Maintenance-mode toggle verified end-to-end
- [ ] Time-to-rollback measured (target ≤ 15 min app-only, ≤ 60 min full)

---

## 5. CI/CD Gate Matrix

### 5.1 Per-Branch Gates

| Branch | CI Trigger | Required Jobs |
|--------|-----------|---------------|
| `feature/*` | push + PR | lint, tsc, pytest, vitest |
| `phase/*` | push + PR | lint, tsc, pytest, vitest |
| `v3-dev` | push + PR | Full 12-job suite |
| `release/v3.N` | push + PR | Full 12-job suite |
| `main` | push + PR | Full 12-job suite |

### 5.2 Branch Protection Rules (ADR-022)

| Branch | Protection |
|--------|-----------|
| `main` | Signed commits, 1 approval, CI green, conversation resolution |
| `v3-dev` | CI green, conversation resolution (single-dev exception: self-merge OK) |
| `phase/*` | CI green (no approval gate) |
| `release/v3.N` | Signed commits, CI green, conversation resolution |

---

## 6. Recommended Timeline

| When | Action | Gate |
|------|--------|------|
| **Now** | Fast-forward merge `feature/ris-integration` → `v3-dev` | Pre-merge checklist §2.2 |
| **After merge** | Verify CI passes on merged `v3-dev` (full 12-job suite) | All green |
| **Week 1–4** | Continue phase branches off `v3-dev` (remaining Phases 7–8) | Per-phase CI |
| **Feature-complete** | Branch `release/v3.0` from `v3-dev` | All phases merged, roadmap complete |
| **Release stabilisation** | Bugfixes on `release/v3.0`, staging deployment, UAT | Staging green, UAT sign-off |
| **Pre-GO** | Rollback rehearsal, DR drill, security audit, go/no-go meeting | Cutover runbook §6 checklist |
| **GA** | `release/v3.0` → `main` (signed, rebased PR) | Main CI green, manual smoke |
| **Post-GA** | Cherry-pick release fixes back to `v3-dev`, delete `release/v3.0` | Clean branch state |

---

## 7. Migration Chain Safety

### 7.1 Current Chain

- 88 migrations (000→087), linear, single head
- Head: `087_template_tenant_scope`
- All migrations ship working `downgrade()` methods

### 7.2 Container Migration Strategy

The backend Docker entrypoint runs `python -m alembic upgrade head` (fail-fast) before uvicorn starts. This means:

- **On deploy:** migrations run automatically inside the backend container
- **On rollback:** app-level rollback (pinned images) is always safe; schema downgrade only if the incident is migration-caused
- **On fresh DB:** chain replays cleanly from 000 to head

### 7.3 Migration Safety Rules

1. Never modify a migration that has been deployed to production
2. New migrations must be additive (ADD COLUMN, CREATE TABLE) or safe backfills
3. Every migration must have a working `downgrade()` method
4. Test `alembic upgrade head` + `alembic downgrade -1` + `alembic upgrade head` on a scratch DB before merge

---

## 8. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| RIS changes break existing PACS functionality | Low | High | 2523 tests pass; e2e Playwright tests |
| `v3-dev` CI fails after merge | Very low | Medium | Pre-merge CI on feature branch; post-merge re-run |
| Migration 086/087 fail on existing `v3-dev` DBs | Low | Medium | Staging rehearsal; downgrade path exists |
| RIS background engines consume excessive resources | Low | Low | D4 configurable SLA; D5 rate limiting |
| Feature branch deletion loses audit trail | None | None | 82 atomic commits preserved in `v3-dev` history |
| `v3-dev` drift from `main` causes future merge friction | Medium | Medium | `v3-dev` absorbs all work; `main` only receives `release/*` merges |

---

## 9. Deliberate Deferrals (Not in This Merge)

These are intentionally deferred per `GAP_AUDIT_TDD_PIPELINE.md` §0.3 and are not merge blockers:

| Item | Why Deferred | Tracks |
|------|-------------|--------|
| AI coding module | Needs 30-day production data | R2-06-11 |
| Real SMS/email providers | Procurement decision | — |
| X12 validators for 837/835 | Until clearinghouse chosen | — |
| Platform-wide chargeback rollup | Cross-tenant aggregation design needed | — |
| UAT execution sign-offs | Material delivered; sign-off belongs to UAT owners | R2-06-13 |
| DR drill rehearsal | Operational, not code | S12-31 |

---

## 10. References

| Document | Path |
|----------|------|
| ADR-022: Git Branching Strategy | `docs/decisions/ADR-022-git-branching-strategy.md` |
| Cutover Runbook | `docs/RIS-integration/CUTOVER_RUNBOOK.md` |
| Hardening Evidence | `docs/RIS-integration/S12_HARDENING_EVIDENCE.md` |
| GAP Audit Pipeline | `docs/RIS-integration/GAP_AUDIT_TDD_PIPELINE.md` |
| v2.1 Sprint Completion | `docs/RIS-integration/V2_1_SPRINT_COMPLETION.md` |
| ROADMAP-v3 | `docs/ROADMAP-v3.md` |
| CI Pipeline | `.github/workflows/ci.yml` |
| Prod Compose | `docker-compose.prod.yaml` |
| UAT Scripts | `docs/uat/*.md` |
| UAT Seeder | `scripts/seed_uat.py` |
