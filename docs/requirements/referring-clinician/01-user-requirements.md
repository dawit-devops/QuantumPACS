# User Requirements — Referring Clinician (R14)

**Version**: 1.0.0 (v3.0 scope)
**Status**: Final
**Date**: 2026-08-02

---

## Role Profile

**Persona**: External physician who orders imaging studies and reviews results for patient care. Non-radiologist; low technical proficiency; occasional per-patient access.
**Context**: Works in a clinic or hospital office; reviews studies referred by their own patients or received via share links; may use SSO or share-key access.
**Top tasks (by frequency)**:
1. Open a shared study link and view images/report (daily)
2. Check study status/results notification (daily)
3. View patient imaging history (weekly)
4. Request follow-up or additional imaging (occasional)
**Pain points**: Multiple PACS logins, proprietary viewers requiring plugins, slow loading on hospital WiFi, no share-link access in v2.
**Devices**: Browser (desktop or mobile); no specialized hardware.
**Working patterns**: Occasional, per-patient referral; low tolerance for complex workflows.
**PHI exposure**: Read-only access to own-patient data; HIPAA minimum necessary applies.

---

## Functional Requirements

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-R14-01 | **Share-link access**: System SHALL allow referring clinicians to view studies via an expiring share link without requiring a login. Share link contains a unique key; accessing `/share/{key}` renders the viewer and report directly. | Must | v3 new capability; replaces v2 "no access" gap |
| FR-R14-02 | **SSO login**: System SHALL support SSO (Azure AD / Okta SAML/OIDC) for referring clinicians who have an enterprise identity. SSO maps to the `referring_physician` role with read-only scope. | Must | v3 enhancement over v2 share-link-only access |
| FR-R14-03 | **Image viewer**: System SHALL render a basic DICOM viewer (scroll, WW/WL, zoom, pan, window preset) for studies accessed via share link or SSO. Viewer SHALL NOT allow annotation, measurement, or save. | Must | Cornerstone3D read-only mode; no annotation plugin |
| FR-R14-04 | **Report retrieval**: System SHALL display the radiology report (structured + narrative) for the study being viewed. Report is read-only; no editing, no signing. | Must | R12 radiologist writes; R14 reads |
| FR-R14-05 | **Study status tracking**: System SHALL show exam status (scheduled/in-progress/completed/available) for studies the referring clinician has ordered or been referred. | Must | Status derived from R06/R07 exam completion events |
| FR-R14-06 | **Results notification**: System SHALL notify the referring clinician (email + in-app) when a study is completed and a report is available. Notification includes study description, modality, and report summary. | Must | Uses existing notification infrastructure |
| FR-R14-07 | **Patient selector**: System SHALL allow the referring clinician to search/filter their referred studies by patient name, MRN, date range, modality, and status. | Must | Search by patient demographics; results paginated (25/page) |
| FR-R14-08 | **Study detail view**: System SHALL display study metadata (patient demographics, modality, protocol, referring physician, performing physician, study date, series count) alongside the viewer and report. | Must | Read-only; no edit capability |
| FR-R14-09 | **Mobile-responsive viewer**: System SHALL render the viewer and report on mobile browsers (320px–768px) with touch gestures (pinch-zoom, swipe-navigate). | Should | v3.1 enhancement if mobile usage data justifies |
| FR-R14-10 | **Follow-up request**: System SHALL allow the referring clinician to request a follow-up study or additional imaging from the reading radiologist via an in-app request form. | Could | Requires R12 radiologist to receive and act on request |
| FR-R14-11 | **Share link management**: System SHALL allow the referring clinician to view their active share links, expiry status, and revoke access. | Could | Share link creation is R08/R12; R14 can only view/revoke |
| FR-R14-12 | **Critical findings alert**: System SHALL display a prominent alert when a study has a critical/urgent finding flagged by the radiologist. | Should | Integrates with R12 critical findings escalation workflow |

## Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-R14-01 | Share link page load (LCP) | ≤ 2.5s | Lighthouse CI |
| NFR-R14-02 | Viewer image load time | ≤ 2s for first series | Backend timing |
| NFR-R14-03 | Share link expiry | Default 7 days, configurable by R08/R12 | `shared_files.expires_at` |
| NFR-R14-04 | Share link uniqueness | Cryptographically random 32-char key | `crypto.randomBytes(32).toString('hex')` |
| NFR-R14-05 | SSO response time | ≤ 3s redirect from IdP | Synthetic probe |
| NFR-R14-06 | Mobile viewport support | 320px, 768px breakpoints | Manual + E2E |
| NFR-R14-07 | WCAG 2.2 AA compliance | 0 axe-core violations | axe-core CI |
| NFR-R14-08 | Design token compliance | 100% (no one-off colors) | Stylelint custom rule |
| NFR-R14-09 | PHI in URLs | PHI never in URL query params | Security audit |
| NFR-R14-10 | Audit logging | All share link accesses logged | DB audit table |
| NFR-R14-11 | Rate limiting | 100 req/min per share key | k6 load test |
| NFR-R14-12 | Concurrent share viewers | ≥ 50 simultaneous | k6 load test |

## Codebase Status (verified 2026-08-03)

**Implemented**: share-link viewer (`/view/:key`, `tempKey` mode — Image tab only,
no sidebar, no mutations), OAuth-provider admin (`/oauth/providers`). **GATED**: order
placement, exam-status tracking, report retrieval (depends on R12 reporting), results
notification, follow-up requests, share self-service — no clinician portal routes
or endpoints exist; flagged to backend. See artifacts 04/07/08.

**Re-verified 2026-08-03 (post-merge 4d136e0)**: `GET /reports/{exam_id}` now exists
behind REPORT_READ (radiologist role only — the `physician` built-in role and
share-link access do not hold it), so report retrieval remains GATED for this role.
In-app notification bell with WS push exists but is not routed to referring
clinicians (and no email service) — results notification remains GATED.

## Assumptions & Constraints

- Share links are the primary access mechanism for external referring clinicians; SSO is optional and configured per tenant by R01/R02.
- PHI is never exposed in URLs, logs, or analytics events. Share keys are the only identifier in URLs.
- The referring clinician role is read-only; no write operations to clinical data (qa_scores, reports, protocols).
- Share links are created by R08 (Front Desk) or R12 (Radiologist) via the existing `ShareFilesHandler`.
- SSO integration uses existing tenant-level IdP configuration (Azure AD / Okta SAML/OIDC).
- Mobile viewer is a responsive adaptation of the desktop viewer; no native mobile app in v3.0.
- The viewer uses Cornerstone3D in read-only mode; no annotation, measurement, or zoom-to-region plugins.
- All share links are single-use or time-limited; no permanent public access.