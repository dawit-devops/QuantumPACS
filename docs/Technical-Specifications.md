# QuantumPACS — Technical Specifications

**Version**: 2.0.0
**Status**: Final
**Date**: 2026-07-23

---

## 1. System Architecture

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Browser (React SPA)                          │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Cornerstone3D Viewer  │  Ant Design UI  │  React Router    │   │
│  │  (Stack viewport,      │  (Tables, Forms, │  (/login, /files,│   │
│  │   10 tools, WebSocket  │   Modals, Menu,  │   /patients/:id, │   │
│  │   annotation sync)     │   Layout)        │   /detail/:id)   │   │
│  └────────────────────────┴──────────────────┴──────────────────┘   │
│                         │           │                               │
│                    HTTP/HTTPS    WebSocket (WSS)                    │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────────┐
│                     Caddy Reverse Proxy (:80)                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Static file serving (dist/)  │  API proxy → :8080           │   │
│  │  SPA fallback (index.html)    │  WS proxy → :8080            │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────────┐
│                     Starlette API Server (:8080)                     │
│                                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ Auth     │  │ REST     │  │ WebSocket│  │ DICOM Listener    │  │
│  │ Middleware│  │ Endpoints│  │ Handler  │  │ (pynetdicom,      │  │
│  │ (JWT +   │  │ (/api/*) │  │ (/api/ws)│  │  port :11112)     │  │
│  │ ShareKey)│  │          │  │          │  │                   │  │
│  └──────────┘  └────┬─────┘  └────┬─────┘  └────────┬──────────┘  │
│                     │              │                   │            │
│              ┌──────▼──────┐  ┌───▼────┐  ┌──────────▼──────────┐ │
│              │ PostgreSQL  │  │ Sync   │  │ Storage Backends    │ │
│              │ (asyncpg)   │  │ Daemon │  │ (Local / S3 / B2)   │ │
│              │ :5432       │  │        │  │                     │ │
│              └──────┬──────┘  └───┬────┘  └────────────────────┘ │
│                     │             │                                │
└─────────────────────┼─────────────┼────────────────────────────────┘
                      │             │
              ┌───────▼───────┐ ┌───▼────────────┐
              │ PostgreSQL    │ │ Elasticsearch  │
              │ (LISTEN/NOTIFY)│ │ (Optional, :9200)│
              └───────────────┘ └────────────────┘
```

### 1.2 Component Responsibilities

| Component | Responsibility | Key Libraries |
|-----------|---------------|---------------|
| **Caddy** | TLS termination, SPA serving, API/WS reverse proxy | Caddy web server |
| **Starlette API** | HTTP request routing, middleware, response handling | Starlette 0.35.x, Uvicorn |
| **Auth Middleware** | JWT verification, share key auth, WebSocket auth | PyJWT 2.x, PBKDF2 |
| **REST Endpoints** | Study search, CRUD, file serving, admin APIs | Pydantic v2, PyPika |
| **WebSocket Handler** | Real-time annotation broadcast, pub/sub | Starlette WebSocket |
| **DICOM Listener** | DICOM C-STORE SCP on port 11112 | pynetdicom, pydicom |
| **Sync Daemon** | Replication, ES indexing, storage walking | asyncpg LISTEN/NOTIFY |
| **PostgreSQL** | Metadata, auth, audit, replication events | asyncpg |
| **Elasticsearch** | Full-text search index (graceful degradation) | elasticsearch-py 8.x |
| **Storage Backends** | File read/write/delete on backend | aiobotocore, b2sdk |
| **React SPA** | User interface, image viewer, state management | React 19, Ant Design 6, Cornerstone3D 5 |

---

## 2. API Specification

### 2.1 Base URL

All API endpoints are mounted under `/api/`.

- **Production**: `https://<host>/api/`
- **Development**: `http://localhost:8080/api/`
- **Dev proxy (Vite)**: `http://localhost:5173/api/` → proxied to `localhost:8080`

### 2.2 Authentication Header

```
X-Auth-Pacs: <JWT token>
```

Fallback for WebSocket and downloads:
```
?token=<JWT token>
```

Share links bypass auth via `shared_files` table key:
```
?key=<64-char-hex>
```

### 2.3 Response Format

All responses use helpers from `api/response.py`:

```typescript
// Success
{ "data": { ... } }                    // 200 OK
{ "data": { ... } }                    // 201 Created
{ }                                    // 204 No Content

// Error
{ "error": "description" }             // 400 Bad Request
{ "error": "Not found" }               // 404 Not Found
{ "error": "Unauthorized" }            // 401 Unauthorized
{ "error": "Forbidden" }               // 403 Forbidden
{ "error": "Server error: ..." }       // 500 Internal Server Error
```

### 2.4 Endpoint Reference

#### Authentication

| Method | Path | Auth | Request | Response | Description |
|--------|------|------|---------|----------|-------------|
| `POST` | `/api/login` | No | `{username, password}` | `{id, username, admin, token}` | Authenticate user |
| `POST` | `/api/change_password` | Yes | `{password}` | `{}` | Change own password |
| `GET` | `/api/health` | No | — | `{"status": "ok"}` | Health check |

#### Files (Studies)

| Method | Path | Auth | Request | Response | Description |
|--------|------|------|---------|----------|-------------|
| `GET` | `/api/files` | Yes | Query: `?<JSON>` | `{data: [...], total: N}` | Search files (ES) |
| `POST` | `/api/files` | Yes | `{query?, field filters}` | `{data: [...], total: N}` | Search files (POST) |
| `POST` | `/api/files/upload` | Yes | Multipart: `file` | `{}` (204) | Upload DICOM |
| `GET` | `/api/files/{id}` | Yes | — | `{id, patient, studies, ...}` | File detail with tree |
| `POST` | `/api/files/{id}` | Yes | `{tools_state?, tag?}` | `{}` | Update file metadata |
| `DELETE` | `/api/files/{id}` | Admin | — | `{}` | Delete file |
| `GET` | `/api/files/{id}/changes` | Yes | Pagination | `{data, total}` | Change audit trail |
| `POST` | `/api/files/{id}/share` | Yes | `{duration}` | `{key}` | Create share link |
| `GET` | `/api/files/{id}/data` | Yes | — | Binary/file | Serve DICOM data |
| `GET` | `/api/files/download_token` | Yes | — | `{token}` | Download auth token |
| `GET` | `/api/files/download.zip` | Yes | `?ids=1,2,3` | ZIP binary | Bulk download |
| `GET` | `/api/files/download.csv` | Yes | `?ids=1,2,3` | CSV text | Bulk metadata export |

#### Patients

| Method | Path | Auth | Request | Response | Description |
|--------|------|------|---------|----------|-------------|
| `GET` | `/api/patients/{id}` | Yes | — | `{id, patient_id, name, ... studies: [...]}` | Patient detail with tree |

#### Admin: Replicas

| Method | Path | Auth | Request | Response | Description |
|--------|------|------|---------|----------|-------------|
| `GET` | `/api/replicas` | Admin | — | `{data: [...], total: N}` | List all replicas |
| `POST` | `/api/replicas` | Admin | `{type, location, ...}` | `{}` | Add replica |
| `POST` | `/api/replicas/{id}` | Admin | `{delay?, master?}` | `{}` | Update replica |
| `DELETE` | `/api/replicas/{id}` | Admin | — | `{}` | Remove replica |

#### Admin: Users

| Method | Path | Auth | Request | Response | Description |
|--------|------|------|---------|----------|-------------|
| `GET` | `/api/users` | Admin | — | `{data: [...], total: N}` | List users |
| `POST` | `/api/users` | Admin | `{username, admin?}` | `{username, password}` | Create user |
| `POST` | `/api/users/deactivate` | Admin | `{id}` | `{}` | Deactivate user |
| `POST` | `/api/users/new_password` | Admin | `{id}` | `{password}` | Reset password |

#### Admin: Logs

| Method | Path | Auth | Request | Response | Description |
|--------|------|------|---------|----------|-------------|
| `GET` | `/api/logs` | Admin | Pagination | `{data: [...], total: N}` | System audit logs |

#### WebSocket

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/ws_token` | Yes | Get 1-minute WS token |
| `WS` | `/api/ws?token=` | Token | Real-time annotation sync |

### 2.5 WebSocket Protocol

#### Client → Server Messages

```json
// Subscribe to file state updates
{ "type": "open", "file": "<file_id>" }

// Broadcast annotation state to other viewers
{ "type": "send_state", "file": "<file_id>", "state": { ... }, "ver": 1 }
```

#### Server → Client Messages

```json
// State update from another subscriber
{ "type": "send_state", "file": "<file_id>", "state": { ... } }

// Initial state on subscribe (if state exists)
{ "type": "send_state", "file": "<file_id>", "state": { ... } }
```

### 2.6 Search API Contract

```json
// POST /api/files
// Body:
{
  "query": "Smith CT",          // free-text (optional)
  "results": 10,                // page size (default 10)
  "page": 1,                    // page number (default 1)
  "Modality": "CT",            // field filter (optional)
  "Patient ID": "P12345"       // field filter (optional)
}

// Response:
{
  "data": [
    {
      "id": 42,
      "Patient ID": "P12345",
      "Patient's Name": "Smith^John",
      "Study ID": "S20260723",
      "Study Description": "CHEST PA AND LAT",
      "Series Number": "1",
      "Series Description": "Scout",
      "Modality": "CT",
      "patient_db_id": 10,
      "study_db_id": 5,
      "series_db_id": 3
    }
  ],
  "total": 1
}
```

---

## 3. Database Schema

### 3.1 Entity-Relationship Diagram (Text)

```
┌───────────┐       ┌───────────┐       ┌───────────┐       ┌───────────┐
│  users    │       │ patients  │       │  studies  │       │  series   │
├───────────┤       ├───────────┤       ├───────────┤       ├───────────┤
│ id (PK)   │       │ id (PK)   │◄──────│ patient_id│◄──────│ study_id  │
│ username  │       │ patient_id│       │ study_id  │       │ number    │
│ password  │       │ name      │       │ desc      │       │ modality  │
│ admin     │       │ birth_date│       └───────────┘       │ desc      │
│ status    │       │ sex       │                            └───────────┘
│ created   │       │ meta (JB)│                                  │
│ updated   │       └───────────┘                                  │
└───────────┘                                                     │
                                                                   │
    ┌──────────────┐        ┌───────────┐                         │
    │ file_changes │        │   files   │◄─────────────────────────┘
    ├──────────────┤        ├───────────┤
    │ id (PK)      │◄───────│ id (PK)   │
    │ file_id (FK) │        │ patient_id│
    │ created      │        │ study_id  │        ┌────────────────┐
    │ by_user(FK)  │        │ series_id │        │ shared_files   │
    │ type         │        │ name      │        ├────────────────┤
    │ old          │        │ hash      │◄───────│ id (PK)        │
    │ new          │        │ indexed   │        │ file_id (FK)   │
    └──────┬───────┘        │ meta (JB) │        │ hash           │
           │                │ tools_st  │        │ expires        │
     ┌─────┴──────┐         │ created   │        └────────────────┘
     │   users    │         │ updated   │
     │ (FK ref)   │         │ deleted   │
     └────────────┘         └─────┬─────┘
                                  │
                         ┌────────┴────────┐
                         │  replica_files  │
                         ├─────────────────┤
                         │ replica_id (FK) │
                         │ file_id (FK)    │
                         │ location        │
                         │ status          │
                         │ created         │
                         │ updated         │
                         │ meta (JB)       │
                         │ UNIQUE(rep,fid) │
                         └────────┬────────┘
                                  │
                          ┌───────┴────────┐
                          │   replicas     │
                          ├────────────────┤
                          │ id (PK)        │
                          │ type           │
                          │ location       │
                          │ master         │
                          │ delay          │
                          │ status         │
                          │ total          │
                          │ meta (JB)      │
                          └────────────────┘

┌──────────────────┐
│      logs        │
├──────────────────┤
│ id (PK)          │
│ created          │
│ log              │
└──────────────────┘
```

### 3.2 DDL (Core Tables)

```sql
-- Requires extensions
CREATE EXTENSION IF NOT EXISTS intarray;
CREATE EXTENSION IF NOT EXISTS citext;

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username CITEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    admin BOOLEAN DEFAULT FALSE,
    status TEXT DEFAULT 'active',
    created TIMESTAMP DEFAULT NOW(),
    updated TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS patients (
    id SERIAL PRIMARY KEY,
    patient_id TEXT UNIQUE NOT NULL,
    name TEXT,
    birth_date TEXT,
    sex TEXT,
    meta JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS studies (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER REFERENCES patients(id) ON DELETE CASCADE,
    study_id TEXT,
    description TEXT,
    UNIQUE(patient_id, study_id)
);

CREATE TABLE IF NOT EXISTS series (
    id SERIAL PRIMARY KEY,
    study_id INTEGER REFERENCES studies(id) ON DELETE CASCADE,
    number TEXT,
    modality TEXT,
    description TEXT,
    UNIQUE(study_id, number)
);

CREATE TABLE IF NOT EXISTS files (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER REFERENCES patients(id) ON DELETE CASCADE,
    study_id INTEGER REFERENCES studies(id) ON DELETE CASCADE,
    series_id INTEGER REFERENCES series(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    hash TEXT,
    indexed BOOLEAN DEFAULT FALSE,
    meta JSONB DEFAULT '{}',
    tools_state JSONB DEFAULT '{}',
    created TIMESTAMP DEFAULT NOW(),
    updated TIMESTAMP DEFAULT NOW(),
    deleted BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS file_changes (
    id SERIAL PRIMARY KEY,
    file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
    created TIMESTAMP DEFAULT NOW(),
    by_user_id INTEGER REFERENCES users(id),
    type TEXT,
    old TEXT,
    new TEXT
);

CREATE TABLE IF NOT EXISTS replicas (
    id SERIAL PRIMARY KEY,
    type TEXT,
    location TEXT UNIQUE,
    master BOOLEAN DEFAULT FALSE,
    delay INTEGER DEFAULT 0,
    status TEXT,
    total INTEGER DEFAULT 0,
    meta JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS replica_files (
    id SERIAL,
    replica_id INTEGER REFERENCES replicas(id) ON DELETE CASCADE,
    file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
    location TEXT,
    status INTEGER DEFAULT 0,
    created TIMESTAMP DEFAULT NOW(),
    updated TIMESTAMP DEFAULT NOW(),
    meta JSONB DEFAULT '{}',
    UNIQUE(replica_id, file_id)
);

CREATE TABLE IF NOT EXISTS logs (
    id SERIAL PRIMARY KEY,
    created TIMESTAMP DEFAULT NOW(),
    log TEXT
);

CREATE TABLE IF NOT EXISTS shared_files (
    id SERIAL PRIMARY KEY,
    created TIMESTAMP DEFAULT NOW(),
    expires TIMESTAMP,
    file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
    hash TEXT
);

-- LISTEN/NOTIFY trigger for replica sync
CREATE OR REPLACE FUNCTION notify_event() RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify(
        'events',
        json_build_object(
            'table', TG_TABLE_NAME,
            'type', TG_OP,
            'old', row_to_json(OLD),
            'new', row_to_json(NEW)
        )::text
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER notify_event
    AFTER INSERT OR UPDATE OR DELETE ON replicas
    FOR EACH ROW EXECUTE FUNCTION notify_event();
```

### 3.3 Key Indexes

```sql
-- Primary keys: auto-indexed by SERIAL
-- Foreign keys: auto-indexed by REFERENCES

-- Search optimization
CREATE INDEX IF NOT EXISTS idx_files_hash ON files(hash);
CREATE INDEX IF NOT EXISTS idx_files_deleted ON files(deleted) WHERE deleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_files_indexed ON files(indexed) WHERE indexed = FALSE;
CREATE INDEX IF NOT EXISTS idx_replica_files_status ON replica_files(status);
CREATE INDEX IF NOT EXISTS idx_shared_files_hash ON shared_files(hash);

-- Full-text search on patient/study names (used as ES fallback)
-- Note: primary search is via ES; these are for direct DB lookups
CREATE INDEX IF NOT EXISTS idx_patients_name ON patients(name);
CREATE INDEX IF NOT EXISTS idx_patients_patient_id ON patients(patient_id);
```

---

## 4. Storage Backend Architecture

### 4.1 Registry Pattern

```python
class Storage(ABC):
    storage_types: dict[str, type[Storage]] = {}  # 'local' → LocalStorage
    storages: dict[int, Storage] = {}              # replica_id → instance

    @classmethod
    def register(cls, storage_cls: type[Storage]):
        cls.storage_types[storage_cls.name] = storage_cls

    @classmethod
    def get(cls, replica: dict) -> Storage:
        rid = replica['id']
        if rid not in cls.storages:
            s = cls.storage_types[replica['type']](replica)
            cls.storages[rid] = s
        return cls.storages[rid]
```

### 4.2 Interface Methods

```python
class Storage(ABC):
    @abstractmethod
    async def init(self): ...

    @abstractmethod
    async def index(self) -> AsyncGenerator[dict, None]: ...

    @abstractmethod
    async def copy(self, src, file_data: dict) -> dict: ...

    @abstractmethod
    async def fetch(self, file_data: dict) -> BytesIO | str: ...

    @abstractmethod
    async def serve(self, file_data: dict) -> Response: ...

    @abstractmethod
    async def delete(self, file_data: dict): ...
```

### 4.3 Path Convention

All three backends store files under the same logical path:

```
{patient_id}/{study_id}/{series_number}/{filename}
```

- `patient_id`: DICOM PatientID, sanitized (no `/`)
- `study_id`: DICOM StudyID, sanitized (no `/`)
- `series_number`: DICOM SeriesNumber, sanitized (no `/`)
- `filename`: UUID-generated filename on ingestion (original name stored in DB metadata)

### 4.4 Backend Comparison

| Feature | Local | S3 | B2 |
|---------|-------|-----|-----|
| Type | `local` | `s3` | `b2` |
| SDK | `shutil` | `aiobotocore` | `b2sdk` (sync, via executor) |
| Auth | Filesystem perms | Access key + secret | App key ID + key |
| Location config | Path | Region | Bucket name |
| Bucket name | N/A | `quantumpacs` (hardcoded) | From replica location |
| Serve strategy | `FileResponse` | Presigned URL (1h) → redirect | Auth token → redirect (fallback: stream) |
| Path traversal guard | `basename(normpath())` | Key construction | Key construction |
| Error handling | `PermissionError` → chmod+retry | `BucketAlreadyOwnedByYou` on init | `Bucket name in use` on init |
| Delete | `os.remove`, idempotent | `delete_object` | By file version ID |

---

## 5. Authentication & Authorization

### 5.1 JWT Token Format

```json
// Header
{
  "alg": "HS256",
  "typ": "JWT"
}

// Payload
{
  "id": 1,
  "admin": true,
  "exp": 1712345678   // 14 days from issue
}
```

### 5.2 Token Lifecycle

| Token Type | Created By | Expiry | Usage |
|------------|-----------|--------|-------|
| Session token | `POST /api/login` | 14 days (configurable) | `X-Auth-Pacs` header on all requests |
| WebSocket token | `GET /api/ws_token` | 1 minute | `?token=` query param on WS connect |
| Download token | `GET /api/files/download_token` | 1 minute | `?token=` for download URLs |
| Share key | `POST /api/files/{id}/share` | User-specified (hours) | `?key=` query param, stored in `shared_files` table |

### 5.3 Auth Flow Diagram

```
Request → AuthMiddleware
  │
  ├── Path in [login, health] OR method is OPTIONS?
  │     └── YES → Skip auth → route to handler
  │
  ├── Read X-Auth-Pacs header
  │     └── Present → jwt.decode(credentials)
  │           ├── Valid → Users.is_active(id)?
  │           │     ├── YES → User(id, admin)
  │           │     └── NO  → AuthenticationError
  │           └── Invalid → fall through to ShareKey check
  │
  ├── (Fallback) Read ?token= query param
  │     └── Present → same JWT flow as header
  │
  ├── (Fallback) Share key auth
  │     ├── SharedFiles.check(credentials)
  │     ├── Valid AND path matches /api/files/{id}
  │     │     └── User(key, admin=False)
  │     └── Invalid → 401
  │
  └── All failed → 401 Unauthorized
```

### 5.4 Password Hashing

```python
# Current (v2.0)
import hashlib, secrets, base64

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 600_000, 32)
    return base64.b64encode(salt + dk).decode()

def check_password(password: str, stored: str) -> bool:
    raw = base64.b64decode(stored)
    if len(raw) == 32:  # legacy (no salt, 10k iterations)
        return hashlib.pbkdf2_hmac('sha256', password.encode(), b'', 10_000, 32) == raw
    salt, dk = raw[:16], raw[16:]
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 600_000, 32) == dk
```

---

## 6. Elasticsearch Integration

### 6.1 Index Mapping

```json
{
  "settings": {
    "index": {
      "number_of_shards": 1,
      "number_of_replicas": 1
    },
    "analysis": {
      "analyzer": {
        "my_ngram_analyzer": {
          "tokenizer": "my_ngram_tokenizer",
          "filter": ["lowercase", "asciifolding"]
        }
      },
      "tokenizer": {
        "my_ngram_tokenizer": {
          "type": "edgeNGram",
          "min_gram": 2,
          "max_gram": 10
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "id": { "type": "long", "coerce": false },
      "patient_db_id": { "type": "long" },
      "study_db_id": { "type": "long" },
      "series_db_id": { "type": "long" },
      "Patient ID": { "type": "keyword" },
      "Patient's Name": {
        "type": "text",
        "fields": {
          "lang_analyzed": {
            "type": "text",
            "analyzer": "my_ngram_analyzer"
          }
        }
      },
      "SOP Class UID": {
        "type": "text",
        "fields": {
          "lang_analyzed": {
            "type": "text",
            "analyzer": "my_ngram_analyzer"
          }
        }
      },
      "Study Description": { "type": "text", "analyzer": "my_ngram_analyzer" },
      "Series Modality": { "type": "keyword" },
      "Series Description": { "type": "text", "analyzer": "my_ngram_analyzer" },
      "Referring Physician's Name": { "type": "text", "analyzer": "my_ngram_analyzer" },
      "Performing Physician's Name": { "type": "text", "analyzer": "my_ngram_analyzer" }
    }
  }
}
```

### 6.2 Graceful Degradation

```python
get_client() → None if ES unavailable

def search(data):
    client = get_client()
    if not client:
        return {'data': [], 'total': 0}  # empty results
    # ... execute ES query ...
```

---

## 7. DICOM Listener (C-STORE SCP)

### 7.1 Supported SOP Classes

All `StoragePresentationContexts` from pynetdicom are supported, including:

| SOP Class | UID |
|-----------|-----|
| CT Image Storage | 1.2.840.10008.5.1.4.1.1.2 |
| MR Image Storage | 1.2.840.10008.5.1.4.1.1.4 |
| Ultrasound Image Storage | 1.2.840.10008.5.1.4.1.1.6.1 |
| Secondary Capture Image Storage | 1.2.840.10008.5.1.4.1.1.7 |
| X-Ray Angiographic Image Storage | 1.2.840.10008.5.1.4.1.1.12.1 |
| Enhanced CT Image Storage | 1.2.840.10008.5.1.4.1.1.2.1 |
| Comprehensive SR | 1.2.840.10008.5.1.4.1.1.88.33 |
| ... and all others | via pynetdicom.StoragePresentationContexts |

### 7.2 Store Flow

```
handle_store(event) [sync]
  │
  ├── Save dataset to BytesIO
  ├── asyncio.run(store(ds, data))
  │
  └── Return 0x0000 (Success) or 0x0001 (Failure)

store(ds, data) [async]
  │
  ├── setup() if not initialized (lazy init: DB pool + ES)
  ├── Acquire DB connection
  ├── get_meta(ds) → extract DICOM tags
  ├── Start transaction
  ├── Get master replica
  ├── SHA-256 hash file bytes
  ├── Files.insert_or_select(metadata) → dedup
  ├── master_storage.copy(data, file_record)
  ├── ReplicaFiles.add(master_id, file_id)
  └── Commit transaction
```

---

## 8. Sync Daemon

### 8.1 Architecture

```
┌──────────────────────────────────────────────────┐
│  sync() — main loop                              │
│                                                  │
│  setup() → create pool + ES client               │
│  create_conn() → dedicated LISTEN connection      │
│                                                  │
│  while True:                                      │
│    try:                                           │
│      do_sync()                                    │
│      await asyncio.sleep(1)                       │
│    except:                                        │
│      log error                                    │
│      await asyncio.sleep(1)                       │
│                                                  │
│  db_event(payload):                               │
│    if change is NOT status-only:                  │
│      work = False   → interrupt current cycle    │
└──────────────────────────────────────────────────┘
```

### 8.2 Sync Cycle (`do_sync`)

```
1. Index unindexed files to ES
   └── Files(conn).unindexed() → for each: es.index_file(f)

2. Load all replicas from DB
   └── Separate master from replicas

3. For each replica:
   ├── Instantiate Storage backend
   ├── If status == 'indexing': storage.index(replica)
   │     └── Walk all files, hash, insert/update DB
   │
   ├── Sync loop (offset pagination, batch=1000):
   │     ├── Fetch replica_files WHERE status IN (indexing, deleted)
   │     │     AND (updated + delay) <= NOW()
   │     │
   │     ├── Deleted files → storage.delete() → remove replica_files
   │     └── Indexing files → fetch from master → storage.copy() → mark ok
   │
   └── If interrupted (work=False), exit without marking complete
```

---

## 9. Frontend Architecture

### 9.1 Component Tree

```
<BrowserRouter>
  <ConfigProvider theme={theme}>
    <App>
      <NavigatorSetter />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/account" element={<ProtectedRoute><Account /></ProtectedRoute>} />
        <Route path="/replicas" element={<ProtectedRoute><Replicas /></ProtectedRoute>} />
        <Route path="/users" element={<ProtectedRoute><Users /></ProtectedRoute>} />
        <Route path="/logs" element={<ProtectedRoute><Logs /></ProtectedRoute>} />
        <Route path="/patients/:id" element={<ProtectedRoute><Patient /></ProtectedRoute>} />
        <Route path="/files/:id" element={<ProtectedRoute><Detail /></ProtectedRoute>} />
        <Route path="/" element={<ProtectedRoute><Files /></ProtectedRoute>} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </App>
  </ConfigProvider>
</BrowserRouter>
```

### 9.2 Detail Page (Viewer) Component Hierarchy

```
Detail
├── Tabs (image | data | share | changes | admin)
│
├── [image] CornerstoneElement
│     ├── RenderingEngine (singleton)
│     │     └── StackViewport
│     ├── ToolGroup (10 tools)
│     ├── ActionBar (14 tool buttons)
│     ├── FileSlider (series navigation)
│     ├── Overlay: Zoom (bottom-left)
│     ├── Overlay: WW/WC (bottom-right)
│     └── WebSocketClient (annotation sync)
│
├── [data] EditableTable
│     └── InlineEditableCells
│
├── [share] Share
│     └── CopyButton
│
├── [changes] Changes
│     └── PaginatedTable
│
└── [admin] Managment
      └── DeleteButton
```

### 9.3 Cornerstone3D Tool Registration

```typescript
const tools = {
  PanTool,             // Left-click (passive when annotation active)
  ZoomTool,            // Middle-click
  WindowLevelTool,     // Right-click
  LengthTool,          // Active annotation
  RectangleROITool,    // Active annotation
  AngleTool,           // Active annotation
  ArrowAnnotateTool,   // Active annotation
  EllipticalROITool,   // Active annotation
  EraserTool,          // Toolbar activated
  StackScrollTool,     // Mouse wheel
};
```

### 9.4 State Management

- **Component-local state**: `useState`, `useEffect`
- **Custom hooks**: `useFetch`, `useFormInput`, `usePrevious`
- **Auth state**: `localStorage` (`userId`, `admin`, `token`, `tempKey`)
- **Navigation**: React Router v7 with imperative singleton
- **Real-time sync**: Singleton WebSocket connection with auto-reconnect
- **Search state**: URL-encoded JSON in query string (bookmarkable)
- **No Redux**: Explicit design decision per ADR-006

---

## 10. Configuration

### 10.1 Configuration Key Reference

| Key | Default | Env Var | Description |
|-----|---------|---------|-------------|
| `secret` | `→ db_password` | `SECRET` | JWT signing key |
| `superadmin_pass` | `pa55w0rd` | `SUPERADMIN_PASS` | Initial admin password |
| `db_host` | `127.0.0.1` | `DB_HOST` | PostgreSQL host |
| `db_port` | `5432` | `DB_PORT` | PostgreSQL port |
| `db_database` | `quantumpacs` | `DB_DATABASE` | PostgreSQL database |
| `db_user` | `quantumpacs` | `DB_USER` | PostgreSQL user |
| `db_password` | `pa55w0rd` | `DB_PASSWORD` | PostgreSQL password |
| `es_host` | `localhost` | `ES_HOST` | Elasticsearch host |
| `pool_size` | `8` | — | asyncpg pool size |

### 10.2 Resolution Order

1. `default_config` (hardcoded in `config.py`)
2. `config.local.yaml` (loaded via PyYAML)
3. Environment variables (uppercased key names)

### 10.3 Docker Mode

Set `QUANTUMPACS_DOCKER=true` to enable:
- Static file serving from `/openpacs/frontend/dist/`
- SPA 404 fallback (non-API paths → `index.html`)

---

## 11. Deployment

### 11.1 Docker (Production)

```dockerfile
# Multi-stage build
# Stage 1: Node 26 Alpine → npm ci + build
# Stage 2: Python 3.11 slim + Caddy
#   - Copies dist/ from stage 1
#   - Installs Python dependencies
#   - CMD: Caddy + Gunicorn (uvicorn workers)
```

```yaml
# Runtime: single container
services:
  postgres:
    image: quantumpacs-postgres:18
    ports: ["5432:5432"]
  app:
    image: quantumpacs:latest
    ports: ["80:80", "11112:11112"]
    environment:
      - DB_HOST=postgres
      - QUANTUMPACS_DOCKER=true
    depends_on:
      postgres:
        condition: service_healthy
```

### 11.2 Native (Development)

| Service | Process | Port | Start Command |
|---------|---------|------|---------------|
| PostgreSQL | Docker container | 5432 | `docker compose up -d` |
| Backend | Gunicorn + Uvicorn | 8080 | `scripts/dev.sh start` |
| Frontend | Vite dev server | 5173 | `scripts/dev.sh start` |
| DICOM | Standalone python | 11112 | `python dcm_server.py` |
| Sync | Standalone python | — | `python sync.py` |

### 11.3 Port Requirements

| Port | Protocol | Service | Purpose |
|------|----------|---------|---------|
| 80 | HTTP/HTTPS | Caddy | Web UI + API |
| 5432 | TCP | PostgreSQL | Database connections |
| 11112 | DICOM | pynetdicom | Modality C-STORE |
| 8080 | HTTP | Starlette | API server (internal) |
| 5173 | HTTP | Vite | Frontend dev server |

### 11.4 Caddy Configuration

```
:80 {
    root * /openpacs/frontend/dist
    try_files {path} /index.html          # SPA fallback

    @api {
        path /api/*
    }
    reverse_proxy @api localhost:8080

    @ws {
        path /ws/*
    }
    reverse_proxy @ws localhost:8080

    file_server
}
```

---

## 12. Testing Strategy

### 12.1 Backend Tests

| Category | Framework | Location | Coverage |
|----------|-----------|----------|----------|
| Unit tests | pytest | `backend/tests/` | Utility functions, storage path traversal |
| Integration | pytest | TBD | API endpoints, DB operations |
| DICOM | pytest | TBD | C-STORE handling, metadata extraction |

### 12.2 Frontend Tests

| Category | Framework | Location | Coverage |
|----------|-----------|----------|----------|
| Unit tests | Vitest | `frontend/src/test/` | Component rendering, hooks |
| E2E tests | Playwright | `frontend/e2e/` | Login flow, navigation |

### 12.3 CI Pipeline (`.github/workflows/ci.yml`)

```yaml
jobs:
  lint-backend:    # flake8
  test-backend:    # pytest
  lint-frontend:   # eslint
  test-frontend:   # vitest
  build-frontend:  # vite build
  build-backend:   # import check
  docker-build:    # build + push to ghcr.io (main + tags)
```

---

## 13. Known Technical Debt

| Issue | Location | Impact | Target |
|-------|----------|--------|--------|
| `editableFields = []` | `EditableTable.tsx:17` | No metadata fields are actually editable | v2.1 |
| No delete confirmation | `Managment.tsx` | Accidental deletion risk | v2.1 |
| WebSocket reconnect flood | `ws.ts` | No backoff on reconnect | v2.1 |
| Single WebSocket handler | `ws.ts` | Last-registered handler wins | v2.2 |
| Global `window.ctinit` hack | `CornerstoneElement.tsx` | Fragile init timing workaround | v2.1 |
| Unused `history.ts` | `frontend/src/history.ts` | Dead code | v2.1 |
| Replica table 2s polling | `Replicas.tsx` | Unnecessary network load | v2.2 |
| Sync daemon single-threaded | `sync.py` | Bottleneck for many replicas | v2.2 |
| No CORS origin validation | `app.py` / `CustomMiddleware` | Security risk for production | v2.1 |
| DICOM listener sync→async bridge | `dcm/server.py:asyncio.run()` | Potential event loop issues | v2.2 |
