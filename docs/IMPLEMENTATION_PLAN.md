# QuantumPACS — Production Hardening Implementation Plan

**Derived from:** `docs/PRODUCTION_READINESS_REVIEW.md`
**Total issues:** 12 critical, 32 high, 24 medium/low
**Estimate:** 15–25 engineer-days across 9 sprints
**Parallel tracks:** Up to 6 concurrent agents per sprint

---

## 0. Dependency Graph

```
Sprint 0: Foundation ──────────────────────────────────  (0 blockers)
  │  C08,C09,L02,L01         (trivial one-liners)
  │  H03,H21,H07,H08         (isolated fixes)
  │  H23,H24,H25             (WebSocket fixes)
  │  M10,M11,M14             (storage + sync fixes)
  │  L07,L08,L09,L10,L11,L12 (minor code quality)
  │  L03,M12,M13             (DICOM + table hardening)
  │  C12,M17                 (lifecycle + exceptions)
  │
  ▼
Sprint 1: Schema Migration ────────────────────────────  (needs S0)
  │  MIG-006: UNIQUE(username), FK indexes,
  │  replica_files PK, shared_files UNIQUE,
  │  patients/logs indexes,
  │  file_changes.by_user_id → nullable
  │
  ▼
Sprint 2: Data Integrity ──────────────────────  ────  (needs S1)
  │  files.py:                  │  independent tracks:
  │    C01: ES atomicity        │  H12: password gen order
  │    C03: LIMIT on get_all()  │  H13: add_superadmin txn
  │    C04: COUNT(*) fix        │  H15: share_files TTL
  │    H11: delete_all() txn    │  H16: file_changes nullable
  │    M07: INSERT..ON CONFLICT │  M04-M06: TOCTOU races
  │    M08: CTE for get_extra() │  L11,L12: KeyError guards
  │  replica_files.py:          │  H14: legacy password rehash
  │    C05: delete() race       │
  │    M09: keyset pagination   │
  │
  ▼
Sprint 3: Auth & Security ────────────────────  ────  (needs S2)
  │  auth.py + tokens.py:       │  independent:
  │    C11: Redis auth cache    │  M20: password constraints
  │    H01: narrow except       │  M21: Literal[type] for replica
  │    M18: jti claim           │  M22: dict size limits
  │    M19: exp validation      │  H09: fail-to-boot guard
  │  H02: Redis rate limiting   │
  │
  ▼
Sprint 4: Performance ───────────────────────  ────  (needs S2)
  │  M01-M03: pool elasticity   │  independent:
  │  H04-H06: storage streaming │  M15: sync double-fetch
  │                             │  M16: sync backoff
  │                             │  M14: corrupt DICOM alert
  │
  ▼
Sprint 5: Observability ──────────────────────  ────  (needs S0)
  │  H22: JSON logging          │  independent:
  │  request_id propagation     │  Prometheus metrics
  │  component health checks    │
  │
  ▼
Sprint 6: Testing ──────────────────────────────────  (needs S2-S4)
  │  H18: fix flaky sleep test
  │  H19: isolate Table.tables
  │  H20: config testability refactor
  │  conftest.py + integration tests (11 tables)
  │  load tests (k6/locust)
  │
  ▼
Sprint 7: Advanced (Redis) ────────────────────────  (needs S4)
  │  C10: WS → Redis pub/sub
  │
  ▼
Sprint 8: Frontend ────────────────────────────────  (independent)
  │  L15: fix PAGINATION.limit mutation
  │  L13: CAPTCHA on login
  │  L14: httpOnly cookies (backend + frontend)
  │  retry logic, progressive loading, code splitting
```

---

## 1. Sprint 0 — Foundation (Day 1)

Trivial fixes — no dependencies, no schema changes, single-file edits.

### Track A0.1: Config & Logging (`backend/config.py`, `backend/log.py`)

| ID | File | Change | Effort |
|----|------|--------|--------|
| L02 | `config.py:22-28` | Replace `yaml.load(f, Loader=FullLoader)` → `yaml.safe_load(f)` | 5 min |
| H09 | `config.py:7-8,37-38` | After config load, if `secret` is `'default'` or `'pa55w0rd'`, `log.critical(...)` then `sys.exit(1)` | 10 min |
| L01 | `log.py:15` | Replace hardcoded `INFO` with `os.getenv('LOG_LEVEL', 'INFO')` | 5 min |

### Track A0.2: Database Connection (`backend/db/conn.py`, `backend/db/database.py`)

| ID | File | Change | Effort |
|----|------|--------|--------|
| H07 | `conn.py:21-22,34-36` | Replace `except Exception: pass` with `log.error(...); raise` | 10 min |
| H08 | `conn.py:55-56` | `get_conn()` → raise `RuntimeError('Database not initialized')` instead of returning `None` | 10 min |
| M01 | `database.py:20-21` | Change `min_size=pool_size` → `min_size=2`, `max_size=pool_size` (elastic pool) | 10 min |
| M02 | `database.py:30` | Add `timeout=10` to `pool.acquire(timeout=10)` | 5 min |

### Track A0.3: DICOM Server (`backend/dcm/server.py`, `backend/dcm/file.py`)

| ID | File | Change | Effort |
|----|------|--------|--------|
| C07 | `server.py:71` | Replace `asyncio.run(store(...))` with single event loop + `loop.run_until_complete()` | 1h |
| H03 | `server.py:26-31` | Add `asyncio.Lock()` around `_initialized` check | 15 min |
| H21 | `server.py:87-91` | Fix signal handler to use main event loop reference | 15 min |
| M12 | `file.py:17` | Wrap `v.repval` in try/except with default empty string | 10 min |
| M13 | `file.py:19-27` | Use `getattr(data, 'PatientID', '')` for all required DICOM fields | 10 min |

### Track A0.4: Storage Backends (`backend/storage/*.py`)

| ID | File | Change | Effort |
|----|------|--------|--------|
| C08 | `local_storage.py:82` | `os.chmod(dst, 0o644)` (add `0o` prefix) | 2 min |
| C09 | `s3.py:100` | Wrap `open(src, 'rb')` in `with` statement | 5 min |
| M10 | `storage.py:22-31` | Add `asyncio.Lock()` to `get()` to prevent double-init | 15 min |
| M11 | `local_storage.py:58-68` | Validate `patient_id` is non-empty; strip null bytes from all path segments | 15 min |
| L10 | `s3.py:41-60` | Remove hardcoded `AllowedOrigins: ['*']`; make configurable or remove | 5 min |

### Track A0.5: WebSocket (`backend/api/ws.py`)

| ID | File | Change | Effort |
|----|------|--------|--------|
| H23 | `ws.py:18` | Replace `threading.Lock()` → `asyncio.Lock()` | 5 min |
| H24 | `ws.py:65-68` | Wrap `c.send_json(data)` in try/except catching `WebSocketDisconnect` | 15 min |
| H25 | `ws.py:70-77` | Add periodic cleanup task for stale connections; handle disconnect in `on_disconnect` | 30 min |

### Track A0.6: Minor Code Quality

| ID | File | Change | Effort |
|----|------|--------|--------|
| L03 | `db/table.py:14` | Raise `ValueError('conn required')` if conn is None | 5 min |
| L07 | `db/files.py:158` | Use parameterized `%s` instead of `f'%{search}%'` | 10 min |
| L08 | `es/es.py:69` | Replace `data.pop(...)` with `data.get(...)` to avoid mutation | 5 min |
| L09 | `es/es.py:93-98` | Check `if not v or len(v) == 0: continue` | 5 min |
| L11 | `db/study.py:35` | `data.get('study_description', '')` | 5 min |
| L12 | `db/series.py:35-36` | `data.get('modality', '')`, `data.get('series_description', '')` | 5 min |
| M14 | `sync.py:52-54` | `log.warning(...)` on corrupt DICOM instead of silent `continue` | 5 min |

### Track A0.7: Lifecycle & Exceptions (`backend/lifecycle.py`, `backend/exceptions.py`)

| ID | File | Change | Effort |
|----|------|--------|--------|
| C12 | `lifecycle.py:29-31` | Call `await teardown()` before `sys.exit(1)` | 10 min |
| C12 | `lifecycle.py:15-27` | Narrow `except Exception` → `except (ConnectionError, OSError, asyncio.TimeoutError)` | 10 min |
| M17 | `exceptions.py:1` | Add `status_code: int` and `error_code: str` fields to `ApiException` | 15 min |

### Sprint 0 Gate

```bash
cd backend && python -m pytest tests/ -v --tb=short -W error::Warning
```

---

## 2. Sprint 1 — Schema Migration (Day 1-2)

Single track — Alembic migration 006.

### Migration 006 Contents

| Change | SQL / Alembic Op | Issue |
|--------|------------------|-------|
| UNIQUE on `users(username)` | `op.create_unique_constraint('uq_users_username', 'users', ['username'])` | C02 |
| FK index on `files(patient_id)` | `op.create_index('ix_files_patient_id', 'files', ['patient_id'])` | C06 |
| FK index on `files(study_id)` | `op.create_index('ix_files_study_id', 'files', ['study_id'])` | C06 |
| FK index on `files(series_id)` | `op.create_index('ix_files_series_id', 'files', ['series_id'])` | C06 |
| FK index on `studies(patient_id)` | `op.create_index('ix_studies_patient_id', 'studies', ['patient_id'])` | C06 |
| FK index on `series(study_id)` | `op.create_index('ix_series_study_id', 'series', ['study_id'])` | C06 |
| PK on `replica_files.id` | `op.create_primary_key('pk_replica_files', 'replica_files', ['id'])` | L05 |
| UNIQUE on `shared_files(hash)` | `op.create_unique_constraint('uq_shared_files_hash', 'shared_files', ['hash'])` | L06 |
| Index on `patients(name)` | `op.create_index('ix_patients_name', 'patients', ['name'])` | L04 |
| Index on `logs(created)` | `op.create_index('ix_logs_created', 'logs', ['created'])` | L04 |
| `file_changes.by_user_id` nullable | `op.alter_column('file_changes', 'by_user_id', nullable=True)` | H16 |

### Pre-Migration Data Cleanup

Before applying the UNIQUE constraint on `username`:
```sql
-- Deduplicate: keep the first user for each username, deactivate duplicates
WITH dupes AS (
  SELECT id, username, ROW_NUMBER() OVER (PARTITION BY username ORDER BY id) AS rn
  FROM users
)
UPDATE users SET is_active = false
WHERE id IN (SELECT id FROM dupes WHERE rn > 1);
```

### Sprint 1 Gate

```bash
cd backend && alembic upgrade head && python -m pytest tests/ -v --tb=short
```

---

## 3. Sprint 2 — Data Integrity (Day 2-4)

### Track A2.1: `backend/db/files.py` overhaul

**Task: ES indexing atomicity (C01 + H10)**

Current flow in `files.py:add()`:
```
1. INSERT file → get id           [inside transaction]
2. COMMIT transaction              [line 65]
3. Set filedata['id'] = id         [line 66]
4. es.index_file(filedata)         [line 68 - may fail]
5. Set indexed = True              [line 70]
```

**Problem:** Crash between step 2 and 5 → file in DB but not indexed.

**Fix option A (preferred):** Move ES indexing inside the transaction:
```
1. INSERT file → get id
2. es.index_file(filedata)         [inside transaction]
3. UPDATE indexed = True           [inside transaction]
4. COMMIT
```
If ES is down, the transaction rolls back and the file isn't stored. This is acceptable — a search outage should prevent data ingestion (or the system should queue ES operations).

**Fix option B (fallback):** Add a compensating transaction:
```
1. INSERT file → get id
2. COMMIT
3. es.index_file(filedata)
4. UPDATE indexed = True
   (If step 3 fails, the sync loop picks it up via unindexed())
```

| ID | Change | Effort |
|----|--------|--------|
| C01 | Move ES indexing before transaction commit, or add compensating transaction | 1h |
| H11 | Wrap `delete_all()` in `async with self.conn.transaction():` | 15 min |
| C03 | Add `LIMIT 1000` to `get_all()` (or accept an optional `limit` parameter) | 10 min |
| C04 | Fix COUNT: replace `len(await self.fetch(q))` with `await self.fetchval(select.count(self.table.id).from_(self.table))` | 30 min |
| M07 | `add()`: Replace sequential patient/study/series SELECT-then-INSERT with `INSERT..ON CONFLICT DO NOTHING RETURNING id` | 1h |
| M08 | `get_extra()`: Replace 3 separate queries with single CTE query JOINing patients/studies/series/files | 1h |
| L07 | Parameterize ILIKE pattern using `self.conn.execute(sql, f'%{search}%')` | 10 min |

### Track A2.2: `backend/db/replica_files.py` fixes

| ID | Change | Effort |
|----|--------|--------|
| C05 | `delete()`: Compute `cnt` AFTER the row is deleted, not before. Use a subquery or UPDATE..RETURNING atomically | 1h |
| M09 | `get_for_sync()`: Replace `OFFSET` pagination with keyset pagination (`WHERE id > last_id LIMIT n`) | 1h |

### Track A2.3: `backend/db/users.py` fixes

| ID | Change | Effort |
|----|--------|--------|
| H12 | `add_user()`: Generate password only AFTER insert succeeds. Return `(user_id, password)` | 30 min |
| H12 | `new_pswd()`: Generate password only AFTER update succeeds | 15 min |
| H13 | `add_superadmin()`: Wrap SELECT + INSERT in `async with self.conn.transaction():` | 15 min |
| H14 | Add `needs_rehash: bool` column to users table. In `_verify_password()`: if old-format hash detected, re-hash with 600K iterations and update row. Set `needs_rehash = false` | 1h |

### Track A2.4: Patient/Study/Series TOCTOU fixes

| ID | Change | Effort |
|----|--------|--------|
| M04-M06 | Replace read-then-insert with single `INSERT..ON CONFLICT DO NOTHING RETURNING id` | 1h total |

### Track A2.5: Share & File Changes

| ID | Change | Effort |
|----|--------|--------|
| H15 | Add `cleanup_expired()` method to `SharedFiles`; call periodically (e.g., every `check()` call prunes 100 expired rows) | 30 min |
| H16 | Make `file_changes.by_user_id` nullable (already done in migration 006); in `add_change()`, only set `by_user_id` if provided | 10 min |

### Sprint 2 Gate

```bash
cd backend && python -m pytest tests/ -v --tb=short -W error::Warning
```

---

## 4. Sprint 3 — Auth & Security (Day 3-5)

### Track A3.1: Auth hardening (`backend/api/auth.py`, `backend/api/tokens.py`)

| ID | Change | Effort |
|----|--------|--------|
| H01 | Replace `except Exception:` with `except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, ...):` | 15 min |
| M18 | Add `jti = str(uuid4())` to token payload. Add Redis SET with TTL for token blocklist | 2h |
| M19 | In `verify_token()`, explicitly check `exp` and raise `jwt.ExpiredSignatureError` if expired | 10 min |
| C11 | Add Redis cache layer: after successful `is_active` check, cache result for 60s. Key: `auth:active:{user_id}` | 2h |

### Track A3.2: Rate limiting (`backend/api/ratelimit.py`)

| ID | Change | Effort |
|----|--------|--------|
| H02 | Replace in-memory `TokenBucket` with Redis-based sliding window. Keep `TokenBucket` as fallback if Redis unavailable | 3h |
| M23 | In `record()`: if `success=True`, don't count the attempt toward lockout | 10 min |
| M24 | In `record_db()`: log error instead of silent `pass` | 5 min |

### Track A3.3: Schema validation (`backend/api/schemas/`)

| ID | Change | Effort |
|----|--------|--------|
| M20 | Add `Field(..., min_length=8, max_length=128)` to `password`. Enforce `password == password2` in model_validator | 15 min |
| M21 | Change `type: str` → `type: Literal['local', 's3', 'b2']` | 5 min |
| M22 | Add `Field(default_factory=dict, max_length=100_000)` to `tag` and `tools_state` | 5 min |

### Sprint 3 Gate

```bash
cd backend && python -m pytest tests/ -v --tb=short -W error::Warning
```

---

## 5. Sprint 4 — Performance & Scalability (Day 4-6)

### Track A4.1: Connection pool optimization (`backend/db/database.py`)

| ID | Change | Effort |
|----|--------|--------|
| M03 | Add `asyncpg.create_pool(..., command_timeout=30, statement_cache_size=100)` | 10 min |

Already covered in Sprint 0: M01 (pool elasticity), M02 (acquire timeout).

### Track A4.2: Storage streaming (`backend/storage/s3.py`, `storage/b2.py`)

| ID | Change | Effort |
|----|--------|--------|
| H04 | `s3.py fetch()`: Stream S3 object to `tempfile.NamedTemporaryFile` instead of `BytesIO` | 1h |
| H05 | `b2.py fetch()`: Stream download to `tempfile.NamedTemporaryFile` instead of `BytesIO` | 1h |
| H06 | Increase `ThreadPoolExecutor(4)` → `ThreadPoolExecutor(16)` or use asyncio-compatible B2 SDK | 15 min |

### Track A4.3: Sync engine (`backend/sync.py`)

| ID | Change | Effort |
|----|--------|--------|
| M15 | Cache fetched file object in `index()` — fetch once, reuse for hashing and DCM parsing | 30 min |
| M16 | Replace `await asyncio.sleep(1)` with exponential backoff: `sleep = min(60, sleep * 2)` with jitter | 15 min |
| M14 | Already handled in Sprint 0 (log.warning on corrupt DICOM) | — |

### Sprint 4 Gate

```bash
cd backend && python -m pytest tests/ -v --tb=short -W error::Warning
```

---

## 6. Sprint 5 — Observability (Day 5-6)

### Track A5.1: Structured logging (`backend/log.py`, `backend/app.py`)

| ID | Change | Effort |
|----|--------|--------|
| H22 | Replace `logging.Formatter(...)` with JSON formatter (e.g., `python-json-logger` or manual `json.dumps`) | 2h |
| H22 | Add middleware to inject `request_id` into logging context (via `contextvars` or `logging.LoggerAdapter`) | 1h |
| — | Add Prometheus metrics: `starlette_exporter` or manual middleware for request count, latency histogram, error rate | 1h |
| — | Add component-level health check endpoint (`GET /health`) that checks DB pool, ES client, storage backends | 30 min |

### Sprint 5 Gate

```bash
cd backend && python -m pytest tests/ -v --tb=short -W error::Warning
```

---

## 7. Sprint 6 — Testing (Day 5-8)

### Track A6.1: Fix flaky tests

| ID | Change | Effort |
|----|--------|--------|
| H18 | `test_ratelimit.py:58`: Replace `time.sleep(0.06)` with mocked `datetime.now` + manual time advancement | 30 min |
| H19 | `test_db_table.py:10`: Remove `Table.tables.clear()` from `setup_method`. Use `tmp_path`-scoped fixture that creates a fresh `Table` subclass per test | 1h |
| H20 | `test_config.py:44,54,61`: Refactor config to accept `dict` overrides instead of env vars. Avoid `importlib.reload()` entirely | 2h |

### Track A6.2: Integration test infrastructure

| ID | Change | Effort |
|----|--------|--------|
| — | Create `backend/tests/conftest.py`: async fixtures for test DB, table creation, test data seeding | 3h |
| — | Write integration tests for all 11 DB tables (happy path + error cases per table) | 8h |
| — | Write auth flow integration test (login → token → authenticated request → expiry) | 2h |
| — | Write DICOM store E2E test (fake DICOM bytes → store → fetch → verify) | 2h |
| — | Add `testcontainers-postgres` dependency or documented test DB setup | 1h |

### Track A6.3: Load tests

| ID | Change | Effort |
|----|--------|--------|
| — | Create `backend/tests/load/` with k6 or locust scenarios: file upload, search, DICOM SCP | 4h |
| — | Create CI pipeline for load tests (separate from unit test run) | 1h |

### Sprint 6 Gate

```bash
cd backend && python -m pytest tests/ -v --tb=short -W error::Warning
cd frontend && npx vitest run
```

---

## 8. Sprint 7 — Advanced Redis Features (Day 6-8)

### Track A7.1: WebSocket → Redis pub/sub (`backend/api/ws.py`)

| ID | Change | Effort |
|----|--------|--------|
| C10 | Replace module-level `files` dict with Redis pub/sub channels (`channel:file:{file_id}`). Each worker subscribes to channels for files it has active connections on. Broadcast via `PUBLISH`, receive via `SUBSCRIBE` | 4h |

Requires:
- `redis` (or `aioredis`) dependency added to `requirements.txt`
- `async ConnectionManager` class that manages Redis pub/sub per file
- Worker-scoped local cache for connected clients (still in memory per worker, but state is consistent via Redis)

### Sprint 7 Gate

```bash
cd backend && python -m pytest tests/ -v --tb=short -W error::Warning
```

---

## 9. Sprint 8 — Frontend (Day 6-9, parallel with Sprints 5-7)

### Track A8.1: Login hardening (`frontend/src/login/Login.tsx`)

| ID | Change | Effort |
|----|--------|--------|
| L13 | Add progressive frontend delay on failed login attempts (exponential: 1s, 2s, 4s...) or integrate a CAPTCHA service | 4h |

### Track A8.2: Secure token storage (`frontend + backend`)

| ID | Change | Effort |
|----|--------|--------|
| L14 | Backend: add `Set-Cookie: token=<jwt>; HttpOnly; Secure; SameSite=Strict; Path=/api` on login response. Frontend: remove localStorage token reads; rely on cookie. `helpers.ts`: remove `X-Auth-Pacs` header population from localStorage | 4h |

### Track A8.3: Minor fixes

| ID | Change | Effort |
|----|--------|--------|
| L15 | Replace `PAGINATION.limit = 5` side effect in `Sidebar.tsx` with React state or context-based pagination config | 30 min |
| — | Add retry logic to `useFetch`/`helpers.request`: retry on 5xx with exponential backoff (max 3 retries) | 1h |
| — | Add progressive image loading to CornerstoneElement: load thumbnail first, then full resolution | 2h |
| — | Add bundle analysis + code-split Viewer: separate chunk for Cornerstone-heavy pages | 2h |

### Sprint 8 Gate

```bash
cd frontend && npx tsc --noEmit && npx vitest run && npx vite build
```

---

## 10. Merge Strategy

```
main
├── [Sprint 0] production-hardening/foundation
│   └── merge → main
├── [Sprint 1] production-hardening/schema
│   └── merge → main
├── [Sprint 2] production-hardening/data-integrity
│   └── merge → main
├── [Sprint 3] production-hardening/auth
│   └── merge → main
├── [Sprint 4] production-hardening/perf
│   └── merge → main
├── [Sprint 5] production-hardening/observability
│   └── merge → main
├── [Sprint 6] production-hardening/testing
│   └── merge → main
├── [Sprint 7] production-hardening/redis
│   └── merge → main
└── [Sprint 8] production-hardening/frontend
    └── merge → main
```

Each sprint is a feature branch. After the sprint gate passes (all tests, typecheck, build), squash-merge into `main`. This keeps `main` always in a working state and allows reverting any sprint independently.

For sprints with parallel tracks (Sprints 0, 2, 3, 4, 5): each track gets a sub-branch merged into the sprint branch before the sprint is merged to `main`.

---

## 11. Rollback Plan

| Scenario | Action |
|----------|--------|
| Sprint 1 migration fails | `alembic downgrade -1` to revert migration 006 |
| Data integrity bug in Sprint 2 | Revert the specific file changes via `git revert` |
| Auth bug in Sprint 3 | Revert sprint branch + roll back token format change (old tokens without `jti` still valid) |
| Performance regression | Revert specific commit; DB pool changes are config-level |
| Frontend regression | Revert sprint branch; old token system still works |

---

## 12. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Migration 006 conflicts with existing data (duplicate usernames) | Medium | High | Pre-migration dedup script (included in sprint) |
| Redis-dependent features fail if Redis is down | Medium | High | Graceful fallback: in-memory rate limit, no WS coherency |
| ES atomicity change breaks uploads | Low | High | Option B (compensating txn) is safe fallback |
| Token format change invalidates active sessions | Low | Medium | Old tokens without `jti` still pass verification |
| Frontend cookie auth breaks existing tabs | Low | Medium | Support both `X-Auth-Pacs` and cookie during transition window |