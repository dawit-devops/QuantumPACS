# Data Dictionary

## Tables

### users
| Column | Type | Index | FK | Description |
|--------|------|-------|----|-------------|
| id | BIGINT | PK | | Auto-increment user ID (identity) |
| username | CITEXT | ix_users_username, uq_users_username | | Username (case-insensitive, unique) |
| password | TEXT | | | PBKDF2-SHA256 password hash |
| admin | BOOLEAN | | | Superadmin flag (deprecated — use role_id) |
| role_id | UUID | | roles.id | FK to roles table |
| status | TEXT | | | active, deactivated |
| oauth_sub | TEXT | users_oauth_sub | | OIDC subject identifier (unique, partial index) |
| email | TEXT | | | User email address |
| avatar_url | TEXT | | | User avatar URL |
| groups | JSONB | | | Group membership list from OIDC |
| tenant | TEXT | users_tenant | | Tenant scope for multi-tenancy |
| token_version | INTEGER | | | Incremented on role/permission change for forced re-auth |
| needs_rehash | BOOLEAN | | | Flag indicating legacy password needs rehashing |
| last_login | TIMESTAMP | | | Last successful login timestamp |
| created | TIMESTAMPTZ | | | Creation timestamp |
| updated | TIMESTAMPTZ | | | Last update timestamp |

### roles
| Column | Type | Index | FK | Description |
|--------|------|-------|----|-------------|
| id | UUID | PK | | UUID primary key |
| name | TEXT | | | Human-readable role name |
| slug | TEXT | roles_slug | | URL-safe role identifier (unique) |
| permissions | JSONB | | | Array of permission strings |
| built_in | BOOLEAN | | | True for system-defined roles (cannot be deleted) |
| tenant_id | TEXT | roles_tenant | | Tenant scope for multi-tenant roles |
| description | TEXT | | | Optional human-readable role explanation |
| created_at | TIMESTAMPTZ | | | Creation timestamp |
| updated_at | TIMESTAMPTZ | | | Last update timestamp |

### patients
| Column | Type | Index | FK | Description |
|--------|------|-------|----|-------------|
| id | BIGINT | PK | | Auto-increment patient ID |
| patient_id | TEXT | patients_patient_id | | External patient identifier (unique) |
| name | TEXT | idx_patients_name | | Patient full name |
| birth_date | TEXT | | | Date of birth |
| sex | TEXT | | | Sex (M/F/O) with CHECK constraint |
| meta | JSONB | | | Metadata key-value pairs |
| created_at | TIMESTAMPTZ | | | Creation timestamp |
| updated_at | TIMESTAMPTZ | ix_patients_updated_at | | Last update timestamp |

### studies
| Column | Type | Index | FK | Description |
|--------|------|-------|----|-------------|
| id | BIGINT | PK | | Auto-increment study ID |
| patient_id | INTEGER | idx_studies_patient_id | patients.id | FK to patients (CASCADE) |
| study_id | TEXT | ix_studies_study_id | | DICOM Study Instance UID or local ID |
| study_instance_uid | TEXT | ix_studies_study_instance_uid | | DICOM Study Instance UID (unique, partial) |
| accession_number | TEXT | ix_studies_accession_number | | DICOM Accession Number |
| description | TEXT | | | Study description |
| created_at | TIMESTAMPTZ | | | Creation timestamp |
| updated_at | TIMESTAMPTZ | ix_studies_updated_at | | Last update timestamp |

### series
| Column | Type | Index | FK | Description |
|--------|------|-------|----|-------------|
| id | BIGINT | PK | | Auto-increment series ID |
| study_id | INTEGER | idx_series_study_id | studies.id | FK to studies (CASCADE) |
| number | TEXT | ix_series_number | | Series number |
| series_instance_uid | TEXT | ix_series_series_instance_uid | | DICOM Series Instance UID (unique, partial) |
| modality | TEXT | | | DICOM modality (CT, MR, US, etc.) |
| description | TEXT | | | Series description |

### files / instances
| Column | Type | Index | FK | Description |
|--------|------|-------|----|-------------|
| id | BIGINT | PK | | Auto-increment file ID |
| patient_id | INTEGER | idx_files_patient_id | patients.id | FK to patients (CASCADE) |
| study_id | INTEGER | idx_files_study_id | studies.id | FK to studies (CASCADE) |
| series_id | INTEGER | idx_files_series_id | series.id | FK to series (CASCADE) |
| name | TEXT | ix_files_name | | Original filename |
| sop_instance_uid | TEXT | ix_files_sop_instance_uid | | DICOM SOP Instance UID (unique, partial) |
| indexed | BOOLEAN | | | Whether the file has been indexed for search |
| hash | TEXT | ix_files_hash | | SHA-256 hash of file contents |
| meta | JSONB | | | DICOM metadata key-value pairs |
| tools_state | JSONB | | | Viewer tool state persistence data |
| deleted | BOOLEAN | | | Soft-delete flag |
| created | TIMESTAMPTZ | | | Ingestion timestamp |
| updated | TIMESTAMPTZ | | | Last update timestamp |

### file_changes
| Column | Type | Index | FK | Description |
|--------|------|-------|----|-------------|
| id | BIGINT | PK | | Auto-increment change ID |
| file_id | INTEGER | idx_file_changes_file_id | files.id | FK to files (CASCADE) |
| by_user_id | INTEGER | idx_file_changes_by_user_id | users.id | FK to users (SET NULL) |
| type | TEXT | | | Change type (created/updated/deleted) |
| old | TEXT | | | Previous value |
| new | TEXT | | | New value |
| created | TIMESTAMPTZ | | | Change timestamp |

### replicas
| Column | Type | Index | FK | Description |
|--------|------|-------|----|-------------|
| id | BIGINT | PK | | Auto-increment replica ID |
| type | TEXT | | | Replica type (local/s3/b2) |
| location | TEXT | | | File path or bucket name (unique) |
| master | BOOLEAN | replicas_master_unique | | True for the master replica (unique partial) |
| delay | INTEGER | | | Replication delay in seconds |
| status | TEXT | | | Replica status |
| total | INTEGER | | | Total files replicated |
| meta | JSONB | | | Metadata key-value pairs |

### replica_files
| Column | Type | Index | FK | Description |
|--------|------|-------|----|-------------|
| id | BIGINT | PK | | Auto-increment ID |
| replica_id | INTEGER | idx_replica_files_replica_id | replicas.id | FK to replicas (CASCADE) |
| file_id | INTEGER | idx_replica_files_file_id | files.id | FK to files (CASCADE) |
| location | TEXT | | | Replica file path |
| status | INTEGER | | | Sync status code |
| meta | JSONB | | | Metadata key-value pairs |
| created | TIMESTAMPTZ | | | Creation timestamp |
| updated | TIMESTAMPTZ | | | Last update timestamp |
| UNIQUE(replica_id, file_id) | | idx_rf_replica_status | | Compound unique + composite index |

### logs / audit_log
| Column | Type | Index | FK | Description |
|--------|------|-------|----|-------------|
| id | BIGINT | PK | | Auto-increment log ID |
| tenant | TEXT | ix_logs_tenant | | Tenant scope for multi-tenant audit |
| request_id | TEXT | ix_logs_request_id | | Request correlation ID |
| trace_id | TEXT | | | Distributed trace ID |
| log | TEXT | ix_audit_log_event_type | | Log content (JSONB GIN index) |
| created | TIMESTAMPTZ | idx_logs_created | | Log timestamp |

### shared_files
| Column | Type | Index | FK | Description |
|--------|------|-------|----|-------------|
| id | BIGINT | PK | | Auto-increment share ID |
| file_id | INTEGER | idx_shared_files_file_id | files.id | FK to files (CASCADE) |
| hash | TEXT | ix_shared_files_hash, uq_shared_files_hash | | Unique share token hash |
| expires | TIMESTAMPTZ | | | Share link expiration |
| created | TIMESTAMPTZ | | | Creation timestamp |
| updated_at | TIMESTAMPTZ | ix_shared_files_updated_at | | Last update timestamp |

### login_attempts
| Column | Type | Index | FK | Description |
|--------|------|-------|----|-------------|
| id | BIGINT | PK | | Auto-increment ID |
| ip | INET | login_attempts_ip_created | | Client IP address |
| endpoint | TEXT | | | Endpoint being accessed (default: login) |
| success | BOOLEAN | | | Whether the attempt succeeded |
| created | TIMESTAMPTZ | login_attempts_created | | Attempt timestamp |

### worklist_entries
| Column | Type | Index | FK | Description |
|--------|------|-------|----|-------------|
| id | UUID | PK | | UUID primary key |
| patient_id | TEXT | | | Patient identifier |
| patient_name | TEXT | | | Patient full name |
| patient_birth_date | TEXT | | | Patient date of birth |
| patient_sex | TEXT | | | Patient sex |
| accession_number | TEXT | ix_worklist_accession, uq_worklist_accession | | Accession number (unique when non-empty) |
| requested_procedure_id | TEXT | | | Requested procedure identifier |
| requested_procedure_desc | TEXT | | | Requested procedure description |
| scheduled_date | DATE | ix_worklist_scheduled_date | | Scheduled procedure date |
| scheduled_time | TIME | | | Scheduled procedure time |
| modality | TEXT | ix_worklist_modality | | DICOM modality |
| station_ae_title | TEXT | | | Target station AE title |
| status | TEXT | ix_worklist_status, ix_worklist_entries_status | | scheduled/performed/cancelled (CHECK constraint) |
| study_uid | TEXT | | | Linked study UID |
| created_by | TEXT | | | User who created the entry |
| created_at | TIMESTAMPTZ | | | Creation timestamp |
| updated_at | TIMESTAMPTZ | | | Last update timestamp |
| performed_at | TIMESTAMPTZ | | | When the procedure was performed |

### hl7_messages
| Column | Type | Index | FK | Description |
|--------|------|-------|----|-------------|
| id | UUID | PK | | UUID primary key |
| raw_hash | TEXT | ix_hl7_messages_hash | | SHA-256 hash of raw message |
| raw_content | TEXT | | | Complete raw HL7 message |
| message_type | TEXT | ix_hl7_messages_type | | HL7 message type (ADT, ORM, etc.) |
| event_type | TEXT | ix_hl7_messages_type | | HL7 event type (A01, O01, etc.) |
| patient_id | TEXT | ix_hl7_messages_patient | | Extracted patient ID |
| accession_number | TEXT | | | Extracted accession number |
| sending_facility | TEXT | | | Sending facility name |
| parsed_fields | JSONB | | | Structured parsed fields |
| parse_status | TEXT | | | ok/partial/failed (CHECK constraint) |
| error_message | TEXT | | | Parse error details |
| created_at | TIMESTAMPTZ | ix_hl7_messages_created | | Ingestion timestamp |

### hl7_parse_errors
| Column | Type | Index | FK | Description |
|--------|------|-------|----|-------------|
| id | UUID | PK | | UUID primary key |
| hl7_message_id | UUID | ix_hl7_parse_errors_msg | hl7_messages.id | FK to hl7_messages (CASCADE) |
| segment | TEXT | | | HL7 segment name |
| field_number | INTEGER | | | Field position in segment |
| field_name | TEXT | | | Human-readable field name |
| raw_value | TEXT | | | Original unparsed value |
| error_message | TEXT | | | Error description |
| created_at | TIMESTAMPTZ | | | Creation timestamp |

### routing_rules
| Column | Type | Index | FK | Description |
|--------|------|-------|----|-------------|
| id | UUID | PK | | UUID primary key |
| name | TEXT | | | Routing rule name |
| description | TEXT | | | Rule description |
| conditions | JSONB | | | DICOM metadata match conditions |
| destination | TEXT | | | Destination AE title or URL |
| priority | INTEGER | ix_routing_rules_priority | | Evaluation priority |
| enabled | BOOLEAN | ix_routing_rules_enabled | | Whether the rule is active |
| tenant_id | TEXT | ix_routing_rules_tenant_id | | Tenant scope for multi-tenant routing |
| created_at | TIMESTAMPTZ | | | Creation timestamp |
| updated_at | TIMESTAMPTZ | | | Last update timestamp |

### fhir_audit
| Column | Type | Index | FK | Description |
|--------|------|-------|----|-------------|
| id | UUID | PK | | UUID primary key |
| user_id | INTEGER | ix_fhir_audit_user | | User who made the request |
| method | TEXT | | | HTTP method |
| path | TEXT | | | Request path |
| query_params | TEXT | | | Query parameters |
| resource_type | TEXT | ix_fhir_audit_resource | | FHIR resource type |
| resource_id | TEXT | ix_fhir_audit_resource | | FHIR resource ID |
| status_code | INTEGER | | | HTTP response status |
| duration_ms | INTEGER | | | Request duration in ms |
| ip_address | TEXT | | | Client IP address |
| created_at | TIMESTAMPTZ | ix_fhir_audit_created | | Request timestamp |

### fhir_config
| Column | Type | Index | FK | Description |
|--------|------|-------|----|-------------|
| key | TEXT | PK | | Configuration key |
| value | TEXT | | | Configuration value |
| updated_at | TIMESTAMPTZ | | | Last update timestamp |

### fhir_clients
| Column | Type | Index | FK | Description |
|--------|------|-------|----|-------------|
| id | UUID | PK | | UUID primary key |
| name | TEXT | | | Client application name |
| description | TEXT | | | Client description |
| client_id | TEXT | ix_fhir_clients_client_id | | OAuth client ID (unique) |
| client_secret | TEXT | | | OAuth client secret |
| redirect_uris | TEXT | | | Authorized redirect URIs |
| grant_type | TEXT | | | OAuth 2.0 grant type |
| active | BOOLEAN | | | Whether the client is enabled |
| last_used | TIMESTAMPTZ | | | Last authentication timestamp |
| created_at | TIMESTAMPTZ | | | Creation timestamp |
| updated_at | TIMESTAMPTZ | | | Last update timestamp |

### notifications
| Column | Type | Index | FK | Description |
|--------|------|-------|----|-------------|
| id | UUID | PK | | UUID primary key |
| user_id | INTEGER | ix_notifications_user_id, ix_notifications_user_unread | users.id | FK to users (CASCADE) |
| event_type | TEXT | | | Notification event type |
| title | TEXT | | | Notification title |
| body | TEXT | | | Notification body |
| link | TEXT | | | Deep link URL |
| read | BOOLEAN | | | Whether the notification has been read |
| created_at | TIMESTAMPTZ | ix_notifications_created | | Creation timestamp |

### webhooks
| Column | Type | Index | FK | Description |
|--------|------|-------|----|-------------|
| id | UUID | PK | | UUID primary key |
| name | TEXT | | | Webhook display name |
| url | TEXT | | | Target URL for outbound payload |
| events | TEXT[] | | | Array of event types to trigger on |
| secret | TEXT | | | HMAC signing secret |
| active | BOOLEAN | | | Whether the webhook is enabled |
| retry_count | INTEGER | | | Max retry attempts on failure |
| timeout_ms | INTEGER | | | Request timeout in ms |
| last_triggered_at | TIMESTAMPTZ | | | Last trigger timestamp |
| last_status_code | INTEGER | | | Last HTTP response status |
| last_error | TEXT | | | Last error message |
| created_at | TIMESTAMPTZ | | | Creation timestamp |
| updated_at | TIMESTAMPTZ | | | Last update timestamp |

### tenants
| Column | Type | Index | FK | Description |
|--------|------|-------|----|-------------|
| id | UUID | PK | | UUID primary key |
| name | TEXT | | | Tenant display name |
| slug | TEXT | tenants_slug | | URL-safe tenant identifier (unique) |
| domain | TEXT | tenants_domain | | Tenant domain for auto-routing |
| db_name | TEXT | | | Dedicated database name |
| db_host | TEXT | | | Dedicated database host |
| db_port | INTEGER | | | Dedicated database port |
| db_user | TEXT | | | Dedicated database user |
| db_password | TEXT | | | Dedicated database password |
| status | TEXT | | | active/inactive/locked |
| storage_quota_bytes | BIGINT | | | Storage quota in bytes |
| storage_used_bytes | BIGINT | | | Current storage usage |
| decommissioned_at | TIMESTAMPTZ | | | Soft-delete timestamp |
| created_at | TIMESTAMPTZ | | | Creation timestamp |
| updated_at | TIMESTAMPTZ | | | Last update timestamp |

### oauth_providers
| Column | Type | Index | FK | Description |
|--------|------|-------|----|-------------|
| id | UUID | PK | | UUID primary key |
| tenant_id | TEXT | | | Tenant scope |
| slug | TEXT | ix_oauth_providers_slug | | URL-friendly provider identifier (unique) |
| issuer | TEXT | | | OIDC issuer URL |
| client_id | TEXT | | | OAuth 2.0 client ID |
| client_secret | TEXT | | | OAuth 2.0 client secret (encrypted at rest) |
| jwks_uri | TEXT | | | JWKS URI for signature verification |
| token_url | TEXT | | | Token endpoint URL |
| redirect_uri | TEXT | | | OAuth redirect URI |
| scope | TEXT | | | OAuth scope string |
| groups_claim | TEXT | | | JWT claim for group mapping |
| default_role | TEXT | | | Default role slug for JIT-provisioned users |
| auto_provision | BOOLEAN | | | Auto-create user accounts on first login |
| enabled | BOOLEAN | | | Whether the provider is active |
| created_at | TIMESTAMPTZ | | | Creation timestamp |
| updated_at | TIMESTAMPTZ | | | Last update timestamp |

### api_keys
| Column | Type | Index | FK | Description |
|--------|------|-------|----|-------------|
| id | UUID | PK | | UUID primary key |
| name | TEXT | | | API key display name |
| key_hash | TEXT | | | SHA-256 hash of the API key (unique) |
| prefix | TEXT | ix_api_keys_prefix | | Readable key prefix for identification |
| service_name | TEXT | | | Name of the service using this key |
| permissions | JSONB | | | Permission strings for this key |
| created_by | UUID | | | User ID that created this key |
| expires_at | TIMESTAMPTZ | | | Expiration timestamp |
| last_used_at | TIMESTAMPTZ | | | Last usage timestamp |
| enabled | BOOLEAN | | | Whether the key is active |
| created_at | TIMESTAMPTZ | | | Creation timestamp |
