# ADR-005: REST API Design with Pydantic Validation

## Status
Accepted

## Date
2026-07-22

## Context
The original API handlers parsed request parameters manually with try/except blocks, leading to inconsistent error messages and missing validation for required fields. Different endpoints returned different error shapes. Requirements:

- Consistent response format across all endpoints
- Structured request validation with clear error messages
- Backward-compatible response shapes
- Minimal dependency addition

## Decision
Standardize on a RESTful API design with centralized response helpers and Pydantic v2 for request validation.

Key components:
- `api/response.py`: Standard response factories — `ok()`, `created()`, `no_content()`, `not_found()`, `validation_error()`, `server_error()`, `unauthorized()`, `forbidden()`
- `api/schemas/`: Pydantic v2 models for request bodies (e.g., `LoginRequest`, `CreateStudyRequest`)
- `api/validate.py`: `parse_body(request, model)` helper — decodes JSON, validates against Pydantic model, returns `(data, error_response)` tuple
- Consistent JSON envelope: `{data: ...}` for success, `{error: "..."}` for errors
- HTTP status codes follow REST conventions: 200 success, 201 created, 204 no content, 400 validation, 401 unauthorized, 403 forbidden, 404 not found, 500 server error

## Alternatives Considered

### GraphQL
- Pros: Flexible queries, strong typing
- Cons: Overkill for a DICOM API; most queries are known (search studies, fetch series, download file)
- Rejected: REST is simpler and sufficient for PACS operations

### Full OpenAPI/Swagger
- Pros: Auto-generated docs, client SDKs
- Cons: Requires maintaining OpenAPI spec or using FastAPI; Phase 5 scope didn't include doc generation
- Rejected: Can add later via FastAPI migration or manual OpenAPI spec

## Consequences
- Consistent error handling reduces frontend error-handling code
- Pydantic validation catches malformed requests early with clear messages
- Response helpers ensure uniform envelope — frontend fetchers can rely on shape
- Migrating to FastAPI in the future would be straightforward (same patterns)
