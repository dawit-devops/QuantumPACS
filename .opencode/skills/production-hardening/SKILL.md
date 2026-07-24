---
name: production-hardening
description: |
  Multi-agent orchestration for production hardening of QuantumPACS.
  Implements the production readiness review findings across 9 sprints
  with parallel agent tracks, automated verification gates, and
  schema-safe migration ordering. Delegates to sub-skills for domain-
  specific work (security, testing, DB schema, compliance).

  Triggers:
  - "implement hardening sprint <N>"
  - "run production hardening"
  - "fix production readiness issue <ID>"
  - "execute sprint <N>"
  - "apply data integrity fixes"
  - "harden auth/security"
  - "add observability"
  - "write integration tests"
  - "frontend hardening"
  - "run all sprints"
  - "start hardening from sprint <N>"

metadata:
  author: quantumrad
  version: "1.0.0"
  depends_on:
    - docs/PRODUCTION_READINESS_REVIEW.md
    - docs/IMPLEMENTATION_PLAN.md
    - docs/PRD.md
  delegates:
    - python-testing-patterns  # When writing/conftest or integration tests
    - postgresql-table-design  # When designing schema migration 006
    - security-fastapi         # When hardening auth/tokens/schemas
    - rest-api-design          # When defining new API endpoints
    - xss-prevention           # When moving tokens from localStorage to cookies
    - frontend-testing         # When writing frontend tests
    - git-workflow             # When branching, committing, PR, merge
    - documentation-and-adrs   # When making architectural decisions
    - hipaa-compliance         # When touching PHI, audit logs, auth
    - docker-containerization  # When modifying Dockerfile or compose
    - dependency-upgrade       # When upgrading framework dependencies
---

# Production Hardening — Multi-Agent Orchestration

## Section 0: Skill Invocation Map

| Trigger | Action |
|---------|--------|
| "implement hardening sprint N" | Execute Sprint N per `docs/IMPLEMENTATION_PLAN.md` |
| "run all sprints" | Execute Sprints 0→8 in sequence with gates |
| "fix issue ID (e.g. C01)" | Identify which sprint contains the fix, execute that track only |
| "start from sprint N" | Skip completed sprints, execute from N forward |
| Mid-task: need schema change | Invoke `postgresql-table-design` for migration design |
| Mid-task: security concern | Invoke `security-fastapi` for route audit |
| Mid-task: need integration tests | Invoke `python-testing-patterns` for conftest+fixtures |
| Mid-task: frontend auth change | Invoke `xss-prevention` for cookie/token review |
| Mid-task: branching/commit/PR | Invoke `git-workflow` |
| Mid-task: architectural decision | Invoke `documentation-and-adrs` |

**Rule:** When any sub-skill trigger occurs mid-implementation, stop and invoke the sub-skill before proceeding.

---

## Section 1: Source-of-Truth Artifacts

| Artifact | Path | Contents | How to Use |
|----------|------|----------|------------|
| Production Readiness Review | `docs/PRODUCTION_READINESS_REVIEW.md` | Full issue catalog (12C, 32H, 24M/L) | Issue IDs (C01–C12, H01–H25, M01–M24, L01–L15) |
| Implementation Plan | `docs/IMPLEMENTATION_PLAN.md` | Sprint breakdowns, tracks, gates, rollback | Per-sprint task lists, file paths, change specs |

---

## Section 2: Git Workflow Protocol

### Branch Structure

```
main (always deployable)
├── production-hardening/foundation      ← Sprint 0
├── production-hardening/schema          ← Sprint 1
├── production-hardening/data-integrity  ← Sprint 2
├── production-hardening/auth            ← Sprint 3
├── production-hardening/perf            ← Sprint 4
├── production-hardening/observability   ← Sprint 5
├── production-hardening/testing         ← Sprint 6
├── production-hardening/redis           ← Sprint 7
└── production-hardening/frontend        ← Sprint 8
```

For sprints with parallel tracks, sub-branch from the sprint branch:

```
production-hardening/foundation
  ├── track/config-logging
  ├── track/db-connection
  ├── track/dicom-server
  ├── track/storage
  ├── track/websocket
  ├── track/code-quality
  └── track/lifecycle-exceptions
```

### Commit Convention

```
sprint(N): <track-name> — <brief description>

Resolves: C0X, H0X, M0X
```

### Workflow Per Sprint

1. Branch off `main`: `git checkout -b production-hardening/<sprint-name>`
2. For each track:
   a. Sub-branch: `git checkout -b track/<track-name>`
   b. Implement changes
   c. Run track-specific verification
   d. PR → squash-merge into sprint branch
3. Run sprint gate (all tests, typecheck, build)
4. PR → squash-merge sprint branch into `main`
5. Tag: `git tag hardening/sprint-<N>`

---

## Section 3: Sprint Definitions

### Sprint 0 — Foundation (Day 1, ~2h)

**Goal:** Eliminate all trivial single-file bugs. No schema changes.

**Parallel tracks (run concurrently — each is a sub-branch):**

| Track | Files | Issues | Agent Role | Effort |
|-------|-------|--------|------------|--------|
| `track/config-logging` | `config.py`, `log.py` | L02, H09, L01 | backend-core | 20 min |
| `track/db-connection` | `conn.py`, `database.py` | H07, H08, M01, M02 | backend-db | 30 min |
| `track/dicom-server` | `dcm/server.py`, `dcm/file.py` | C07, H03, H21, M12, M13 | backend-dicom | 2h |
| `track/storage` | `storage/*.py` | C08, C09, M10, M11, L10 | backend-storage | 45 min |
| `track/websocket` | `api/ws.py` | H23, H24, H25 | backend-realtime | 50 min |
| `track/code-quality` | `db/files.py`, `es/es.py`, `db/study.py`, `db/series.py`, `sync.py` | L07, L08, L09, L11, L12, M14 | backend-db | 40 min |
| `track/lifecycle-exceptions` | `lifecycle.py`, `exceptions.py`, `db/table.py` | C12, M17, L03 | backend-core | 35 min |

**Gate:**
```bash
cd backend && python -m pytest tests/ -v --tb=short -W error::Warning
```

---

### Sprint 1 — Schema Migration (Day 1–2, ~1h)

**Goal:** Database schema hardening (single track — sequential).

| Step | Task | Details |
|------|------|---------|
| 1 | Create Alembic migration 006 | `alembic revision --autogenerate -m "006_schema_harden_production"` |
| 2 | Add UNIQUE(username) | `op.create_unique_constraint('uq_users_username', 'users', ['username'])` |
| 3 | Add FK indexes | 5 indexes on `files(patient_id, study_id, series_id)`, `studies(patient_id)`, `series(study_id)` |
| 4 | Add PK on `replica_files.id` | `op.create_primary_key('pk_replica_files', 'replica_files', ['id'])` |
| 5 | Add UNIQUE on `shared_files(hash)` | `op.create_unique_constraint('uq_shared_files_hash', 'shared_files', ['hash'])` |
| 6 | Add indexes on `patients(name)`, `logs(created)` | `op.create_index(...)` |
| 7 | Make `file_changes.by_user_id` nullable | `op.alter_column('file_changes', 'by_user_id', nullable=True)` |
| 8 | Pre-migration dedup script | Remove duplicate usernames before applying UNIQUE |

Invoke `postgresql-table-design` sub-skill before writing the migration if uncertain about any constraint.

**Gate:**
```bash
cd backend && alembic upgrade head && python -m pytest tests/ -v --tb=short
```

---

### Sprint 2 — Data Integrity (Day 2–4, ~5h)

**Goal:** Fix all data-loss and race-condition bugs in the data layer.

**Parallel tracks:**

| Track | Files | Issues | Agent Role | Effort |
|-------|-------|--------|------------|--------|
| `track/files-core` | `db/files.py` | C01, C03, C04, H11, M07, M08, L07 | backend-db | 4h |
| `track/replica-sync` | `db/replica_files.py` | C05, M09 | backend-db | 2h |
| `track/users-auth` | `db/users.py` | H12, H13, H14 | backend-security | 2h |
| `track/patient-study-series` | `db/patient.py`, `db/study.py`, `db/series.py` | M04, M05, M06, L11, L12 | backend-db | 1h |
| `track/share-file-changes` | `db/share_files.py`, `db/file_changes.py` | H15, H16 | backend-db | 45 min |

**Critical path item:** C01 (ES atomicity) — review both Option A and Option B in `docs/IMPLEMENTATION_PLAN.md` before implementing.

**Gate:**
```bash
cd backend && python -m pytest tests/ -v --tb=short -W error::Warning
```

---

### Sprint 3 — Auth & Security (Day 3–5, ~5h)

**Goal:** Eliminate all authentication and authorization vulnerabilities.

**Parallel tracks:**

| Track | Files | Issues | Agent Role | Effort |
|-------|-------|--------|------------|--------|
| `track/auth-hardening` | `api/auth.py`, `api/tokens.py` | C11, H01, M18, M19 | backend-security | 3h |
| `track/rate-limiting` | `api/ratelimit.py` | H02, M23, M24 | backend-security | 3h |
| `track/schema-validation` | `api/schemas/*.py` | M20, M21, M22 | backend-core | 25 min |

Invoke `security-fastapi` sub-skill to audit the auth middleware changes before finalizing.

**Gate:**
```bash
cd backend && python -m pytest tests/ -v --tb=short -W error::Warning
```

---

### Sprint 4 — Performance & Scalability (Day 4–6, ~4h)

**Goal:** Fix all OOM risks, blocking patterns, and scaling bottlenecks.

**Parallel tracks:**

| Track | Files | Issues | Agent Role | Effort |
|-------|-------|--------|------------|--------|
| `track/pool-tuning` | `db/database.py` | M03 | backend-db | 10 min |
| `track/storage-streaming` | `storage/s3.py`, `storage/b2.py` | H04, H05, H06 | backend-storage | 2h |
| `track/sync-engine` | `sync.py` | M15, M16 | backend-db | 45 min |

**Gate:**
```bash
cd backend && python -m pytest tests/ -v --tb=short -W error::Warning
```

---

### Sprint 5 — Observability (Day 5–6, ~4h)

**Goal:** Make the system observable in production.

**Single track (sequential):**

| Step | Task | Files | Effort |
|------|------|-------|--------|
| 1 | Add JSON logging formatter | `log.py` | 2h |
| 2 | Add request_id middleware + log context | `app.py`, `log.py` | 1h |
| 3 | Add Prometheus metrics middleware | `app.py` | 1h |
| 4 | Add component-level health check | `api/routes.py` | 30 min |

**Gate:**
```bash
cd backend && python -m pytest tests/ -v --tb=short -W error::Warning
```

---

### Sprint 6 — Testing (Day 5–8, ~2d)

**Goal:** Eliminate flaky tests, add real integration test coverage.

**Parallel tracks:**

| Track | Task | Issues | Agent Role | Effort |
|-------|------|--------|------------|--------|
| `track/fix-flakes` | Fix 3 flaky tests | H18, H19, H20 | backend-testing | 4h |
| `track/integration-infra` | Create conftest.py + test DB fixture | — | backend-testing | 3h |
| `track/integration-tests` | Tests for all 11 DB tables | — | backend-testing | 8h |
| `track/load-tests` | k6/locust scenarios | — | backend-testing | 4h |

Invoke `python-testing-patterns` sub-skill for conftest design and fixture patterns.

**Gate:**
```bash
cd backend && python -m pytest tests/ -v --tb=short -W error::Warning
cd frontend && npx vitest run
```

---

### Sprint 7 — Advanced Redis Features (Day 6–8, ~4h)

**Goal:** Horizonally-scalable WebSocket state via Redis pub/sub.

**Single track:**

| Step | Task | Files | Effort |
|------|------|-------|--------|
| 1 | Add `redis` to `requirements.txt` | `requirements.txt` | 2 min |
| 2 | Create `RedisPubSub` channel-per-file manager | `api/ws.py` or new `api/redis_ws.py` | 3h |
| 3 | Replace module-level `files` dict with Redis-backed state | `api/ws.py` | 1h |
| 4 | Keep in-memory local cache for connected clients | `api/ws.py` | 30 min |

**Requirement:** Redis must be running. Add to `docker-compose.yaml` if using Docker.

**Gate:**
```bash
cd backend && python -m pytest tests/ -v --tb=short -W error::Warning
```

---

### Sprint 8 — Frontend Hardening (Day 6–9, ~5h)

**Goal:** Secure the frontend and improve user experience under production load.

**Parallel tracks:**

| Track | Task | Files | Issues | Agent Role | Effort |
|-------|------|-------|--------|------------|--------|
| `track/login` | CAPTCHA/progressive delay | `src/login/Login.tsx` | L13 | frontend | 4h |
| `track/auth-storage` | httpOnly cookies | `src/helpers.ts`, `backend/api/auth.py` | L14 | frontend + backend-security | 4h |
| `track/sidebar` | Fix PAGINATION.limit mutation | `src/common/Sidebar.tsx` | L15 | frontend | 30 min |
| `track/retry` | Add retry logic to useFetch | `src/hooks.ts` | — | frontend | 1h |
| `track/perf` | Progressive loading + code splitting | `src/detail/CornerstoneElement.tsx`, `vite.config.js` | — | frontend | 3h |

Invoke `xss-prevention` sub-skill for the auth-storage track (moving tokens to httpOnly cookies).

**Gate:**
```bash
cd frontend && npx tsc --noEmit && npx vitest run && npx vite build
```

---

## Section 4: Pre-Flight Gate (Before Every Sprint)

Before starting any sprint, run:

```bash
# 1. Ensure main is clean
git checkout main && git pull && git status

# 2. Run current tests to establish baseline
cd backend && python -m pytest tests/ -v --tb=short -W error::Warning 2>&1 | tail -5
cd ../frontend && npx tsc --noEmit && npx vitest run && npx vite build 2>&1 | tail -5

# 3. Note the baseline test count and pass rate
```

If baseline tests fail, do not proceed — fix the test environment first.

---

## Section 5: Post-Sprint Verification

After each sprint merge to `main`:

1. **Test Gate:** All backend tests pass with zero warnings
2. **Type Gate:** TypeScript compiles with zero errors
3. **Build Gate:** Vite build succeeds
4. **Migration Gate** (Sprint 1 only): `alembic upgrade head` and `alembic downgrade -1` both succeed
5. **Tag:** `git tag hardening/sprint-<N>`

If any gate fails:
- Revert the sprint merge: `git revert -m 1 <merge-commit>`
- Fix the issue on the sprint branch
- Re-verify, then merge again

---

## Section 6: Rollback Procedures

| Scenario | Action |
|----------|--------|
| Sprint 1 migration fails | `alembic downgrade -1` |
| Any other sprint breaks tests | `git revert -m 1 HEAD` of the sprint merge commit |
| Production hotfix needed mid-hardening | Branch from `main`, apply hotfix, merge to `main` and sprint branches |
| Conflicting changes between tracks | Resolve in sprint branch before merging to `main` |

---

## Section 7: Common Pitfalls

| Pitfall | Mitigation |
|---------|------------|
| Running parallel tracks on the SAME file | Ensure each track targets disjoint files. If they overlap, sequence them within the sprint |
| Forgetting to run `alembic upgrade head` before tests | Add to Sprint 1 gate. The CI pipeline must include migration |
| ES being down breaks Sprint 2 tests | Mock ES client in tests or run ES locally via Docker |
| Redis not available for Sprint 3/7 | Graceful fallback: in-memory rate limit (Sprint 3), local WS state (Sprint 7) |
| Token format change invalidates sessions | Old tokens without `jti` still pass `verify_token()` — only new tokens get `jti` |
| LSP errors in IDE (imports not resolved) | These are pre-existing and unrelated to hardening work — ignore |
| Multiple agents editing same file concurrently | Use sub-branch-per-track strategy; merge tracks sequentially into sprint branch |

---

## Section 8: References

| Reference | Path |
|-----------|------|
| Full issue catalog with severities | `docs/PRODUCTION_READINESS_REVIEW.md` |
| Detailed sprint tracks with file paths | `docs/IMPLEMENTATION_PLAN.md` |
| DB schema documentation | `docs/DB_SCHEMA_REVIEW.md` |
| Security audit | `docs/SECURITY_AUDIT.md` |
| API documentation | `docs/REST_API_REVIEW.md` |
| Token audit | `docs/token-audit.md` |
| Risk assessment | `docs/Risks.md` |

---

## Section 9: Quick-Start for Each Agent Role

### backend-core
Targets: `config.py`, `log.py`, `exceptions.py`, `lifecycle.py`, `app.py`, `api/schemas/*.py`

### backend-db
Targets: `db/*.py`, `sync.py`, `es/es.py`

### backend-dicom
Targets: `dcm/server.py`, `dcm/file.py`

### backend-storage
Targets: `storage/*.py`

### backend-realtime
Targets: `api/ws.py`

### backend-security
Targets: `api/auth.py`, `api/tokens.py`, `api/ratelimit.py`, `db/users.py`

### backend-testing
Targets: `tests/*.py`, `tests/conftest.py`, `tests/load/*.py`

### frontend
Targets: `src/**/*.tsx`, `src/**/*.ts`, `vite.config.js`