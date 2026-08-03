# Requirements Package — R19 Other Hospital Staff

| Field | Value |
|-------|-------|
| **Version** | 1.1.2 |
| **Status** | draft |
| **Generated** | 2026-08-03 |
| **Changelog** | [CHANGELOG.md](CHANGELOG.md) |

## Codebase Alignment (verified 2026-08-03; re-verified 2026-08-03 post-merge 4d136e0)

**Presentation layer**: role-based; see artifact 04 — "Role-Based Routing &
Navigation": hospital-staff accounts today have Files/patient read-only views or a
share link. `PermissionRoute` now enforces role-based access at the URL boundary —
deep links to routes without the required permission redirect to `/` (Files).

**Implemented**: view own-patient imaging/results via study browser or share link.
**GATED**: limited-scope portal with order awareness + results notification — no
portal routes/endpoints exist; flagged to backend.

**Post-merge re-verification (4d136e0)**: in-app notification bell with WS push
exists, but `report.signed` notifications fan out to the `qa` role only — no
care-team/report-finalize fan-out for hospital staff and no email service, so
FR-R19-04 remains GATED. Reports are readable via `GET /reports/{exam_id}` only
behind REPORT_READ (radiologist/admin roles) — no scoped hospital-staff access, so
FR-R19-02 remains GATED. No other changes.

## Role Summary

**Persona**: Other hospital staff (ward nurses, lab, pharmacy) viewing their
patients' imaging results. Limited clinical read scope.
**Access tier**: Limited clinical — scoped read-only (no write, no annotation,
no download).
**Context**: Mobile-first portal; strict HIPAA minimum-necessary scoping and
zero-write enforcement.

## Artifact Index

| # | Artifact | File |
|---|----------|------|
| 01 | User Requirements | `01-user-requirements.md` |
| 02 | End-to-End Workflow Maps | `02-workflow-maps.md` |
| 03 | User Stories | `03-user-stories.md` |
| 04 | UI/UX Requirements | `04-ui-ux-requirements.md` |
| 05 | Metrics & SLAs | `05-metrics-slas.md` |
| 06 | Acceptance Criteria (validator-gated) | `06-acceptance-criteria.md` |
| 07 | Traceability Matrix | `07-traceability.md` |
| 08 | Implementation Roadmap | `08-implementation-roadmap.md` |

## Cross-Role Dependencies

- **R12/R18 Radiologist** — finalized reports and images viewed read-only.
- **R04/R15** — order status awareness.
- **R01/R02 Admin** — scope model, audit retention, role config.
- **R14 Referring Clinician** — shares the read-only viewer mode.

## Flagged Gaps (backend — must be raised before sprint commitment)

- Care-team scope model for patient access does not exist.
- Report-finalize notification event (R12 dependency) not wired.
- Read-only enforcement for this role (UI + API) not built.
- Follow-up request primitive does not exist.
