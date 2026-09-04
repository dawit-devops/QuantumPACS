# Persona: EMR/EHR Applications

## Persona Card

| Attribute | Detail |
|-----------|--------|
| **Role** | Electronic Medical/Health Record system (e.g., Epic, Cerner, Meditech) integrating with QuantumPACS for imaging retrieval and referral |
| **Description** | Backend machine application (system-to-system) that queries patient demographics and imaging studies via FHIR R4 APIs or DICOMweb, and retrieves DICOM data for display within the EMR workflow |
| **Technical Level** | High — API-driven integration, OAuth/OIDC tokens, FHIR R4 resource handling |
| **Frequency** | Continuous — invoked per patient encounter, per ordered study |
| **Devices** | Application server, backend service, middleware |
| **Critical Needs** | Reliable FHIR endpoint availability, correct Patient/ImagingStudy mapping, secure token management, DICOM retrieval for in-EMR display |
| **Frustrations** | FHIR CapabilityStatement doesn't declare all supported search params; no client_credentials grant in v3; XML format not yet supported |
| **Integration Pattern** | Backend services / machine-to-machine (API Key or OAuth Client Credentials) |

## Routes & Permissions

### Authentication Methods

#### A. API Key (Recommended for EMR/EHR Backend Services)

| Method | Header | Format | Permission Required |
|--------|--------|--------|---------------------|
| API Key header | `X-API-Key` | `qpk_<secrets.token_urlsafe(32)>` (55 chars, SHA-256 hash stored in DB) | `SERVICE_KEY_WRITE` (to create key) |

- EMR calls `POST /api/api-keys` to generate a key (requires `SERVICE_KEY_WRITE`)
- Key identity appears as `svc_{service_name}` user identity
- Permissions are embedded in the API key record
- Key prefix (`qpk_` + 8 chars) used for lookup; full key hashed for comparison

#### B. JWT Bearer Token (EMR Exchanges OAuth Token for QuantumPACS JWT)

| Method | Header | Format |
|--------|--------|--------|
| Bearer token exchange | `Authorization: Bearer <jwt>` | HS256 JWT signed by QuantumPACS |
| PACS header | `X-Auth-Pacs` | Same JWT as above |

#### C. OAuth/OIDC (Human-Facing; EMR Backend Uses Token Exchange)

| Method | Endpoint | Grant Type |
|--------|----------|-----------|
| OIDC discovery | `GET /api/.well-known/openid-configuration` | — |
| Token endpoint | `POST /api/oauth/token` | `refresh_token` |
| Login redirect | `GET /api/oauth/login?idp=<slug>` | Authorization Code + PKCE |

#### Auth Middleware Resolution Order (`backend/api/auth.py`)

1. Check `_PUBLIC_PATHS` — exempt if matches
2. Check `OPTIONS` method — exempt
3. Check `X-API-Key` header → validate via `ApiKeys.validate()`
4. Check `X-Auth-Pacs` header → JWT decode
5. Check `Authorization: Bearer {token}` → JWT decode
6. Check `?token=` query parameter → JWT decode
7. Check `token` cookie → JWT decode
8. Check shared file key → `SharedFiles.check()`
9. Fall through to 401

### FHIR R4 API Endpoint Catalog (all under `/api/fhir/`, aliased to `/api/v2/fhir/`)

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| GET | `/api/v2/fhir/metadata` | `PATIENT_READ` | CapabilityStatement (FHIR server capabilities) |
| GET | `/api/v2/fhir/Patient` | `PATIENT_READ` | Search patients |
| POST | `/api/v2/fhir/Patient` | `PATIENT_WRITE` | Create patient |
| GET | `/api/v2/fhir/Patient/{id}` | `PATIENT_READ` | Read single patient |
| PUT | `/api/v2/fhir/Patient/{id}` | `PATIENT_WRITE` | Update patient |
| DELETE | `/api/v2/fhir/Patient/{id}` | `PATIENT_WRITE` | Delete patient |
| GET | `/api/v2/fhir/ImagingStudy` | `DICOMWEB_READ` | Search imaging studies |
| GET | `/api/v2/fhir/ImagingStudy/{id}` | `DICOMWEB_READ` | Read single imaging study |
| GET | `/api/v2/fhir/DocumentReference` | `FILE_READ` | Search document references (reports) |
| GET | `/api/v2/fhir/DocumentReference/{id}` | `FILE_READ` | Read single document reference |

### FHIR Search Parameters by Resource

#### Patient (`GET /api/v2/fhir/Patient`)

| Parameter | Type | Implementation |
|-----------|------|---------------|
| `identifier` | token | Exact match on `patients.patient_id` |
| `name` | string | Partial match (`ILIKE '%value%'`) on `patients.name` |
| `birthdate` | date | Exact match on `patients.birth_date` |
| `_lastUpdated` | date | Prefix operators: `ge`, `gt`, `le`, `lt`, `eq`, `ne`, `sa`, `eb`, `ap` |
| `_count` | number | Page size (max 100, default all) |
| `_sort` | string | Allowed: `patient_id`, `name`, `birth_date` (prefix `-` for DESC) |

#### ImagingStudy (`GET /api/v2/fhir/ImagingStudy`)

| Parameter | Type | Implementation |
|-----------|------|---------------|
| `patient` | reference | Subquery on `patients.patient_id` matching `Patient/{id}` format |
| `accession` | token | Exact match on `studies.accession_number` |
| `modality` | token | Subquery on `series.modality` |
| `started` | date | Parsed but not applied in code (bug/limitation) |
| `_lastUpdated` | date | Prefix operators on `studies.updated_at` |
| `_count` | number | Page size (max 100) |
| `_sort` | string | Allowed: `study_instance_uid`, `accession_number`, `description` |

#### DocumentReference (`GET /api/v2/fhir/DocumentReference`)

| Parameter | Type | Implementation |
|-----------|------|---------------|
| `patient` | reference | `WHERE pa.patient_id = $1` |
| `type` | token | Matches `files.meta->>'type'` |
| `period` | date | Date range on `shared_files.created` with prefix operators |
| `_lastUpdated` | date | Prefix operators on shared_files |

### DICOMweb API (Alternative Query Path)

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| GET | `/api/v2/dicomweb/studies` | `DICOMWEB_READ` | QIDO-RS study search |
| GET | `/api/v2/dicomweb/studies/{uid}/series` | `DICOMWEB_READ` | QIDO-RS series search |
| GET | `/api/v2/dicomweb/studies/{uid}/series/{uid}/instances` | `DICOMWEB_READ` | QIDO-RS instance search |
| GET | `/api/v2/dicomweb/studies/{uid}` | `DICOMWEB_READ` | WADO-RS full study retrieval |
| GET | `/api/v2/dicomweb/studies/{uid}/series/{uid}` | `DICOMWEB_READ` | WADO-RS series retrieval |
| GET | `/api/v2/dicomweb/studies/{uid}/series/{uid}/instances/{uid}` | `DICOMWEB_READ` | WADO-RS single instance retrieval |
| POST | `/api/v2/dicomweb/studies` | `DICOMWEB_WRITE` | STOW-RS DICOM upload |

### Tenant Isolation

- EMR sends `X-Tenant-ID: <slug>` header to scope requests to a specific hospital tenant
- `TenantMiddleware` resolves tenant → routes to that tenant's PostgreSQL database
- JWT can also carry `tenant` claim (from `create_token()` when `user['tenant']` is set)

## End-to-End Flows

### Flow 1: "Show Me All Imaging for Patient X" (FHIR R4)

#### Step 1: Authenticate

```
Option A — API Key:
  Header: X-API-Key: qpk_...
  No token exchange needed; static key validated on each request

Option B — JWT:
  1. EMR has stored JWT from initial login/token exchange
  2. Each request includes: Authorization: Bearer <jwt>
  3. JWT HS256 verified by QuantumPACS middleware
  4. Token expiry: 1h access token, 14d refresh token

Option C — OAuth Token Exchange:
  1. EMR calls POST /api/oauth/token { grant_type: <type>, ... }
  2. Receives HS256 JWT access_token
  3. Uses token in subsequent FHIR requests
```

#### Step 2: Resolve Patient

```
GET /api/v2/fhir/Patient?identifier=MRN12345
Headers: Authorization: Bearer <jwt>
Accept: application/fhir+json

Response 200:
{
  "resourceType": "Bundle",
  "type": "searchset",
  "total": 1,
  "entry": [{
    "resource": {
      "resourceType": "Patient",
      "id": "MRN12345",
      "identifier": [{"value": "MRN12345"}],
      "name": [{"family": "Smith", "given": ["John"]}],
      "gender": "male",
      "birthDate": "1970-01-01"
    }
  }]
}
```

Identity mapping: DICOM `PatientID` (0010,0020) → `patients.patient_id` → FHIR `Patient.identifier.value` (system: `http://hl7.org/fhir/v2/0203`, code: `MR`)

#### Step 3: Query Imaging Studies

```
GET /api/v2/fhir/ImagingStudy?patient=Patient/MRN12345
Headers: Authorization: Bearer <jwt>
Accept: application/fhir+json

Response 200:
{
  "resourceType": "Bundle",
  "type": "searchset",
  "total": 3,
  "entry": [{
    "resource": {
      "resourceType": "ImagingStudy",
      "id": "1.2.840.12345.1.234",
      "identifier": [{"value": "S20260723"}],
      "status": "available",
      "subject": {"reference": "Patient/MRN12345"},
      "endpoint": [{"reference": "http://localhost:8080/api/dicomweb"}],
      "description": "CHEST PA AND LAT",
      "series": [{
        "uid": "1.2.840.12345.1.235",
        "number": 1,
        "modality": {"system": "http://dicom.nema.org/resources/ontology/DCM", "code": "CT"},
        "description": "Scout",
        "instance": [{
          "uid": "1.2.840.12345.1.236",
          "sopClass": {"system": "http://dicom.nema.org/resources/ontology/DCM", "code": "1.2.840.10008.5.1.4.1.1.2"},
          "number": 1
        }]
      }]
    }
  }]
}
```

Patient identity mapping for `patient` search param:
Format `Patient/{logical_id}` → subquery `EXISTS (SELECT 1 FROM patients pa WHERE pa.id = studies.patient_id AND pa.patient_id = {value})`

#### Step 4 (Optional): Read Individual Study

```
GET /api/v2/fhir/ImagingStudy/1.2.840.12345.1.234
Headers: Authorization: Bearer <jwt>

→ Single ImagingStudy resource (same structure as above)
```

#### Step 5 (Optional): Retrieve DICOM Data

```
GET /api/v2/dicomweb/studies/1.2.840.12345.1.234
  (multipart/related; type=application/dicom — all instances in study)

GET /api/v2/dicomweb/studies/1.2.840.12345.1.234/series/1.2.840.12345.1.235
  (single series retrieval)

GET /api/v2/dicomweb/studies/1.2.840.12345.1.234/series/1.2.840.12345.1.235/instances/1.2.840.12345.1.236
  (single DICOM instance)
```

#### Step 6 (Optional): Get Reports

```
GET /api/v2/fhir/DocumentReference?patient=Patient/MRN12345
Headers: Authorization: Bearer <jwt>

→ Bundle of DocumentReference resources (maps from shared_files table)
```

### Flow 2: EMR System-to-System Full Integration (API Key + FHIR)

```
1. PACS Admin generates API key for EMR service account
   POST /api/api-keys { service_name: "epic-ehr" }
   → { key: "qpk_...", permissions: [...] }
   → Raw key shown once; stored as SHA-256 hash

2. EMR stores key in secure vault

3. Every request uses API key header:
   GET /api/v2/fhir/Patient?identifier=MRN12345
   X-API-Key: qpk_...
   X-Tenant-ID: hospital-a

4. PACS validates key → looks up permissions → routes to tenant DB

5. EMR parses FHIR responses and displays in context
```

### Flow 3: Discover Server Capabilities (CapabilityStatement)

```
GET /api/v2/fhir/metadata
Headers: Authorization: Bearer <jwt> (or X-API-Key)

Response 200 (application/fhir+json):
{
  "resourceType": "CapabilityStatement",
  "status": "active",
  "date": "2026-07-26",
  "publisher": "QuantumPACS",
  "kind": "instance",
  "software": {"name": "QuantumPACS", "version": "3.0.0"},
  "fhirVersion": "4.0.1",
  "format": ["application/fhir+json"],
  "rest": [{
    "mode": "server",
    "resource": [
      {"type": "Patient", "interaction": [{"code": "read"}, {"code": "search-type"}],
       "searchParam": [{"name": "identifier", "type": "token"}, {"name": "name", "type": "string"}, {"name": "birthdate", "type": "date"}]},
      {"type": "ImagingStudy", "interaction": [{"code": "read"}, {"code": "search-type"}],
       "searchParam": [{"name": "patient", "type": "reference"}, {"name": "accession", "type": "token"}, {"name": "modality", "type": "token"}, {"name": "started", "type": "date"}]},
      {"type": "DocumentReference", "interaction": [{"code": "read"}, {"code": "search-type"}],
       "searchParam": [{"name": "patient", "type": "reference"}, {"name": "type", "type": "token"}]}
    ]
  }]
}
```

Note: CapabilityStatement does NOT declare `_lastUpdated`, `_count`, or `_sort` parameters even though the code supports them — an inconsistency between docs and implementation.

### Flow 4: OIDC Discovery (for Human-Facing EMR Workflows)

```
1. EMR user agent redirects to GET /api/oauth/login?idp=msft
2. QuantumPACS redirects to Microsoft Entra ID (or configured IdP)
3. After consent, IdP redirects back to /api/oauth/callback?code=...&state=...
4. QuantumPACS exchanges code for tokens
5. JWT issued for user session
6. User can now access FHIR endpoints with this JWT

OIDC Discovery available at:
  GET /.well-known/openid-configuration

  Returns standard OIDC discovery document with:
  issuer, authorization_endpoint, token_endpoint, jwks_uri,
  response_types_supported, grant_types_supported, scopes_supported,
  code_challenge_methods_supported
```

### Flow 5: FHIR Audit Trail (How PACS Logs EMR Access)

```
Every FHIR request is logged by FhirAuditMiddleware:
- user_id (from JWT or API key identity)
- HTTP method + path + query params
- Resource type + resource ID (if applicable)
- Status code
- Duration in milliseconds
- IP address

Logged to fhir_audit table in tenant database.
```

## Metrics & SLAs

| Metric | Target | Notes |
|--------|--------|-------|
| FHIR endpoint response time | < 500ms (search) | Elasticsearch-backed |
| CapabilityStatement load | < 100ms | Generated dynamically, no DB query |
| Patient read | < 100ms | Direct PK lookup |
| ImagingStudy search (patient) | < 300ms | Subquery on patients table |
| DICOMweb study retrieval | < 2s (100 instances) | WADO-RS multipart response |
| STOW-RS upload throughput | < 500ms per instance | Same pipeline as C-STORE |
| API key validation overhead | < 5ms | Prefix-based lookup + hash comparison |
| Tenant routing overhead | < 10ms | `TenantMiddleware` pool lookup from `dict[slug, asyncpg.Pool]` |
| Availability (FHIR endpoints) | 99.9% | Matches overall PACS SLA |

## Acceptance Criteria

### From U-v3.9 (PRD-v3.md)

1. `GET /api/v2/fhir/ImagingStudy?patient=Patient/{id}` returns FHIR bundle of ImagingStudy resources for the specified patient
2. `GET /api/v2/fhir/ImagingStudy/{id}` returns a single ImagingStudy resource by study UID
3. `GET /api/v2/fhir/Patient/{id}` returns patient demographics in FHIR format
4. All search endpoints support `_lastUpdated`, `_count`, and `_sort` FHIR search parameters
5. All FHIR responses use `application/fhir+json` content type (`FhirJsonResponse` with `media_type = 'application/fhir+json'`)
6. `GET /api/v2/fhir/metadata` returns a CapabilityStatement resource with FHIR version 4.0.1 and supported resource types
7. API Key auth (`X-API-Key` header) works for all FHIR endpoints without JWT exchange
8. Tenant isolation enforced: EMR requests with `X-Tenant-ID` header scope to correct tenant database
9. FHIR audit logging records every FHIR API request (user, method, path, status, duration, IP)

### Derived from Code (Additional)

10. Patient identity mapping: DICOM `PatientID` (0010,0020) maps to FHIR `Patient.identifier.value` with system `http://hl7.org/fhir/v2/0203` and code `MR`
11. Sex mapping: DICOM `M`→FHIR `male`, `F`→`female`, `O`→`other`, empty→`unknown`
12. Name mapping: DICOM `^` delimited `PatientName` → FHIR `name.family` and `name.given` arrays
13. Base URL hardcoded in `fhir.py` as `http://localhost:8080/api/fhir` (must be configurable for production reverse proxies)
14. FHIR responses use `FhirJsonResponse` class; read/Find errors return `OperationOutcome` resource with FHIR-compliant error body
15. HTTP status codes: 200 (success), 201 (created), 204 (deleted), 400, 404, 422
16. The CapabilityStatement does not declare `_lastUpdated`, `_count`, or `_sort` even though the handler supports them — inconsistency with v3 spec

## Implementation Gaps

| Feature | Status | Impact | Target Version |
|---------|--------|--------|---------------|
| OAuth 2.0 Client Credentials grant | NOT IMPLEMENTED | EMR cannot do pure machine-to-machine token exchange via OAuth; must use API keys or user delegation | v3.1 |
| FHIR XML format support | NOT IMPLEMENTED | `_format=xml` and `Accept: application/fhir+xml` not supported; only `application/fhir+json` | v3.1 |
| SMART-on-FHIR frontend launch | NOT IMPLEMENTED | No SMART launch context handling; EMR cannot embed PACS within its UI | v3.2 |
| FHIR audit table | IMPLEMENTED | `fhir_audit` table + middleware exists | — |
| DICOM JSON model responses | IMPLEMENTED | DICOMweb uses `application/dicom+json` per PS3.18 | — |
| Base URL configurability | MISSING | Hardcoded `http://localhost:8080/api/fhir` in `fhir.py`; not configurable for production reverse proxies | v3.1 |
| CapabilityStatement completeness | PARTIAL | Does not declare all supported search params (`_lastUpdated`, `_count`, `_sort`) in metadata output | v3.1 |
| FHIR subscription (push notifications) | NOT IMPLEMENTED | EMR cannot receive real-time study availability notifications; must poll | v3.x |
| Content negotiation for FHIR | MISSING | No `Accept` header variant handling beyond JSON | v3.1 |
| Study-level operations (create/update) | MISSING | FHIR ImagingStudy has `read` and `search-type` only; no create/update/write for ImagingStudy | v3.x (planned) |
| Bundle operations (batch) | NOT IMPLEMENTED | No `$batch` or `$transaction` FHIR bulk operations | v3.x |
| Compartment search optimization | PARTIAL | `_getPatientContext` and compartment search not optimized | v3.x |
| FHIR validation | NOT IMPLEMENTED | No incoming request validation against FHIR R4 schemas | v3.x |
| Patient identity merge/reconcile | MISSING | No FHIR $merge or $reconcile operations for duplicate patients | v3.x |

## Key Files Reference

| File | Purpose |
|------|---------|
| `docs/PRD-v3.md` (§3 FHIR R4, §U-v3.9) | FHIR endpoint requirements, acceptance criteria |
| `docs/decisions/ADR-013-fhir-api-layer.md` | FHIR architecture decision, SMART-on-FHIR pattern |
| `backend/api/fhir_patient.py` | Patient CRUD (FHIR) |
| `backend/api/fhir_imagingstudy.py` | ImagingStudy search/read (FHIR) |
| `backend/api/fhir_documentreference.py` | DocumentReference search/read (FHIR) |
| `backend/api/fhir_metadata.py` | CapabilityStatement endpoint |
| `backend/api/fhir.py` | FHIR response formatting (`FhirJsonResponse`) |
| `backend/api/fhir_audit_middleware.py` | FHIR request audit logging |
| `backend/api/oauth.py` | OAuth/OIDC flow handlers |
| `backend/api/oauth_providers.py` | OAuth provider configuration CRUD |
| `backend/api/api_keys.py` | API key generation and validation |
| `backend/api/auth.py` | Authentication middleware resolution order |
| `backend/api/routes.py` | FHIR and DICOMweb route registration |
| `backend/api/tenant_middleware.py` | Tenant resolution and connection pool routing |
| `backend/api/rbac.py` | `requires_permission()` decorator |
| `backend/api/tokens.py` | JWT creation, verification, blocklist |
| `backend/api/encryption.py` | Fernet AES-256-GCM for OAuth client secrets |
| `backend/db/tenants.py` | Tenant registry and connection pool |
| `frontend/src/dicomweb/StudyBrowser.tsx` | DICOMweb QIDO-RS based study browser (for testing) |