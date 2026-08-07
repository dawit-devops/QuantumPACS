# Acceptance Criteria — Super Admin (R01)

Verifiable acceptance criteria mapped to FR/NFR IDs. Every UI outcome is stated in
observable terms per the ui-visual-validator gate (Section 6.4 of the skill): no
criterion is satisfiable by "code exists" alone; each must be provable by automated
test or visual evidence.

## Acceptance Criteria Matrix

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method | Validator Gate |
|-------|----------|----------------------------|---------------------|----------------|
| AC-R01-01 | FR-R01-01, NFR-R01-05 | Given super admin opens Tenants, when a tenant is provisioned successfully, then the tenant appears in the list AND an audit entry `tenant.provisioned` exists with actor/resource/timestamp AND a live alembic-migrated tenant DB + registry admin user (`users.tenant = slug`) exist | API test (POST + audit query) + integration test (tenant lifecycle roundtrip) | Pass — observable via API state + audit row + tenant DB probe |
| AC-R01-02 | FR-R01-01 | Given the provision dialog is open, when I close it before confirming "I saved the password", then the one-time password is not retrievable afterwards (no second display) | Component test + visual check + Playwright (provision → one-time password panel → copy → "I saved it" → panel gone) | Pass — state verified by UI test; visual: panel absent on reopen |
| AC-R01-03 | FR-R01-01 | Given a duplicate slug, when I submit, then an inline error on the slug field appears and the form values are preserved | Component test with mocked 409 | Pass — observable inline field error |
| AC-R01-04 | FR-R01-02, NFR-R01-09 | Given multi-tenant super admin, when I switch tenant via switcher, then all admin lists refetch tenant-scoped data within 1s and header shows the new tenant | E2E (Playwright) with 2 tenants | Pass — measurable: network calls scoped, header text |
| AC-R01-05 | FR-R01-03, FR-R01-19 | Given super admin creates a user, when the API returns success, then the user row appears with assigned role AND audit entry recorded | API + component test | Pass — API state + audit row |
| AC-R01-06 | FR-R01-03, NFR-R01-06 | Given a user is deactivated, when they attempt login, then 401/403 is returned and the attempt is audit-logged | API test | Pass — response code + audit row |
| AC-R01-07 | FR-R01-04 | Given a CSV with mixed valid/invalid rows, when validation completes, then a per-row report shows errors with row numbers and only valid rows import after explicit confirm | Component test (BulkImport) | Pass — report table content asserted |
| AC-R01-08 | FR-R01-05 | Given the permission catalog loads, when a role with SYSTEM_ADMIN is saved, then a privilege-escalation confirmation is required before persistence | Component test | Pass — modal presence + API not called until confirm |
| AC-R01-09 | FR-R01-05 | Given a role has assigned users, when deletion is attempted, then it is blocked and affected users are listed | Component + API test | Pass — blocking state + user list rendered |
| AC-R01-10 | FR-R01-06 | Given a replica is degraded, when the list renders, then status is shown as icon + text (not color alone) and expands to last-sync error | Visual test (axe + screenshot) | Pass — contrast + non-color cue verified visually |
| AC-R01-11 | FR-R01-06, NFR-R01-05 | Given a replica is deleted, when confirmed, then deletion succeeds and is audit-logged | API test | Pass — API state + audit row |
| AC-R01-12 | FR-R01-07 | Given two overlapping routing rules, when the second is saved, then an overlap warning names the existing rule and requires confirmation | Component test | Pass — warning text content asserted |
| AC-R01-13 | FR-R01-07 | Given rules exist, when reordered via drag, then priority order is persisted and applied | E2E (Playwright) | Pass — persisted order observable in list |
| AC-R01-14 | FR-R01-08 | Given a service key is created, when the secret is returned, then it is shown exactly once with copy + "I saved the secret" confirmation | Component test + visual | Pass — copy button present; secret not in DOM after confirm |
| AC-R01-15 | FR-R01-08, NFR-R01-06 | Given a key is revoked, when confirmed, then the confirmation names the key label and the action is audit-logged (`api_key.revoked`) | Component + API test | Pass — dialog text + audit row |
| AC-R01-16 | FR-R01-10, NFR-R01-03 | Given the Logs screen loads with 1M seeded rows, when filtered by event type + date, then first page renders ≤ 2s p90 | Synthetic probe | Pass — measurable timing |
| AC-R01-17 | FR-R01-10 | Given a log row is expanded, then details render as pretty-printed JSON with copy button | Component test + visual | Pass — JSON pre block + copy control |
| AC-R01-18 | FR-R01-10 | Given a broad query times out, when the request fails, then a "narrow your date range" prompt is shown instead of an indefinite spinner | Component test (mocked timeout) | Pass — observable prompt state |
| AC-R01-19 | FR-R01-11 | Given Metrics loads, when one area endpoint is down, then that panel shows "metrics unavailable" with retry while other panels render | E2E with mocked failure | Pass — panel isolation observable |
| AC-R01-20 | FR-R01-11 | Given a threshold is breached, when the dashboard renders, then the flag includes icon + text (not color alone) and charts expose an accessible data table | axe + visual screenshot | Pass — color-blind-safe verified |
| AC-R01-21 | FR-R01-13 | Given the FHIR integration test runs, when it completes, then structured results (status, latency, request/response) are displayed ≤ 5s | Component + API probe | Pass — structured output asserted |
| AC-R01-22 | FR-R01-13 | Given an OAuth client secret is issued, when the dialog closes, then the secret is never re-displayed | Component test + visual | Pass — no secret in DOM/API after close |
| AC-R01-23 | FR-R01-14 | Given the HL7 listener is down, when status is polled, then "not listening" state with retry and a notification are shown | E2E with mocked status | Pass — status text + notification event |
| AC-R01-24 | FR-R01-14 | Given a message failed parsing, when opened, then parse errors are highlighted per HL7 segment alongside raw payload | Component test + visual | Pass — segment-level error markers |
| AC-R01-25 | FR-R01-15 | Given a provider is disabled with existing users, when confirmed, then a login-impact warning is shown before disabling | Component test | Pass — warning text asserted |
| AC-R01-26 | FR-R01-15, NFR-R01-06 | Given provider secrets are stored, then they are encrypted at rest and never appear in API responses after creation | API + encryption test | Pass — encrypted blob verified |
| AC-R01-27 | FR-R01-16 | Given a replica failure occurs, when detected, then a notification is created and the unread badge updates ≤ 5s | Synthetic event probe | Pass — measurable event latency |
| AC-R01-28 | FR-R01-19, NFR-R01-05 | Given any admin mutation succeeds, then an audit entry exists with actor, action, resource, timestamp, request_id, tenant | Audit coverage test across all mutating endpoints | Pass — 100% coverage asserted |
| AC-R01-29 | FR-R01-20 | Given a non-admin actor hits any admin endpoint, then 403 is returned | API test matrix (all admin endpoints × non-admin role) | Pass — status code matrix |
| AC-R01-30 | NFR-R01-01 | Given the admin console loads on desktop 4G, then LCP ≤ 2.5s p75 | Lighthouse CI | Pass — measured budget |
| AC-R01-31 | NFR-R01-02 | Given an admin list interaction, then INP ≤ 200ms p75 | RUM / Lighthouse | Pass — measured budget |
| AC-R01-32 | NFR-R01-07/08 | Given any admin screen, then it passes axe-core with zero serious violations and is keyboard-operable end-to-end | axe-core + manual keyboard pass | Pass — no violations, tab order verified |
| AC-R01-33 | NFR-R01-11 | Given Elasticsearch is down, then admin search degrades gracefully and admin CRUD functions remain usable | Failure-injection E2E | Pass — search degraded state + CRUD working |
| AC-R01-34 | NFR-R01-13 | Given admin inactivity, when the idle timeout (30 min) is reached, then the session expires and re-auth is required | Config/integration test | Pass — re-auth prompt observed |
| AC-R01-35 | FR-R01-09 | Given a webhook exists, when "Test delivery" runs, then a structured result (HTTP status, latency, response body) is shown ≤ 5s | API probe (`POST /webhooks/test`) | Pass — structured result asserted |
| AC-R01-36 | FR-R01-12 | Given the DICOMweb admin screen, when a station AE title is created/edited, then it appears in the station list and is usable by modality worklists | API + component test | Pass — list state + MWL integration probe |
| AC-R01-37 | FR-R01-17 | Given the health dashboard is implemented, when an area is degraded, then it is flagged with icon + text and links to the area dashboard with matching time scope | API test (component keys/status) + component test (link rendering, per-panel isolation) | Pass — API test (`GET /v2/dashboard/health` component keys/status) + component test (link rendering, per-panel isolation) |
| AC-R01-38 | FR-R01-18 | Given backup exists, when triggered, then a single artifact (DB + files) with timestamp and checksum is produced; restore returns to that state and is audit-logged | E2E (pending implementation — roadmap) | GATED — no implementation exists; backlog |
| AC-R01-39 | NFR-R01-04 | Given a list with >1,000 rows, when it loads, then pagination is server-side with page size 20–100 and the client payload stays bounded | API test (payload size assertion) | Pass — bounded response verified |
| AC-R01-40 | NFR-R01-12 | Given 10 concurrent super-admin sessions, when they perform admin operations simultaneously, then no session errors or data corruption occur | Load test | Pass — concurrent load verified |
| AC-R01-41 | NFR-R01-14 | Given audit retention policy of 1 year, when logs are queried across the retention window, then all entries remain searchable; archive beyond window is configurable | Storage policy test | Pass — retention window verified |

## Excluded Scope / Out of Scope

- **Clinical reading workflow** (R12/R18) — not part of R01 package.
- **Billing/payments** (R09) and scheduling UX (R04) — separate packages.
- **Backup/restore implementation** (US-R01-16) — backlog; AC retained as Could but not gateable today.
- **Mobile experience** for R01 — explicitly not required (desktop-first).

## Validator Gate Verdict (ui-visual-validator lens)

From the verification evidence, I observe:

- **Achieved**: 37 of 41 ACs are verifiable today against the existing API surface
  (`backend/api/routes.py`) and frontend screens (tenants, users, roles, replicas,
  routing, service keys, webhooks, station AEs, logs, metrics, fhir, hl7, oauth,
  notifications, system health). Post-ADR-026, tenant provisioning exercises the
  real DB-per-tenant lifecycle (AC-R01-01) and the tenant switcher routes requests
  end-to-end via JWT claim / `X-Tenant-ID` (AC-R01-04).
- **Partially achieved**: AC-R01-14/22 (secret one-time display) are specified but
  require frontend implementation to confirm; the API already returns secrets once.
  AC-R01-02 (tenant one-time password panel) is now E2E-covered via Playwright.
- **Not achieved (gated)**: AC-R01-38 (backup/restore — no implementation exists).
  This remains a flagged gap.
- **Risk noted**: notification-creation rules for admin events (US-R01-14) depend on
  backend event wiring that must be confirmed before sprint commitment.

Verdict: package **approved for sprint planning** with the remaining gated item
(backup/restore) tracked as a backend dependency.
