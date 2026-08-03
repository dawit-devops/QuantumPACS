# Delta — Hospital IT / Tenant Admin (R02) — 2026-08-03

## Summary
- **Trigger**: re-verification after v3-dev merge 4d136e0 (no new admin/analytics endpoints; role-based route enforcement added)
- **Version change**: 1.2.1 → 1.2.2 (PATCH)
- **Stakeholder**: PACS requirements architect

## Changed Requirements
No requirement meaning changed — re-verification only. FR-R02-15 remains
partially implemented (`GET /tenants/{id}/stats` exists with storage + quota);
the usage/quota dashboard UI remains GATED.

## Impact on Existing Artifacts
| Artifact | Changed? | Summary |
|----------|----------|---------|
| README | Yes | Codebase Alignment re-verified post-merge 4d136e0; PermissionRoute route-level enforcement noted; new built-in roles + permission groups noted in `/roles` catalog; version 1.2.2 |
| CHANGELOG | Yes | New `## [1.2.2] — 2026-08-03` entry (`### Changed`) |
| 01-user-requirements | No | FR-R02-15 GAP note still accurate |
| 07-traceability | No | GATED entries still accurate |
| 08-implementation-roadmap | No | Statuses unaffected by merge |

## Notes
- New post-merge backend routes (`/exams/*`, `/qa/*`, `/reports/*`,
  `/reading-presets/*`, `/peer-reviews/*`, `/protocols`) are clinical-role scoped
  (R06/R12/R05), NOT tenant-admin managed — intentionally NOT added to the R02
  tenant-scoped API surface.
