# Graph Report - .  (2026-07-25)

## Corpus Check
- 194 files · ~92,983 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1136 nodes · 2262 edges · 90 communities (66 shown, 24 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 186 edges (avg confidence: 0.59)
- Token cost: 30,000 input · 6,500 output

## Community Hubs (Navigation)
- Redis & Data Management
- API Routes & Auth
- DICOM File Processing
- JWT Authentication
- Site Metrics Collection
- Telemetry & Middleware
- Cornerstone Viewer Tools
- File Download API
- B2 Cloud Storage
- Linting Configuration
- Rate Limiting
- DICOM MWL SCP
- Logging & Patient API
- Replica Management
- CI & Branch Conventions
- Response Helpers & Tests
- TypeScript Config
- App Theme & Layout
- Frontend Dependencies
- Dev & Test Dependencies
- Account UI Components
- Storage Abstraction
- Changes UI
- Upload & Replica
- Database Connection Pool
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 73
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84

## God Nodes (most connected - your core abstractions)
1. `ReplicaFiles` - 46 edges
2. `Replica` - 43 edges
3. `get_conn()` - 42 edges
4. `Table` - 40 edges
5. `Users` - 40 edges
6. `Files` - 39 edges
7. `CornerstoneElement` - 39 edges
8. `Storage` - 36 edges
9. `request()` - 35 edges
10. `ok()` - 32 edges

## Surprising Connections (you probably didn't know these)
- `Backend PostgreSQL Service` --semantically_similar_to--> `Root Docker Compose`  [INFERRED] [semantically similar]
  backend/docker-compose.yaml → docker-compose.yaml
- `Pre-commit Hook Configuration` --conceptually_related_to--> `CI Pipeline Workflow`  [INFERRED]
  .pre-commit-config.yaml → .github/workflows/ci.yml
- `Pre-commit Hook Configuration` --references--> `Backend Python Dependencies`  [INFERRED]
  .pre-commit-config.yaml → backend/requirements.txt
- `Dependabot Configuration` --references--> `Backend Python Dependencies`  [EXTRACTED]
  .github/dependabot.yml → backend/requirements.txt
- `Backend CI Workflow` --references--> `Backend Python Dependencies`  [EXTRACTED]
  .github/workflows/backend.yml → backend/requirements.txt

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **External Healthcare System Integration** — _claude_docs_ai_fhir_r4_api_backend_requirements_fhir_r4_api, _claude_docs_ai_hl7_adt_orm_backend_requirements_hl7_v2x, _claude_docs_ai_dicom_mwl_scp_backend_requirements_dicom_mwl_scp [INFERRED 0.85]
- **Patient Data Pipeline** — _claude_docs_ai_hl7_adt_orm_backend_requirements_adt_messages, _claude_docs_ai_dicom_mwl_scp_backend_requirements_worklist_entry, _claude_docs_ai_fhir_r4_api_backend_requirements_patient_resource [INFERRED 0.75]
- **CI/CD Pipeline System** — _github_dependabot_file, _github_workflows_backend_file, _github_workflows_branch_name_file, _github_workflows_ci_file, _github_workflows_frontend_file, _github_workflows_security_file [EXTRACTED 1.00]
- **Production Hardening Sprint Program** — _opencode_skills_production_hardening_skill_file, _opencode_skills_production_hardening_skill_sprint_0, _opencode_skills_production_hardening_skill_sprint_1, _opencode_skills_production_hardening_skill_sprint_2, _opencode_skills_production_hardening_skill_sprint_3, _opencode_skills_production_hardening_skill_sprint_4, _opencode_skills_production_hardening_skill_sprint_5, _opencode_skills_production_hardening_skill_sprint_6, _opencode_skills_production_hardening_skill_sprint_7, _opencode_skills_production_hardening_skill_sprint_8 [EXTRACTED 1.00]
- **Production Hardening Agent Role System** — _opencode_skills_production_hardening_skill_backend_core, _opencode_skills_production_hardening_skill_backend_db, _opencode_skills_production_hardening_skill_backend_dicom, _opencode_skills_production_hardening_skill_backend_storage, _opencode_skills_production_hardening_skill_backend_realtime, _opencode_skills_production_hardening_skill_backend_security, _opencode_skills_production_hardening_skill_backend_testing, _opencode_skills_production_hardening_skill_frontend [EXTRACTED 1.00]
- **QuantumPACS Full Architecture Stack** — docs_prd_starlette_backend, docs_prd_postgresql_metadata_store, docs_prd_asyncpg_alembic, docs_prd_elasticsearch_search, docs_prd_multi_tier_storage, docs_prd_caddy_reverse_proxy, docs_prd_react_vite_antd_frontend, docs_prd_cornerstone3d_viewer, docs_prd_dicom_c_store_scp, docs_prd_jwt_auth [EXTRACTED 1.00]
- **Critical Production Blockers Requiring Immediate Fix** — docs_production_readiness_review_c01_es_atomicity, docs_production_readiness_review_c02_duplicate_usernames, docs_production_readiness_review_c05_replica_delete_race, docs_production_readiness_review_c06_missing_fk_indexes, docs_production_readiness_review_c10_ws_memory_state, docs_production_readiness_review_h09_default_secrets, docs_security_audit_s01_cors_wide_open, docs_security_audit_s03_no_rate_limiting, docs_db_schema_review_replica_files_no_pk, docs_db_schema_review_missing_cascade [EXTRACTED 1.00]
- **Database Schema Deficiencies Identified in Review** — docs_db_schema_review_replica_files_no_pk, docs_db_schema_review_timestamp_vs_timestamptz, docs_db_schema_review_serial_vs_identity, docs_db_schema_review_missing_cascade, docs_db_schema_review_insert_or_select_race, docs_db_schema_review_n_plus_one_risks, docs_db_schema_review_notify_event_trigger, docs_production_readiness_review_c06_missing_fk_indexes [EXTRACTED 1.00]

## Communities (90 total, 24 thin omitted)

### Community 0 - "Redis & Data Management"
Cohesion: 0.05
Nodes (33): close_client(), get_client(), create_conn(), Files, Log, Patient, Status, Series (+25 more)

### Community 1 - "API Routes & Auth"
Cohesion: 0.06
Nodes (22): AsyncMock, ChangePasswordRequest, LoginRequest, BaseModel, CreateUserRequest, BaseModel, UserActionRequest, ChangePassword (+14 more)

### Community 2 - "DICOM File Processing"
Cohesion: 0.07
Nodes (15): clean(), get_meta(), parse_dcm(), _safe_repval(), store(), _AsyncContextMock, TestClean, TestGetMeta (+7 more)

### Community 3 - "JWT Authentication"
Cohesion: 0.08
Nodes (24): AuthenticationBackend, _get_cache_redis(), _get_cached_active(), Starlette authentication backend — JWT token verification on every API request., _set_cached_active(), TokenAuth, User, decode() (+16 more)

### Community 4 - "Site Metrics Collection"
Cohesion: 0.07
Nodes (42): collect_metrics(), count_code_blocks(), count_equations(), count_faq_questions(), count_glossary_terms(), count_list_items(), count_quiz_questions(), count_references() (+34 more)

### Community 5 - "Telemetry & Middleware"
Cohesion: 0.10
Nodes (22): health_endpoint(), metrics_endpoint(), BaseHTTPMiddleware, record_request(), RequestIDMiddleware, parse_body(), Exception, Request body parsing with Pydantic v2 validation. Usage: data = await parse_body (+14 more)

### Community 7 - "File Download API"
Cohesion: 0.12
Nodes (17): DownloadData, DownloadFiles, DownloadToken, FileChangesHandler, FileHandler, FilesHandler, get_file_by_id(), HTTPEndpoint (+9 more)

### Community 8 - "B2 Cloud Storage"
Cohesion: 0.09
Nodes (4): B2Storage, LocalStorage, S3Storage, TestLocalStorage

### Community 9 - "Linting Configuration"
Cohesion: 0.08
Nodes (29): jsx, env, browser, es2021, extends, parser, parserOptions, ecmaFeatures (+21 more)

### Community 10 - "Rate Limiting"
Cohesion: 0.13
Nodes (5): _get_rate_redis(), Token-bucket rate limiter for login endpoint.  Limits to N attempts per IP per w, RedisTokenBucket, TokenBucket, TestTokenBucket

### Community 11 - "DICOM MWL SCP"
Cohesion: 0.10
Nodes (27): C-FIND MWL, DICOM Modality Worklist SCP, Modality Connection Status, Patient/Study Lookup, Status Transitions, Worklist Entry Management, Client State Management, Cornerstone3D (+19 more)

### Community 12 - "Logging & Patient API"
Cohesion: 0.15
Nodes (18): Any, LogsHandler, HTTPEndpoint, get_patient_by_id(), PatientHandler, HTTPEndpoint, api_error(), _default() (+10 more)

### Community 13 - "Replica Management"
Cohesion: 0.13
Nodes (8): HTTPEndpoint, ReplicaHandlers, ReplicasHandlers, created(), CreateReplicaRequest, BaseModel, UpdateReplicaRequest, Replica

### Community 14 - "CI & Branch Conventions"
Cohesion: 0.09
Nodes (24): Pull Request Template, Branch Name Convention Workflow, Backend Core Agent Role, Backend Database Agent Role, Backend DICOM Agent Role, Backend Realtime Agent Role, Backend Security Agent Role, Backend Storage Agent Role (+16 more)

### Community 15 - "Response Helpers & Tests"
Cohesion: 0.12
Nodes (4): ok(), server_error(), http_exception(), TestResponseHelpers

### Community 16 - "TypeScript Config"
Cohesion: 0.08
Nodes (23): compilerOptions, allowImportingTsExtensions, allowSyntheticDefaultImports, esModuleInterop, forceConsistentCasingInFileNames, isolatedModules, jsx, lib (+15 more)

### Community 17 - "App Theme & Layout"
Cohesion: 0.11
Nodes (17): BRAND, theme, Account, App(), Detail, Files, Login, Logs (+9 more)

### Community 18 - "Frontend Dependencies"
Cohesion: 0.10
Nodes (21): @ant-design/icons, antd, @cornerstonejs/core, @cornerstonejs/dicom-image-loader, @cornerstonejs/metadata, events, dependencies, @ant-design/icons (+13 more)

### Community 19 - "Dev & Test Dependencies"
Cohesion: 0.10
Nodes (21): eslint-plugin-react, devDependencies, eslint-plugin-react, jsdom, @playwright/test, @testing-library/jest-dom, @testing-library/user-event, @types/react (+13 more)

### Community 20 - "Account UI Components"
Cohesion: 0.15
Nodes (11): withSidebar(), Props, columns, Logs(), NotFound(), columns, mappings, Patient() (+3 more)

### Community 21 - "Storage Abstraction"
Cohesion: 0.16
Nodes (4): Storage, do_sync(), index(), TestStorageBase

### Community 22 - "Changes UI"
Cohesion: 0.17
Nodes (10): Changes(), columns, fetchWithRetry(), request(), RequestOptions, AddReplica(), s3regions, Replicas() (+2 more)

### Community 24 - "Database Connection Pool"
Cohesion: 0.15
Nodes (5): init_db(), Database connection management — unified singleton pool. Use get_conn() or get_d, Database, PostgreSQL async connection pool wrapper. Usage: get_database().acquire() for co, init()

### Community 25 - "Community 25"
Cohesion: 0.20
Nodes (11): Account(), handleResponse(), useFetch(), useFormInput(), usePrevious(), clearAttempts(), getLoginDelay(), LoginForm() (+3 more)

### Community 27 - "Community 27"
Cohesion: 0.26
Nodes (8): LinkExt(), getKey(), getOpenKey(), Sidebar(), encodeQuery(), isAdmin(), parseParams(), updateQuery()

### Community 28 - "Community 28"
Cohesion: 0.24
Nodes (7): PAGINATION, AdminFiles(), decodeUrl(), encodeUrl(), Files(), initialAdvancedFields, open()

### Community 30 - "Community 30"
Cohesion: 0.20
Nodes (11): GitHub Flow with Release Branches and Conventional Commits, FHIR R4 API for EHR Integration, Pydantic v2 Request Validation, QuantumPACS, Starlette Backend Framework, Strangler Fig Incremental Modernization Pattern, WebSocket Real-Time Annotation Sync, C10: Module-Level Mutable WS Dict Prevents Horizontal Scaling (+3 more)

### Community 31 - "Community 31"
Cohesion: 0.22
Nodes (10): Badge Generation, README Generator, Site Metrics Collection, Badge Best Practices, Badge Reference Guide, Shields.io, Badge Templates, Book Metrics (+2 more)

### Community 32 - "Community 32"
Cohesion: 0.20
Nodes (9): compilerOptions, allowSyntheticDefaultImports, module, moduleResolution, noEmit, strict, target, include (+1 more)

### Community 34 - "Community 34"
Cohesion: 0.25
Nodes (9): 9 of 10 Foreign Keys Lack Explicit ON DELETE Actions, replica_files.id Missing PRIMARY KEY Constraint, SERIAL Shorthand Creates INTEGER — Should be BIGINT IDENTITY, TIMESTAMP Without Time Zone Discards Timezone Metadata, Backup and Disaster Recovery Procedures, asyncpg + Alembic Database Layer, PostgreSQL Metadata and Audit Store, C06: Missing FK Indexes on files, studies, series (+1 more)

### Community 35 - "Community 35"
Cohesion: 0.22
Nodes (9): scripts, build, preview, start, test, test:all, test:e2e, test:e2e:ui (+1 more)

### Community 36 - "Community 36"
Cohesion: 0.33
Nodes (5): Detail(), wrap(), Managment(), sleep(), Share()

### Community 37 - "Community 37"
Cohesion: 0.25
Nodes (7): *.css, dicom-parser, *.jpg, *.png, react-highlight-words, *.svg, Window

### Community 38 - "Community 38"
Cohesion: 0.43
Nodes (7): Dependabot Configuration, Backend CI Workflow, CI Pipeline Workflow, Frontend CI Workflow, Security Lint Workflow, Pre-commit Hook Configuration, Backend Python Dependencies

### Community 39 - "Community 39"
Cohesion: 0.62
Nodes (6): manage script, create_db(), create_exts(), drop_db(), handle_db(), postgres_psql()

### Community 40 - "Community 40"
Cohesion: 0.29
Nodes (7): Login, Sidebar, Files Table, and Viewer Component Specs, QuantumPACS Brand Identity with Design Tokens, React + Vite + Ant Design Frontend, Hardcoded Color Token Audit (11 raw hex values in 5 files), Component State Matrix for 12 UI Components, Design Token System with Color Palette and Typography, QuantumPACS SVG Favicon with Blue-Indigo Gradient

### Community 41 - "Community 41"
Cohesion: 0.29
Nodes (4): bottomLeftStyle, bottomRightStyle, CEProps, CEState

### Community 42 - "Community 42"
Cohesion: 0.40
Nodes (6): DICOM Modality Worklist (MWL) SCP, HL7 v2.x ADT/ORM Message Ingestion via MLLP, DICOM C-STORE SCP, D-01: Modality Cannot Connect to DICOM Listener (Score 16), v2.1 Integration and Hardening Features (MWL, HL7, Security), E1-S1: DICOM C-STORE Receiving with Dedup (P0)

### Community 43 - "Community 43"
Cohesion: 0.33
Nodes (6): JWT Token Authentication (HS256, 14-day expiry), PBKDF2-HMAC-SHA256 Password Hashing (600k iterations), C02: No UNIQUE Constraint on Username, H09: Hardcoded Default Secrets in VCS, R-01: Custom X-Auth-Pacs Header Instead of Authorization: Bearer, S-03: No Rate Limiting on /api/login

### Community 44 - "Community 44"
Cohesion: 0.47
Nodes (5): EditableCell(), EditableContext, editableFields, EditableRow(), EditableTable()

### Community 45 - "Community 45"
Cohesion: 0.83
Nodes (4): Docker Security Practices, Layer Caching, Multi-Stage Builds, Multi-Stage Dockerfile Skill

### Community 46 - "Community 46"
Cohesion: 0.83
Nodes (3): downgrade(), _fk_name(), upgrade()

### Community 47 - "Community 47"
Cohesion: 0.50
Nodes (4): N+1 Query Risks in Replica.get_all() and Patient.get_extra(), notify_event() PostgreSQL Trigger with NULL and Size Issues, Multi-Tier Pluggable Storage Backend, Async Replication Sync Daemon (LISTEN/NOTIFY)

### Community 48 - "Community 48"
Cohesion: 0.50
Nodes (4): Sprint 0: Foundation Fixes (Config, Logging, DICOM, Storage, WS), Elasticsearch Full-Text Search, Production Readiness Verdict: NOT PRODUCTION READY (12 Critical), C01: ES Indexing Runs Outside DB Transaction

### Community 49 - "Community 49"
Cohesion: 0.50
Nodes (4): Caddy Reverse Proxy with Auto TLS, R-01/S-01: CORS Wide-Open Risk (Score 16), S-01: CORS Wide-Open (*) with Auth Error CORS Gap, S-04: No TrustedHostMiddleware Configured

### Community 50 - "Community 50"
Cohesion: 0.50
Nodes (3): name, private, version

### Community 58 - "Community 58"
Cohesion: 0.67
Nodes (3): Cornerstone3D Zero-Footprint Viewer, Zero-Footprint First UX Principle, Radiologist Persona: Board-Certified Radiologist Interpreting Images

## Knowledge Gaps
- **176 isolated node(s):** `start.sh script`, `build_docker.sh script`, `docker-entrypoint.sh script`, `browser`, `es2021` (+171 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Storage` connect `Storage Abstraction` to `Redis & Data Management`, `File Download API`, `B2 Cloud Storage`, `Replica Management`, `Upload & Replica`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Why does `Table` connect `Redis & Data Management` to `API Routes & Auth`, `Community 33`, `File Download API`, `Replica Management`, `Upload & Replica`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Why does `Users` connect `API Routes & Auth` to `Redis & Data Management`, `JWT Authentication`, `File Download API`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `ReplicaFiles` (e.g. with `DownloadData` and `DownloadFiles`) actually correct?**
  _`ReplicaFiles` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `Replica` (e.g. with `DownloadData` and `DownloadFiles`) actually correct?**
  _`Replica` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `Table` (e.g. with `FileChange` and `Files`) actually correct?**
  _`Table` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `Users` (e.g. with `Table` and `ApiException`) actually correct?**
  _`Users` has 2 INFERRED edges - model-reasoned connections that need verification._