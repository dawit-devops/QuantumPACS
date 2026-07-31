# Persona: PACS Administrator (Enterprise/Regional)

## Persona Card

| Attribute | Detail |
|-----------|--------|
| **Role** | PACS Administrator managing QuantumPACS at enterprise or regional level — multi-site, multi-tenant environment with storage replication, DICOM routing, audit compliance, and system monitoring |
| **Description** | System administrator responsible for provisioning tenants, configuring DICOM routing rules, managing storage replicas across regions, configuring RBAC roles/permissions, monitoring system health, and investigating audit trails for HIPAA compliance |
| **Technical Level** | High — deep understanding of DICOM, DICOMweb, HL7, multi-region storage, PostgreSQL, Redis, Kubernetes/container orchestration |
| **Frequency** | Daily monitoring + periodic configuration changes (routing rules, user/role management, tenant provisioning) |
| **Devices** | Administrative workstation with browser access to PACS admin UI; also may access via API directly |
| **Critical Needs** | Tenant lifecycle management, storage hierarchy configuration, routing rule management, audit trail access, system health monitoring, RBAC configuration |
| **Frustrations** | No audit alert rules, no storage tier management UI, no multi-site federation UI, verbose JSONB condition editor for routing rules |
| **Default Role** | `super_admin` (cross-tenant) or `admin` (single tenant) |

## Routes & Permissions

### Sidebar Navigation (Admin Submenu)

The Admin submenu appears when user has any of these permissions:
`USER_READ`, `REPLICA_READ`, `TENANT_READ`, `ROLE_READ`, `LOG_READ`, `SERVICE_KEY_READ`, `WORKLIST_READ`, or legacy `user.admin`.

| Menu Item | Path | Permission | Type |
|-----------|------|------------|------|
| Metrics Dashboard | `/metrics` | `METRICS_READ` | Top-level (always visible) |
| Storage Replicas | `/replicas` | `REPLICA_READ` | Admin submenu |
| Users | `/users` | `USER_READ` | Admin submenu |
| Tenants | `/tenants` | `TENANT_READ` | Admin submenu |
| Roles | `/roles` | `ROLE_READ` | Admin submenu |
| Audit Logs | `/logs` | `LOG_READ` | Admin submenu |
| Worklist | `/worklist` | `WORKLIST_READ` | Admin submenu |
| Service Keys | `/service-keys` | `SERVICE_KEY_READ` | Admin submenu |
| Routing Rules | `/routing` | `ROUTING_READ` | Admin submenu |
| Account | `/account` | Authenticated | Top-level |
| Sign In | `/login` | Public | — |

### Complete Permission Slug Catalog (34 slugs across 13 resource domains)

```
FILE_READ, FILE_WRITE, FILE_DELETE
PATIENT_READ, PATIENT_WRITE
STUDY_READ, STUDY_WRITE
USER_READ, USER_WRITE, USER_DELETE, USER_ADMIN
REPLICA_READ, REPLICA_WRITE, REPLICA_DELETE
LOG_READ
TENANT_READ, TENANT_WRITE, TENANT_ADMIN
ROLE_READ, ROLE_WRITE, ROLE_DELETE
SERVICE_KEY_READ, SERVICE_KEY_WRITE, SERVICE_KEY_DELETE
WORKLIST_READ, WORKLIST_WRITE
DICOMWEB_READ, DICOMWEB_WRITE
ROUTING_READ, ROUTING_WRITE
METRICS_READ
```

### Built-In Roles and Their Permission Scope

| Role | Key Permissions | Clinical/System Use |
|------|-----------------|---------------------|
| **super_admin** | ALL 34 permissions | Cross-tenant system-wide administration |
| **admin** | All except TENANT_* | Single-tenant full administration |
| **tenant_admin** | FILE/PATIENT/STUDY/USER/REPLICA/LOG/ROLE/WORKLIST/METRICS (r+w), ROLE_READ + (no TENANT, no SERVICE_KEY d) | Tenant-scoped administration — manages users, roles, replicas, routing, logs for their own tenant |
| **technologist** | FILE r/w/d, PATIENT r/w, STUDY r/w, WORKLIST r/w, DICOMWEB read | Day-to-day modality operations |
| **radiologist** | FILE_READ, PATIENT_READ, STUDY_READ, DICOMWEB_READ | View + annotate diagnostic studies |
| **physician** | Same as radiologist in v2 (view-only) | Referring physician review |
| **cashier** | PATIENT_READ, PATIENT_WRITE | Billing department — no study access |
| **auditor** | LOG_READ, FILE_READ (metadata only) | Read-only audit access (v3 PRD) |

## End-to-End Flows

### Flow 1: Provision a New Hospital Tenant

```
1. Super admin navigates to Tenants page (/tenants)
2. Clicks "Provision Tenant" button
3. Modal form appears with fields:
   - Name (e.g., "St. Mary's Hospital")
   - Slug (e.g., "stmarys")
   - Domain (e.g., "stmarys.hospital.example.com")
   - Admin Email (e.g., "pacs-admin@stmarys.org")
4. Admin submits form

Backend provisioning (TenantProvisioner):
  a. Creates PostgreSQL database: CREATE DATABASE "stmarys"
  b. Runs Alembic migrations: alembic upgrade head on new database
  c. Creates initial tenant_admin user with auto-generated random password
  d. Inserts registry row:
     - status = 'active'
     - storage_quota_bytes = configured default
     - storage_used_bytes = 0
  e. Returns admin password (shown once, never stored in plaintext)

5. New tenant row appears in table:
   - Name: St. Mary's Hospital
   - Slug: stmarys
   - Domain: stmarys.hospital.example.com
   - Users: inline health indicator
   - Status: active (green tag)
   - Action: Decommission button

6. Admin shares credentials with hospital's PACS admin
7. Hospital PACS admin logs in at /login with stmarys tenant context
8. Tenant isolation active: all DB queries routed to stmarys database

Timeline target: Provisioning completes in < 60 seconds (PRD-v3).
```

### Flow 2: Configure Storage Replicas

```
1. Admin navigates to Replicas page (/replicas)
2. First replica (auto-assigned as master on creation):
   a. Click "Add Replica"
   b. Select type: local, s3, or b2
   c. Configure connection:
      - local: path on server filesystem
      - s3: endpoint URL, bucket name, access key, secret key, region
      - b2: application key ID, application key, bucket name
   d. Click "Create"
   e. First replica auto-assigned as master (replication source)
3. Subsequent replicas added as copies:
   - Replicas sync asynchronously from master
   - Configurable delay (minutes) before sync starts
   - Status: indexing (orange) → ok (green) or deleted (red)
4. Admin can:
   - Update delay for a replica via edit modal
   - Set any replica as new master via "Set Master" action
   - Delete replica via "Delete" action (cascades to replica_files records)
5. Auto-refresh polls every 2 seconds for status updates

Replication flow:
  1. C-STORE/STOW-RS ingests file to master replica
  2. Files table records file with master storage backend
  3. Sync daemon (backend/sync.py) polls every 1 second:
     a. Indexes unindexed files → Elasticsearch
     b. For each replica: fetches files with status 'indexing' or 'deleted'
     c. Copies from master to replica backend (respecting delay)
     d. Batch size: 1000 files per cycle
  4. Replica_files records track per-replica file status and location
```

### Flow 3: Configure DICOM Auto-Routing Rules

```
1. Admin navigates to Routing Rules page (/routing)
2. Clicks "Create Rule"
3. Modal form:
   - Name (required): e.g., "Route CT Chest to Fast Storage"
   - Description (optional): e.g., "Chest CT studies from ER to SSD storage"
   - Conditions (JSON textarea, required):
     {
       "modality": "CT",
       "study_description": {"contains": "CHEST"}
     }
   - Destination (required): replica ID as string, e.g., "2"
   - Priority (InputNumber, default 0): lower = evaluated first
   - Enabled (Switch, default true)
4. POST /api/routing creates rule
5. Rule stored in routing_rules table (conditions as JSONB)
6. Rule takes effect immediately
7. Admin can:
   - Edit rule (PUT /api/routing/{id}) — update conditions, destination, priority, enabled
   - Delete rule (DELETE /api/routing/{id}) — soft delete, audit logged
8. All CRUD operations logged as AuditLog:
   routing.rule_created / routing.rule_updated / routing.rule_deleted

Condition DSL examples:
  {"modality": "CT"}                        → Route all CT studies
  {"station_ae_title": "CT01"}              → Route by scanner identity
  {"modality": "MR", "study_description": {"contains": "BRAIN"}} → Route MR Brain
  {"$or": [{"modality": "CT"}, {"modality": "MR"}]} → Route CT or MR
  {"accession_number": {"gt": "1000"}}      → Numeric comparison
  {"$or": [{"modality": "CT"}, {"modality": "MR"}]} → Compound OR

Operators: eq, ne, contains, gt, gte, lt, lte, $or (disjunction)
Evaluation: per-instance at C-STORE/STOW-RS time; synchronous in-memory
All matching rules applied (not first-match-only)
```

### Flow 4: Audit Trail Investigation

```
1. Admin navigates to Logs page (/logs)
2. Audit log table renders server-side paginated
3. Each row shows: Time (UTC), Log content (JSON text)
4. Expandable row: clicking expands to show full JSON payload
5. Log payload includes: event_type, actor_id, resource_type, resource_id, details, tenant, request_id
6. Filtering options (server-side):
   - By tenant: ?tenant=<slug> (requires TENANT_READ to filter)
   - By event_type: ?event_type=routing.rule_created
   - By actor_id: ?actor_id=<user_id>
7. Key event types visible in logs:
   Tenant: tenant.provisioned, tenant.deleted
   Routing: routing.rule_created, routing.rule_updated, routing.rule_deleted
   Roles: role.created, role.updated, role.deleted
   Worklist: worklist.entry_created, worklist.entry_updated, worklist.entry_cancelled
   Files: read, download, annotations changed, metadata tag edits
   FHIR: all FHIR requests (user_id, method, path, status_code, duration_ms)
8. Audit events written by:
   - AuditLog.log_event() in backend/db/audit_log.py
   - FhirAuditMiddleware for FHIR endpoints
   - File change tracking in files table / file_changes table
9. SHA-256 hash of raw HL7 messages stored in hl7_messages table for non-repudiation
```

### Flow 5: Configure RBAC Roles and Users

#### Role Management

```
1. Admin navigates to Roles page (/roles)
2. View built-in roles (protected — cannot delete):
   - super_admin, admin, tenant_admin, technologist, radiologist, physician, cashier, auditor
3. Create custom role:
   a. Click "Create Role"
   b. Fill: Name, Slug (auto-derived or custom)
   c. Select permissions from checkbox grid organized into 13 groups:
      Files, Patients, Studies, Users, Replicas, Logs, Tenants, Roles,
      Service Keys, Worklist, DICOMweb, Routing, Metrics
   d. Submit → Role created with exact permission set
4. Edit custom role (PUT /api/roles/{id}):
   - Update name, slug, permissions
   - Triggers automatic token version increment → all user tokens invalidated
5. Delete custom role: built-in roles protected from deletion
```

#### User Management

```
1. Admin navigates to Users page (/users)
2. View existing users with columns: ID, Username, Role (inline Select dropdown), Admin tag, Status tag
3. Add user:
   a. Click "Add User" modal
   b. Enter username, toggle admin flag
   c. Submit → system generates random password
   d. Raw password shown once (never stored in plaintext)
   e. Password hashed with PBKDF2-HMAC-SHA256 (600k iterations)
4. Change role:
   a. Select user → inline dropdown to change role
   b. PUT /api/users/role triggers token blocklist
5. Deactivate user: marks user inactive
6. Reset password: POST /api/users/new_password generates new random password
7. All user management operations audit logged
```

#### Token Lifecycle (v3 RBAC)

```
Access token TTL: 1 hour
Refresh token TTL: 14 days (rotated on each refresh use)
Revocation: jti added to Redis blocklist (GET /api/auth/revoke)
Password change: all user tokens blocklisted
Role change: all user tokens blocklisted (via role update trigger)
```

### Flow 6: System Health Monitoring

```
1. Admin navigates to Metrics Dashboard (/metrics)
2. Top row: Stat cards with live counts:
   - Patients (total count)
   - Studies (total count)
   - Series (total count)
   - Files (total count)
   - Users (total count)
   - Storage used (bytes, formatted)
3. System Health panel (left column):
   - Each component shown with status icon + tag:
     database: green(ok) / yellow(degraded) / red(down)
     elasticsearch: green/yellow/red
     redis: green/yellow/red
     storage: green/yellow/red
     dicom_listener: green/yellow/red (TCP port probe on 11112)
     ingestion_service: green/yellow/red
4. Modality Distribution (bar chart): counts per modality (CT, MR, US, etc.)
5. Component Latency (horizontal bar chart): response times per component
6. Ingestion 30-Day Trend (line chart): daily ingestion volume
7. Latest Files table: most recently added files

External monitoring endpoint: GET /api/v2/metrics (Prometheus format)
  - http_requests_total (counter by method, path, status_code)
  - http_request_duration_seconds (histogram by method, path)
  - http_requests_in_progress (gauge)
  - db_connections_available / db_connections_in_use (gauge by tenant)
  - db_query_duration_seconds (histogram by operation)
  - redis_stream_lag_seconds (gauge by stream, consumer_group)
  - dicom_cstore_throughput_bytes (counter)
  - dicomweb_requests_total (counter by method, resource)

Health probe (unauthenticated): GET /api/health
  - Critical: database → 503 if down
  - Non-critical: elasticsearch, redis, storage, dicom_listener, ingestion_service
```

### Flow 7: OAuth/OIDC SSO Provider Configuration

```
1. Admin creates OAuth provider via API:

   POST /api/oauth/providers
   {
     "issuer": "https://login.microsoftonline.com/{tenant}",
     "client_id": "...",
     "client_secret": "encrypted-at-rest via Fernet",
     "jwks_uri": "https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys",
     "token_url": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
     "redirect_uri": "http://pacs.example.com/api/oauth/callback",
     "scope": "openid email profile",
     "groups_claim": "groups",
     "auto_provision": true,
     "default_role": "radiologist",
     "slug": "msft"
   }

2. Configuration stored in oauth_providers table:
   - client_secret encrypted via Fernet (AES-256-GCM)
   - encrypted at rest in tenant database

3. OIDC discovery at GET /.well-known/openid-configuration
   Returns standard OIDC discovery document

4. Login flow: GET /api/oauth/login?idp=msft → redirect to IdP → callback → JWT issued

5. JIT provisioning (auto_provision=true):
   - On first OAuth login, if user not found → creates new user
   - Placeholder password (cannot login with password)
   - Role from default_role config
   - oauth_sub stored for subsequent lookups
   - Audit logged as user.provisioned

6. Token exchange (backend services):
   POST /api/oauth/token supports refresh_token grant type
   → Returns new JWT access token
```

### Flow 8: API Key Management

```
1. Admin navigates to Service Keys page (/service-keys)
2. Generate key for external service (e.g., RIS system, EMR/EHR):
   a. Click "Generate Key"
   b. Select service name (e.g., "epic-ehr", "ris-primary")
   c. Select permissions (permission slugs for this key)
   d. Submit → POST /api/api-keys
   e. System generates: qpk_ + secrets.token_urlsafe(32) (55 char key)
   f. Stores SHA-256 hash of full key in api_keys table
   g. Stores only prefix (qpk_ + 8 chars) in DB for lookup
   h. Raw key shown ONCE to admin → must be stored securely
3. Key validation on each request:
   - X-API-Key header → extract prefix → lookup by prefix + hash comparison
   - Checks: enabled flag, expiry, tenant scope
4. Revoke compromised key: DELETE /api/api-keys/{id}
5. Audit logged for key creation and revocation
```

### Flow 9: Storage Management and Quota

```
1. Admin views tenant storage usage in Tenants table:
   - Color-coded usage indicator:
     green: < 50% of quota
     orange: 50-75% of quota
     red: > 75% of quota
2. Per-tenant stats at /api/tenants/{id}/stats:
   - storage_used_bytes, storage_quota_bytes, user_count, study_count, file_count, last_activity
3. Storage tiering (replicas table):
   - Tier concept: hot (local), warm (s3), cold (b2)
   - Current implementation uses master boolean + delay config
   - v3 PRD plans explicit tier column replacement
4. Storage accounting:
   - storage_used_bytes updated via periodic aggregation job
   - files.deleted = true for soft delete (not physically removed)
5. Tenant provisioning:
   - storage_quota_bytes configured per tenant
   - Enforced at storage write time
```

### Flow 10: Worklist Management

```
1. Admin navigates to Worklist page (/worklist)
2. Manual worklist entry creation:
   - Patient info: ID, Name, Birth Date, Sex
   - Exam info: Accession #, Procedure Description, Modality, Station AE Title
   - Schedule: Date, Time
   - POST /api/worklist → creates entry with status='scheduled'
3. Worklist table shows: Patient Name, Patient ID, Accession #, Modality,
   Scheduled Date, Status, Action buttons
4. Status filters: scheduled (blue), performed (green), cancelled (red)
5. Edit entries inline (pencil icon)
6. Cancel entries (X icon with Popconfirm confirmation for scheduled entries only)
7. Status transitions: scheduled → performed (auto via C-STORE) → cancelled (manual)
8. When C-STORE arrives with matching accession → auto-mark performed + store study_uid
```

## Metrics & SLAs

| Metric | Target | How Measured |
|--------|--------|-------------|
| Tenant provisioning time | < 60s (PRD-v3) | Provisioner timing |
| Database connection pool creation | < 200ms (first request per tenant) | Lazy pool init |
| Database connection pool eviction | 300s idle timeout | _max_pools (50) with LRU |
| Connection pool size | min=1, max=4 per tenant | asyncpg pool config |
| Replica sync latency | Configurable delay (minutes) | Sync daemon polling every 1s |
| Sync batch size | 1000 files per cycle | Sync daemon config |
| Health check response | < 100ms | TCP port probe |
| Metrics endpoint response | < 100ms | Prometheus exposition |
| Audit log query response | < 200ms (paginated) | LIKE query on JSONB |
| RBAC permission check | < 1ms (in-memory set lookup) | @requires_permission decorator |
| Route resolution | < 5ms | Starlette router |

## Acceptance Criteria

### From PRD-v3.md / UX-Functionality.md / User-Stories.md

1. Admin can provision new tenants with automatic database, migration, and initial user creation
2. Tenants are isolated via database-per-tenant architecture (ADR-016)
3. Replicas can be configured as local, S3-compatible, or Backblaze B2
4. Storage replication from master to replicas works asynchronously with configurable delay
5. Routing rules can be created with flexible JSON condition expressions (modality, description, etc.)
6. Routing rules are evaluated on every C-STORE/STOW-RS ingestion and copy files to matched replicas
7. Admin can view real-time system health with per-component status indicators
8. Metrics dashboard shows key aggregates: patient/study/series/file counts, storage usage, modality distribution, ingestion trends
9. Audit trail is accessible with expandable log entries showing full JSON payload
10. Audit events cover: tenant lifecycle, routing changes, role management, MWL CRUD, file operations, FHIR access
11. RBAC system supports 34 permission slugs across 13 resource domains
12. Built-in roles (super_admin, admin, tenant_admin, technologist, radiologist, physician, cashier) are pre-configured
13. Custom roles can be created with granular permission sets from 13 resource groups
14. Role changes trigger automatic token invalidation for all affected users
15. OAuth/OIDC provider configuration supports SAML/OIDC IdPs with auto-provisioning
16. API keys can be generated with scoped permissions for service-to-service auth
17. Tenant isolation enforced via X-Tenant-ID header + TenantMiddleware + tenant-scoped DB pool
18. Prometheus metrics available at /api/v2/metrics for external monitoring systems

### Derived from Code (Additional)

19. TenantConnectionPool max 50 pools with LRU eviction after 300s idle
20. Per-pool: min_size=1, max_size=4, command_timeout=30s
21. Tenant status states: provisioning, active, quarantined, decommissioned
22. Tenant decommission soft-deletes (sets status='decommissioned', not DB drop)
23. Routing rule evaluation is synchronous in-memory — no async/background processing
24. FHIR audit logs every request to fhir_audit table (user_id, method, path, status_code, duration_ms, IP)
25. HL7 messages stored with SHA-256 hash in hl7_messages.raw_hash for non-repudiation
26. Encrypted secrets (OAuth client_secret) via Fernet/AES-256-GCM in api/encryption.py
27. Structured JSON logging includes request_id, tenant, user_id, trace_id, span_id (ADR-020)
28. OpenTelemetry traces via OTLP exporter with W3C Trace Context propagation
29. DICOM listener health check does TCP port probe on 11112
30. Ingestion service health check monitors Redis Streams consumer lag
31. Storage used_bytes updated via periodic aggregation (SELECT COALESCE(SUM(...)) FROM files)
32. File soft delete: files.deleted = true, not physically removed from storage backends
33. C-MOVE/C-GET SCP handlers are stubs — no-op with warning log
34. DICOMweb STOW-RS validates modality against VALID_MODALITIES whitelist frozenset (200+ modalities)

## Implementation Gaps

| Feature | Status | Impact | Target Version |
|---------|--------|--------|---------------|
| Audit alert rules | NOT IMPLEMENTED | Admin must manually review logs — no automated alerts for suspicious activity | v3.x |
| Storage tier management UI | PARTIAL | Tier concept (hot/warm/cold) defined in PRD-v3; current UI uses master boolean + delay | v3.x |
| Multi-site federation UI | NOT IMPLEMENTED | No cross-tenant study sharing UI; tenant federation via API only | v3.x |
| Tenant usage quota enforcement UI | MISSING | No admin UI to set or adjust storage_quota_bytes per tenant | v3.x |
| DICOM conformance statement generator | NOT IMPLEMENTED | No admin tool to generate/conformance statement for auditing | v3.x |
| Bulk user import (CSV/JSON) | NOT IMPLEMENTED | Users must be created individually via API or UI | v3.x |
| Role permission diff/comparison UI | MISSING | No visual comparison between custom and built-in role permission sets | v3.x |
| Storage backend health monitoring | PARTIAL | Storage health checked in /api/health but detailed per-backend metrics not exposed in UI | v3.x |
| Replica sync conflict resolution | MISSING | No UI or logic for handling conflicting file versions across replicas | v3.x |
| Cross-tenant audit log aggregation | MISSING | Tenant-isolated audit logs cannot be aggregated across tenants without super_admin access | v3.x |
| DICOM network encryption (TLS on DIMSE) | NOT CONFIGURED | DIMSE traffic on port 11112 is unencrypted; TLS options exist for MLLP but not DIMSE | v3.x |
| Backup/restore admin tooling | MISSING | No admin UI for database backup, restore, or point-in-time recovery | v3.x |
| Configuration versioning/audit | MISSING | No change tracking on config.key value modifications | v3.x |

## Key Files Reference

| File | Purpose |
|------|---------|
| `docs/PRD-v3.md` | v3 admin user stories (U-v3.3–U-v3.10) |
| `docs/decisions/ADR-016-database-per-tenant-multi-tenancy.md` | Multi-tenant database-per-tenant architecture |
| `docs/decisions/ADR-017-oauth-oidc-rbac-auth.md` | RBAC + OAuth authentication architecture |
| `docs/decisions/ADR-020-observability-stack.md` | OpenTelemetry + Prometheus + structured logging |
| `docs/decisions/ADR-007-shared-tenancy.md` | Storage replica / shared tenancy decision |
| `backend/api/tenants.py` | Tenant CRUD + provisioning + stats endpoints |
| `backend/api/replicas.py` | Replica CRUD endpoints |
| `backend/api/routing.py` | Routing rule CRUD endpoints |
| `backend/api/roles.py` | Role CRUD with token invalidation on change |
| `backend/api/logs.py` | Audit log querying endpoint |
| `backend/api/users.py` | User CRUD, role assignment, login, token refresh |
| `backend/api/oauth_providers.py` | OAuth provider configuration CRUD |
| `backend/api/api_keys.py` | API key generation and management |
| `backend/api/permissions.py` | All 34 permission slugs + built-in role definitions |
| `backend/api/rbac.py` | `requires_permission()` decorator |
| `backend/api/tenant_middleware.py` | Tenant resolution and connection pool routing |
| `backend/api/telemetry.py` | Health checks, Prometheus metrics |
| `backend/api/dashboard_metrics.py` | Dashboard aggregation endpoint |
| `backend/api/ws.py` | WebSocket handler |
| `backend/db/tenants.py` | TenantConnectionPool, Tenants model |
| `backend/db/tenant_provisioner.py` | DB creation, migration, initial admin |
| `backend/db/routing_rule.py` | Routing rule storage with JSONB conditions |
| `backend/db/audit_log.py` | Structured audit event logging + querying |
| `backend/db/roles.py` | Role CRUD + built-in seeding |
| `backend/db/api_keys.py` | API key model (hash storage, prefix lookup) |
| `backend/db/oauth_providers.py` | OAuth provider model (encrypted secret) |
| `backend/api/encryption.py` | Fernet AES-256-GCM for secrets |
| `frontend/src/tenants/Tenants.tsx` | Tenant management UI |
| `frontend/src/replicas/Replicas.tsx` | Replica management UI |
| `frontend/src/routing/RoutingRules.tsx` | Routing rules UI |
| `frontend/src/roles/Roles.tsx` | Role editor UI |
| `frontend/src/users/Users.tsx` | User management UI |
| `frontend/src/logs/Logs.tsx` | Audit log viewer UI |
| `frontend/src/metrics/Metrics.tsx` | Metrics/health dashboard UI |
| `frontend/src/worklist/Worklist.tsx` | MWL admin UI |
| `frontend/src/service-keys/ServiceKeys.tsx` | API key management UI |
| `frontend/src/common/Sidebar.tsx` | Admin sidebar with permission-gated entries |
| `frontend/src/common/MobileNav.tsx` | Mobile bottom navigation |
| `frontend/src/auth/TenantSelector.tsx` | Tenant context switcher |
| `frontend/src/auth/AuthContext.tsx` | Auth state management |
| `frontend/src/index.tsx` | All route definitions |