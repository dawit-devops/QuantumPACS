# Backend Requirements: R14 Referring Clinician

## Context

The Referring Clinician is an external physician who orders imaging and reviews
results. In v3 they access studies **via share links — no login required**
(optional SSO). Strictly **read-only**: no annotation, no share creation, no
report editing. The existing anonymous share-view mode in the frontend is the
surface for this role.

**Screens (existing)**: Share-view (read-only viewer mode of the Detail page —
Image tab only, no other tabs, no download, no sidebar).

**Personas**: P3 (Clinician). **Access tier**: read-only via share key.

## Screens/Components

### Read-only Study Viewer (share link)

**Purpose**: View a shared study and its report without logging in.

**Data I need to display**:
- The study images in a read-only viewer (no measurement/annotation tools).
- The radiologist's report once it exists (report display via share is the
  intended flow — depends on R12 reporting being built).
- Clear expiry indication if the link has expired.

**Actions**: open the link, view images, view report, (optionally) download —
**download is currently disabled** for share mode per the viewer rules; confirm
intent.

**States to handle**:
- **Valid link**: viewer renders, read-only.
- **Expired link**: clear message ("This link has expired"), no viewer.
- **Invalid/revoked link**: treated as expired.
- **Link valid but study unavailable**: error state.

**Business rules affecting UI**:
- Share-key mode hides Share/Changes/Admin tabs and disables annotations.
- The key is a 64-char hex; expiry is set at creation (1–8760 h).
- Optional SSO (Azure AD/Okta) is a v3 possibility — the same read-only surface
  with an authenticated identity.

## Uncertainties
- [ ] Report delivery: can the share view render the report once R12 reporting
  exists? Contract needed.
- [ ] Should share links support password protection in addition to expiry?
  (v3.1 open question.)
- [ ] Multi-study bundles (one link → several studies) is a v3.1 open question.
- [ ] Second-opinion request from the referring clinician is a v3.2 idea.
- [ ] Is share-link access itself audited (who/IP/when) for HIPAA?

## Questions for Backend
- Does the share-key viewer currently return the full study hierarchy needed for
  the read-only breadcrumb, or a reduced view?
- Should expired vs. revoked links be distinguishable in the UI, or is one
  "expired" message enough?
- When SSO is enabled for a clinician, does the same share view render with the
  user's identity, or is it a separate path?

## Discussion Log

_(pending backend review)_
