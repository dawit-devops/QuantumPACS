# Graph Report - .  (2026-07-21)

## Corpus Check
- Corpus is ~15,144 words - fits in a single context window. You may not need a graph.

## Summary
- 523 nodes · 1034 edges · 33 communities (23 shown, 10 thin omitted)
- Extraction: 78% EXTRACTED · 22% INFERRED · 0% AMBIGUOUS · INFERRED: 223 edges (avg confidence: 0.67)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Auth & File API Handlers
- API Route Registry
- Frontend Dependencies
- File & Replica CRUD
- Patient & DB Models
- DICOM Viewer Internals
- ESLint Config
- System Architecture Concepts
- Storage Layer
- Share, Replicas, Helpers
- App Shell & Viewer UI
- Account, History, Hooks
- Detail Page & EditableTable
- B2 Storage Backend
- File Browser & Config
- Sidebar, Logs, Patient
- WebSocket & Token
- Utility Helpers
- DB Management Script
- Auth User Model
- Sidebar & Admin Check
- File Hashing & Share
- Delete Management
- Start Script
- Docker Build Script
- Frontend Manage Script
- HTML Entry Point

## God Nodes (most connected - your core abstractions)
1. `ReplicaFiles` - 40 edges
2. `Replica` - 38 edges
3. `CornerstoneElement` - 33 edges
4. `request()` - 32 edges
5. `Files` - 30 edges
6. `get_conn()` - 29 edges
7. `Storage` - 25 edges
8. `react` - 24 edges
9. `Table` - 23 edges
10. `Users` - 22 edges

## Surprising Connections (you probably didn't know these)
- `Status` --uses--> `Table`  [INFERRED]
  backend/db/replica_files.py → backend/db/table.py
- `User` --uses--> `SharedFiles`  [INFERRED]
  backend/api/auth.py → backend/db/share_files.py
- `get_file_by_id()` --calls--> `Files`  [INFERRED]
  backend/api/files.py → backend/db/files.py
- `get_patient_by_id()` --calls--> `get_id()`  [INFERRED]
  backend/api/patient.py → backend/api/utils.py
- `get_patient_by_id()` --calls--> `get_conn()`  [INFERRED]
  backend/api/patient.py → backend/db/conn.py

## Import Cycles
- None detected.

## Communities (33 total, 10 thin omitted)

### Community 0 - "Auth & File API Handlers"
Cohesion: 0.05
Nodes (20): AuthenticationBackend, TokenAuth, DownloadData, DownloadFiles, DownloadToken, FileChangesHandler, FileHandler, FilesHandler (+12 more)

### Community 1 - "API Route Registry"
Cohesion: 0.07
Nodes (34): LogsHandler, HTTPEndpoint, add_cors(), custom_middleware(), http_exception(), create_conn(), init_db(), init() (+26 more)

### Community 2 - "Frontend Dependencies"
Cohesion: 0.05
Nodes (43): antd, cornerstone-core, cornerstone-math, cornerstone-tools, cornerstone-wado-image-loader, cornerstone-web-image-loader, dicom-parser, eslint-plugin-react (+35 more)

### Community 3 - "File & Replica CRUD"
Cohesion: 0.10
Nodes (17): get_file_by_id(), HTTPEndpoint, ReplicaHandlers, ReplicasHandlers, ChangePassword, Login, HTTPEndpoint, UsersDeactivate (+9 more)

### Community 4 - "Patient & DB Models"
Cohesion: 0.09
Nodes (8): get_patient_by_id(), PatientHandler, HTTPEndpoint, Files, Patient, Series, Study, Table

### Community 6 - "ESLint Config"
Cohesion: 0.09
Nodes (25): jsx, env, browser, es6, extends, parserOptions, ecmaFeatures, ecmaVersion (+17 more)

### Community 7 - "System Architecture Concepts"
Cohesion: 0.11
Nodes (24): Backend (Python/Starlette), DICOM Support, Frontend (React/antd), Infrastructure, OpenPACS System, Storage Layer, PyJWT==1.7.1, react@16.8.6 (+16 more)

### Community 9 - "Share, Replicas, Helpers"
Cohesion: 0.18
Nodes (11): Share(), Wrapped, request(), AddReplica(), EditReplicaModal, s3regions, EditDelay, Replicas() (+3 more)

### Community 10 - "App Shell & Viewer UI"
Cohesion: 0.20
Nodes (8): bottomLeftStyle, bottomRightStyle, App(), NotFound(), addEventListener(), init(), onOpen(), react

### Community 11 - "Account, History, Hooks"
Cohesion: 0.21
Nodes (8): Account(), WrappedAccountForm, handleResponse(), history, TODO: optimize with reducer?, useFetch(), LoginForm(), WrappedLoginForm

### Community 12 - "Detail Page & EditableTable"
Cohesion: 0.21
Nodes (9): Changes(), columns, Detail(), wrap(), EditableCell(), EditableContext, editableFields, EditableFormRow (+1 more)

### Community 14 - "File Browser & Config"
Cohesion: 0.27
Nodes (8): PAGINATION, AdminFiles(), AdvancedSearch(), decodeUrl(), encodeUrl(), Files(), initialAdvancedFields, open()

### Community 15 - "Sidebar, Logs, Patient"
Cohesion: 0.27
Nodes (7): withSidebar(), columns, Logs(), columns, mappings, Patient(), wrap()

### Community 16 - "WebSocket & Token"
Cohesion: 0.22
Nodes (5): gen_token(), HTTPEndpoint, WebsocketHandler, WSToken, WebSocketEndpoint

### Community 17 - "Utility Helpers"
Cohesion: 0.46
Nodes (4): LinkExt(), encodeQuery(), parseParams(), updateQuery()

### Community 18 - "DB Management Script"
Cohesion: 0.62
Nodes (6): manage script, create_db(), create_exts(), drop_db(), handle_db(), postgres_psql()

### Community 20 - "Sidebar & Admin Check"
Cohesion: 0.70
Nodes (4): getKey(), getOpenKey(), Sidebar(), isAdmin()

## Knowledge Gaps
- **59 isolated node(s):** `start.sh script`, `build_docker.sh script`, `browser`, `es6`, `extends` (+54 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Storage` connect `Auth & File API Handlers` to `Storage Layer`, `B2 Storage Backend`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Why does `Table` connect `Patient & DB Models` to `Auth & File API Handlers`, `API Route Registry`, `File & Replica CRUD`?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **Why does `Replica` connect `Auth & File API Handlers` to `API Route Registry`, `File & Replica CRUD`, `Patient & DB Models`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Are the 27 inferred relationships involving `ReplicaFiles` (e.g. with `DownloadData` and `.get()`) actually correct?**
  _`ReplicaFiles` has 27 INFERRED edges - model-reasoned connections that need verification._
- **Are the 26 inferred relationships involving `Replica` (e.g. with `DownloadData` and `.get()`) actually correct?**
  _`Replica` has 26 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `Files` (e.g. with `.delete()` and `.post()`) actually correct?**
  _`Files` has 15 INFERRED edges - model-reasoned connections that need verification._
- **What connects `start.sh script`, `build_docker.sh script`, `browser` to the rest of the system?**
  _59 weakly-connected nodes found - possible documentation gaps or missing edges._