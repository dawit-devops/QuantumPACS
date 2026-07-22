# Non-Breaking Upgrade Plan — OpenPACS

Strategy: **Strangler Fig pattern** — upgrade incrementally with compatibility wrappers, never breaking production.

---

## Phase 0: Foundation (4-6 weeks)

Goal: Unblock all dependency upgrades by modernizing the runtime and build system.

### 0.1 — Python Runtime Upgrade: 3.7.4 → 3.11 LTS

**Strategy:** Parallel container deployment.

1. Build new Docker image `openpacs:py311` using `python:3.11-slim`
2. Deploy alongside existing `openpacs:latest` behind load balancer
3. Route internal health checks to both; once py311 passes all integration checks, swap traffic
4. Keep rollback: old container still running for 48h

**Adapter needed:** None — Python 3.11 is source-compatible with 3.7 for this codebase (no removed stdlib APIs used).

**Risk:** Low. Test with `pip install -r requirements.txt` on 3.11. Pin asyncio event loop.

### 0.2 — PostgreSQL 11.4 → 16 LTS

**Strategy:** Logical replication migration.

1. Deploy PostgreSQL 16 as read replica (pglogical/pg_basebackup)
2. Run both in parallel for 1 week
3. Switch application connection string via env var `DB_HOST`
4. Drop old PG 11 after validation

**Adapter needed:** None — `asyncpg` works with PG 16. No PG 11-specific features used.

**Risk:** Low. Test query compatibility first. PG dump/restore path as fallback.

### 0.3 — CRA/Vite Migration (Critical Path)

**Strategy:** In-place migration using `vite` + `vite-plugin-react` with compatibility shims.

**Migration steps:**

1. `npm install --save-dev vite @vitejs/plugin-react`
2. Create `vite.config.js`:
   ```js
   import { defineConfig } from 'vite';
   import react from '@vitejs/plugin-react';
   export default defineConfig({
     plugins: [react()],
     server: { port: 3000, proxy: { '/api': 'http://localhost:8080' } },
     define: { 'process.env': {} },  // CRA compat shim
   });
   ```
3. Move `index.html` from `public/` to root, add `<script type="module" src="/src/index.js">`
4. Move `public/favicon.ico` to `public/` (Vite serves from root)
5. Replace `process.env.PUBLIC_URL` → inline or `import.meta.env.BASE_URL`
6. Test: `npx vite` should serve the app

**Compatibility shims needed:**
- `process.env` → `import.meta.env` (define `process.env = {}` in vite config as bridge)
- JSX `import React` — Vite's `@vitejs/plugin-react` auto-injects the JSX runtime
- `package.json` scripts: `"start": "vite", "build": "vite build", "preview": "vite preview"`
- ESLint: update `.eslintrc.json` parser to `@babel/eslint-parser` or switch to `eslint-plugin-react` with flat config

**Risk:** Medium. `antd` 3.x Less import may need `vite-plugin-less`. Test build output matches existing behavior.

---

## Phase 1: Security (2-3 weeks)

### 1.1 — PyJWT 1.7.1 → 2.x

**Strategy:** Adapter wrapper.

```python
# api/jwt_compat.py — Compatibility adapter
import jwt as jwt_new
from jwt import PyJWTError  # Same exception name in 2.x

# v1.x encode returns str; v2.x returns bytes
def compat_jwt_encode(payload, key, algorithm='HS256'):
    token = jwt_new.encode(payload, key, algorithm=algorithm)
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    return token

# v2.x requires explicit algorithms parameter
def compat_jwt_decode(token, key, algorithms=['HS256']):
    return jwt_new.decode(token, key, algorithms=algorithms)
```

Replace in `api/utils.py` and `api/auth.py` with `from .jwt_compat import compat_jwt_encode, compat_jwt_decode`. No behavior change.

**Rollback:** Swap imports back. Stateless change.

### 1.2 — Elasticsearch Client Replacement

**Strategy:** Facade/adapter over new `elasticsearch` 8.x async client.

1. Install `elasticsearch>=8.0,<9.0`
2. Create adapter `es/es_adapter.py` matching the current `elasticsearch-async` API surface
3. Replace imports in `es/es.py` with adapter
4. The `index_file()`, `search()`, `delete()` methods should be functionally identical

```python
# es/es_adapter.py — Facade pattern
from elasticsearch import AsyncElasticsearch, NotFoundError

class AsyncElasticsearchAdapter:
    def __init__(self, hosts):
        self.client = AsyncElasticsearch(hosts)
    
    async def index(self, index, id, body, **kwargs):
        return await self.client.index(index=index, id=id, document=body, **kwargs)
    
    async def search(self, index, body, **kwargs):
        return await self.client.search(index=index, query=body.get('query'), **kwargs)
    
    async def delete(self, index, id, **kwargs):
        try:
            return await self.client.delete(index=index, id=id, **kwargs)
        except NotFoundError:
            return None
    
    async def close(self):
        await self.client.close()
```

Reindex existing ES data via `es_reindex.py`.

**Risk:** Low-Medium. Query DSL may differ slightly between ES 6/7/8 (field mapping removal). Test search queries match.

---

## Phase 2: Framework (3-4 weeks)

### 2.1 — Starlette 0.12.8 → 0.35.x (bridge) → 1.x

**Strategy:** Progressive upgrade through minor versions.

**Bridge v0.12 → 0.35:**
- `UJSONResponse` → `JSONResponse` (ujson still works as serializer)
- `Router` → `Route` immutability fix (routes are frozen in later 0.x)
- Middleware `@app.middleware("http")` still works
- `AuthenticationMiddleware` API unchanged

**Testing:** Run test suite after each minor bump. Pin to highest 0.x that passes before jumping to 1.x.

**v0.35 → 1.x:**
- Python 3.10+ required (Phase 0.1 must be done)
- `HTTPEndpoint` class-based views → function-based views (can use adapter pattern)
- `WebSocketEndpoint` → updated API

### 2.2 — React 16 → 18 (bridge) → 19

**Strategy:** Dependency bump + codemod.

1. `npm install react@18 react-dom@18`
2. Replace `ReactDOM.render(<App />, root)` with `createRoot(root).render(<App />)`
3. No other breaking changes for this codebase (no legacy lifecycle methods used except in `CornerstoneElement` class component)
4. Test all pages render without console warnings
5. If stable, upgrade to React 19: `npm install react@19 react-dom@19`

**Adapter needed for CornerstoneElement:**
- Class component `componentDidMount/WillUnmount` → no change needed for React 18
- For React 19, check ref forwarding compatibility

### 2.3 — react-router-dom v5 → v6

**Strategy:** Codemod with manual review.

Key changes in `index.js`:
```jsx
// BEFORE (v5):
<Router history={history}>
  <Switch>
    <Route exact path="/login" component={Login} />
    <Route exact path="/" component={Files} />
  </Switch>
</Router>

// AFTER (v6):
<BrowserRouter>
  <Routes>
    <Route path="/login" element={<Login />} />
    <Route path="/" element={<Files />} />
  </Routes>
</BrowserRouter>
```

Replace `withRouter()` → hooks:
- `this.props.history` → `useNavigate()`
- `this.props.match.params.id` → `useParams()`
- `this.props.location` → `useLocation()`

Custom `history.js` → replace with `useNavigate` or `<Navigate>` redirect component.

**Risk:** Medium. Affects 10 files with router usage. Test every route after migration.

---

## Phase 3: UI Library (2-3 weeks)

### 3.1 — antd 3.x → 4.x (bridge)

**Migration steps (v3→v4):**

1. `npm install antd@4` and `npm install @ant-design/icons`
2. Replace `<Icon type="xxx" />` → `<xxxOutlined />` from `@ant-design/icons`
3. Replace `Form.create()` HOC → function components with hooks:
   ```jsx
   // BEFORE:
   const WrappedForm = Form.create()(MyForm);
   
   // AFTER:
   function MyForm() {
     const [form] = Form.useForm();
     return <Form form={form}>...</Form>;
   }
   ```
4. Replace `LocaleProvider` → `ConfigProvider`
5. Replace `message.warn` → `message.warning`
6. Table API: `rowKey` prop required, `pagination` object format changed
7. `Modal` no longer needs `visible` boolean on children

### 3.2 — antd 4.x → 5.x

1. `npm install antd@5`
2. Remove Less imports (`import 'antd/dist/antd.css'` → Vite handles CSS-in-JS automatically)
3. Remove `babel-plugin-import` (not needed with Vite)
4. Replace Moment.js with Dayjs (unless date formatting is heavy)
5. Use `ConfigProvider` theme tokens instead of Less variables
6. `message.warning` still works; `message.info/success/error/warning` all fine

**Vite Less plugin (bridge):** If custom Less variables were used:
```bash
npm install -D vite-plugin-less
```

---

## Phase 4: Storage Backends (2 weeks)

### 4.1 — aiobotocore 0.10.3 → 2.x

**Adapter pattern for S3:**

```python
# storage/s3_adapter.py
from aiobotocore.session import AioSession  # New API

class S3Client:
    def __init__(self, region, access_key, secret_key):
        self.session = AioSession()
        self.config = {'region_name': region,
                       'aws_access_key_id': access_key,
                       'aws_secret_access_key': secret_key}
    
    async def get_object(self, bucket, key):
        async with self.session.create_client('s3', **self.config) as client:
            return await client.get_object(Bucket=bucket, Key=key)
```

Replace `get_client()` → `S3Client()` in `storage/s3.py`.

### 4.2 — b2sdk 2.x

Similar adapter pattern. Check B2 API compatibility for the operations used (`fetch`, `store`, `delete`, `copy`).

---

## Phase 5: DICOM Libraries (2 weeks)

### 5.1 — pydicom 1.3 → 2.x → 3.x

**Changes to expect:**
- `ds.PatientName` → `ds.PatientName` (unchanged for basic access)
- `ds.data_element('Tag')` still works
- `pydicom.read_file()` → removed in 3.0 (use `dcmread()` instead)
- Some tag keywords renamed

**Adapter wrapper in `dcm/file.py`:**
```python
# Compat check
if pydicom.__version__.startswith('1.'):
    from pydicom import read_file as dcmread
```

### 5.2 — pynetdicom 1.4 → 2.x → 3.x

**Changes:**
- `AE.start_server()` still exists but signature changed
- `evt.EVT_C_STORE` → `evt.EventType.C_STORE`
- `StoragePresentationContexts` → different import

**Test with DICOM test modality before production deploy.**

---

## Phase 6: Remaining Libraries (1 week)

Non-breaking bumps for:
- `asyncpg 0.18 → 0.29` — test pool creation
- `uvicorn 0.8 → 0.30` — test app startup
- `gunicorn 19.9 → 23` — test worker config
- `PyPika 0.35 → 0.48` — test query generation
- `PyYAML 5.1 → 6.x` — test config loading
- `python-dateutil 2.8 → 2.9` — test share link expiry
- `aiofiles 0.4 → 24.x` — test file ops
- `ujson 1.35 → 5.x` — test JSON responses

**All tested individually, one pin bump at a time.**

---

## Rollback Plan

Every upgrade phase has a documented rollback:

| Phase | Rollback Action | Downtime | Data Loss |
|---|---|---|---|
| Phase 0.1 (Python) | Switch load balancer to old container | <30s | None |
| Phase 0.2 (PostgreSQL) | Point DB_HOST to old PG 11 | <30s | None (replica) |
| Phase 0.3 (Vite) | `npm install react-scripts@3`, revert configs | Build time | None |
| Phase 1.1 (PyJWT) | Revert import to direct jwt calls | <1min | None |
| Phase 1.2 (ES) | Revert to elasticsearch-async adapter | <1min | None |
| Phase 2-6 | `git revert` the commit, redeploy | Build time | None |
