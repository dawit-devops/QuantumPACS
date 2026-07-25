# Product Requirements Document: QuantumPACS v3.0

**Version**: 3.0.0-draft
**Status**: Draft
**Date**: 2026-07-25
**Audience**: Engineering Team, Hospital IT / PACS Administrators, Radiology Leadership, RIS Vendors
**Supersedes**: `docs/PRD.md` (v2.0.0)
**Companion Documents**:
- [Implementation Plan](IMPLEMENTATION_PLAN-v3.md) — Phased delivery with TDD vertical-slice guidance
- [Roadmap](ROADMAP-v3.md) — Versioned timeline through v4.0
- [Technical Specifications](Technical-Specifications-v3.md) — Supplement to v2 specs (not yet written)
- [Risks](Risks.md) — Expanded risk register (v3 section appended)
- [ADRs](decisions/) — ADR-014 through ADR-021 cover all major v3 decisions

---

## 1. Executive Summary

### Problem Statement

QuantumPACS v2.0.0 proved the core PACS workflow (DICOM C-STORE, web viewer, search, sharing) works well for single-site deployments, but three gaps block enterprise adoption: **(1)** no multi-tenancy — each hospital site needs a separate deployment; **(2)** no DICOMweb API — modern EHRs and RIS apps cannot integrate via REST; **(3)** no enterprise auth — hospitals cannot use their existing SSO/OAuth infrastructure. Production-readiness review (July 2026) identified 12 critical and 32 high-severity issues across data integrity, auth, performance, and testing.

### Proposed Solution

QuantumPACS v3.0 evolves the v2 monolith into a **modular monolith** with a strict internal service boundary, Redis Streams message bus, database-per-tenant multi-tenancy, full DICOMweb API (QIDO-RS / STOW-RS / WADO-RS / WADO-URI), OAuth/OIDC + RBAC enterprise auth, and HL7/FHIR integration endpoints for external RIS/EHR connectivity. The existing production-hardening sprints (S0–S8 from `IMPLEMENTATION_PLAN.md`) are a prerequisite — v3.0 ships only after all 12 critical and 32 high-severity findings are resolved.

### Success Criteria (Measurable KPIs)

| KPI | v2 Baseline | v3.0 Target | Verification Method |
|-----|-------------|-------------|---------------------|
| Study retrieval first-image p95 (500-inst CT, LAN) | ~2.5s | ≤ 1.5s | Playwright + k6 timed HTTP fetch |
| DICOM C-STORE SCP sustained throughput | ~100 MB/s | ≥ 150 MB/s | k6 + pynetdicom load fixture, 50 concurrent stores |
| Concurrent web viewer sessions | ~50 | ≥ 200 | k6 WebSocket scenario: 200 parallel viewers, 100 msgs/s each |
| API p95 latency (non-viewer endpoints, 50 RPS) | ~500ms | ≤ 300ms | k6 nightly run |
| DICOMweb QIDO-RS response time (10k studies) | N/A | ≤ 500ms p95 | k6 search benchmark |
| Test coverage — backend integration | ~0% | ≥ 80% | pytest --cov + CI gate |
| Test coverage — frontend components | ~5% | ≥ 60% | Vitest + RTL + CI gate |
| E2E critical flows automated | 3 tests | ≥ 10 Playwright specs | CI pipeline |
| Security: OWASP ZAP high-risk findings | Unknown | 0 | CI gate, every merge |
| Security: critical CVEs in deps | Unknown | 0 | pip-audit + npm audit, CI gate |
| Multi-tenant provisioning time | N/A | ≤ 60s for new tenant | Timed script |
| Cross-tenant data isolation | N/A | 0 leaks in property-based fuzz suite | Custom property test run nightly |
| System uptime SLO | ~99.9% | ≥ 99.95% excluding maintenance | Synthetic uptime monitor |
| DICOMweb conformance | N/A | Pass IHE Connectathon test suite | External audit (Q3 2027) |

---

## 2. User Experience & Functionality

### User Personas (v3 Additions and Changes)

| Persona | Role | v3-Specific Goals | v3 Pain Points Solved |
|---------|------|-------------------|-----------------------|
| **RIS Administrator** | Manages RIS↔PACS integration | Configure HL7/FHIR endpoints, map fields, monitor sync | No automated RIS integration; manual order entry |
| **Hospital IT / Security Officer** | Enterprise identity, compliance | SSO via Azure AD/Okta, audit trails, tenant isolation | Per-deployment usernames/passwords; no SOC audit lines |
| **PACS Administrator (Multi-site)** | Manages multiple hospital sites | Provision new tenants, monitor per-site health, cross-site RBAC | Separate deployments per site; no unified admin dashboard |
| **External RIS Application** | Schedules exams, sends orders | Push ORM messages, query MWL, receive DICOMweb study status | No HL7 or FHIR endpoints; no machine-readable study status |
| **Radiologist (existing, unchanged)** | Reads images | Same v2 workflow, now with DICOMweb client support | No change to core viewer workflow |
| **Referring Physician (existing, unchanged)** | Views images/reports | Same share-link workflow, now also SSO-enabled | No change, plus optional SSO login |

### User Stories (v3-Specific)

#### U-v3.1: Multi-Tenant Deployment (PACS Admin, Multi-site)

> As a multi-site PACS administrator, I want to provision a new hospital tenant from the admin dashboard so that the hospital gets its own isolated PACS instance in under 60 seconds.

**Acceptance Criteria:**
- Admin fills tenant form (name, domain, admin email, storage quota) and clicks "Provision"
- System creates new database, runs Alembic migrations, creates tenant admin user, sends welcome email
- Tenant is operational in ≤ 60s from form submission
- Tenant data is fully isolated at the database level
- Provisioning is recorded in super-admin audit log

#### U-v3.2: DICOMweb QIDO-RS (RIS Application)

> As a RIS application, I want to query studies by patient ID, accession number, modality, and date range via DICOMweb QIDO-RS so that I can display relevant imaging history in the RIS workflow.

**Acceptance Criteria:**
- `GET /api/v2/dicomweb/studies` returns JSON array of DICOM study resources per QIDO-RS spec
- Supports `PatientID`, `AccessionNumber`, `Modality`, `StudyDate` query parameters
- Returns `application/dicom+json` content type
- Pagination via `offset` and `limit` parameters (default limit 100)
- Returns 400 on unsupported query parameters
- Returns empty result set (not error) when no studies match

#### U-v3.3: DICOMweb STOW-RS (RIS / Modality)

> As a modality or RIS application, I want to push DICOM instances to QuantumPACS via HTTP POST (STOW-RS) so that I can avoid DICOM networking (port 11112) entirely.

**Acceptance Criteria:**
- `POST /api/v2/dicomweb/studies` accepts `multipart/related` with `application/dicom` parts
- Successfully parsed instances are stored identically to C-STORE path (same metadata extraction, dedup, sync)
- Returns `200` with `0000` (Success) in the response
- Returns `409` on duplicate (matching SHA-256 hash) with existing instance UID
- Rejects malformed payloads with `400`

#### U-v3.4: WADO-RS Study Retrieval (External Viewer / RIS)

> As a RIS application, I want to retrieve a study as a multipart DICOM stream via WADO-RS so that I can display images in the RIS without a separate PACS viewer launch.

**Acceptance Criteria:**
- `GET /api/v2/dicomweb/studies/{studyUID}` returns `multipart/related; type=application/dicom`
- `GET /api/v2/dicomweb/studies/{studyUID}/series/{seriesUID}` returns series-level multipart
- `GET /api/v2/dicomweb/studies/{studyUID}/series/{seriesUID}/instances/{instanceUID}` returns single instance
- Supports `Accept: application/dicom+json` for metadata-only retrieval
- Supports `?viewport=100,100` for thumbnail rendering (return `image/png`)

#### U-v3.5: OAuth/OIDC SSO Login (All Users)

> As a hospital staff member, I want to log into QuantumPACS with my corporate Azure AD / Okta credentials so that I don't need a separate PACS username and password.

**Acceptance Criteria:**
- Login page shows "Sign in with SSO" button alongside existing username/password form
- OAuth 2.0 Authorization Code flow with PKCE
- OIDC `id_token` decoded and verified against configured JWKS endpoint
- On first SSO login, user is auto-provisioned (JIT) if the email domain matches a configured tenant
- User's role is assigned from OIDC `groups` claim (configurable mapping)
- Existing v2 JWT tokens continue to work during transition
- Login failure returns to login page with descriptive error (no stack traces)

#### U-v3.6: RBAC Permissions (PACS Admin)

> As a PACS administrator, I want to assign fine-grained permissions to users so that technologists can upload studies but cannot delete files or manage users.

**Acceptance Criteria:**
- Admin UI shows role editor: create/edit/delete roles with per-resource permissions (read/write/delete/admin on files, patients, studies, users, replicas, logs, tenants)
- Built-in roles: `super_admin`, `tenant_admin`, `radiologist`, `technologist`, `referring_physician`, `auditor`
- Custom roles can be created with any combination of permissions
- Permission check runs server-side on every API call (not client-only)
- `X-Auth-Pacs` token now encodes the user's role+permissions (not just admin boolean)
- RBAC changes take effect on next token refresh (or immediately for token blocklist revocation)

#### U-v3.7: HL7 ADT/ORM Ingestion (RIS Integration)

> As a RIS application, I want to send ADT (admission/discharge/transfer) and ORM (order) messages to QuantumPACS via HL7 v2.x MLLP so that patient demographics and study orders are automatically reflected in the PACS.

**Acceptance Criteria:**
- MLLP listener on configurable port (default 12579) with TLS support
- ADT-A01 (admit) creates/updates patient record in the correct tenant
- ADT-A08 (update) updates patient demographics
- ADT-A03 (discharge) marks patient as inactive
- ORM-O01 creates a modality worklist entry linked to the patient
- Unknown HL7 segments are logged and skipped (not fatal)
- Inbound HL7 messages are logged to audit trail with SHA-256 hash for non-repudiation

#### U-v3.8: Modality Worklist C-FIND (MWL SCP)

> As a modality, I want to query the scheduled procedure worklist via DICOM MWL C-FIND so that I can retrieve patient demographics and scheduled procedure details without manual entry.

**Acceptance Criteria:**
- DICOM MWL SCP on port 11113 (configurable; alongside existing C-STORE on 11112)
- Supports C-FIND with PatientName, PatientID, AccessionNumber, ScheduledProcedureStepStartDate, Modality
- Worklist entries originate from HL7 ORM messages or from MWL admin UI
- Returns all required DICOM MWL attributes per PS3.4

#### U-v3.9: FHIR R4 ImagingStudy Query (EHR Integration)

> As an EHR application, I want to query a patient's imaging studies via FHIR R4 `ImagingStudy` resource so that I can display relevant exam history in the patient chart.

**Acceptance Criteria:**
- `GET /api/v2/fhir/ImagingStudy?patient=Patient/{id}` returns FHIR bundle
- `GET /api/v2/fhir/ImagingStudy/{id}` returns single resource
- `GET /api/v2/fhir/Patient/{id}` returns patient demographics in FHIR format
- Supports `_lastUpdated`, `_count`, `_sort` FHIR search parameters
- Returns `application/fhir+json` content type
- Returns `CapabilityStatement` at `GET /api/v2/fhir/metadata`

#### U-v3.10: Tenant-Switching Admin Dashboard (Super Admin)

> As a super administrator managing multiple hospital sites, I want to switch between tenant dashboards from a single admin panel so that I can monitor and manage all tenants without separate logins.

**Acceptance Criteria:**
- Super admin sees a tenant selector in the sidebar header
- Selecting a tenant reloads the dashboard scoped to that tenant's data
- Storage usage, user count, study count, replica status per tenant visible in tenant list
- Thumbnail health indicators (green/yellow/red) per tenant
- Super admin can impersonate a tenant admin user for debugging (logged as impersonation)

#### U-v3.11: API Versioning and Migration

> As a PACS administrator, I want to migrate from the v2 API to the v2 API without breaking existing integrations so that connected systems can upgrade on their own schedule.

**Acceptance Criteria:**
- Existing `/api/*` endpoints continue to work unchanged (aliased to `/api/v1/*`)
- New `/api/v2/*` endpoints carry all v2 functionality plus new DICOMweb, FHIR, and tenant features
- `X-API-Deprecated: true` header added to all `/api/v1/*` responses
- Deprecation notice published in release notes with sunset date (target: v4.0)
- `/api/docs` serves both v1 and v2 OpenAPI specs

### Non-Goals (Updated for v3)

These are explicitly out of scope for v3.0:

- **Built-in RIS** — QuantumPACS v3.0 exposes HL7/FHIR/MWL endpoints for external RIS integration but does not include a scheduling, billing, reporting, or physician portal UI. The `src/ris/` directory does not exist in v3.0. A built-in RIS module is scoped for v3.1.
- **Full microservices decomposition** — The v3.0 codebase is a modular monolith with one extracted service (ingestion). Full 8-service split is deferred to v3.1/v4.0 per ADR-014.
- **AI/ML inference engine** — No built-in CAD, segmentation, or inference pipeline. DICOMweb STOW-RS can receive AI-generated results, but QuantumPACS does not run models. AI pipeline is scoped for v3.2.
- **Native mobile apps** — Responsive web PWA only. No iOS or Android app builds.
- **VNA / XDS-I registry** — No IHE XDS-I.b or Cross-Community Document Sharing. Out of scope.
- **DICOM Print Management** — Not included (was v2.1 roadmapped but not built; deferred indefinitely).
- **Blockchain-based audit** — Audit trail is in PostgreSQL; no blockchain/DLT integration.

---

## 3. Technical Specifications

### 3.1 System Architecture (v3)

```
                         ┌─────────────────────────────────┐
                         │      HTTP/HTTPS / WSS (:80)      │
                         │         Caddy Reverse Proxy       │
                         └────────────────┬────────────────┘
                                          │
                    ┌─────────────────────┼──────────────────────┐
                    │                     │                      │
             ┌──────▼──────┐    ┌────────▼────────┐   ┌─────────▼─────────┐
             │  v1 API     │    │   v2 API        │   │   WebSocket       │
             │  (/api/v1/*)│    │  (/api/v2/*)    │   │   (/api/v2/ws)    │
             │  (aliased   │    │  DICOMweb       │   │                   │
             │   from /*)  │    │  FHIR R4        │   │                   │
             └──────┬──────┘    └────────┬────────┘   └─────────┬─────────┘
                    │                    │                      │
             ┌──────▼────────────────────▼──────────────────────▼──────────┐
             │                    Modular Monolith Core                      │
             │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐ │
             │  │ AuthN/Z  │ │ Metadata │ │ Storage  │ │ DICOM Listener │ │
             │  │ Module   │ │ Module   │ │ Module   │ │ (pynetdicom)   │ │
             │  │ JWT/OAuth│ │ DB + FHIR│ │ Local/S3 │ │ C-STORE + MWL  │ │
             │  │ RBAC     │ │          │ │ /B2      │ │ + C-MOVE/GET   │ │
             │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └───────┬────────┘ │
             │       │            │            │               │          │
             │  ┌────▼────────────▼────────────▼───────────────▼────────┐ │
             │  │              Redis Streams (Message Bus)              │ │
             │  │  events:ingestion │ events:sync │ events:notify       │ │
             │  └───────────────────────────────────────────────────────┘ │
             │       │            │                                        │
             │  ┌────▼────────────▼────────────────────────────────────┐  │
             │  │              Ingestion Service (extracted)            │  │
             │  │   HL7 MLLP │ ORM→MWL │ DICOMweb→C-STORE bridge       │  │
             │  └───────────────────────────────────────────────────────┘  │
             └──────────────────────────────────────────────────────────────┘
                                          │
             ┌────────────────────────────┼────────────────────────────┐
             │                  ┌─────────▼──────────┐                  │
             │                  │  Tenant Registry   │                  │
             │                  │  DB-per-tenant     │                  │
             │                  │  Connection Router  │                  │
             │                  └─────────┬──────────┘                  │
             │                            │                             │
             │    ┌───────────────────────┼───────────────────────┐    │
             │    │        ┌──────────────┴──────────────┐        │    │
             │    │        │     PostgreSQL (per tenant)  │        │    │
             │    │        │  Metadata · Auth · Audit     │        │    │
             │    │        │  + Super-admin registry DB    │        │    │
             │    │        └─────────────────────────────┘        │    │
             │    └───────────────────────────────────────────────┘    │
                                                                       
              ┌─────────────────────────────────────────────────────┐
              │            Elasticsearch (per-tenant index)          │
              │            Optional, graceful degradation            │
              └─────────────────────────────────────────────────────┘
```

**Key architectural changes from v2:**

| Aspect | v2 | v3 |
|--------|----|----|
| Architecture | Monolith, single process | Modular monolith + extracted ingestion service |
| Multi-tenancy | Single-organization only | Database-per-tenant + tenant registry |
| Auth | JWT HS256, `admin` boolean | JWT HS256 (svc) + RS256 JWKS (human) + OAuth/OIDC + RBAC |
| Message bus | PostgreSQL LISTEN/NOTIFY | Redis Streams (consumer groups, at-least-once) |
| API versioning | No prefix (`/api/*`) | `/api/v1/*` (deprecated) + `/api/v2/*` (stable) |
| DICOM network | C-STORE only | C-STORE + MWL + C-MOVE + C-GET |
| REST imaging | WADO-URI (internal only) | Full DICOMweb: QIDO-RS, STOW-RS, WADO-RS, WADO-URI |
| Integration | None | HL7 v2.x MLLP + FHIR R4 |
| Search | ES optional (graceful-degrade) | Per-tenant ES index; same graceful fallback |
| Logging | Plain-text | Structured JSON + OpenTelemetry traces |
| Testing | Unit-only (~31 tests) | Integration-first (≥80% coverage) + E2E + load |

### 3.2 Integration Points

| Integration | Protocol | Port | v3 Change from v2 |
|-------------|----------|------|-------------------|
| DICOM C-STORE SCP | DIMSE | 11112 | Unchanged (keep) |
| DICOM MWL SCP | DIMSE C-FIND | 11113 | NEW |
| DICOM C-MOVE SCP/SCU | DIMSE | 11114 | NEW |
| DICOMweb QIDO-RS | HTTPS | 80→8080 | NEW (`/api/v2/dicomweb/studies?...)` |
| DICOMweb STOW-RS | HTTPS | 80→8080 | NEW (`POST /api/v2/dicomweb/studies`) |
| DICOMweb WADO-RS | HTTPS | 80→8080 | NEW (`GET /api/v2/dicomweb/studies/{uid}`) |
| DICOMweb WADO-URI | HTTPS | 80→8080 | NEW (`/api/v2/wado?requestType=WADO&...)` |
| REST API (v1) | HTTPS | 80→8080 | Aliased from `/api/*` to `/api/v1/*`; deprecation headers |
| REST API (v2) | HTTPS | 80→8080 | NEW — all endpoints under `/api/v2/*` |
| WebSocket | WSS | 80→8080 | `/api/v2/ws` ; Redis pubsub unchanged |
| HL7 v2.x MLLP | MLLP | 12579 (config) | NEW — ingestion service |
| FHIR R4 | HTTPS | 80→8080 | NEW (`/api/v2/fhir/*`) |
| PostgreSQL | TCP | 5432 | Per-tenant DB instance or schema |
| Redis Streams | TCP | 6379 | NEW — replaces LISTEN/NOTIFY for cross-cutting events |
| Elasticsearch | HTTP | 9200 | Per-tenant index (unchanged semantics) |

### 3.3 API Surface — v2 Additions

All new endpoints under `/api/v2/*`. Existing `/api/*` endpoints remain at `/api/v1/*`.

#### DICOMweb (QIDO-RS / STOW-RS / WADO-RS / WADO-URI)

| Method | Path | Description | Auth | DICOMweb Standard |
|--------|------|-------------|------|--------------------|
| GET | `/api/v2/dicomweb/studies` | QIDO-RS: search studies | JWT/OAuth | PS3.18 §6.3 |
| GET | `/api/v2/dicomweb/studies/{studyUID}` | WADO-RS: retrieve study | JWT/OAuth | PS3.18 §6.5 |
| GET | `/api/v2/dicomweb/studies/{studyUID}/metadata` | WADO-RS: study metadata | JWT/OAuth | PS3.18 §6.5.1 |
| GET | `/api/v2/dicomweb/series?{filters}` | QIDO-RS: search series | JWT/OAuth | PS3.18 §6.4 |
| GET | `/api/v2/dicomweb/studies/{studyUID}/series/{seriesUID}` | WADO-RS: retrieve series | JWT/OAuth | PS3.18 §6.6 |
| GET | `/api/v2/dicomweb/studies/{studyUID}/series/{seriesUID}/metadata` | WADO-RS: series metadata | JWT/OAuth | PS3.18 §6.6.1 |
| GET | `/api/v2/dicomweb/instances?{filters}` | QIDO-RS: search instances | JWT/OAuth | PS3.18 §6.4 |
| GET | `/api/v2/dicomweb/studies/{studyUID}/series/{seriesUID}/instances/{instanceUID}` | WADO-RS: retrieve instance | JWT/OAuth | PS3.18 §6.7 |
| GET | `/api/v2/dicomweb/studies/{studyUID}/series/{seriesUID}/instances/{instanceUID}/metadata` | WADO-RS: instance metadata | JWT/OAuth | PS3.18 §6.7.1 |
| GET | `/api/v2/dicomweb/studies/{studyUID}/series/{seriesUID}/instances/{instanceUID}/frames/{frameNumbers}` | WADO-RS: retrieve frames | JWT/OAuth | PS3.18 §6.8 |
| POST | `/api/v2/dicomweb/studies` | STOW-RS: store instances | JWT/OAuth | PS3.18 §6.6 |
| GET | `/api/v2/wado` | WADO-URI: legacy retrieve | JWT/OAuth | PS3.18 §8 |

#### FHIR R4

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/v2/fhir/metadata` | CapabilityStatement | No |
| GET | `/api/v2/fhir/Patient` | Search patients | JWT/OAuth |
| GET | `/api/v2/fhir/Patient/{id}` | Read patient | JWT/OAuth |
| GET | `/api/v2/fhir/ImagingStudy` | Search imaging studies | JWT/OAuth |
| GET | `/api/v2/fhir/ImagingStudy/{id}` | Read imaging study | JWT/OAuth |
| GET | `/api/v2/fhir/DocumentReference` | Search reports | JWT/OAuth |
| GET | `/api/v2/fhir/DocumentReference/{id}` | Read report reference | JWT/OAuth |

#### Multi-Tenancy & Admin

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/v2/tenants` | List tenants | Super admin |
| POST | `/api/v2/tenants` | Provision tenant | Super admin |
| GET | `/api/v2/tenants/{id}` | Tenant details | Super admin |
| DELETE | `/api/v2/tenants/{id}` | Decommission tenant | Super admin |
| GET | `/api/v2/tenants/{id}/stats` | Tenant usage stats | Super/tenant admin |

#### RBAC

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/v2/roles` | List roles | Super/tenant admin |
| POST | `/api/v2/roles` | Create custom role | Super/tenant admin |
| PUT | `/api/v2/roles/{id}` | Update role permissions | Super/tenant admin |
| DELETE | `/api/v2/roles/{id}` | Delete role | Super/tenant admin |

#### OAuth/OIDC

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/v2/oauth/login` | Initiate OAuth flow | No |
| GET | `/api/v2/oauth/callback` | OAuth callback handler | No |
| POST | `/api/v2/oauth/token` | Exchange auth code for JWT | No |
| GET | `/api/v2/.well-known/openid-configuration` | OIDC discovery | No |

### 3.4 Multi-Tenancy: Database-per-Tenant

**Decision**: ADR-016 covers the full reasoning. Key mechanics:

- **Tenant Registry Database** — A lightweight PostgreSQL database (`quantumpacs_tenants`) stores one row per tenant: `id`, `name`, `slug`, `domain`, `db_name`, `db_host`, `db_port`, `db_user`, `db_password_encrypted`, `status`, `created_at`, `storage_quota_bytes`, `storage_used_bytes`.
- **Per-Tenant Database** — Each tenant gets a dedicated PostgreSQL database with the full QuantumPACS schema (users, patients, studies, series, files, logs, etc.). Alembic runs migrations per-tenant on provision.
- **Connection Routing** — A `TenantConnectionPool` class maintains a dict of per-tenant asyncpg pools. On first request for a tenant, the pool is created. Idle pools are evicted after TTL.
- **Tenant Resolution** — Extracted from request header `X-Tenant-ID: <slug>` or from the JWT's `tenant` claim. Super-admin operates on the registry DB.
- **Data Export/Import** — `./manage tenant export <slug>` produces a dump; `./manage tenant import <slug> <dump>` restores.

**Isolation boundary**: database-level. No SQL in the application code can accidentally cross tenants because each connection points to a different database.

### 3.5 Authentication & Authorization (v3)

#### Auth Stack

| Component | Protocol | Scope | Libraries |
|-----------|----------|-------|-----------|
| Internal JWT (service-to-service) | HS256 with `jti` | Internal API calls, ingestion service ↔ monolith | PyJWT (existing) |
| OAuth 2.0 Authorization Code + PKCE | RS256 (JWKS-verified) | Human login via Azure AD, Okta, Keycloak | `authlib` or `python-jose` + `httpx` |
| OIDC Discovery | `/.well-known/openid-configuration` | IdP metadata | Automatic via authlib |
| Share Links | HMAC key (unchanged from v2) | Unauthenticated study access | Existing `shared_files` table |

#### RBAC Model

The v2 `users.admin` boolean is replaced by a **role-permission** model:

```
users.role_id → roles.id
roles.permissions: JSONB
  {
    "files": ["read", "write", "delete"],
    "patients": ["read", "write"],
    "studies": ["read"],
    "users": ["read", "write", "delete", "admin"],
    "replicas": ["read", "write", "delete"],
    "logs": ["read"],
    "tenants": ["read", "write", "admin"],
    "roles": ["read", "write", "delete"]
  }
```

**Default roles:**

| Role | Permissions | Notes |
|------|-------------|-------|
| `super_admin` | All resources: all actions | Can manage tenants and all tenant data |
| `tenant_admin` | All resources within their tenant: all actions | Cannot access other tenants or tenant registry |
| `radiologist` | files/patients/studies: read, write; logs: read | Can view, annotate, edit studies |
| `technologist` | files/patients/studies: read, write | Can upload, cannot delete, cannot manage users |
| `referring_physician` | files/patients/studies: read | View-only access |
| `auditor` | logs: read; files: read (metadata only) | Read-only audit trail access |

#### Token Changes from v2

| Claim | v2 | v3 |
|-------|----|----|
| `sub` | `user_id` | `user_id` (unchanged) |
| `admin` | `true`/`false` | Removed; replaced by `role` and `permissions` |
| `role` | (absent) | Role slug |
| `permissions` | (absent) | Permission map |
| `tenant` | (absent) | Tenant slug |
| `jti` | (absent) | UUID token ID (for revocation) |

#### OAuth Flow

```
1. User clicks "Sign in with SSO"
2. Browser → GET /api/v2/oauth/login?idp=azure-ad
3. Backend redirects to IdP authorization URL (with PKCE code_verifier stored in Redis, TTL 10min)
4. User authenticates at IdP, grants consent
5. IdP redirects to /api/v2/oauth/callback?code=...
6. Backend exchanges code for tokens at IdP token endpoint
7. Backend verifies id_token (RS256, JWKS, audience, issuer, nonce)
8. Backend extracts email, groups from id_token claims
9. Backend finds or JIT-provisions user in the resolved tenant
10. Backend issues QuantumPACS JWT (HS256, with role + permissions + tenant)
11. Browser stores JWT in httpOnly cookie (unchanged from v2 L14 hardening)
```

### 3.6 DICOMweb Implementation

All DICOMweb endpoints follow **DICOM PS3.18** (DICOMweb RESTful Services):

- **Media Types**: `application/dicom+json` for metadata (QIDO-RS, WADO-RS metadata), `multipart/related; type=application/dicom` for bulk data (WADO-RS retrieve, STOW-RS store), `image/png` or `image/jpeg` for rendered thumbnails.
- **Bulk Data URI**: Instances with bulk data URIs reference `/api/v2/dicomweb/studies/{uid}/series/{uid}/instances/{uid}/bulk/{tag}`.
- **Pagination** (QIDO-RS): `offset` and `limit` query parameters. `X-Total-Count` header on response. Default limit 100, max 1000.
- **Error Responses**: Use standard DICOMweb error JSON body (`{ "error": { "code": "xxx", "message": "..." } }`).
- **CORS**: DICOMweb clients often run in-browser; CORS must allow `Accept: multipart/related`, `Content-Type: multipart/related` headers.

**STOW-RS → C-STORE bridge**: DICOM instances received via STOW-RS are stored identically to C-STORE-received instances (same metadata extraction, SHA-256 dedup, storage backend write, sync trigger). The ingestion service publishes a `study.stored` event to Redis Streams that the sync daemon consumes.

### 3.7 Redis Streams Message Bus

Replaces PostgreSQL `LISTEN/NOTIFY` as the primary inter-process event bus:

| Stream | Consumer Groups | Payload | Producers | Consumers |
|--------|----------------|---------|-----------|-----------|
| `events:ingestion` | `sync-worker`, `replica-worker`, `search-indexer` | `{study_uid, series_uid, instance_uid, hash, timestamp}` | C-STORE handler, STOW-RS handler, HL7 handler | Sync daemon, replica worker, ES indexer |
| `events:sync` | `replica-worker` | `{replica_id, file_id, action: copy/delete}` | Sync daemon | Replica copy workers |
| `events:notify` | `ws-broadcaster`, `webhook-sender` | `{file_id, change_type, by_user}` | Metadata module, file_changes module | WebSocket broadcaster, webhook interface |
| `events:auth` | `token-blocklist` | `{jti, reason: logout/revoke/expire}` | Auth module | Token blocklist consumer (Redis db=1) |

**Backward compatibility**: The existing `sync.py` LISTEN/NOTIFY listener continues to work during transition. A bridge consumer reads from `events:ingestion` and also publishes to the PG `NOTIFY events` channel so the legacy sync worker can coexist.

### 3.8 Database Schema (v3 Changes)

**New tables:**

| Table | Database | Purpose |
|-------|----------|---------|
| `tenants` | `quantumpacs_tenants` (registry DB) | Tenant registry: id, name, slug, domain, db_name, storage_quota, status |
| `roles` | Per-tenant | RBAC roles: id, name, slug, permissions (JSONB), built_in (bool) |
| `login_attempts` | Per-tenant (already exists via migration 005) | Extended with `tenant` field, OAuth provider tracking |
| `oauth_providers` | Per-tenant | OIDC provider config: id, issuer, client_id, client_secret_encrypted, jwks_uri, groups_claim, auto_provision |
| `webhooks` | Per-tenant | Registered webhooks: id, event_type, url, secret_hmac, retry_count, last_success |

**Modified tables:**

| Table | Change |
|-------|--------|
| `users` | Add `role_id` (FK to roles), `oauth_sub` (nullable, unique per provider), `groups` (JSONB, cached from OIDC) |
| `users` | Mark `admin` column as deprecated (kept for v1 backward compat; default `false`) |
| `files` | Add `dicomweb_ref` (text, URL for WADO-RS self-link) |
| `replicas` | Add `tier` column (`hot`/`warm`/`cold`) replacing `master` boolean semantics |
| `logs` | Add `tenant` column, `request_id` column, `trace_id` column |

**Indexes added** (per-tenant DB):

| Table | Index | Purpose |
|-------|-------|---------|
| `files` | `ix_files_dicomweb_ref` | DICOMweb lookup |
| `users` | `ix_users_oauth_sub` | OAuth subject lookup on JIT provisioning |
| `logs` | `ix_logs_trace_id` | Trace correlation |

### 3.9 Security & Privacy (v3 Additions)

| Concern | v3 Implementation |
|---------|-------------------|
| OAuth/OIDC tokens | Verified against IdP JWKS (RS256). Nonce + PKCE prevents replay. Tokens scoped per tenant. |
| RBAC enforcement | Server-side middleware on every API call. Permissions encoded in JWT, re-verified against DB on sensitive operations. |
| Tenant isolation | Database-per-tenant. Connection pool never crosses tenant boundary. Tenant resolver validates `X-Tenant-ID` against registry before pool assignment. |
| API versioning | Deprecation headers (`X-API-Deprecated`, `X-API-Sunset-Date`) on v1 endpoints. Grace period >12 months. |
| Audit trail | All RBAC changes, tenant provisioning, OAuth logins, and permission modifications logged to audit DB. |
| Secrets management | OAuth client secrets encrypted at rest in `oauth_providers` table (AES-256-GCM, key from env). Tenant DB passwords encrypted similarly. |
| Rate limiting | Extended from login-only (v2) to all `/api/v2/*` endpoints. Per-tenant token bucket via Redis Streams consumer. |
| Webhook security | Outbound webhooks signed with HMAC-SHA256 using per-webhook secret. Payload includes timestamp to prevent replay. |
| TLS | Caddy termination (unchanged). MLLP listener supports TLS. OAuth callbacks require HTTPS. |

---

## 4. Risks & Roadmap

### 4.1 Phased Rollout

See [`ROADMAP-v3.md`](ROADMAP-v3.md) for full timeline and dependency graph.

```
Q3 2026              Q4 2026              Q1 2027              Q2 2027
│                    │                    │                    │
├── Phase 0 ─────────┤                    │                    │
│ Production         │                    │                    │
│ Hardening (S0-S8)  │                    │                    │
├── Phase 1 ─────────┤                    │                    │
│ Foundation:        │                    │                    │
│ modular monolith   │                    │                    │
│ Redis Streams      │                    │                    │
├── Phase 2 ─────────┼────────────────────┤                    │
│ Auth & Tenancy:    │                    │                    │
│ DB-per-tenant      │                    │                    │
│ OAuth/OIDC + RBAC  │                    │                    │
│ Tenant provisioning│                    │                    │
├── Phase 3 ─────────┼────────────────────┼────────────────────┤
│ DICOM Core:        │                    │                    │
│ MWL SCP            │                    │                    │
│ C-MOVE/C-GET       │                    │                    │
│ DICOMweb full      │                    │                    │
├── Phase 4 ─────────┼────────────────────┼────────────────────┤
│ Integration:       │                    │                    │
│ HL7 MLLP           │                    │                    │
│ FHIR R4            │                    │                    │
├── Phase 5 ─────────┤                    │                    │
│ Observability:     │                    │                    │
│ Prometheus + OTLP  │                    │                    │
│ Structured logs    │                    │                    │
├── Phase 6 ─────────┼────────────────────┼────────────────────┤
│ Frontend v3:       │                    │                    │
│ RBAC UI · tenant   │                    │                    │
│ switcher · OAuth   │                    │                    │
│ mobile viewer      │                    │                    │
├── Phase 7 ─────────┼────────────────────┼────────────────────┤
│ Verification:      │                    │                    │
│ k6 nightly · IHE  │                    │                    │
│ OWASP · dep audit  │                    │                    │
├── Phase 8 ─────────┼────────────────────┼────────────────────┤
│ v1→v2 Migration:   │                    │                    │
│ dual-write · dep   │                    │                    │
│ headers · docs     │                    │                    │
│                    │                    │                    │
│ v3.0 GA ●────────────────────────────────────────────────────┤
│                    │                    │                    │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| DB-per-tenant connection pool memory exhaustion at scale | Medium | High | Idle pool eviction (TTL: 5 min); max pools configurable; connection pooling per tenant capped at 8 |
| OAuth/OIDC integration failure with hospital IdP | High | High | Test against Azure AD, Okta, Keycloak before GA; support multiple OAuth libraries `(authlib`, `python-jose`); documented IdP requirements checklist |
| Redis Streams consumer lag during ingestion burst | Medium | Medium | Monitor consumer group lag via Prometheus; auto-scale consumers by lag threshold; configure maxlen to bound memory |
| DICOMweb QIDO-RS performance degradation with large result sets | Medium | Medium | Pagination enforced (max 1000); keyset pagination for deep offsets; Elasticsearch-backed query for QIDO (graceful fallback to PG) |
| HL7 MLLP message parsing errors with non-standard HL7 variants | High | Low | Log and skip unknown segments; fuzz testing with real HL7 samples from 3+ hospital systems before GA |
| FHIR resource mapping complexity | Medium | High | Start with `Patient` + `ImagingStudy` only; `DocumentReference` deferred to v3.1 if scope expands |
| Multi-tenant schema migration conflicts | Medium | Critical | Run Alembic migrations per-tenant sequentially; migration test suite iterates over all tenant DBs before marking success |
| Frontend v3 feature scope exceeds capacity | High | Medium | Feature flags for mobile viewer, tenant switcher, OAuth screen; defer lower-priority UI to v3.1 |
| IHE Connectathon scheduling slip | Medium | High | Register 6 months in advance; run self-certification test suite 2 months before; if schedule misses, ship GA without Connectathon badge and badge in v3.0.1 |
| Production hardening (S0–S8) slips, delaying v3 start | Medium | High | Phase 0 runs in parallel with v3 planning and ADR authoring; hardening completion is a hard gate for Phase 2 but Phase 1 can start |

### 4.3 Resource Estimation

| Phase | Duration | Backend | Frontend | DevOps | DICOM/HL7 Expert | QA |
|-------|----------|---------|----------|--------|-------------------|----|
| Phase 0 (Hardening) | 2–3 weeks | 2 FTE | 1 FTE | 0.5 FTE | — | — |
| Phase 1 (Foundation) | 2 weeks | 2 FTE | — | 0.5 FTE | — | — |
| Phase 2 (Auth & Tenancy) | 4–6 weeks | 2 FTE | 1 FTE | 0.5 FTE | — | 1 FTE |
| Phase 3 (DICOM Core) | 6–8 weeks | 2 FTE | 1 FTE | 0.5 FTE | 1 FTE (contract) | 1 FTE |
| Phase 4 (Integration) | 4–6 weeks | 2 FTE | — | 0.5 FTE | 1 FTE (contract) | 1 FTE |
| Phase 5 (Observability) | 2 weeks | 1 FTE | — | 0.5 FTE | — | — |
| Phase 6 (Frontend v3) | 6–8 weeks | — | 2 FTE | — | — | 1 FTE |
| Phase 7 (Verification) | 2–3 weeks | 1 FTE | 1 FTE | 0.5 FTE | 1 FTE (contract) | 2 FTE |
| Phase 8 (Migration) | 2 weeks | 1 FTE | 1 FTE | 0.5 FTE | — | 1 FTE |
| **Total v3.0** | **~30–40 weeks** | **~13 FTE-weeks** | **~6 FTE-weeks** | **~3.5 FTE-weeks** | **~3 FTE-weeks (contract)** | **~6 FTE-weeks** |

---

## 5. Competitive Positioning (v3 Update)

| Feature | QuantumPACS v3 | Orthanc v1.12 | DCM4CHEE 5.x | Commercial (GE/Philips/Siemens) |
|---------|---------------|---------------|--------------|-------------------------------|
| Zero-footprint web viewer | Cornerstone3D (full tools) | Basic HTML viewer | Basic HTML viewer | Proprietary plugin |
| DICOMweb API (QIDO/STOW/WADO) | **Full (v3 new)** | Partial (WADO only) | Full | Full |
| Multi-tenancy | **DB-per-tenant (v3 new)** | Single-org only | Single-org only | Per-deployment licensing |
| OAuth/OIDC SSO | **Yes (v3 new)** | LDAP only | LDAP only | SAML, OAuth (enterprise tier) |
| RBAC | **Role-permission (v3 new)** | Admin/user only | Admin/user only | Full RBAC |
| HL7 v2.x integration | **Yes (v3 new)** | No | Yes (dcm4chee HL7) | Yes |
| FHIR R4 API | **Yes (v3 new)** | No | Yes | Varies |
| Elasticsearch search | Optional | Built-in SQLite FTS | No | Vendor-specific |
| Storage tiering | Local/S3/B2 + hot/warm/cold | Local only | Local + S3 | Proprietary only |
| Deployment | Single Docker image (modular monolith) | Docker | Complex EAR deploy | Appliance/cloud |
| API Versioning | v1→v2 with sunset policy | No versioning | No versioning | Vendor-specific |
| License | MIT (open source) | GPLv3 | LGPLv2 | Proprietary |
| Price | Free | Free | Free | $50k–$500k+/year |

---

## 6. Success Evaluation (v3 Gates)

### Engineering Gates (Merges Blocked If Failed)

| Gate | Check | Action |
|------|-------|--------|
| Backend integration tests | `pytest --cov --cov-fail-under=80` | Fix coverage gap |
| Frontend component tests | `vitest run --coverage --coverage.threshold.functions=60` | Fix coverage gap |
| E2E tests | `npx playwright test --reporter=json` (all 10 specs pass) | Fix broken flow |
| TypeScript strict | `tsc --noEmit --strict` (0 errors) | Fix type errors |
| Dependency audit | `pip-audit` + `npm audit` (0 critical, 0 high) | Pin or patch CVEs |
| Security scan | OWASP ZAP baseline scan (0 high-risk findings) | Fix or document false positive |
| Lint | `ruff check .` + `eslint src/` (0 errors) | Fix lint issues |
| Load test | k6: p95 < 300ms at 50 RPS for all API endpoints | Optimize bottleneck |

### Clinical Gates (Release Criteria)

| Gate | Criterion | Who Verifies |
|------|-----------|-------------|
| Study load time | p95 ≤ 1.5s for 500-inst CT over LAN | Engineering + Playwright |
| DICOM C-STORE throughput | ≥ 150 MB/s sustained | Engineering + k6 |
| Concurrent viewers | ≥ 200 simultaneous WS connections | Engineering + k6 |
| Multi-tenant isolation | 0 data leaks in property-based fuzz suite | Engineering |
| Tenant provisioning | New tenant fully operational in ≤ 60s | Engineering |
| IHE Conformance (post-GA) | Pass DICOMweb Connectathon tests | External audit |
| Upgrade from v2.0 | Zero data loss, ≤ 5 min downtime | QA + manual test |

---

*This PRD describes the scope and architecture of QuantumPACS v3.0. It supersedes `docs/PRD.md` for all v3-related work. Existing v2 capabilities documented in the previous PRD remain unless explicitly marked as removed (see §4). For implementation details, consult the companion documents and ADRs referenced above.*