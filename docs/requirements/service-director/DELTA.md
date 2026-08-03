# Delta — Radiology & Imaging Service Director (R03) — 2026-08-03

## Summary
- **Trigger**: re-verification after v3-dev merge 4d136e0 (no new admin/analytics endpoints; role-based route enforcement added)
- **Version change**: 1.2.0 → 1.2.1 (PATCH)
- **Stakeholder**: PACS requirements architect

## Changed Requirements
No requirement meaning changed — re-verification only. FR-R03-01..05, FR-R03-10,
FR-R03-12, FR-R03-14, FR-R03-15 and all v3.1 items remain GATED: no `/analytics/*`
endpoints exist, the `service_director` built-in role is still absent from
`BUILT_IN_ROLES`, and the post-merge `REPORT_*` permissions are reading-report
scoped (R12), not the analytics report builder.

## Impact on Existing Artifacts
| Artifact | Changed? | Summary |
|----------|----------|---------|
| README | Yes | Codebase Alignment re-verified post-merge 4d136e0; PermissionRoute route-level enforcement noted; clarified `REPORT_*` is R12-scoped and `service_director` role still missing; version 1.2.1 |
| CHANGELOG | Yes | New `## [1.2.1] — 2026-08-03` entry (`### Changed`) |
| 07-traceability | Yes | GATED section reworded for post-merge accuracy (clinical `/reports/*`/`/qa/*` routes are R12/R05-scoped; still no `/analytics/*`) |
| 01-user-requirements | No | FR GAP notes still accurate |
| 08-implementation-roadmap | No | All FR-R03-01..15 "Not yet scoped" still accurate |

## Notes
- Proposed permission slugs (`ANALYTICS_READ/EXPORT`, `REPORT_BUILD`, `REPORT_SCHEDULE`,
  `ALERT_MANAGE`) still absent from `PERMISSION_GROUPS`; proposed `service_director`
  role still absent — GATED status unchanged.
