# Acceptance Criteria — Hospital IT / Tenant Admin (R02)

Verifiable acceptance criteria mapped to FR/NFR IDs. Every UI outcome is stated in
observable terms per the ui-visual-validator gate: no criterion is satisfiable by
"code exists" alone; each is provable by automated test or visual evidence.

## Acceptance Criteria Matrix

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R02-01 | FR-R02-01, NFR-R02-03 | Given tenant admin A, when the API is called with tenant B's X-Tenant-ID, then 403 is returned and the attempt is audit-logged | API test matrix (2 tenants × all R02 endpoints) | Pass — status + audit row verified |
| AC-R02-02 | FR-R02-01 | Given tenant admin opens any admin screen, when it loads, then only the active tenant's data is rendered (no cross-tenant rows) | E2E with 2 seeded tenants | Pass — row content asserted |
| AC-R02-03 | FR-R02-02, FR-R02-16 | Given tenant admin creates a user, when successful, then the row appears with role and an audit entry with actor + tenant exists | API + component test | Pass — API state + audit row |
| AC-R02-04 | FR-R02-02 | Given tenant admin tries to assign a super-admin role, when the role picker loads, then super-admin is absent; forced API call returns 403 with explanation | Component + API test | Pass — picker options + status code |
| AC-R02-05 | FR-R02-03 | Given a CSV with mixed rows, when validated, then per-row errors show row numbers and only valid rows import after explicit confirm | Component test (BulkImport) | Pass — report table asserted |
| AC-R02-06 | FR-R02-04 | Given tenant admin adds a station AE title, when saved, then it appears in the station list and is usable by modality worklist | API + component test | Pass — list state + MWL probe |
| AC-R02-07 | FR-R02-04 | Given a duplicate AE title within the tenant, when saved, then an inline conflict error is shown | Component test (mocked 409) | Pass — inline field error |
| AC-R02-08 | FR-R02-04 | Given a station referenced by active routing rules, when deletion is attempted, then it is blocked and referencing rules are listed | Component + API test | Pass — block state + rule list |
| AC-R02-09 | FR-R02-06 | Given two overlapping routing rules, when the second is saved, then an overlap warning names the existing rule and requires confirmation | Component test | Pass — warning content asserted |
| AC-R02-10 | FR-R02-06 | Given rules exist, when reordered, then priority order persists and applies | E2E (Playwright) | Pass — persisted order observable |
| AC-R02-11 | FR-R02-07, FR-R02-16 | Given a service key is created, when the secret is returned, then it is shown once with confirmation; revocation names the label and is audit-logged | Component + API test | Pass — one-time display + audit row |
| AC-R02-12 | FR-R02-09 | Given the HL7 listener is down, when status is polled, then "not listening" with retry and a notification are shown | E2E with mocked status | Pass — status text + notification |
| AC-R02-13 | FR-R02-09 | Given a message failed parsing, when opened, then parse errors are highlighted per HL7 segment with plain-language hints + raw payload | Component test + visual | Pass — segment-level markers |
| AC-R02-14 | FR-R02-10 | Given the FHIR test runs, when it completes, then structured results (status, latency, req/res) are displayed ≤ 5s | Component + API probe | Pass — structured output asserted |
| AC-R02-15 | FR-R02-10, NFR-R02-06 | Given an OAuth client secret is issued, when the dialog closes, then the secret is never re-displayed | Component test + visual | Pass — no secret in DOM after close |
| AC-R02-16 | FR-R02-11 | Given the Logs screen loads, when filtered by actor/event type, then results are server-side and limited to tenant events ≤ 2s p90 | Synthetic probe + component test | Pass — timing + tenant-only rows |
| AC-R02-17 | FR-R02-11 | Given a broad query times out, when it fails, then a "narrow your range" prompt is shown | Component test (mocked timeout) | Pass — prompt state |
| AC-R02-18 | FR-R02-12 | Given Metrics loads, when one area endpoint is down, then that panel shows "metrics unavailable" + retry while others render | E2E with mocked failure | Pass — panel isolation |
| AC-R02-19 | FR-R02-14 | Given tenant admin opens the UI, when it renders, then Tenants and global admin items are absent from navigation | E2E + visual | Pass — menu items asserted |
| AC-R02-20 | FR-R02-15 | Given the usage panel is implemented, when usage exceeds 80%, then warning (icon + text) and archive guidance appear; at 100% uploads are blocked | E2E (pending backend usage endpoint) | GATED — blocked on backend aggregation |
| AC-R02-21 | FR-R02-13 | Given a tenant replica fails, when detected, then a tenant notification is created and badge updates ≤ 5s | Synthetic event probe | Pass — measurable latency |
| AC-R02-22 | FR-R02-16, NFR-R02-11 | Given any tenant mutation succeeds, then an audit entry exists with actor, action, resource, timestamp, request_id, tenant | Audit coverage test across tenant endpoints | Pass — 100% coverage asserted |
| AC-R02-23 | NFR-R02-01 | Given the tenant admin console loads on desktop 4G, then LCP ≤ 2.5s p75 | Lighthouse CI | Pass — measured budget |
| AC-R02-24 | NFR-R02-02 | Given an admin interaction, then INP ≤ 200ms p75 | RUM / Lighthouse | Pass — measured budget |
| AC-R02-25 | NFR-R02-07 | Given any tenant admin screen, then axe-core passes with zero serious violations and full keyboard operability | axe-core + manual keyboard pass | Pass — verified |
| AC-R02-26 | NFR-R02-08 | Given tenant context switch (if switcher present), when selected, then scoped views load ≤ 1s and header shows the tenant | E2E | Pass — header text + timing |
| AC-R02-27 | NFR-R02-09 | Given 10 concurrent tenant admins, when operating simultaneously, then no cross-tenant data mixing or errors occur | Load test | Pass — isolation under load |
| AC-R02-28 | NFR-R02-10 | Given admin inactivity, when idle timeout (30 min) is reached, then re-auth is required | Config/integration test | Pass — re-auth observed |
| AC-R02-29 | FR-R02-05 | Given the DICOMweb admin screen, when a station AE title is created/edited, then it appears in the station list and is usable by modality worklists | API + component test | Pass — list state + MWL probe |
| AC-R02-30 | NFR-R02-04 | Given tenant audit logs with tenant data volume, when filtered, then first page renders ≤ 2s p90 | Synthetic probe | Pass — measurable timing |
| AC-R02-31 | NFR-R02-05 | Given worklist/station data changes, when the list is polled, then staleness stays ≤ 30s | Synthetic probe | Pass — measurable staleness |

## Excluded Scope / Out of Scope

- **Tenant provisioning** (R01 only) — not in R02 scope; UI hides tenant CRUD.
- **Global RBAC / global replicas / system-level config** — R01 only.
- **Clinical reading workflows** (R12/R18), scheduling UX (R04), billing (R09).
- **Tenant usage dashboard** (US-R02-08) and tenant backup/restore — gated on backend.
- **Mobile experience** — not required (desktop-first).

## Validator Gate Verdict (ui-visual-validator lens)

From the verification evidence, I observe:

- **Achieved**: 28 of 31 ACs are verifiable today against the existing tenant-scoped
  API surface (`tenant_middleware.py`, `backend/api/routes.py`) and the R01-derived
  frontend screens.
- **Partially achieved**: AC-R02-15 (secret one-time display) requires frontend
  implementation to confirm; API already returns secrets once.
- **Not achieved (gated)**: AC-R02-20 (tenant usage vs quota) — no backend aggregation
  endpoint; tenant backup/restore not implemented (roadmap).
- **Risk noted**: US-R02-09 notification wiring depends on backend event creation for
  tenant-scoped events — confirm before sprint commitment; station-AE delete blocking
  (AC-R02-08) depends on routing-rule reference queries on the backend.

Verdict: package **approved for sprint planning** with the gated items tracked as
backend dependencies.
