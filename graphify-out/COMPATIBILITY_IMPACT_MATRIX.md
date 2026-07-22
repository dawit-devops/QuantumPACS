# Compatibility Impact Matrix — OpenPACS

## Dependency → Affected Modules Mapping

---

### Backend Dependencies

| Dependency | Files/Modules Affected | Usage Type | Risk | Refactor Scope |
|---|---|---|---|---|
| **starlette** 0.12.8 | `app.py`, `api/routes.py`, `api/auth.py`, `api/files.py`, `api/logs.py`, `api/patient.py`, `api/replicas.py`, `api/users.py`, `api/utils.py`, `api/ws.py`, `storage/local_storage.py`, `storage/s3.py`, `storage/b2.py` | **Framework** — entire app | 🔴 High | ~15 files. Router API changed (`Router`→`Route` immutability). Middleware API changed. `UJSONResponse` → `JSONResponse`. `HTTPEndpoint` class-based views → function-based. Startup/shutdown events API changed. |
| **asyncpg** 0.18.3 | `db/conn.py`, all `db/*.py` modules | **Infrastructure** — DB access | 🟡 Medium | Connection pool API stable. Minor changes in `Pool` constructor. |
| **aiobotocore** 0.10.3 | `storage/s3.py` | **Infrastructure** — S3 storage | 🔴 High | Entire client API changed in 2.x. `create_client()` → session-based. `get_client()` → `AioSession`. |
| **b2sdk** 1.0.0rc1 | `storage/b2.py` | **Infrastructure** — B2 storage | 🔴 High | RC → stable has breaking auth API. `B2Api` initialization changed. |
| **elasticsearch-async** 6.2.0 | `es/es.py`, `es/mapping.py`, `sync.py`, `lifecycle.py`, `es_reindex.py` | **Infrastructure** — Search | 🚨 Critical | Library archived. Must migrate to `elasticsearch-py` 7.x/8.x async client. `AsyncElasticsearch` → `AsyncElasticsearch` from `elasticsearch[async]`. Mapping/query API changed. |
| **pydicom** 1.3.0 | `dcm/file.py` | **Business Logic** — DICOM parsing | 🟡 Medium | 1.3→2.0 had major tag API changes (removed `dataset` property shortcuts). 2.0→3.0 added type hints. `parse_file()` still works but tag access patterns changed. |
| **pynetdicom** 1.4.1 | `dcm/server.py` | **Business Logic** — DICOM networking | 🟡 Medium | 1.4→2.0→3.0: `AE` class API changed. `StoragePresentationContexts` → different import path. Event handling (`evt`) signature changed. |
| **PyJWT** 1.7.1 | `api/auth.py`, `api/utils.py` | **Security** — Auth tokens | 🔴 High | 1.x→2.x: `jwt.decode()` now requires `algorithms` parameter explicitly. `jwt.encode()` returns bytes not string. `PyJWTError` → different exception hierarchy. Must use `algorithms=["HS256"]`. |
| **PyPika** 0.35.2 | `db/table.py`, `db/patient.py`, `db/study.py`, `db/series.py`, `db/replica.py`, `db/replica_files.py`, `db/files.py`, `db/log.py`, `db/file_changes.py` | **Infrastructure** — Query builder | 🟢 Low | API is largely backward-compatible. `PostgreSQLQuery` still exists. Minor import path changes. |
| **PyYAML** 5.1.2 | `config.py` | **Utility** — Config parsing | 🟢 Low | `FullLoader` → `SafeLoader` recommended. `yaml.load()` still works with Loader arg. |
| **gunicorn** 19.9.0 | `api_conf.py`, `start.sh` | **Infrastructure** — WSGI server | 🟡 Medium | Config API mostly stable. Workers param still same. |
| **uvicorn** 0.8.6 | `app.py`, `start.sh` | **Infrastructure** — ASGI server | 🟡 Medium | `uvicorn.run()` API changed. `workers` param moved. |

---

### Frontend Dependencies

| Dependency | Files/Modules Affected | Usage Type | Risk | Refactor Scope |
|---|---|---|---|---|
| **react** 16.8.6 → 18.x+ | All `.js` files | **Framework** — Entire UI | 🔴 High | 16→18: Automatic batching, `useId` hook, `useDeferredValue`. 18→19: `use()`, refs as props, context improvements. Most functional components will work, but `CornerstoneElement` is a class component. |
| **react-scripts** 3.0.1 | Build pipeline (no direct imports) | **Build System** | 🚨 Critical | Must replace with Vite. All scripts (`start`, `build`, `test`) change. `process.env` vars → `import.meta.env`. Proxy config. |
| **antd** 3.21.2 | `Login.js`, `Account.js`, `Sidebar.js`, `Detail.js`, `Files.js`, `CornerstoneElement.js`, `Logs.js`, `Patient.js`, `Replicas.js`, `Users.js`, `Share.js`, `Managment.js`, `EditableTable.js`, `Changes.js`, `AdminFiles.js`, `AdvancedSearch.js`, `EditReplica.js`, `EditUser.js` | **UI Library** — All pages | 🔴 High | 3→4: Icon system changed (`Icon` → `@ant-design/icons`). Form API changed (`Form.create` → `Form` hooks). `Table` API changed. `Modal` API changed. `message.warn` → `message.warning`. LocaleProvider → ConfigProvider. 4→5: Less → CSS-in-JS. Moment.js → Dayjs. `babel-plugin-import` no longer needed. |
| **react-router-dom** 5.0.1 | `index.js`, `Sidebar.js`, `Detail.js`, `Files.js`, `Login.js`, `Account.js`, `NotFound.js`, `Patient.js`, `LinkExt.js`, `Share.js`, `Managment.js` | **Framework** — Routing | 🔴 High | v5→v6: `<Switch>` → `<Routes>`. `<Route component={}>` → `<Route element={}>`. `withRouter` → hooks (`useParams`, `useNavigate`, `useLocation`). `history.push()` → `navigate()`. |
| **cornerstone-tools** 3.18.3 | `CornerstoneElement.js` | **Business Logic** — DICOM viewer | 🟡 Medium | v3→v6/v7: `cornerstoneTools.init()` → different. Tool registration API changed. `saveToolState()`/`restoreToolState()` may differ. External references setup still similar. |
| **cornerstone-wado-image-loader** 3.0.0 | `CornerstoneElement.js` | **Business Logic** — Image loading | 🟡 Medium | v3→v4: `configure()` API changed. `beforeSend` callback still exists. Image ID format still `wadouri:`. |
| **cornerstone-math** 0.1.8 | `CornerstoneElement.js` | **Utility** — Math helpers | 🟢 Low | Merged into cornerstone-tools in later versions. May not be needed as separate import. |
| **hammerjs** 2.0.8 | `CornerstoneElement.js` | **Utility** — Touch gestures | 🟢 Low | Stable API. Used only as external for cornerstoneTools. |

---

## Risk Classification Legend

- 🚨 **Critical** — Security vulnerability, no patches available, blocks all other upgrades
- 🔴 **High** — Breaking API changes across multiple files, requires significant refactoring
- 🟡 **Medium** — Breaking changes in isolated modules, moderate refactoring
- 🟢 **Low** — Backward-compatible or trivial changes

---

## Dependency Upgrade Blockers

```
Python 3.7 EOL
  └── Blocks upgrading: starlette (>0.42 requires 3.10), uvicorn (>=0.30 requires 3.8),
      asyncpg (>0.28 requires 3.8), aiobotocore (2.x requires 3.8+)
  
CRA/react-scripts sunset
  └── Blocks upgrading: React 18/19 (CRA 3 doesn't support), antd 5.x (requires
      modern build pipeline), all modern JS tooling
  
Elasticsearch-async archived
  └── Blocks: ES client upgrade, ES 8.x migration, search reliability
```

---

## Phased Upgrade Dependency Graph

```
Phase 0 (Foundation):
  Python 3.7 → 3.11 LTS (or 3.12)
  PostgreSQL 11.4 → 16 LTS
  CRA → Vite

Phase 1 (Security):
  PyJWT 1.7.1 → 2.x
  elasticsearch-async → elasticsearch-py 8.x async

Phase 2 (Framework):
  starlette 0.12 → 0.35 (LTS bridge) → 1.x
  react 16 → 18 (bridge) → 19
  react-router-dom 5 → 6

Phase 3 (UI):
  antd 3 → 4 (bridge) → 5

Phase 4 (Storage):
  aiobotocore 0.10 → 2.x
  b2sdk 1.0.0rc → 2.x

Phase 5 (DICOM):
  pydicom 1.3 → 2.x → 3.x
  pynetdicom 1.4 → 2.x → 3.x

Phase 6 (Remaining):
  asyncpg, uvicorn, gunicorn, PyPika, PyYAML, etc.
  cornerstone-tools 3 → 6/7 (if needed)
