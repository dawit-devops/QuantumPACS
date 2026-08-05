# Backend Requirements: R19 Other Hospital Staff

## Context

Other hospital staff (non-radiology nurses, lab, pharmacy, and similar) need a
**limited, read-only** view of imaging and results for their own patients. No
annotation, share creation, download, or report editing. Access must be scoped to
legitimate patients (ward/care-team linkage), never global, and every access is
audited. A mobile-responsive portal is the target surface.

**Screens (existing)**: the shared Files study browser + patient page + viewer in
read-only mode, and the share-link viewer (`/view/:key`) — but these are not
scoped to a "care team" model. See `existing-screens/`, `viewer/`,
`patient-page/`, `share/`, `notifications/`.

**Screens (new/planned — GATED on a portal backend)**: Scoped Patient Lookup,
Read-Only Study & Report View, Order Awareness, Results Notification, Read-Only
Viewer, Follow-Up Request.

**Personas**: P12 (Other Hospital Staff). **Access tier**: read-only,
scoped (`PATIENT_READ` + care-team scope; proposed `PORTAL_*`).

## Screens/Components

### Scoped Patient Lookup

**Purpose**: Find patients the staff member has a legitimate need to view.

**Data I need**: patient list scoped by ward/care-team linkage (MRN/name search),
never a global directory.

**Actions**: search within scope (≤500ms p95).

**States to handle**: empty ("no accessible patients"), loading, error.

**Business rules affecting UI**: access scoping is the core differentiator from
the full Files browser — needs a backend care-team scope model (**GATED**).

### Read-Only Study & Report View / Viewer

**Purpose**: View imaging and finalized reports for permitted patients.

**Data I need**: study list, finalized reports, read-only images via the viewer.

**Actions**: open study, view images (read-only), view finalized report.

**States to handle**: read-only mode; 403-style "not permitted" on anything
outside scope.

**Business rules affecting UI**: **read-only enforcement** — 0 mutations possible
via UI or API (FR-R19-06); annotations, edits, shares, and downloads disabled;
share-link viewer mode is the closest existing pattern but is unscoped.

### Order Awareness / Results Notification / Follow-Up

**Purpose**: Track order status and be notified of results.

**Data I need**: order status (scheduled / in-progress / complete) for permitted
patients; in-app (and optional email) notification when a report finalizes;
follow-up request primitive.

**Actions**: view order status, receive notifications, request follow-up/stat read.

**Business rules affecting UI**: notifications must not leak PHI in their bodies
(FR-R19-04); notification routing to external/hospital-staff users is **GATED**
(the bell serves authenticated internal users today).

## Uncertainties

- [ ] **Limited-scope portal is GATED** — no care-team scope model, no portal
  shell, no order-status or results-notification endpoints. Must be raised with
  backend.
- [ ] How is "permitted patients" computed (ward linkage, care-team assignment,
  ordering physician)? No model exists today.
- [ ] Results notification to hospital staff — in-app only or email, and what is
  the PHI-safe body format?
- [ ] Does read-only enforcement require a dedicated portal shell, or can the
  existing viewer/sidebar be permission-gated (RequirePermission + hidden menu)?

## Questions for Backend

- What is the roadmap for a care-team scope model + limited portal?
- Is order status derivable from the worklist (`/worklist*`) or does it need a
  separate visit/order model (shared with R08)?
- Should the portal reuse the share-link viewer pattern with a scoped auth, or
  be a fully authenticated permission-gated surface?

## Discussion Log

_(pending backend review)_
