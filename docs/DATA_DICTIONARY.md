# Data Dictionary

Comprehensive reference for all QuantumPACS database tables, columns, indexes, and constraints.

---

## users

Core user accounts with authentication and authorization fields.

| Column | Type | Default | FK | Description |
|--------|------|---------|----|-------------|
| id | BIGINT | GENERATED ALWAYS AS IDENTITY | — | Primary key |
| username | CITEXT | — | — | Unique username (case-insensitive) |
| password | TEXT | — | — | PBKDF2-HMAC-SHA256 hashed password |
| admin | BOOLEAN | FALSE | — | DEPRECATED — use role_id for v3 |
| status | TEXT | 'active' | — | Account status: active, deactivated |
| created | TIMESTAMPTZ | now() | — | Row creation timestamp |
| updated | TIMESTAMPTZ | now() | — | Row last-updated timestamp |
| role_id | UUID | — | roles(id) | FK to RBAC role |
| oauth_sub | TEXT | — | — | OAuth/OpenID subject identifier |
| groups | JSONB | — | — | Group membership from OAuth claims |
| email | VARCHAR(255) | '' | — | Email address |
| avatar_url | TEXT | — | — | Avatar image URL |
| tenant | TEXT | — | — | Tenant slug for multi-tenant scoping |
| token_version | INTEGER | 0 | — | Incremented on role/perm change to force re-auth |
| needs_rehash | BOOLEAN | FALSE | — | Flag to upgrade legacy password hash |
| last_login | TIMESTAMP | — | — | Last successful login timestamp |

**Indexes:**
- `users_username` — UNIQUE on `username`
- `users_oauth_sub` — on `oauth_sub` (partial, WHERE oauth_sub IS NOT NULL)
- `users_tenant` — on `tenant`

**Constraints:**
- `users_username_unique` — UNIQUE (username)
- `users_status_check` — CHECK (status IN ('active', 'deactivated'))

---

## patients

Patient demographic records.

| Column | Type | Default | FK | Description |
|--------|------|---------|----|-------------|
| id | BIGINT | GENERATED ALWAYS AS IDENTITY | — | Primary key |
| patient_id | TEXT | — | — | Primary patient identifier (MRN) |
| name | TEXT | — | — | Patient name in DICOM format |
| birth_date | TEXT | — | — | Date of birth (YYYYMMDD or ISO) |
| sex | TEXT | — | — | Sex: M, F, or O |
| meta | JSONB | — | — | Additional patient metadata |
| created_at | TIMESTAMPTZ | now() | — | Row creation timestamp |
| updated_at | TIMESTAMPTZ | now() | — | Row last-updated timestamp |

**Indexes:**
- `idx_patients_name` — on `name`
- `idx_patients_updated_at` — on `updated_at`

**Constraints:**
- `patients_patient_id_key` — UNIQUE (patient_id)
- `patients_sex_check` — CHECK (sex IS NULL OR sex IN ('M', 'F', 'O'))

---

## studies

DICOM study records linked to patients.

| Column | Type | Default | FK | Description |
|--------|------|---------|----|-------------|
| id | BIGINT | GENERATED ALWAYS AS IDENTITY | — | Primary key |
| patient_id | INTEGER | — | patients(id) ON DELETE CASCADE | FK to patient |
| study_id | TEXT | — | — | DICOM Study ID |
| description | TEXT | — | — | Study description |
| study_instance_uid | TEXT | — | — | DICOM Study Instance UID |
| accession_number | TEXT | — | — | Accession number |
| created_at | TIMESTAMPTZ | now() | — | Row creation timestamp |
| updated_at | TIMESTAMPTZ | now() | — | Row last-updated timestamp |

**Indexes:**
- `idx_studies_patient_id` — on `patient_id`
- `ix_studies_study_instance_uid` — UNIQUE on `study_instance_uid` (partial, WHERE NOT NULL)
- `ix_studies_accession_number` — on `accession_number`
- `ix_studies_updated_at` — on `updated_at`
- `studies_study_id` — on `study_id`

**Constraints:**
- UNIQUE (patient_id, study_id)

---

## series

DICOM series records within a study.

| Column | Type | Default | FK | Description |
|--------|------|---------|----|-------------|
| id | BIGINT | GENERATED ALWAYS AS IDENTITY | — | Primary key |
| study_id | INTEGER | — | studies(id) ON DELETE CASCADE | FK to study |
| number | TEXT | — | — | Series number |
| modality | TEXT | — | — | DICOM modality (CT, MR, etc.) |
| description | TEXT | — | — | Series description |
| series_instance_uid | TEXT | — | — | DICOM Series Instance UID |

**Indexes:**
- `idx_series_study_id` — on `study_id`
- `ix_series_series_instance_uid` — UNIQUE on `series_instance_uid` (partial, WHERE NOT NULL)
- `series_number` — on `number`

**Constraints:**
- UNIQUE (study_id, number)

---

## files

DICOM file/instance records.

| Column | Type | Default | FK | Description |
|--------|------|---------|----|-------------|
| id | BIGINT | GENERATED ALWAYS AS IDENTITY | — | Primary key |
| patient_id | INTEGER | — | patients(id) ON DELETE CASCADE | FK to patient |
| study_id | INTEGER | — | studies(id) ON DELETE CASCADE | FK to study |
| series_id | INTEGER | — | series(id) ON DELETE CASCADE | FK to series |
| name | TEXT | — | — | File name |
| indexed | BOOLEAN | FALSE | — | Whether file is indexed for search |
| hash | TEXT | — | — | SHA-256 hash of file content |
| created | TIMESTAMPTZ | now() | — | Row creation timestamp |
| updated | TIMESTAMPTZ | now() | — | Row last-updated timestamp |
| deleted | BOOLEAN | FALSE | — | Soft-delete flag |
| meta | JSONB | — | — | DICOM metadata (SOPClassUID, InstanceNumber, etc.) |
| tools_state | JSONB | — | — | Viewer tools state snapshot |
| sop_instance_uid | TEXT | — | — | DICOM SOP Instance UID |

**Indexes:**
- `idx_files_patient_id` — on `patient_id`
- `idx_files_study_id` — on `study_id`
- `idx_files_series_id` — on `series_id`
- `ix_files_sop_instance_uid` — UNIQUE on `sop_instance_uid` (partial, WHERE NOT NULL)
- `files_name` — on `name`
- `files_hash` — on `hash`

---

## file_changes

Audit trail for file modifications.

| Column | Type | Default | FK | Description |
|--------|------|---------|----|-------------|
| id | BIGINT | GENERATED ALWAYS AS IDENTITY | — | Primary key |
| file_id | INTEGER | — | files(id) ON DELETE CASCADE | FK to file |
| created | TIMESTAMPTZ | now() | — | Change timestamp |
| by_user_id | INTEGER | — | users(id) ON DELETE SET NULL | FK to user who made the change |
| type | TEXT | — | — | Change type (tag, delete, restore, etc.) |
| old | TEXT | — | — | Previous value |
| new | TEXT | — | — | New value |

**Indexes:**
- `idx_file_changes_by_user_id` — on `by_user_id`
- `file_changes_file_id` — on `file_id`

---

## replicas

Storage replica configuration for multi-site replication.

| Column | Type | Default | FK | Description |
|--------|------|---------|----|-------------|
| id | BIGINT | GENERATED ALWAYS AS IDENTITY | — | Primary key |
| type | TEXT | — | — | Storage type: local, s3, b2 |
| location | TEXT | — | — | File path or bucket name |
| master | BOOLEAN | FALSE | — | Whether this is the active master replica |
| delay | INTEGER | 0 | — | Replication delay in seconds |
| status | TEXT | — | — | Replica status |
| total | INTEGER | 0 | — | Total files count |
| meta | JSONB | — | — | Additional config (credentials, options) |

**Indexes:**
- `replicas_master_unique` — UNIQUE on `master` (partial, WHERE master = TRUE)

**Constraints:**
- UNIQUE (location)

---

## replica_files

File-to-replica mapping for distributed storage.

| Column | Type | Default | FK | Description |
|--------|------|---------|----|-------------|
| id | BIGINT | GENERATED ALWAYS AS IDENTITY | — | Primary key |
| replica_id | INTEGER | — | replicas(id) ON DELETE CASCADE | FK to replica |
| file_id | INTEGER | — | files(id) ON DELETE CASCADE | FK to file |
| location | TEXT | — | — | Replica-specific file path |
| status | INTEGER | — | — | Sync status code |
| created | TIMESTAMPTZ | now() | — | Row creation timestamp |
| updated | TIMESTAMPTZ | now() | — | Row last-updated timestamp |
| meta | JSONB | — | — | Replica-specific metadata |

**Indexes:**
- `idx_replica_files_file_id` — on `file_id`
- `idx_rf_replica_status` — on `(replica_id, status)`
- `replica_files_replica_id` — on `replica_id`

**Constraints:**
- UNIQUE (replica_id, file_id)

---

## logs

Application audit log entries.

| Column | Type | Default | FK | Description |
|--------|------|---------|----|-------------|
| id | BIGINT | GENERATED ALWAYS AS IDENTITY | — | Primary key |
| created | TIMESTAMPTZ | now() | — | Log entry timestamp |
| log | TEXT | — | — | Log message text |
| tenant | TEXT | — | — | Tenant slug for multi-tenant audit |
| request_id | TEXT | — | — | Correlation request ID |
| trace_id | TEXT | — | — | Distributed tracing trace ID |

**Indexes:**
- `idx_logs_created` — on `created`
- `ix_logs_tenant` — on `tenant`
- `ix_logs_request_id` — on `request_id`

---

## shared_files

Expiring share links for file access.

| Column | Type | Default | FK | Description |
|--------|------|---------|----|-------------|
| id | BIGINT | GENERATED ALWAYS AS IDENTITY | — | Primary key |
| created | TIMESTAMPTZ | now() | — | Share creation timestamp |
| expires | TIMESTAMPTZ | — | — | Expiration timestamp |
| file_id | INTEGER | — | files(id) ON DELETE CASCADE | FK to shared file |
| hash | TEXT | — | — | Share token hash |
| updated_at | TIMESTAMPTZ | now() | — | Row last-updated timestamp |

**Indexes:**
- `idx_shared_files_file_id` — on `file_id`
- `ix_shared_files_updated_at` — on `updated_at`
- `shared_files_hash` — on `hash`

**Constraints:**
- `uq_shared_files_hash` — UNIQUE (hash)

---

## login_attempts

Persistent rate-limiting audit for login endpoints.

| Column | Type | Default | FK | Description |
|--------|------|---------|----|-------------|
| id | BIGINT | GENERATED ALWAYS AS IDENTITY | — | Primary key |
| ip | INET | — | — | Client IP address |
| endpoint | TEXT | 'login' | — | Endpoint path |
| success | BOOLEAN | FALSE | — | Whether login succeeded |
| created | TIMESTAMPTZ | now() | — | Attempt timestamp |

**Indexes:**
- `login_attempts_ip_created` — on `(ip, created DESC)`
- `login_attempts_created` — on `created`

---

## roles

RBAC role definitions with permission sets.

| Column | Type | Default | FK | Description |
|--------|------|---------|----|-------------|
| id | UUID | gen_random_uuid() | — | Primary key |
| name | TEXT | — | — | Display name |
| slug | TEXT | — | — | Unique URL-safe slug |
| permissions | JSONB | '[]'::jsonb | — | Array of permission slugs |
| built_in | BOOLEAN | FALSE | — | Whether role is system-defined |
| tenant_id | TEXT | — | — | Tenant scope (null = global) |
| description | TEXT | — | — | Human-readable description |
| created_at | TIMESTAMPTZ | now() | — | Row creation timestamp |
| updated_at | TIMESTAMPTZ | now() | — | Row last-updated timestamp |

**Indexes:**
- `roles_slug` — on `slug`
- `roles_tenant` — on `tenant_id`

**Seeded roles:** super_admin, admin, technologist, radiologist, physician, cashier, tenant_admin

---

## tenants

Multi-tenant registry for isolated database deployments.

| Column | Type | Default | FK | Description |
|--------|------|---------|----|-------------|
| id | UUID | gen_random_uuid() | — | Primary key |
| name | TEXT | — | — | Organization display name |
| slug | TEXT | — | — | Unique URL-safe identifier |
| domain | TEXT | — | — | Domain for automatic routing |
| db_name | TEXT | — | — | Dedicated database name |
| db_host | TEXT | '127.0.0.1' | — | Database host |
| db_port | INTEGER | 5432 | — | Database port |
| db_user | TEXT | — | — | Database user |
| db_password | TEXT | '' | — | Database password |
| status | TEXT | 'active' | — | Tenant status: active, decommissioned |
| storage_quota_bytes | BIGINT | 0 | — | Storage quota in bytes (0 = unlimited) |
| storage_used_bytes | BIGINT | 0 | — | Current storage usage |
| decommissioned_at | TIMESTAMPTZ | — | — | Soft-delete timestamp |
| created_at | TIMESTAMPTZ | now() | — | Row creation timestamp |
| updated_at | TIMESTAMPTZ | now() | — | Row last-updated timestamp |

**Indexes:**
- `tenants_slug` — on `slug`
- `tenants_domain` — on `domain`

---

## oauth_providers

Multi-provider OAuth/OpenID Connect configuration.

| Column | Type | Default | FK | Description |
|--------|------|---------|----|-------------|
| id | UUID | gen_random_uuid() | — | Primary key |
| tenant_id | TEXT | — | — | Tenant scope (null = global) |
| slug | TEXT | — | — | Unique slug for ?idp=<slug> param |
| issuer | TEXT | — | — | OAuth issuer URL |
| client_id | TEXT | — | — | OAuth client ID |
| client_secret | TEXT | '' | — | Client secret (encrypted at rest) |
| jwks_uri | TEXT | — | — | JWKS URI for token verification |
| token_url | TEXT | — | — | Token endpoint URL |
| redirect_uri | TEXT | — | — | Callback redirect URI |
| scope | TEXT | 'openid email profile' | — | Requested scopes |
| groups_claim | TEXT | 'groups' | — | JWT claim for group membership |
| auto_provision | BOOLEAN | TRUE | — | Auto-create users on first login |
| enabled | BOOLEAN | TRUE | — | Whether provider is active |
| default_role | TEXT | 'cashier' | — | Default role for provisioned users |
| created_at | TIMESTAMPTZ | now() | — | Row creation timestamp |
| updated_at | TIMESTAMPTZ | now() | — | Row last-updated timestamp |

**Indexes:**
- `ix_oauth_providers_slug` — UNIQUE on `slug`

---

## api_keys

Service-to-service API key credentials.

| Column | Type | Default | FK | Description |
|--------|------|---------|----|-------------|
| id | UUID | gen_random_uuid() | — | Primary key |
| name | TEXT | — | — | Key display name |
| key_hash | TEXT | — | — | SHA-256 hash of the API key |
| prefix | TEXT | — | — | First 8 chars for key identification |
| service_name | TEXT | — | — | Friendly service identifier |
| permissions | JSONB | '[]' | — | Granted permission slugs |
| created_by | UUID | — | — | Admin user who created the key |
| expires_at | TIMESTAMPTZ | — | — | Key expiration timestamp |
| last_used_at | TIMESTAMPTZ | — | — | Last usage timestamp |
| enabled | BOOLEAN | TRUE | — | Whether key is active |
| created_at | TIMESTAMPTZ | now() | — | Row creation timestamp |

**Indexes:**
- `ix_api_keys_prefix` — on `prefix`

**Constraints:**
- UNIQUE (key_hash)

---

## worklist_entries

DICOM Modality Worklist scheduled procedure entries.

| Column | Type | Default | FK | Description |
|--------|------|---------|----|-------------|
| id | UUID | gen_random_uuid() | — | Primary key |
| patient_id | TEXT | — | — | Patient identifier (MRN) |
| patient_name | TEXT | '' | — | Patient name in DICOM format |
| patient_birth_date | TEXT | '' | — | Date of birth (YYYYMMDD) |
| patient_sex | TEXT | '' | — | Sex: M, F, O |
| accession_number | TEXT | '' | — | Accession number |
| requested_procedure_id | TEXT | '' | — | Procedure identifier |
| requested_procedure_desc | TEXT | '' | — | Procedure description |
| scheduled_date | DATE | — | — | Scheduled procedure date |
| scheduled_time | TIME | — | — | Scheduled procedure time |
| modality | TEXT | '' | — | DICOM modality |
| station_ae_title | TEXT | '' | — | Modality AE title |
| status | TEXT | 'scheduled' | — | Status: scheduled, performed, cancelled |
| study_uid | TEXT | '' | — | Study UID when performed |
| created_by | TEXT | '' | — | User who created the entry |
| created_at | TIMESTAMPTZ | now() | — | Row creation timestamp |
| updated_at | TIMESTAMPTZ | now() | — | Row last-updated timestamp |
| performed_at | TIMESTAMPTZ | — | — | When procedure was performed |

**Indexes:**
- `ix_worklist_accession` — on `accession_number`
- `ix_worklist_status` — on `status`
- `ix_worklist_scheduled_date` — on `scheduled_date`
- `ix_worklist_modality` — on `modality`
- `uq_worklist_accession` — UNIQUE on `accession_number` (partial, WHERE accession_number != '')

**Constraints:**
- CHECK (status IN ('scheduled', 'performed', 'cancelled'))

---

## hl7_messages

Raw HL7 message storage for audit and debugging.

| Column | Type | Default | FK | Description |
|--------|------|---------|----|-------------|
| id | UUID | gen_random_uuid() | — | Primary key |
| raw_hash | TEXT | — | — | SHA-256 hash of raw message |
| raw_content | TEXT | — | — | Full original HL7 message text |
| message_type | TEXT | '' | — | HL7 message type (ADT, ORM, etc.) |
| event_type | TEXT | '' | — | HL7 event type (A01, O01, etc.) |
| patient_id | TEXT | '' | — | Extracted patient identifier |
| accession_number | TEXT | '' | — | Extracted accession number |
| sending_facility | TEXT | '' | — | Sending facility name |
| parsed_fields | JSONB | — | — | Structured field extraction results |
| parse_status | TEXT | 'ok' | — | Parse status: ok, partial, failed |
| error_message | TEXT | '' | — | Parse error details |
| created_at | TIMESTAMPTZ | now() | — | Row creation timestamp |

**Indexes:**
- `ix_hl7_messages_hash` — on `raw_hash`
- `ix_hl7_messages_type` — on `(message_type, event_type)`
- `ix_hl7_messages_patient` — on `patient_id`
- `ix_hl7_messages_created` — on `created_at`

**Constraints:**
- CHECK (parse_status IN ('ok', 'partial', 'failed'))

---

## hl7_parse_errors

Per-field HL7 parsing failure tracking.

| Column | Type | Default | FK | Description |
|--------|------|---------|----|-------------|
| id | UUID | gen_random_uuid() | — | Primary key |
| hl7_message_id | UUID | — | hl7_messages(id) ON DELETE CASCADE | FK to parent HL7 message |
| segment | TEXT | '' | — | Segment name (PID, OBR, etc.) |
| field_number | INT | 0 | — | Field position within segment |
| field_name | TEXT | '' | — | Field display name |
| raw_value | TEXT | '' | — | Original unparsed value |
| error_message | TEXT | '' | — | Parse error description |
| created_at | TIMESTAMPTZ | now() | — | Row creation timestamp |

**Indexes:**
- `ix_hl7_parse_errors_msg` — on `hl7_message_id`

---

## routing_rules

DICOM study routing rules based on metadata conditions.

| Column | Type | Default | FK | Description |
|--------|------|---------|----|-------------|
| id | UUID | gen_random_uuid() | — | Primary key |
| name | TEXT | — | — | Rule display name |
| description | TEXT | '' | — | Rule description |
| conditions | JSONB | '{}' | — | Matching conditions on DICOM metadata |
| destination | TEXT | — | — | Target storage replica ID or URL |
| priority | INT | 0 | — | Evaluation priority (lower = first) |
| enabled | BOOLEAN | TRUE | — | Whether rule is active |
| tenant_id | TEXT | '' | — | Tenant scope |
| created_at | TIMESTAMPTZ | now() | — | Row creation timestamp |
| updated_at | TIMESTAMPTZ | now() | — | Row last-updated timestamp |

**Indexes:**
- `ix_routing_rules_enabled` — on `enabled`
- `ix_routing_rules_priority` — on `priority`
- `ix_routing_rules_tenant_id` — on `tenant_id`

---

## fhir_audit

FHIR API request audit trail.

| Column | Type | Default | FK | Description |
|--------|------|---------|----|-------------|
| id | UUID | gen_random_uuid() | — | Primary key |
| user_id | INTEGER | 0 | — | User ID making the request |
| method | TEXT | '' | — | HTTP method (GET, POST, etc.) |
| path | TEXT | '' | — | Request path |
| query_params | TEXT | '' | — | URL query parameters |
| resource_type | TEXT | '' | — | FHIR resource type |
| resource_id | TEXT | '' | — | FHIR resource ID |
| status_code | INTEGER | 0 | — | HTTP response status code |
| duration_ms | INTEGER | 0 | — | Request processing time in milliseconds |
| ip_address | TEXT | '' | — | Client IP address |
| created_at | TIMESTAMPTZ | now() | — | Row creation timestamp |

**Indexes:**
- `ix_fhir_audit_created` — on `created_at`
- `ix_fhir_audit_user` — on `user_id`
- `ix_fhir_audit_resource` — on `(resource_type, resource_id)`

---

## notifications

In-app user notification infrastructure.

| Column | Type | Default | FK | Description |
|--------|------|---------|----|-------------|
| id | UUID | gen_random_uuid() | — | Primary key |
| user_id | INTEGER | — | users(id) ON DELETE CASCADE | FK to recipient user |
| event_type | TEXT | — | — | Notification event type |
| title | TEXT | — | — | Notification title |
| body | TEXT | — | — | Notification body content |
| link | TEXT | — | — | Deep link URL |
| read | BOOLEAN | FALSE | — | Whether user has read the notification |
| created_at | TIMESTAMPTZ | now() | — | Row creation timestamp |

**Indexes:**
- `ix_notifications_user_id` — on `user_id`
- `ix_notifications_user_unread` — on `user_id` (partial, WHERE NOT read)
- `ix_notifications_created` — on `created_at DESC`

---

## fhir_config

FHIR module key-value configuration.

| Column | Type | Default | FK | Description |
|--------|------|---------|----|-------------|
| key | TEXT | — | — | Configuration key (PK) |
| value | TEXT | '' | — | Configuration value |
| updated_at | TIMESTAMPTZ | now() | — | Row last-updated timestamp |

**Seeded defaults:** enabled=false, base_url=http://localhost:8080/api/fhir, publisher=QuantumPACS, max_search_results=100, log_retention_days=30

---

## fhir_clients

SMART-on-FHIR client registrations.

| Column | Type | Default | FK | Description |
|--------|------|---------|----|-------------|
| id | UUID | gen_random_uuid() | — | Primary key |
| name | TEXT | — | — | Client display name |
| description | TEXT | '' | — | Client description |
| client_id | TEXT | — | — | OAuth client ID (unique) |
| client_secret | TEXT | — | — | OAuth client secret |
| redirect_uris | TEXT | '' | — | Space-separated allowed redirect URIs |
| grant_type | TEXT | 'client_credentials' | — | OAuth grant type |
| active | BOOLEAN | TRUE | — | Whether client is active |
| last_used | TIMESTAMPTZ | — | — | Last authentication timestamp |
| created_at | TIMESTAMPTZ | now() | — | Row creation timestamp |
| updated_at | TIMESTAMPTZ | now() | — | Row last-updated timestamp |

**Indexes:**
- `ix_fhir_clients_client_id` — on `client_id`

---

## webhooks

Outbound webhook event notification configuration.

| Column | Type | Default | FK | Description |
|--------|------|---------|----|-------------|
| id | UUID | gen_random_uuid() | — | Primary key |
| name | TEXT | — | — | Webhook display name |
| url | TEXT | — | — | Target URL for POST delivery |
| events | TEXT[] | '{}' | — | Array of event types to subscribe to |
| secret | TEXT | '' | — | HMAC signing secret |
| active | BOOLEAN | TRUE | — | Whether the webhook is enabled |
| retry_count | INTEGER | 3 | — | Delivery retry count |
| timeout_ms | INTEGER | 5000 | — | Request timeout in milliseconds |
| last_triggered_at | TIMESTAMPTZ | — | — | Last delivery attempt timestamp |
| last_status_code | INTEGER | — | — | Last HTTP response status code |
| last_error | TEXT | — | — | Last delivery error message |
| created_at | TIMESTAMPTZ | now() | — | Row creation timestamp |
| updated_at | TIMESTAMPTZ | now() | — | Row last-updated timestamp |

---

## Database Functions & Triggers

### notify_event()

PostgreSQL NOTIFY trigger function for real-time event streaming.

- **Language:** PL/pgSQL
- **Channel:** `events`
- **Payload:** JSON with keys: `table`, `action`, `old`, `new`
- **Usage:** Called by triggers on replicas and files tables

### Triggers

| Trigger | Table | Events | Function |
|---------|-------|--------|----------|
| `notify_replica_event` | replicas | INSERT, UPDATE, DELETE | notify_event() |
| `notify_file_event` | files | INSERT, UPDATE, DELETE | notify_event() |

---

## Migrations Overview

| Revision | Name | Description |
|----------|------|-------------|
| 001 | initial_schema | Core tables: users, patients, studies, series, files, file_changes, replicas, replica_files, logs, shared_files + notify_event trigger |
| 002 | schema_harden | PK on replica_files, UNIQUE on users.username, 8 FK indexes, CHECK constraints, composite index, drop redundant index |
| 003 | fk_cascades_timestamptz | ON DELETE CASCADE on 8 FKs, SET NULL on file_changes.by_user_id, TIMESTAMP→TIMESTAMPTZ conversion |
| 004 | bigint_identity | SERIAL→BIGINT GENERATED ALWAYS AS IDENTITY on 10 tables |
| 005 | login_attempts | login_attempts table for persistent rate limiting |
| 368510d43c08 | schema_harden_production | Indexes on patients(name), logs(created), UNIQUE on shared_files(hash), nullable by_user_id, users.needs_rehash |
| 007 | notify_file_events | notify trigger on files table |
| 008 | rbac_roles | roles table, role_id/oauth_sub/groups on users, 7 seed roles |
| 009 | oauth_fields | oauth_sub UNIQUE, email, avatar_url on users |
| 010 | tenants_table | tenants table for multi-tenant registry |
| 011 | tenant_column | tenant column on users |
| 012 | oauth_providers | oauth_providers table |
| 013 | oauth_providers_extras | slug + default_role on oauth_providers |
| 014 | multi_tenant_logs | tenant, request_id, trace_id on logs |
| 015 | tenant_decommissioned_at | decommissioned_at on tenants |
| 016 | api_keys | api_keys table |
| 017 | uids | study_instance_uid, accession_number, series_instance_uid, sop_instance_uid columns |
| 018 | worklist | worklist_entries table |
| 019 | hl7_tables | hl7_messages + hl7_parse_errors tables |
| 020 | routing_rules | routing_rules table |
| 021 | routing_rules_tenant_id | tenant_id on routing_rules |
| 022 | fhir_audit | fhir_audit table |
| 023 | updated_at_columns | created_at/updated_at on patients, studies, shared_files |
| 024 | token_version | token_version on users |
| 025 | fix_notify_event | COALESCE fix in notify_event() for NULL OLD/NEW |
| 026 | email_last_login | email VARCHAR(255) + last_login on users |
| 027 | worklist_unique_accession | Unique partial index on worklist_entries.accession_number |
| 028 | role_description | description column on roles |
| 029 | notifications | notifications table |
| 030 | fhir_admin | fhir_config + fhir_clients tables |
| 031 | webhooks | webhooks table |
