# QuantumPACS API Contract

Contract for frontend consumers (and external integrators) of the QuantumPACS
HTTP + WebSocket API. Source of truth: `backend/api/routes.py` (route table),
`backend/api/response.py` (envelope helpers), `frontend/src/api/client.ts`
(client parsing). The live OpenAPI JSON is served at `/docs/openapi.json` but
only covers a subset of routes — this document covers the full contract.

## 1. Base URL and versioning

- Base path: `/api` (all v2 routes are mounted under `/api` via the `v2()`
  helper; a handful of legacy routes such as `/v2/dashboard/metrics` and
  `/api/v2/wado` also exist).
- Versioning: URL prefix `/api/...`; no Accept-header negotiation. Breaking
  changes require a new prefix, not in-place edits.
- Content type: `application/json` for both directions on JSON routes.
  Binary routes (`/files/{id}/data`, `/files/{id}/thumbnail`, `/wado`)
  return `application/octet-stream` / DICOM types.

## 2. Authentication

- Bearer-style token sent as the **`X-Auth-Pacs`** header (not `Authorization`
  — DICOMweb QIDO/WADO paths use the same header for interoperability).
- Tokens: short-lived JWT access token + refresh token. The refresh token is
  delivered only as an `HttpOnly` cookie scoped to `/api/auth/refresh`; the
  access token lives in `localStorage` for API calls.
- Refresh flow (client): on `401`, if a `tempKey` (shared-study key) is
  present, mark `shareKeyError=expired`; call `POST /auth/refresh` once; on
  success retry the original request with the new token **once**. A second
  `401` (or refresh failure) triggers `unauthorized()` callback or a redirect
  to `/login`.
- All routes require authentication by default, including `/ws_token` and the
  WebSocket handshake (`/ws?token=...`).

## 3. Success envelopes

- Plain helpers return the raw body (`ok()`, `created()`); `204 No Content`
  returns `{}` (`no_content()`).
- Paginated list endpoints use:

```json
{
  "data": [...],
  "meta": { "page": 1, "per_page": 20, "total": 1337, "total_pages": 67 },
  "links": { "self": "...", "first": "...", "last": "...", "prev": "..." , "next": "..." }
}
```

## 4. Error envelope

Two forms are produced by the backend; the client accepts both:

```json
{ "error": "Human readable message" }                    // simple helpers
{ "error": { "code": "AUTH_FAILED", "message": "...", "details": {}, "request_id": "ab12cd34" } }  // api_error()
```

- `api_error()` helpers: `VALIDATION_ERROR` (422, with `details` from the
  validator), `AUTH_FAILED` (401), `PASSWORD_ERROR` (400), `RATE_LIMITED`
  (429), `SSRF_BLOCKED` (400), plus per-domain codes in `users.py`,
  `roles.py`, etc.
- `request_id` is attached only on `status >= 500` (first 8 hex chars of a
  UUID) for correlating with server logs.
- Client behavior (`frontend/src/api/client.ts` `handleResponse`):
  - Parses either envelope form; unknown statuses map to a static table
    (401 → "Session expired — please sign in again", 500 → "Server error", …).
  - `sanitizeMessage()` strips control characters and caps messages at 240
    chars before they reach toast/alert surfaces.
  - Non-JSON or empty error bodies fall back to the status table.
  - `ApiError` instances carry `status`, `code`, `details`, `requestId`;
    components should render `error.message`.
  - Fetch aborts (`AbortError`, `DOMException code 20`) are swallowed by
    `request()` and `useFetch()`.

## 5. Endpoint reference

Grouped by domain. `GET` unless noted. All under `/api` (v2).

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness |
| GET | `/metrics` | Prometheus-style metrics |
| POST | `/login` | Username/password login; sets token cookies |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/logout` | Revoke session |
| POST | `/auth/revoke` | Revoke specific token |
| GET | `/oauth/login`, `/oauth/callback`, `/oauth/token` | OAuth/OIDC |
| GET | `/.well-known/openid-configuration` | OIDC discovery |
| POST | `/change_password` | Password change (rate limited) |
| GET/PUT | `/account/profile` | Profile read/update |
| GET/POST | `/users` | List/create users |
| POST | `/users/deactivate`, `/users/new_password` | User admin actions |
| PUT | `/users/role` | Assign role |
| GET | `/patients/{id}` | Patient record + studies |
| GET/POST | `/files` | Study/file search + upload |
| GET | `/files/upload` (w/ token), `POST /files/upload` | Chunked upload |
| GET | `/files/download_token` | One-time download token |
| GET | `/files/download.zip`, `/files/download.csv` | Bulk export |
| GET/DELETE | `/files/{id}` | File metadata / delete |
| GET | `/files/{id}/changes` | Change history |
| POST | `/files/{id}/share`; GET | `/files/{id}/shares` | Study sharing |
| GET | `/files/{id}/data`, `/files/{id}/thumbnail` | Pixel data |
| GET/POST | `/logs`, `/logs/event-types`, `/logs/actors` | Audit log |
| GET/POST | `/roles`, `/roles/{id}`, `/roles/{id}/users`, `/permissions` | RBAC |
| GET/POST | `/notifications`, `/notifications/unread-count`, `/notifications/read-all`, `/notifications/{id}` | Notifications |
| GET/POST | `/tenants`, `/tenants/{id}`, `/tenants/{id}/stats` | Tenancy |
| GET/POST | `/api-keys`, `/api-keys/{id}` | API keys |
| GET/POST | `/oauth/providers`, `/oauth/providers/{id}` | IdP registry |
| GET | `/dicomweb/studies`, `/dicomweb/studies/{study_uid}` (+`/series`, `/instances` depth) | QIDO-RS |
| GET | `/dicomweb/studies/{uid}/series/{uid}/instances/{uid}`; `/wado` | WADO-RS/URI |
| GET | `/dicomweb/admin`, `/dicomweb/admin/metrics` | DICOMweb admin |
| POST | `/webhooks/test`; GET/POST `/webhooks`, `/webhooks/{id}` | Webhooks |
| GET | `/fhir/metadata` | FHIR capability |
| GET | `/fhir/Patient`, `/fhir/ImagingStudy`, `/fhir/DocumentReference` (+`/{id}`) | FHIR reads/search |
| POST | `/hl7` | MLLP-style HL7 ingest (external) |
| GET | `/hl7/admin/messages` (+`/{id}`), `/hl7/admin/metrics`, `/hl7/admin/config`, `/hl7/admin/status` | HL7 admin |
| GET/POST | `/worklist`, `/worklist/{id}`, `/worklist/station-aes` | MWL |
| GET/POST | `/routing`, `/routing/{id}` | Routing rules |
| GET/PUT | `/fhir/admin/config`, `/fhir/admin/clients` (+`/{id}`), `/fhir/admin/metrics`, `/fhir/admin/requests`, `/fhir/admin/test` | FHIR integration admin |
| GET | `/v2/dashboard/metrics` | Legacy dashboard |
| GET | `/ws_token` | One-time WS token |

## 6. WebSocket protocol

- Handshake: `GET /ws?token=<ws_token>` (`ws`/`wss` per API_URL scheme).
  Token obtained from `GET /ws_token` (authenticated).
- Frames: JSON text frames both directions.
- Client → server: `{ "type": "open", "file": "wadors:..." }`,
  `{ "type": "send_state", ... }` (annotation state sync, `ws/send_state`).
- Server → client: event objects (annotation updates, file index status,
  notifications) dispatched to `onMessage` listeners.
- Reconnect: capped exponential backoff with jitter (1s → 30s max); a single
  in-flight reconnect timer prevents overlapping attempts.

## 7. Frontend standard: typed API modules

Every domain gets a typed module in `frontend/src/api/` that wraps `request()`
from `./client` — never call `request()` directly from components. The
contract for new modules (pattern reference: `src/api/dicomweb-admin.ts`):

```ts
import { request } from "./client";

export interface DicomwebAdminInfo { ... }        // response shape
export const getDicomwebAdmin = (): Promise<DicomwebAdminInfo> =>
  request<DicomwebAdminInfo>("dicomweb/admin");
```

- Naming: `getX`, `listX` (paginated), `createX`, `updateX`, `deleteX`,
  `testX` for probes.
- Query params via the `query` option; JSON bodies via `data`; explicit
  `method` for PUT/DELETE (the client defaults payloads to POST only when no
  method is given).
- Errors propagate as `ApiError` (see §4) — components read
  `error.message`/`error.status`; never stringify the error object.
- Paginated responses are typed against the `{ data, meta, links }` envelope.

## 8. Cross-cutting notes

- File binary routes accept `X-Auth-Pacs` (temp share keys via `tempKey`
  query/localStorage flow); `/files/download_token` issues expiring tokens
  for external fetchers.
- All diagnostic payloads that embed upstream exception text (webhook test,
  FHIR admin reachability, telemetry checks) are truncated to 200 chars server
  side — see `backend/api/webhooks.py`, `fhir_admin.py`, `telemetry.py`.
- Rate limiting: login (`/login`) and `/change_password` return 429
  (`RATE_LIMITED`) after repeated failures; the login screen enforces a
  client-side lockout with backoff.
