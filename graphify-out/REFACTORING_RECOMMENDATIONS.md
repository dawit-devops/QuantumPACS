# Refactoring Recommendations — OpenPACS

---

## Safe Refactor Targets (Low Risk, High Payoff)

### 1. DB Connection as Singleton → Dependency Injection

**Current (`db/conn.py`):** Per-process singleton via `os.getpid()` dict. Every model calls `get_conn()` which checks PID.

**Recommendation:** Extract a `Database` class with connection pool as instance, inject into models.

```python
# BEFORE — in every model:
class Files:
    async def find(self):
        conn = await get_conn()
        # ...

# AFTER:
class Files:
    def __init__(self, db: Database):
        self.db = db
    
    async def find(self):
        conn = await self.db.get_conn()
        # ...
```

**Impact:** 10 model files. Enables unit testing with mock DB. No behavior change.

### 2. Extract API Response Helpers

**Current:** Every handler returns `UJSONResponse` or `JSONResponse` directly.

**Recommendation:** Create `api/response.py` with helpers:
```python
def ok(data, status=200): ...
def created(data): ...
def not_found(message="Not found"): ...
def validation_error(fields): ...
```

**Impact:** 9 handler files. Unifies error format. Enables Swagger/OpenAPI generation later.

### 3. Centralize JWT Token Logic

**Current:** Token generation in `api/utils.py`, decoding in `api/auth.py`.

**Recommendation:** Extract `api/tokens.py` with `create_token()` and `verify_token()`. The JWT compat adapter (Phase 1.1) lives here.

**Impact:** Low effort. Eliminates duplicate `jwt.decode()` config.

### 4. Extract Database Migration System

**Current:** `db_init.py` creates all tables at once. No migration history.

**Recommendation:** Adopt `alembic` or a simple sequential migration system:
- One-time: dump schema as `migrations/001_initial.sql`
- Future: numbered migration files with up/down
- Track applied migrations in a `_migrations` table

**Impact:** New capability. Existing init code stays until first real migration.

### 5. Endpoint Input Validation

**Current:** No input validation for most API params (query params, request bodies).

**Recommendation:** Add `pydantic` schemas for request validation in a `api/schemas/` directory:
```python
from pydantic import BaseModel

class FileSearchQuery(BaseModel):
    query: str
    page: int = 1
    limit: int = 10
```

**Impact:** New capability. Wraps existing handlers gradually.

---

## Optional Improvements (Medium Risk)

### 6. PyPika ORM → SQLAlchemy (Deferred)

**Current:** Custom PyPika-based `Table` class with manual query building.

**Recommendation:** Consider SQLAlchemy 2.0 async for long-term maintainability. **Not recommended now** — the current ORM works and is simple. Revisit after all other upgrades are done.

**Risk:** High effort, full ORM rewrite. Value: better migration tooling, type safety, ecosystem.

### 7. WebSocket → Server-Sent Events (Optional)

**Current:** WebSocket for collaborative annotation sync.

**Recommendation:** Keep WebSocket. It works. SSE only if browser compatibility becomes an issue.

### 8. Frontend State Management (Optional)

**Current:** No Redux/MobX/Zustand. All state is local `useState` + `useFetch` hook.

**Recommendation:** Add `zustand` only if cross-component shared state becomes unmanageable. Current pattern is fine for this scale.

---

## Deferred Risk Areas

### 9. Cornerstone.js Ecosystem Fragmentation

The cornerstone libraries (cornerstone-core, cornerstone-tools, etc.) have been in flux. OHIF merged them into `cornerstone3D` / `@cornerstonejs/core`. The v3 → v6 upgrade path is unclear.

**Recommendation:** Keep current v3 pinned. Only upgrade if a security issue or browser compatibility problem arises. The DICOM viewer is critical path — any regression is immediately visible to radiologists.

### 10. Elasticsearch 8.x Migration

Elasticsearch 8.x changes security defaults (TLS required by default). The current `elasticsearch-async` library targets ES 6.x API.

**Recommendation:** Phase 1.2 replaces the client library. The ES container upgrade to 8.x is a separate infra operation. Test reindexing thoroughly.

### 11. No Test Suite

**Current:** Zero tests in both frontend and backend.

**Recommendation:** Add tests *before* starting Phase 2 (Framework upgrades). Write integration tests for:
- DICOM store + parse pipeline
- File upload → search → download flow
- JWT auth middleware
- Replica sync cycle
- Critical frontend rendering (Files, Detail, Login)

### 12. Docker Compose for Production

**Current:** Single `docker-compose.yaml` mixes infra + app.

**Recommendation:** Split into `docker-compose.infra.yaml` (PG + ES) and `docker-compose.app.yaml` (app + DCM server). Add health checks, resource limits.
