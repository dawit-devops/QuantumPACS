# QuantumPACS REST API Design Review

**Date:** 2026-07-23
**Scope:** All endpoints in `backend/api/routes.py`

---

## Findings Summary

| ID | Finding | Severity | Status |
|----|---------|----------|--------|
| R-01 | Custom auth header instead of `Authorization: Bearer` | Low | Open |
| R-02 | `POST /api/files/{id}` for partial updates (should be PATCH) | Medium | Open |
| R-03 | `POST /api/users/deactivate` is RPC-style — should be `DELETE` or `PATCH` | Medium | Open |
| R-04 | `POST /api/users/new_password` is RPC-style — should use sub-resource | Medium | Open |
| R-05 | Download endpoints in resource namespace (`/api/files/download.zip`) | Low | Open |
| R-06 | Search uses both GET and POST inconsistently | Low | Open |
| R-07 | No standard pagination envelope (no `meta`, no `links`) | Low | Open |
| R-08 | No standard error envelope | Low | Open |
| R-09 | Resource IDs in response are flat (no `type` field) | Low | Open |
| R-10 | WebSocket token endpoint is a separate resource | Low | Accept |

---

## Detailed Findings

### R-01: Custom Auth Header (Low)

**Current state:**
```
X-Auth-Pacs: <token>
```

**REST best practice:**
```
Authorization: Bearer <token>
```

**Issue:** The custom header is non-standard. API clients, SDK generators, and API gateways expect `Authorization: Bearer`.

**Recommendation:** Support `Authorization: Bearer` alongside `X-Auth-Pacs` for backward compatibility. Phase out `X-Auth-Pacs` in v3.0 documentation.

---

### R-02: POST for Partial Updates (Medium)

**Current state:**
```
POST /api/files/{id}   → updates tools_state, tag
```

**REST best practice:**
```
PATCH /api/files/{id}  → partial update
```

**Issue:** `POST` is semantically incorrect for partial updates. `POST` should be for creating resources. `PATCH` is the standard method for partial updates.

**Recommendation:** Change to `PATCH /api/files/{id}` (breaking change — document in changelog, support both methods during transition).

---

### R-03: RPC-Style Deactivation Endpoint (Medium)

**Current state:**
```
POST /api/users/deactivate   → body: {id}
```

**REST best practice:**
```
DELETE /api/users/{id}      → removes user
PATCH /api/users/{id}       → {status: "deactivated"}
```

**Issue:** `POST /api/users/deactivate` with `{id}` in the body is RPC-style. It doesn't follow resource-oriented design.

**Recommendation:** Change to either:
- `DELETE /api/users/{id}` (if truly removing the user record)
- `PATCH /api/users/{id}  → {status: "deactivated"}` (if soft-deactivating)

---

### R-04: RPC-Style Password Reset (Medium)

**Current state:**
```
POST /api/users/new_password  → body: {id}
```

**REST best practice:**
```
POST /api/users/{id}/reset-password   → action sub-resource
```

**Issue:** Similar to R-03, this is RPC-style. However, password reset is inherently an action (not CRUD), so a sub-resource action pattern is acceptable.

**Recommendation:** Change to `POST /api/users/{id}/reset-password` for better REST conformance. Keep the existing endpoint as deprecated alias during transition.

---

### R-05: Download Endpoints in Resource Namespace (Low)

**Current state:**
```
GET /api/files/download.zip    → query: ids=1,2,3
GET /api/files/download.csv    → query: ids=1,2,3
GET /api/files/download_token  → no params
```

**REST best practice:** Downloads should use content negotiation:
```
GET /api/files/bulk-download   → Accept: application/zip
GET /api/files/export          → Accept: text/csv
```

**Issue:** The current pattern mixes resource paths with action-style URLs. The `.zip` and `.csv` extensions are unusual for REST APIs.

**Recommendations:**
- `GET /api/files/download.zip` → `GET /api/files/download?format=zip` (or Accept header)
- `GET /api/files/download.csv` → `GET /api/files/download?format=csv`
- `GET /api/files/download_token` → include token in download response instead of separate endpoint

---

### R-06: Inconsistent Search Interface (Low)

**Current state:**
```
GET  /api/files?<url-encoded-JSON>    → search via query string
POST /api/files?<body>                → search via request body
```

**REST best practice:** For complex search with many filters, POST is preferred (URL length limits for GET).

**Issue:** The dual GET/POST interface is confusing. The URL-encoded JSON in query strings is non-standard and opaque.

**Recommendation:** Standardize on POST for search. Remove GET support or keep only for simple query parameters. Document clearly which approach to use.

---

### R-07: No Standard Pagination Envelope (Low)

**Current state:** Response returns `{data: [...], total: N}` — flat, no pagination metadata.

**REST best practice:**
```json
{
  "data": [...],
  "meta": {
    "page": 1,
    "per_page": 10,
    "total": 1234,
    "total_pages": 124
  },
  "links": {
    "self": "/api/files?page=1",
    "next": "/api/files?page=2",
    "prev": null,
    "first": "/api/files?page=1",
    "last": "/api/files?page=124"
  }
}
```

**Recommendation:** Add `meta` and `links` to paginated responses. The current `{data, total}` format is functional but lacks navigation links for clients.

---

### R-08: No Standard Error Envelope (Low)

**Current state:** Errors return `{"error": "message"}` — flat string, no error code, no details array.

**REST best practice:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": [
      {"field": "email", "message": "Invalid email format", "code": "INVALID_FORMAT"}
    ],
    "request_id": "req_abc123"
  }
}
```

**Recommendation:** Add structured error codes, optional details array, and request ID for debugging. Non-breaking — the current format is a subset.

---

### R-09: Flat Resource IDs (Low)

**Current state:** Response includes bare IDs without context:
```json
{"id": 42, "patient_db_id": 10, "study_db_id": 5}
```

**REST best practice:** Use typed IDs or resource references:
```json
{"id": 42, "patient": {"id": 10, "href": "/api/patients/10"}}
```

**Recommendation:** Add `href` links for related resources. Non-breaking addition.

---

### R-10: Separate WebSocket Token Endpoint (Low — Accept)

**Current state:**
```
GET /api/ws_token  → returns short-lived token for WS auth
```

**Issue:** Requires an extra round-trip before WebSocket connection.

**REST best practice:** Could use the main auth token directly for WebSocket auth (as a query param).

**Recommendation:** Accept current design — the 1-minute WS token provides better security (limits exposure if token is logged in URLs). Consider merging into the main auth flow in v3.0.

---

## Endpoint-by-Endpoint Review

| Method | Path | Verdict | Issues |
|--------|------|---------|--------|
| GET | `/api/health` | ✅ OK | Public, no auth needed |
| POST | `/api/login` | ✅ OK | Standard auth pattern |
| POST | `/api/change_password` | ✅ OK | Self-service action |
| GET | `/api/files` | ⚠️ Minor | Inconsistent with POST variant (R-06) |
| POST | `/api/files` | ⚠️ Minor | Search via POST is correct, but dual GET/POST is confusing (R-06) |
| POST | `/api/files/upload` | ✅ OK | File upload |
| GET | `/api/files/{id}` | ✅ OK | Standard resource retrieval |
| POST | `/api/files/{id}` | ⚠️ Should be PATCH (R-02) |
| DELETE | `/api/files/{id}` | ✅ OK | Standard delete |
| GET | `/api/files/{id}/changes` | ✅ OK | Clean sub-resource pattern |
| POST | `/api/files/{id}/share` | ✅ OK | Clean action pattern |
| GET | `/api/files/{id}/data` | ✅ OK | Sub-resource for file data |
| GET | `/api/files/download_token` | ⚠️ Minor | Should be part of download response (R-05) |
| GET | `/api/files/download.zip` | ⚠️ Minor | Non-standard extension in URL (R-05) |
| GET | `/api/files/download.csv` | ⚠️ Minor | Non-standard extension in URL (R-05) |
| GET | `/api/patients/{id}` | ✅ OK | Standard resource retrieval |
| GET | `/api/replicas` | ✅ OK | Standard collection |
| POST | `/api/replicas` | ✅ OK | Standard creation |
| POST | `/api/replicas/{id}` | ⚠️ Minor | Should be PATCH for updates |
| DELETE | `/api/replicas/{id}` | ✅ OK | Standard delete |
| GET | `/api/users` | ✅ OK | Standard collection |
| POST | `/api/users` | ✅ OK | Standard creation |
| POST | `/api/users/deactivate` | ❌ RPC-style (R-03) |
| POST | `/api/users/new_password` | ❌ RPC-style (R-04) |
| GET | `/api/logs` | ✅ OK | Standard collection |
| GET | `/api/ws_token` | ⚠️ Minor | Extra round-trip (R-10) |
| WS | `/api/ws` | ✅ OK | Standard WS path |

---

## Recommendations

### Breaking Changes (v3.0)
1. `POST /api/files/{id}` → `PATCH /api/files/{id}`
2. `POST /api/users/deactivate` → `DELETE /api/users/{id}` or `PATCH /api/users/{id}`
3. `POST /api/users/new_password` → `POST /api/users/{id}/reset-password`
4. `POST /api/replicas/{id}` → `PATCH /api/replicas/{id}`

### Non-Breaking Improvements (v2.1)
5. Add `meta` and `links` to paginated responses
6. Add structured error codes and `request_id` to error responses
7. Add `href` links to related resources
8. Support `Authorization: Bearer` alongside `X-Auth-Pacs`

### Backward-Compatible Deprecation Strategy
- Add new endpoints in v2.1 (non-breaking additions)
- Mark old endpoints as deprecated with `X-API-Deprecated: true` header
- Keep deprecated endpoints for at least 2 minor versions
- Remove deprecated endpoints in v3.0
