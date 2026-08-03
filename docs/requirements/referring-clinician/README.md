# R14 — Referring Clinician Requirements Package

| Field | Value |
|-------|-------|
| **Version** | 1.2.1 |
| **Status** | approved |
| **Generated** | 2026-08-03 |
| **Changelog** | [CHANGELOG.md](CHANGELOG.md) |

## Codebase Alignment (verified 2026-08-03; re-verified 2026-08-03 post-merge 4d136e0)

**Presentation layer**: share-link only. See artifact 04 — "Role-Based Routing &
Navigation": the referring clinician accesses `/view/:key` (`tempKey` mode — Image
tab only, no sidebar, no mutations); OAuth/SSO provider admin exists
(`/oauth/providers`) but no clinician SSO portal. `PermissionRoute` now enforces
role-based access at the URL boundary for authenticated routes (share-link access is
independent of it).

**Implemented**: share-link viewer (FR-R14-01/03), OAuth admin scaffolding
(FR-R14-02 partial). **GATED**: report retrieval (FR-R14-04), study status
(FR-R14-05), results notification (FR-R14-06), patient selector (FR-R14-07),
follow-up requests (FR-R14-10), share-link self-service (FR-R14-11) — depends on R12
reporting + notification backend.

**Post-merge re-verification (4d136e0)**: `GET /reports/{exam_id}` now exists but
requires REPORT_READ — held by the `radiologist` built-in role only; the `physician`
built-in role (FILE_READ/PATIENT_READ/STUDY_READ/DICOMWEB_READ) does **not** have it,
and the share-link path does not render reports (`ShareView` has no report tab).
FR-R14-04 therefore remains GATED for the referring clinician. In-app notification
bell with WS push exists, but `report.signed` notifications fan out to the `qa` role
only, with no email service — FR-R14-06 remains GATED.

---

## Role Summary

The Referring Clinician is an external physician who orders imaging studies and reviews results. In v3, this role gains a dedicated access path via share links (no login required) and optional SSO. The referring clinician is read-only — no annotation, no share creation, no report editing.

## Artifact Index

| # | Artifact | File | Description |
|---|----------|------|-------------|
| 01 | User Requirements | `01-user-requirements.md` | Functional + non-functional requirements with IDs |
| 02 | Workflow Maps | `02-workflow-maps.md` | Mermaid sequence diagrams for top tasks |
| 03 | User Stories | `03-user-stories.md` | Given/When/Then stories with AC |
| 04 | UI/UX Requirements | `04-ui-ux-requirements.md` | Screens, components, tokens, a11y, responsive |
| 05 | Metrics & SLAs | `05-metrics-slas.md` | KPIs, SLA tiers, measurement methods |
| 06 | Acceptance Criteria | `06-acceptance-criteria.md` | Validator-gated AC matrix with traceability |
| 07 | Traceability Matrix | `07-traceability.md` | FR/NFR → AC traceability, cross-artifact dependencies, cross-role dependencies |
| 08 | Implementation Roadmap | `08-implementation-roadmap.md` | Dependency-ordered plan with status (done/partial/missing) per artifact |

## Cross-Role Dependencies

| Dependency | Role | Contract |
|------------|------|----------|
| Share link creation | R08 Front Desk / R12 Radiologist | `POST /api/v2/files/{id}/share` |
| Share link access | R14 Referring Clinician | `GET /api/v2/share/{share_key}` |
| Study access | R06 Technologist (creates) | R14 reads via share |
| Report retrieval | R12 Staff Radiologist (writes) | R14 reads via share |
| Patient demographics | R16 External EMR (system) | HL7 ADT / FHIR Patient |
| Order context | R15 External RIS (system) | HL7 ORM / FHIR ServiceRequest |
| SSO authentication | R01 Super Admin (configures) | Azure AD / Okta SAML/OIDC |
| Image delivery | R17 External PACS (system) | DICOMweb C-FIND/C-MOVE |

## Open Questions

1. Should share links support password protection in addition to expiry? (v3.1)
2. Should referring clinicians be able to request a second opinion from a radiologist? (v3.2)
3. Should the share link workflow support multi-study bundles? (v3.1)