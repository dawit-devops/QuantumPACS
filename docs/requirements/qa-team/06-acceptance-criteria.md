# Acceptance Criteria — Radiology & Imaging Service QI/QA Team (R05)

**Version**: 1.0.0 (v3.0 scope)
**Status**: Final
**Date**: 2026-08-02

---

## Overview

This document defines the acceptance criteria for the QI/QA Team requirements package (R05). Each criterion is mapped to its originating requirement (FR or NFR) and assigned a validation state. All criteria must pass for the feature to be accepted.

**Validation Methods**: Manual test, automated test (unit/integration/E2E), synthetic probe, audit log review, accessibility audit (axe-core), performance benchmark (k6), code review, design token lint.

---

## Traceability Matrix

| AC ID | Maps to | Requirement | Validation Method |
|-------|---------|-------------|-------------------|
| AC-R05-01 | FR-R05-01 | QA queue with filtering | Manual + E2E |
| AC-R05-02 | FR-R05-01 | Priority-based sorting | Manual + E2E |
| AC-R05-03 | FR-R05-01 | Status column display | Manual + E2E |
| AC-R05-04 | FR-R05-01 | Queue auto-refresh ≤ 1min | Synthetic probe |
| AC-R05-05 | FR-R05-01 | Keyboard navigation (Tab/Enter) | Manual + axe-core |
| AC-R05-06 | FR-R05-01 | Screen reader announces queue changes | Screen reader test |
| AC-R05-07 | FR-R05-01 | Focus trap in queue panel | Manual + axe-core |
| AC-R05-08 | FR-R05-01 | Queue data freshness ≤ 5min | Synthetic probe |
| AC-R05-09 | FR-R05-01 | Queue loads within 2s LCP | Lighthouse CI |
| AC-R05-10 | FR-R05-01 | Queue query p95 ≤ 200ms | k6 benchmark |
| AC-R05-11 | FR-R05-02 | Exam detail view (all fields) | Manual + E2E |
| AC-R05-12 | FR-R05-02 | DICOM metadata display | Manual + E2E |
| AC-R05-13 | FR-R05-02 | Protocol selection dropdown | Manual + E2E |
| AC-R05-14 | FR-R05-02 | Protocol CRUD (create/edit/delete) | Manual + E2E |
| AC-R05-15 | FR-R05-02 | Protocol CRUD p95 ≤ 300ms | k6 benchmark |
| AC-R05-16 | FR-R05-02 | Protocol save ≤ 300ms | Backend timing |
| AC-R05-17 | FR-R05-02 | Inline validation on all fields | Manual + E2E |
| AC-R05-18 | FR-R05-02 | Validation latency ≤ 200ms | Frontend timing |
| AC-R05-19 | FR-R05-02 | ACR benchmark field per protocol | Manual + E2E |
| AC-R05-20 | FR-R05-02 | Protocol registry coverage 100% | Audit log review |
| AC-R05-21 | FR-R05-03 | QA score form (all fields) | Manual + E2E |
| AC-R05-22 | FR-R05-03 | Pass/Fail radio group | Manual + E2E |
| AC-R05-23 | FR-R05-03 | Discrepancy level select | Manual + E2E |
| AC-R05-24 | FR-R05-03 | Discrepancy type select | Manual + E2E |
| AC-R05-25 | FR-R05-03 | Findings text area | Manual + E2E |
| AC-R05-26 | FR-R05-03 | Corrective action text area | Manual + E2E |
| AC-R05-27 | FR-R05-03 | Submit button with loading state | Manual + E2E |
| AC-R05-28 | FR-R05-03 | Success notification on submit | Manual + E2E |
| AC-R05-29 | FR-R05-03 | Error notification on failure | Manual + E2E |
| AC-R05-30 | FR-R05-03 | QA score INSERT ≤ 500ms | Backend timing |
| AC-R05-31 | FR-R05-03 | Form completion ≤ 3min (user timing) | Performance.now() |
| AC-R05-32 | FR-R05-03 | Required field validation | Manual + E2E |
| AC-R05-33 | FR-R05-03 | Duplicate submission prevention | Manual + E2E |
| AC-R05-34 | FR-R05-04 | Incident log form (all fields) | Manual + E2E |
| AC-R05-35 | FR-R05-04 | Incident type select (defined types) | Manual + E2E |
| AC-R05-36 | FR-R05-04 | Severity level select | Manual + E2E |
| AC-R05-37 | FR-R05-04 | Repeat study checkbox | Manual + E2E |
| AC-R05-38 | FR-R05-04 | Repeat study UID field (conditional) | Manual + E2E |
| AC-R05-39 | FR-R05-04 | Corrective action required field | Manual + E2E |
| AC-R05-40 | FR-R05-04 | Incident save ≤ 500ms | Backend timing |
| AC-R05-41 | FR-R05-04 | Incident notification ≤ 1min | Synthetic probe |
| AC-R05-42 | FR-R05-04 | Incident notification delivered to all assignees | Manual + E2E |
| AC-R05-43 | FR-R05-04 | Retake study UID validation (format) | Manual + E2E |
| AC-R05-44 | FR-R05-05 | QA dashboard (all widgets) | Manual + E2E |
| AC-R05-45 | FR-R05-05 | Dashboard LCP ≤ 2.5s | Lighthouse CI |
| AC-R05-46 | FR-R05-05 | Dashboard widget freshness ≤ 5min | Synthetic probe |
| AC-R05-47 | FR-R05-05 | Dashboard p95 ≤ 300ms | k6 benchmark |
| AC-R05-48 | FR-R05-05 | Dashboard concurrent reviewers ≥ 10 | k6 load test |
| AC-R05-49 | FR-R05-05 | Dashboard uses semantic tokens (no one-off colors) | Stylelint custom rule |
| AC-R05-50 | FR-R05-05 | Dashboard WCAG AA (0 violations) | axe-core CI |
| AC-R05-51 | FR-R05-05 | Dashboard responsive (mobile/tablet/desktop) | Manual + E2E |
| AC-R05-52 | FR-R05-05 | Dashboard keyboard navigable | Manual + axe-core |
| AC-R05-53 | FR-R05-05 | Dashboard screen reader announces widget updates | Screen reader test |
| AC-R05-54 | FR-R05-05 | Dashboard focus management (no focus trap) | Manual + axe-core |
| AC-R05-55 | FR-R05-06 | Peer review assignment (role-based) | Manual + E2E |
| AC-R05-56 | FR-R05-06 | Peer review assignment ≤ 7 days target | Manual + E2E |
| AC-R05-57 | FR-R05-06 | Peer review status tracking | Manual + E2E |
| AC-R05-58 | FR-R05-06 | Peer review completion notification | Manual + E2E |
| AC-R05-59 | FR-R05-06 | Peer review completion rate ≥ 98% within 7 days | Weekly metric |
| AC-R05-60 | FR-R05-06 | Peer review major discrepancy rate ≤ 2% | Weekly metric |
| AC-R05-61 | FR-R05-06 | Peer review WebSocket real-time updates | E2E + WebSocket test |
| AC-R05-62 | FR-R05-06 | Peer review WebSocket reconnection on disconnect | Manual + E2E |
| AC-R05-63 | FR-R05-06 | Peer review WebSocket message latency ≤ 200ms | k6 WebSocket test |
| AC-R05-64 | FR-R05-06 | Peer review supports ≥ 10 concurrent reviewers | k6 WebSocket test |
| AC-R05-65 | FR-R05-07 | Corrective action tracking (all fields) | Manual + E2E |
| AC-R05-66 | FR-R05-07 | Corrective action assignment (user select) | Manual + E2E |
| AC-R05-67 | FR-R05-07 | Corrective action status (open/in-progress/resolved/closed) | Manual + E2E |
| AC-R05-68 | FR-R05-07 | Corrective action resolution ≤ 7 days target | Manual + E2E |
| AC-R05-69 | FR-R05-07 | Corrective action notification ≤ 1min | Synthetic probe |
| AC-R05-70 | FR-R05-07 | Corrective action notification delivered to assignee | Manual + E2E |
| AC-R05-71 | FR-R05-07 | Corrective action resolution notification to QA Lead | Manual + E2E |
| AC-R05-72 | FR-R05-08 | Audit log (all QA operations) | Audit log review |
| AC-R05-73 | FR-R05-08 | Audit log includes user ID, timestamp, action, target | Audit log review |
| AC-R05-74 | FR-R05-08 | Audit log immutable (no edit/delete) | DB constraint review |
| AC-R05-75 | FR-R05-08 | Audit log queryable by date range and user | Manual + E2E |
| AC-R05-76 | FR-R05-08 | Audit log queryable by action type | Manual + E2E |
| AC-R05-77 | FR-R05-08 | Audit log retention ≥ 6 years | DB retention policy review |
| AC-R05-78 | FR-R05-08 | Audit log access restricted to authorized roles | Permission test |
| AC-R05-79 | FR-R05-08 | Audit log entries created within 1s of operation | Backend timing |
| AC-R05-80 | FR-R05-09 | Role-based access control (4 roles) | Permission test |
| AC-R05-81 | FR-R05-09 | QA Reviewer can view queue, submit scores, log incidents | Permission test |
| AC-R05-82 | FR-R05-09 | QA Lead can assign peer reviews, view all metrics | Permission test |
| AC-R05-83 | FR-R05-09 | R03 Service Director can view compliance reports | Permission test |
| AC-R05-84 | FR-R05-09 | Admin can manage protocols, users, and audit log | Permission test |
| AC-R05-85 | FR-R05-09 | All QA endpoints require authentication (JWT) | Security test |
| AC-R05-86 | FR-R05-09 | Unauthorized access returns 403 | Security test |
| AC-R05-87 | FR-R05-09 | Permission changes take effect immediately | Permission test |
| AC-R05-88 | NFR-R05-01 | WCAG 2.2 AA compliance (0 axe-core violations) | axe-core CI |
| AC-R05-89 | NFR-R05-01 | All interactive elements keyboard accessible | Manual + axe-core |
| AC-R05-90 | NFR-R05-01 | Color contrast ratio ≥ 4.5:1 (WCAG AA) | Manual + Coblis |
| AC-R05-91 | NFR-R05-01 | Focus visible on all interactive elements | Manual + axe-core |
| AC-R05-92 | NFR-R05-01 | ARIA labels on all custom widgets | axe-core |
| AC-R05-93 | NFR-R05-01 | Semantic HTML (no div soup) | axe-core |
| AC-R05-94 | NFR-R05-02 | Semantic tokens used (no hardcoded colors) | Stylelint custom rule |
| AC-R05-95 | NFR-R05-02 | Responsive layout (320px, 768px, 1024px, 1440px) | Manual + E2E |
| AC-R05-96 | NFR-R05-02 | Dark mode support (system preference) | Manual + E2E |
| AC-R05-97 | NFR-R05-02 | Bundle size ≤ 50KB (QA module chunk) | Vite Bundle Analyzer |
| AC-R05-98 | NFR-R05-03 | API rate limiting (100 req/min per user) | k6 load test |
| AC-R05-99 | NFR-R05-03 | Rate limit returns 429 with Retry-After header | k6 load test |
| AC-R05-100 | NFR-R05-03 | SQL injection prevention (parameterized queries) | Security test |
| AC-R05-101 | NFR-R05-03 | XSS prevention (React auto-escaping + sanitization) | Security test |
| AC-R05-102 | NFR-R05-03 | CSRF protection (SameSite cookies + CSRF token) | Security test |
| AC-R05-103 | NFR-R05-03 | Input sanitization on all user-provided fields | Security test |
| AC-R05-104 | NFR-R05-04 | Error messages user-friendly (no stack traces) | Manual + E2E |
| AC-R05-105 | NFR-R05-04 | Error messages actionable (suggest fix) | Manual + E2E |
| AC-R05-106 | NFR-R05-04 | Network error handling (offline detection + retry) | Manual + E2E |
| AC-R05-107 | NFR-R05-04 | Graceful degradation when WebSocket unavailable | Manual + E2E |
| AC-R05-108 | NFR-R05-04 | Retry with exponential backoff (max 3 attempts) | Manual + E2E |
| AC-R05-109 | NFR-R05-05 | Unit test coverage ≥ 80% for QA module | Jest coverage report |
| AC-R05-110 | NFR-R05-05 | Integration test coverage for all API endpoints | Jest + Supertest |
| AC-R05-111 | NFR-R05-05 | E2E test coverage for all user workflows (W1-W5) | Playwright |
| AC-R05-112 | NFR-R05-05 | E2E tests pass on CI | GitHub Actions |
| AC-R05-113 | NFR-R05-05 | Peer review workflow E2E test (keyboard + screen reader) | Playwright |
| AC-R05-114 | NFR-R05-05 | Corrective action workflow E2E test | Playwright |
| AC-R05-115 | NFR-R05-05 | Incident logging E2E test | Playwright |
| AC-R05-116 | NFR-R05-05 | Dashboard widget E2E test (all 4 widgets) | Playwright |
| AC-R05-117 | NFR-R05-05 | Protocol CRUD E2E test | Playwright |
| AC-R05-118 | NFR-R05-05 | QA score submission E2E test | Playwright |
| AC-R05-119 | NFR-R05-05 | Access control E2E test (4 roles) | Playwright |
| AC-R05-120 | NFR-R05-06 | Database migration applied cleanly | Alembic dry-run + test DB |
| AC-R05-121 | NFR-R05-06 | Migration rollback works | Alembic downgrade test |
| AC-R05-122 | NFR-R05-06 | DB constraints enforced (NOT NULL, FK, CHECK) | DB constraint review |
| AC-R05-123 | NFR-R05-06 | DB indexes on all query columns | DB index review |
| AC-R05-124 | NFR-R05-06 | DB connection pool sized for ≥ 10 concurrent reviewers | Config review |
| AC-R05-125 | NFR-R05-07 | JWT token validation on all endpoints | Security test |
| AC-R05-126 | NFR-R05-07 | Token expiry handled gracefully (401 → redirect to login) | Manual + E2E |
| AC-R05-127 | NFR-R05-07 | Refresh token rotation implemented | Security test |
| AC-R05-128 | NFR-R05-07 | Session management (no session fixation) | Security test |
| AC-R05-129 | NFR-R05-07 | CORS configured for QA module origins | Config review |
| AC-R05-130 | NFR-R05-07 | Security headers present (CSP, HSTS, X-Frame-Options) | Security test |
| AC-R05-131 | NFR-R05-08 | API documentation (OpenAPI spec) for all QA endpoints | Docs review |
| AC-R05-132 | NFR-R05-08 | API docs include request/response examples | Docs review |
| AC-R05-133 | NFR-R05-08 | API docs include error codes and descriptions | Docs review |
| AC-R05-134 | NFR-R05-08 | Frontend code documented (JSDoc on public functions) | Docs review |
| AC-R05-135 | NFR-R05-08 | Component props documented (TypeScript interfaces) | Docs review |
| AC-R05-136 | NFR-R05-08 | README updated with QA module setup instructions | Docs review |
| AC-R05-137 | NFR-R05-09 | Deployment follows existing CI/CD pipeline | Config review |
| AC-R05-138 | NFR-R05-09 | No breaking changes to existing API endpoints | Integration test |
| AC-R05-139 | NFR-R05-09 | Backward compatible with existing QA data | Migration test |
| AC-R05-140 | NFR-R05-09 | Rollback plan documented | Docs review |
| AC-R05-141 | NFR-R05-10 | All QA endpoints tested with 401/403/422/500 | Security test |
| AC-R05-142 | NFR-R05-10 | Input validation rejects malformed data | Security test |
| AC-R05-143 | NFR-R05-10 | SQL injection payloads rejected | Security test |
| AC-R05-144 | NFR-R05-10 | XSS payloads sanitized | Security test |
| AC-R05-145 | NFR-R05-10 | CSRF tokens validated on state-changing requests | Security test |
| AC-R05-146 | NFR-R05-10 | Sensitive data not logged (PII redaction) | Log review |
| AC-R05-147 | NFR-R05-10 | Error responses do not leak stack traces | Security test |
| AC-R05-148 | NFR-R05-10 | Rate limiting applied to all public endpoints | k6 load test |
| AC-R05-149 | NFR-R05-10 | Dependency vulnerability scan passes (npm audit / pip-audit) | CI gate |
| AC-R05-150 | NFR-R05-10 | No known CVEs in critical dependencies | Dependency scan |
| AC-R05-151 | FR-R05-11 | ACR phantom QA: schedule phantom scans, auto-analyze against thresholds, flag failures, track compliance | Manual + E2E |
| AC-R05-152 | FR-R05-12 | Regulatory reporting: export compliance reports (MQSA, ACR, state-specific), CSV/PDF/XML formats | Manual + E2E |
| AC-R05-153 | FR-R05-10 | Peer review workflow: QA lead lists radiologists (`GET /qa/reviewers`), assigns a peer review (`POST /peer-reviews`), R12 submits findings (`POST /peer-reviews/{id}/submit`), discrepancy tracked; `qa_team` role has `PEER_REVIEW_READ`/`PEER_REVIEW_WRITE` | Backend test + E2E |

### Implementation Status (verified 2026-08-03)

QA module is implemented end-to-end (backend `api/qa.py` + routes in `routes.py`;
frontend `frontend/src/qa/`). AC-R05-01..71 (queue/review/protocols/scores/
incidents/corrective actions/RBAC) and AC-R05-153 (peer review) are verifiable
today via backend tests + E2E/visual evidence. AC-R05-72..79 (automated dose
validation, FR-R05-08) and AC-R05-80..87 (DICOM tag validation, FR-R05-09) remain
**GATED** — no rules engine or tag parser. AC-R05-151/152 (phantom QA, regulatory
reporting) remain GATED (v3.1).

---

## Out of Scope (v3.0)

| Item | Reason | Target Version |
|------|--------|----------------|
| Configurable threshold alerting | Requires alerting infrastructure not in v3.0 scope | v3.1 |
| AI-assisted QA (FR-R05-13) | Requires AI inference integration; deferred | v3.2+ |
| Protocol versioning/audit trail (FR-R05-02 extended) | Protocol CRUD audit trail deferred to v3.1 | v3.1 |
| Corrective action workflow automation (FR-R05-07 extended) | Auto-escalation and SLA breach automation deferred | v3.1 |
| QA analytics dashboard (FR-R05-05 extended) | Trend analysis and predictive analytics deferred | v3.1 |
| Multi-site QA coordination | Out of scope for single-service deployment | v3.2 |
| HL7 order integration | Out of scope for QA module (handled by R16) | N/A |
| FHIR Patient context integration | Out of scope for QA module (handled by R16) | N/A |
| Equipment status correlation | Out of scope for QA module (handled by R10) | N/A |
| Worklist integration | Out of scope for QA module (handled by R04) | N/A |
| RIS turnaround correlation | Out of scope for QA module (handled by R12) | N/A |
| Automated dose alerting | Out of scope for v3.0 (deferred to v3.1) | v3.1 |
| Protocol ACR benchmark auto-import | Out of scope for v3.0 (manual entry only) | v3.1 |
| QA report PDF export | Out of scope for v3.0 (async job deferred) | v3.1 |
| RBAC for audit log access | Out of scope for v3.0 (admin-only access only) | v3.1 |
| WebSocket load testing at scale (>50 concurrent) | Out of scope for v3.0 (10 concurrent is sufficient) | v3.1 |
| Dark mode theme customization | Out of scope for v3.0 (system preference only) | v3.1 |
| i18n/l10n for QA module | Out of scope for v3.0 (English only) | v3.2 |

---

## Acceptance Criteria Validation Checklist

### Pre-Acceptance Gates

- [ ] All AC IDs present in traceability matrix (AC-R05-01 through AC-R05-152)
- [ ] Every FR has at least one AC mapped to it
- [ ] Every NFR has at least one AC mapped to it
- [ ] All AC IDs follow `AC-R05-NNN` format
- [ ] All FR IDs follow `FR-R05-NN` format
- [ ] All NFR IDs follow `NFR-R05-NN` format
- [ ] All ACs have a defined validation method
- [ ] All ACs have a defined owner
- [ ] Out-of-scope items documented with target version

### Functional Validation

- [ ] QA queue loads and displays all 4 columns (AC-R05-01 through AC-R05-10)
- [ ] Exam detail view shows all metadata (AC-R05-11 through AC-R05-20)
- [ ] QA score form submits successfully (AC-R05-21 through AC-R05-33)
- [ ] Incident log form submits successfully (AC-R05-34 through AC-R05-43)
- [ ] Dashboard renders all 4 widgets (AC-R05-44 through AC-R05-54)
- [ ] Peer review assignment works (AC-R05-55 through AC-R05-64)
- [ ] Corrective action tracking works (AC-R05-65 through AC-R05-71)
- [ ] Audit log records all operations (AC-R05-72 through AC-R05-79)
- [ ] RBAC enforces 4 roles correctly (AC-R05-80 through AC-R05-87)
- [ ] ACR phantom QA scheduling and analysis works (AC-R05-151)
- [ ] Regulatory reporting export works (AC-R05-152)

### Non-Functional Validation

- [ ] WCAG 2.2 AA passes (axe-core) (AC-R05-88 through AC-R05-93)
- [ ] Design tokens used (no one-off colors) (AC-R05-94)
- [ ] Responsive at breakpoints (AC-R05-95)
- [ ] Dark mode works (AC-R05-96)
- [ ] Bundle size within limit (AC-R05-97)
- [ ] Rate limiting works (AC-R05-98 through AC-R05-99)
- [ ] Security: SQL injection, XSS, CSRF prevented (AC-R05-100 through AC-R05-103)
- [ ] Error handling: user-friendly messages (AC-R05-104 through AC-R05-108)
- [ ] Retry with exponential backoff (AC-R05-108)
- [ ] Unit, integration, E2E tests pass (AC-R05-109 through AC-R05-119)
- [ ] Database migration clean (AC-R05-120 through AC-R05-124)
- [ ] Auth: JWT, token expiry, refresh rotation (AC-R05-125 through AC-R05-129)
- [ ] Security headers present (AC-R05-130)
- [ ] API docs complete (AC-R05-131 through AC-R05-136)
- [ ] Deployment non-breaking (AC-R05-137 through AC-R05-140)
- [ ] Security: 401/403/422/500 tested (AC-R05-141 through AC-R05-150)

### Quality Gate Summary

| Gate | Criteria | Status |
|------|----------|--------|
| **ID Prefixes** | All ACs use `AC-R05-NNN`, FRs use `FR-R05-NN`, NFRs use `NFR-R05-NN` | ☐ |
| **FR-AC Mapping** | Every FR has ≥ 1 AC; every AC maps to exactly 1 FR or NFR (FR-R05-11, FR-R05-12 added) | ☐ |
| **4 States** | QA queue supports 4 states (pending/in-review/reviewed/escalated) | ☐ |
| **Design Tokens** | No hardcoded colors; semantic tokens used throughout | ☐ |
| **WCAG AA** | axe-core 0 violations; keyboard accessible; screen reader tested | ☐ |
| **Mermaid Diagrams** | All 5 workflow diagrams (W1-W5) present and renderable | ☐ |
| **HL7/FHIR Mappings** | Inbound + reverse mappings documented; all fields accounted for | ☐ |
| **Metric Targets** | All 28 KPIs have defined targets, measurement methods, and frequencies | ☐ |
| **SLA Tiers** | Availability, support, data freshness, and QA review SLAs defined | ☐ |
| **E2E Coverage** | All 5 workflows (W1-W5) have Playwright E2E tests | ☐ |
| **Security** | SQL injection, XSS, CSRF, auth, rate limiting all tested | ☐ |
| **Out-of-Scope** | All deferred items documented with target versions | ☐ |