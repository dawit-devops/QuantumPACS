# Acceptance Criteria — Referring Clinician (R14)

**Version**: 1.0.0 (v3.0 scope)
**Status**: Final
**Date**: 2026-08-02

---

## Overview

This document defines the acceptance criteria for the Referring Clinician requirements package (R14). Each criterion is mapped to its originating requirement (FR or NFR) and assigned a validation state. All criteria must pass for the feature to be accepted.

**Validation Methods**: Manual test, automated test (unit/integration/E2E), synthetic probe, audit log review, accessibility audit (axe-core), performance benchmark (k6), code review, design token lint.

---

## Traceability Matrix

| AC ID | Links to | Criteria (Given/When/Then) | Verification Method |
|-------|----------|----------------------------|---------------------|
| AC-R14-01 | FR-R14-01 | Given a valid share link URL, when opened in browser, then study images and report display without login | Manual + E2E |
| AC-R14-02 | FR-R14-01 | Given an expired share link, when opened, then friendly error page with "Request new link" CTA | Manual + E2E |
| AC-R14-03 | FR-R14-01 | Given an invalid share key, when opened, then same error page as expired (no info leakage) | Manual + E2E |
| AC-R14-04 | FR-R14-01 | Given a study with no report, when share link opens, then viewer loads and report panel shows "Report pending" | Manual + E2E |
| AC-R14-05 | FR-R14-01 | Share link page LCP ≤ 2.5s | Lighthouse CI |
| AC-R14-06 | FR-R14-01 | Viewer first image load ≤ 2s | Backend timing |
| AC-R14-07 | FR-R14-01 | Share key is 32-char cryptographically random string | Code review |
| AC-R14-08 | FR-R14-01 | No PHI in share link URL | Security audit |
| AC-R14-09 | FR-R14-02 | Given SSO button clicked, when IdP auth completes, then redirected to study list with referring_physician role | Manual + E2E |
| AC-R14-10 | FR-R14-02 | Given invalid SSO assertion, when login attempted, then "Authentication failed" with retry | Manual + E2E |
| AC-R14-11 | FR-R14-02 | Given SSO identity not provisioned, when login attempted, then "Access not provisioned" message | Manual + E2E |
| AC-R14-12 | FR-R14-02 | Given already logged in, when /login/sso accessed, then redirected to study list | Manual + E2E |
| AC-R14-13 | FR-R14-02 | SSO redirect completes within 3s | Synthetic probe |
| AC-R14-14 | FR-R14-02 | JWT validated against IdP public key; token expiry handled gracefully | Security test |
| AC-R14-15 | FR-R14-03 | Given study detail page, when viewer loads, then first series displayed with scroll/WW/WL/zoom/pan | Manual + E2E |
| AC-R14-16 | FR-R14-03 | Given viewer loaded, when annotation/measure attempted, then no tools available and "View Only" badge shown | Manual + E2E |
| AC-R14-17 | FR-R14-03 | Given series thumbnails, when series clicked, then viewer loads that series within 2s | Manual + E2E |
| AC-R14-18 | FR-R14-03 | Given mobile device, when pinch-zoom used, then image zooms smoothly | Manual + E2E |
| AC-R14-19 | FR-R14-03 | Given mobile device, when swipe used, then image navigates to next/previous slice | Manual + E2E |
| AC-R14-20 | FR-R14-03 | Viewer has ARIA labels on all controls; keyboard shortcuts documented | Manual + axe-core |
| AC-R14-21 | FR-R14-03 | Viewer first image load ≤ 2s | Backend timing |
| AC-R14-22 | FR-R14-04 | Given completed study, when report panel renders, then structured report and narrative displayed | Manual + E2E |
| AC-R14-23 | FR-R14-04 | Given critical findings, when report renders, then prominent alert banner shown | Manual + E2E |
| AC-R14-24 | FR-R14-04 | Given edit attempted on report, then no edit capability available | Manual + E2E |
| AC-R14-25 | FR-R14-04 | Given report not yet signed, when study viewed, then "Report pending radiologist review" shown | Manual + E2E |
| AC-R14-26 | FR-R14-04 | Report text has contrast ≥ 4.5:1; critical alert uses color + icon | Manual + Coblis |
| AC-R14-27 | FR-R14-04 | Report renders within 1s of study detail page load | Frontend timing |
| AC-R14-28 | FR-R14-05 | Given study list page, when loaded, then table of referred studies with status column | Manual + E2E |
| AC-R14-29 | FR-R14-05 | Given completed study with report, when study list viewed, then status "Available" and row clickable | Manual + E2E |
| AC-R14-30 | FR-R14-05 | Given status filter applied, when selected, then table shows only matching studies | Manual + E2E |
| AC-R14-31 | FR-R14-05 | Given date sort clicked, when header clicked, then table sorts by date newest first | Manual + E2E |
| AC-R14-32 | FR-R14-05 | Given no referred studies, when study list viewed, then empty state with "No referred studies found" | Manual + E2E |
| AC-R14-33 | FR-R14-05 | Table has `<th scope="col">`; rows keyboard-navigable; status badges have ARIA labels | Manual + axe-core |
| AC-R14-34 | FR-R14-05 | Study list loads within 2s; pagination (25/page) works without full reload | Manual + E2E |
| AC-R14-35 | FR-R14-06 | Given report signed for referred study, when notification generated, then email + in-app notification sent | Manual + E2E |
| AC-R14-36 | FR-R14-06 | Given unread notifications, when bell icon viewed, then badge count reflects unread count | Manual + E2E |
| AC-R14-37 | FR-R14-06 | Given notification clicked, when opened, then study viewer and report displayed | Manual + E2E |
| AC-R14-38 | FR-R14-06 | Given notification marked as read, when clicked, then badge count decrements | Manual + E2E |
| AC-R14-39 | FR-R14-06 | Notification report summary truncated to 200 chars with "View full report" link | Manual + E2E |
| AC-R14-40 | FR-R14-06 | Notifications announced by screen reader; bell has ARIA label; dropdown keyboard-navigable | Manual + axe-core |
| AC-R14-41 | FR-R14-06 | Notification badge updates within 5s of report sign-off | Synthetic probe |
| AC-R14-42 | FR-R14-07 | Given search field, when text entered, then table filters to matching studies | Manual + E2E |
| AC-R14-43 | FR-R14-07 | Given modality filter, when applied, then table shows only that modality | Manual + E2E |
| AC-R14-44 | FR-R14-07 | Given date range filter, when applied, then table shows only studies in range (capped at 90 days) | Manual + E2E |
| AC-R14-45 | FR-R14-07 | Given multiple filters combined, when applied, then table shows only matching all filters | Manual + E2E |
| AC-R14-46 | FR-R14-07 | Given no matches, when filters applied, then empty state with "No studies match your filters" | Manual + E2E |
| AC-R14-47 | FR-R14-07 | Given date range > 90 days, when applied, then warning shown and range capped at 90 days | Manual + E2E |
| AC-R14-48 | FR-R14-07 | Search field has ARIA label; filter dropdowns have ARIA labels; table has `<th scope="col">` | Manual + axe-core |
| AC-R14-49 | FR-R14-07 | Filtering responds within 500ms; debounced search input (300ms delay) | Manual + E2E |
| AC-R14-50 | FR-R14-08 | Given study opened from list, when detail page loads, then metadata panel left + viewer/report right | Manual + E2E |
| AC-R14-51 | FR-R14-08 | Given metadata panel viewed, then all fields read-only and cannot be edited | Manual + E2E |
| AC-R14-52 | FR-R14-08 | Given study with multiple series, when detail viewed, then series count displayed | Manual + E2E |
| AC-R14-53 | FR-R14-08 | Given study with referring/performing physician, when detail viewed, then both displayed | Manual + E2E |
| AC-R14-54 | FR-R14-08 | Metadata panel uses semantic HTML (`<dl>`, `<dt>`, `<dd>`); fields have ARIA labels | Manual + axe-core |
| AC-R14-55 | FR-R14-08 | Metadata panel renders within 1s of page load | Frontend timing |
| AC-R14-56 | FR-R14-09 | Given "Request Follow-Up" clicked, then follow-up request form displayed | Manual + E2E |
| AC-R14-57 | FR-R14-09 | Given form filled and submitted, then confirmation toast shown and request created | Manual + E2E |
| AC-R14-58 | FR-R14-09 | Given form submitted, when radiologist reviews, then request visible in follow-up queue | Manual + E2E |
| AC-R14-59 | FR-R14-09 | Given radiologist approves, when clinician notified, then "Follow-up approved" with notes | Manual + E2E |
| AC-R14-60 | FR-R14-09 | Given radiologist rejects, when clinician notified, then "Follow-up rejected" with reason and resubmit option | Manual + E2E |
| AC-R14-61 | FR-R14-09 | Form fields have ARIA labels; validation errors announced by screen reader | Manual + axe-core |
| AC-R14-62 | FR-R14-09 | Form submission response within 1s; notification delivery within 5min | Backend timing + synthetic probe |
| AC-R14-63 | FR-R14-10 | Given share links page, when loaded, then list of active share links with study, dates | Manual + E2E |
| AC-R14-64 | FR-R14-10 | Given link expiring within 24h, when list viewed, then "Expiring soon" badge shown | Manual + E2E |
| AC-R14-65 | FR-R14-10 | Given revoke clicked, when confirmed, then link deactivated and inaccessible | Manual + E2E |
| AC-R14-66 | FR-R14-10 | Given revoked link accessed, when opened, then "This link has been revoked" error | Manual + E2E |
| AC-R14-67 | FR-R14-10 | Share link list has ARIA labels; revoke button has confirmation dialog; expiry badges color + text | Manual + axe-core |
| AC-R14-68 | FR-R14-10 | Share link list loads within 2s | Manual + E2E |
| AC-R14-69 | FR-R14-11 | Given critical findings flagged, when study viewed, then prominent alert banner displayed | Manual + E2E |
| AC-R14-70 | FR-R14-11 | Given alert displayed, when "View Details" clicked, then full report with finding highlighted | Manual + E2E |
| AC-R14-71 | FR-R14-11 | Given alert dismissed, when page refreshed, then alert reappears | Manual + E2E |
| AC-R14-72 | FR-R14-11 | Alert uses color + icon (not color alone); has `role="alert"`; screen reader announced; keyboard-dismissable | Manual + axe-core |
| AC-R14-73 | FR-R14-11 | Alert appears within 1s of report load | Frontend timing |
| AC-R14-74 | NFR-R14-01 | Share link page LCP ≤ 2.5s | Lighthouse CI |
| AC-R14-75 | NFR-R14-02 | Viewer first image load ≤ 2s | Backend timing |
| AC-R14-76 | NFR-R14-03 | Share link default expiry 7 days; configurable by R08/R12 | Config review |
| AC-R14-77 | NFR-R14-04 | Share key is 32-char cryptographically random string | Code review |
| AC-R14-78 | NFR-R14-05 | SSO redirect completes within 3s | Synthetic probe |
| AC-R14-79 | NFR-R14-06 | Mobile viewport supported at 320px and 768px | Manual + E2E |
| AC-R14-80 | NFR-R14-07 | WCAG 2.2 AA passes (0 axe-core violations) | axe-core CI |
| AC-R14-81 | NFR-R14-08 | Semantic tokens used; no one-off colors | Stylelint custom rule |
| AC-R14-82 | NFR-R14-09 | PHI never in URL query params | Security audit |
| AC-R14-83 | NFR-R14-10 | All share link accesses logged in audit table | Audit log review |
| AC-R14-84 | NFR-R14-11 | Rate limiting applied to share endpoints (100 req/min per key) | k6 load test |
| AC-R14-85 | NFR-R14-12 | Share endpoints support ≥ 50 concurrent viewers | k6 load test |
| AC-R14-86 | NFR-R14-13 | Mobile viewport supported at 320px, 768px breakpoints | Manual + E2E |
| AC-R14-87 | NFR-R14-14 | Mobile viewer touch gestures work (pinch-zoom, swipe) | Manual + E2E |
| AC-R14-88 | NFR-R14-01 | SSO login LCP ≤ 2.5s | Lighthouse CI |
| AC-R14-89 | NFR-R14-02 | SSO assertion validation ≤ 500ms | Backend timing |
| AC-R14-90 | NFR-R14-07 | SSO login page has ARIA labels; keyboard-operable | Manual + axe-core |
| AC-R14-91 | NFR-R14-08 | SSO login page uses semantic tokens; no one-off colors | Stylelint custom rule |
| AC-R14-92 | NFR-R14-09 | No PHI in SSO redirect URLs | Security audit |
| AC-R14-93 | NFR-R14-10 | SSO login events logged in audit table | Audit log review |
| AC-R14-94 | NFR-R14-11 | SSO endpoint rate limited (100 req/min per IP) | k6 load test |
| AC-R14-95 | NFR-R14-12 | SSO supports ≥ 50 concurrent logins | k6 load test |
| AC-R14-96 | NFR-R14-01 | Study list LCP ≤ 2s | Lighthouse CI |
| AC-R14-97 | NFR-R14-02 | Study list query p95 ≤ 200ms | Backend timing |
| AC-R14-98 | NFR-R14-07 | Study list has ARIA labels; table has `<th scope="col">`; rows keyboard-navigable | Manual + axe-core |
| AC-R14-99 | NFR-R14-08 | Study list uses semantic tokens; no one-off colors | Stylelint custom rule |
| AC-R14-100 | NFR-R14-09 | No PHI in study list URLs or query params | Security audit |
| AC-R14-101 | NFR-R14-10 | Study list access events logged in audit table | Audit log review |
| AC-R14-102 | NFR-R14-11 | Study list rate limited (100 req/min per user) | k6 load test |
| AC-R14-103 | NFR-R14-12 | Study list supports ≥ 50 concurrent viewers | k6 load test |
| AC-R14-104 | NFR-R14-01 | Study detail LCP ≤ 2.5s | Lighthouse CI |
| AC-R14-105 | NFR-R14-02 | Report panel render ≤ 1s | Frontend timing |
| AC-R14-106 | NFR-R14-07 | Study detail has ARIA labels; metadata uses `<dl>`/`<dt>`/`<dd>`; viewer has ARIA labels | Manual + axe-core |
| AC-R14-107 | NFR-R14-08 | Study detail uses semantic tokens; no one-off colors | Stylelint custom rule |
| AC-R14-108 | NFR-R14-09 | No PHI in study detail URLs | Security audit |
| AC-R14-109 | NFR-R14-10 | Study detail access events logged in audit table | Audit log review |
| AC-R14-110 | NFR-R14-11 | Study detail rate limited (100 req/min per user) | k6 load test |
| AC-R14-111 | NFR-R14-12 | Study detail supports ≥ 50 concurrent viewers | k6 load test |
| AC-R14-112 | NFR-R14-07 | Follow-up form has ARIA labels; validation errors announced by screen reader | Manual + axe-core |
| AC-R14-113 | NFR-R14-08 | Follow-up form uses semantic tokens; no one-off colors | Stylelint custom rule |
| AC-R14-114 | NFR-R14-09 | No PHI in follow-up form URLs | Security audit |
| AC-R14-115 | NFR-R14-10 | Follow-up request creation events logged in audit table | Audit log review |
| AC-R14-116 | NFR-R14-11 | Follow-up endpoint rate limited (100 req/min per user) | k6 load test |
| AC-R14-117 | NFR-R14-12 | Follow-up endpoints support ≥ 50 concurrent requests | k6 load test |
| AC-R14-118 | NFR-R14-07 | Share links management has ARIA labels; revoke button has confirmation dialog | Manual + axe-core |
| AC-R14-119 | NFR-R14-08 | Share links management uses semantic tokens; no one-off colors | Stylelint custom rule |
| AC-R14-120 | NFR-R14-09 | No PHI in share links management URLs | Security audit |
| AC-R14-121 | NFR-R14-10 | Share link management events logged in audit table | Audit log review |
| AC-R14-122 | NFR-R14-11 | Share link management rate limited (100 req/min per user) | k6 load test |
| AC-R14-123 | NFR-R14-12 | Share link management supports ≥ 50 concurrent viewers | k6 load test |
| AC-R14-124 | NFR-R14-07 | Notifications page has ARIA labels; bell has ARIA label; dropdown keyboard-navigable | Manual + axe-core |
| AC-R14-125 | NFR-R14-08 | Notifications page uses semantic tokens; no one-off colors | Stylelint custom rule |
| AC-R14-126 | NFR-R14-09 | No PHI in notification URLs or payload | Security audit |
| AC-R14-127 | NFR-R14-10 | Notification access events logged in audit table | Audit log review |
| AC-R14-128 | NFR-R14-11 | Notification endpoint rate limited (100 req/min per user) | k6 load test |
| AC-R14-129 | NFR-R14-12 | Notifications support ≥ 50 concurrent viewers | k6 load test |
| AC-R14-130 | NFR-R14-01 | All R14 pages LCP ≤ 2.5s | Lighthouse CI |
| AC-R14-131 | NFR-R14-07 | All R14 pages pass axe-core (0 violations) | axe-core CI |
| AC-R14-132 | NFR-R14-08 | All R14 pages use semantic tokens; no one-off colors | Stylelint custom rule |
| AC-R14-133 | NFR-R14-09 | No PHI in any R14 URL | Security audit |
| AC-R14-134 | NFR-R14-10 | All R14 access events logged in audit table | Audit log review |
| AC-R14-135 | NFR-R14-11 | All R14 endpoints rate limited | k6 load test |
| AC-R14-136 | NFR-R14-12 | All R14 endpoints support ≥ 50 concurrent viewers | k6 load test |
| AC-R14-137 | NFR-R14-01 | All R14 endpoints tested with 401/403/422/500 | Security test |
| AC-R14-138 | NFR-R14-10 | Input validation on all user-provided fields | Security test |
| AC-R14-139 | NFR-R14-10 | SQL injection prevention (parameterized queries) | Security test |
| AC-R14-140 | NFR-R14-10 | XSS prevention (React auto-escaping + sanitization) | Security test |
| AC-R14-141 | NFR-R14-10 | CSRF protection (SameSite cookies + CSRF token) | Security test |
| AC-R14-142 | NFR-R14-10 | Sensitive data not logged (PII redaction) | Log review |
| AC-R14-143 | NFR-R14-10 | Error responses do not leak stack traces | Security test |
| AC-R14-144 | NFR-R14-10 | Dependency vulnerability scan passes | CI gate |
| AC-R14-145 | NFR-R14-10 | No known CVEs in critical dependencies | Dependency scan |
| AC-R14-146 | NFR-R14-10 | Error messages user-friendly (no stack traces) | Manual + E2E |
| AC-R14-147 | NFR-R14-10 | Error messages actionable (suggest fix) | Manual + E2E |
| AC-R14-148 | NFR-R14-10 | Network error handling (offline detection + retry) | Manual + E2E |
| AC-R14-149 | NFR-R14-10 | Retry with exponential backoff (max 3 attempts) | Manual + E2E |
| AC-R14-150 | NFR-R14-05 | Database migration applied cleanly | Alembic dry-run + test DB |
| AC-R14-151 | NFR-R14-05 | Migration rollback works | Alembic downgrade test |
| AC-R14-152 | NFR-R14-05 | DB constraints enforced (NOT NULL, FK, CHECK) | DB constraint review |
| AC-R14-153 | NFR-R14-05 | DB indexes on all query columns | DB index review |
| AC-R14-154 | NFR-R14-05 | DB connection pool sized for ≥ 50 concurrent share viewers | Config review |
| AC-R14-155 | NFR-R14-07 | JWT token validation on all R14 endpoints | Security test |
| AC-R14-156 | NFR-R14-07 | Token expiry handled gracefully (401 → redirect to login) | Manual + E2E |
| AC-R14-157 | NFR-R14-07 | Refresh token rotation implemented | Security test |
| AC-R14-158 | NFR-R14-07 | Session management (no session fixation) | Security test |
| AC-R14-159 | NFR-R14-07 | CORS configured for referring clinician origins | Config review |
| AC-R14-160 | NFR-R14-07 | Security headers present (CSP, HSTS, X-Frame-Options) | Security test |
| AC-R14-161 | NFR-R14-08 | API documentation (OpenAPI spec) for all R14 endpoints | Docs review |
| AC-R14-162 | NFR-R14-08 | API docs include request/response examples | Docs review |
| AC-R14-163 | NFR-R14-08 | API docs include error codes and descriptions | Docs review |
| AC-R14-164 | NFR-R14-08 | Frontend code documented (JSDoc on public functions) | Docs review |
| AC-R14-165 | NFR-R14-08 | Component props documented (TypeScript interfaces) | Docs review |
| AC-R14-166 | NFR-R14-08 | README updated with R14 setup instructions | Docs review |
| AC-R14-167 | NFR-R14-09 | Deployment follows existing CI/CD pipeline | Config review |
| AC-R14-168 | NFR-R14-09 | No breaking changes to existing API endpoints | Integration test |
| AC-R14-169 | NFR-R14-09 | Backward compatible with existing share link data | Migration test |
| AC-R14-170 | NFR-R14-09 | Rollback plan documented | Docs review |

---

## Out of Scope (v3.0)

| Item | Reason | Target Version |
|------|--------|----------------|
| Mobile native app | v3.0 responsive web only; native app deferred | v3.2 |
| Share link password protection | Requires additional auth layer; deferred | v3.1 |
| Multi-study share bundles | Share link creates per-study only; bundle support deferred | v3.1 |
| Follow-up request workflow (R12 integration) | R12 follow-up queue not in v3.0 scope for R14 | v3.1 |
| Critical findings alert UI | R12 critical findings escalation not in v3.0 scope for R14 | v3.1 |
| SSO configuration UI | IdP configuration managed by R01/R02; R14 uses SSO only | N/A |
| Annotation tools for referring clinician | Read-only access; no annotation in v3.0 | N/A |
| Patient-facing portal | R19 hospital staff handles patient-facing access | v3.2 |
| Second opinion request | Requires R12 integration; deferred | v3.2 |
| Custom report viewer | R14 uses standard report display; custom viewer deferred | v3.1 |
| Dose report display | R14 is read-only; dose report is R05/QA concern | N/A |
| Protocol compliance display | R14 does not need protocol compliance metrics | N/A |
| Worklist management | R14 has no worklist management capability | N/A |
| Exam scheduling | R14 cannot schedule exams; R04 handles scheduling | N/A |
| Patient registration | R08 handles patient registration | N/A |
| Billing/insurance | R09 handles billing | N/A |

---

## Acceptance Criteria Validation Checklist

### Pre-Acceptance Gates

- [ ] All AC IDs present in traceability matrix (AC-R14-01 through AC-R14-170)
- [ ] Every FR has at least one AC mapped to it
- [ ] Every NFR has at least one AC mapped to it
- [ ] All AC IDs follow `AC-R14-NNN` format
- [ ] All FR IDs follow `FR-R14-NN` format
- [ ] All NFR IDs follow `NFR-R14-NN` format
- [ ] All ACs have a defined validation method
- [ ] All ACs have a defined owner
- [ ] Out-of-scope items documented with target versions

### Functional Validation

- [ ] Share-link access works without login (AC-R14-01 through AC-R14-08)
- [ ] SSO login works with enterprise identity (AC-R14-09 through AC-R14-14)
- [ ] Read-only viewer renders images with scroll/WW/WL/zoom/pan (AC-R14-15 through AC-R14-21)
- [ ] Report display is read-only with critical findings alert (AC-R14-22 through AC-R14-27)
- [ ] Study list with status tracking works (AC-R14-28 through AC-R14-34)
- [ ] Notifications delivered via email + in-app (AC-R14-35 through AC-R14-41)
- [ ] Search and filter works for referred studies (AC-R14-42 through AC-R14-49)
- [ ] Study detail with metadata displays correctly (AC-R14-50 through AC-R14-55)
- [ ] Follow-up request workflow works (AC-R14-56 through AC-R14-62)
- [ ] Share links management works (AC-R14-63 through AC-R14-68)
- [ ] Critical findings alert works (AC-R14-69 through AC-R14-73)

### Non-Functional Validation

- [ ] WCAG 2.2 AA passes (axe-core) (AC-R14-80, AC-R14-90, AC-R14-98, AC-R14-107, AC-R14-112, AC-R14-118, AC-R14-124, AC-R14-131)
- [ ] Design tokens used (no one-off colors) (AC-R14-81, AC-R14-91, AC-R14-99, AC-R14-107, AC-R14-113, AC-R14-119, AC-R14-125, AC-R14-132)
- [ ] Responsive at breakpoints (AC-R14-79, AC-R14-86, AC-R14-87)
- [ ] No PHI in URLs (AC-R14-82, AC-R14-92, AC-R14-100, AC-R14-108, AC-R14-120, AC-R14-126)
- [ ] Audit logging for all R14 operations (AC-R14-83, AC-R14-93, AC-R14-101, AC-R14-109, AC-R14-115, AC-R14-121, AC-R14-127)
- [ ] Rate limiting on all R14 endpoints (AC-R14-84, AC-R14-94, AC-R14-102, AC-R14-110, AC-R14-116, AC-R14-122, AC-R14-128)
- [ ] Concurrent viewers ≥ 50 (AC-R14-85, AC-R14-95, AC-R14-103, AC-R14-111, AC-R14-117, AC-R14-123, AC-R14-129)
- [ ] Security: SQL injection, XSS, CSRF prevented (AC-R14-139 through AC-R14-143)
- [ ] Error handling: user-friendly messages (AC-R14-146, AC-R14-147, AC-R14-148, AC-R14-149)
- [ ] Retry with exponential backoff (AC-R14-149)
- [ ] Database migration clean (AC-R14-150 through AC-R14-154)
- [ ] Auth: JWT, token expiry, refresh rotation (AC-R14-155 through AC-R14-160)
- [ ] Security headers present (AC-R14-160)
- [ ] API docs complete (AC-R14-161 through AC-R14-166)
- [ ] Deployment non-breaking (AC-R14-167 through AC-R14-170)

### Quality Gate Summary

| Gate | Criteria | Status |
|------|----------|--------|
| **ID Prefixes** | All ACs use `AC-R14-NNN`, FRs use `FR-R14-NN`, NFRs use `NFR-R14-NN` | ☐ |
| **FR-AC Mapping** | Every FR has ≥ 1 AC; every AC maps to exactly 1 FR or NFR | ☐ |
| **4 States** | Study list supports loading/empty/error/success states | ☐ |
| **Design Tokens** | No hardcoded colors; semantic tokens used throughout | ☐ |
| **WCAG AA** | axe-core 0 violations; keyboard accessible; screen reader tested | ☐ |
| **Mermaid Diagrams** | All 5 workflow diagrams (W1-W5) present and renderable | ☐ |
| **HL7/FHIR Mappings** | Inbound + reverse mappings documented; all fields accounted for | ☐ |
| **Metric Targets** | All 35 KPIs have defined targets, measurement methods, and frequencies | ☐ |
| **SLA Tiers** | Availability, support, data freshness, and access SLAs defined | ☐ |
| **E2E Coverage** | All 5 workflows (W1-W5) have Playwright E2E tests | ☐ |
| **Security** | SQL injection, XSS, CSRF, auth, rate limiting all tested | ☐ |
| **Out-of-Scope** | All deferred items documented with target versions | ☐ |