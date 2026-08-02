# User Requirements — Other Hospital Staff (R19)

**Version**: 1.0.0 (v3.0 scope)
**Status**: Draft
**Date**: 2026-08-02

## Functional Requirements

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-R19-01 | **Patient Lookup (Scoped)**: Look up patients by MRN/name within a limited scope — only patients for which the staff member has a legitimate need (own ward/patients). | Must | Scope-limited search |
| FR-R19-02 | **Read-Only Study & Report View**: View imaging studies and finalized reports for permitted patients in read-only mode (no edit, no annotation). | Must | Portal (limited scope) |
| FR-R19-03 | **Order Awareness**: See the status of imaging orders (scheduled, in-progress, complete) for permitted patients. | Must | Order status view |
| FR-R19-04 | **Results Notification**: Receive in-app (and optional email) notifications when a permitted patient's report is finalized. | Should | Notification wiring |
| FR-R19-05 | **Image Access (Read-Only Viewer)**: Open read-only images for permitted patients using the existing viewer in a limited mode. | Should | Read-only viewer mode |
| FR-R19-06 | **No Write Access**: All clinical actions (annotations, edits, shares, downloads) are disabled for this role. | Must | Enforcement |
| FR-R19-07 | **Mobile-Responsive Portal**: The portal is usable on tablets and phones for ward rounds and on-call checks. | Must | Mobile-first |
| FR-R19-08 | **PHI Minimum Necessary**: Access scoped to minimum necessary data; no full access to unrelated patients or bulk data. | Must | HIPAA §164.514(d) |
| FR-R19-09 | **Access Audit**: Every patient access is audited (who, what, when) for HIPAA compliance. | Must | Audit log |
| FR-R19-10 | **Follow-Up Request**: Optionally request a follow-up/stat read from the radiology team for a permitted patient. | Could | Request primitive |

## Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-R19-01 | Portal load time (mobile) | LCP ≤ 2.5s on mid-tier phone | Lighthouse CI, RUM |
| NFR-R19-02 | Patient lookup latency | ≤ 500ms p95 | Synthetic probe |
| NFR-R19-03 | Notification latency | ≤ 60s from finalize | Notification probe |
| NFR-R19-04 | WCAG 2.2 AA compliance | 100% (portal) | axe-core CI + manual |
| NFR-R19-05 | PHI exposure scope | Zero unrelated-patient access | Audit scan |
| NFR-R19-06 | Read-only enforcement | 0 mutations possible via UI or API | Pen test + E2E |

## Codebase Status (verified 2026-08-03)

**Implemented**: view own-patient imaging/results via study browser or share link.
**GATED**: limited-scope portal with order awareness + results notification — no
portal routes/endpoints exist; flagged to backend. See artifacts 04/07/08.

## Assumptions & Constraints

- A1: This role covers nurses (non-radiology), lab, pharmacy, and other hospital staff — view-only scope.
- A2: Access is scoped to assigned/legitimate patients (ward/care-team linkage), never global.
- A3: The frontend surface is a limited portal reusing the existing patient/study/result views in read-only mode.
- A4: No annotation, share creation, download, or report editing.
- A5: All access is audited; notifications must not leak PHI in their bodies.
