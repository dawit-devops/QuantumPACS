# Delta — Super Admin / PACS Admin (R01) — 2026-08-03

## Summary
- **Trigger**: re-verification after v3-dev merge 4d136e0 (no new admin/analytics endpoints; role-based route enforcement added)
- **Version change**: 1.2.0 → 1.2.1 (PATCH)
- **Stakeholder**: PACS requirements architect

## Changed Requirements
No requirement meaning changed — re-verification only. FR-R01-17 (global health
dashboard) and FR-R01-18 (backup/restore) remain GATED: no `/dashboard/health`
endpoint exists and backup is script-only (`scripts/backup_db.sh`), no API.

## Impact on Existing Artifacts
| Artifact | Changed? | Summary |
|----------|----------|---------|
| README | Yes | Codebase Alignment re-verified post-merge 4d136e0; PermissionRoute route-level enforcement noted; new built-in roles + permission groups (`Exams`, `Reports`, `Peer Review`, `QA`) noted in `/roles` catalog; version 1.2.1 |
| CHANGELOG | Yes | New `## [1.2.1] — 2026-08-03` entry (`### Changed`) |
| 01-user-requirements | No | FR-R01-17/18 GAP notes still accurate |
| 07-traceability | No | GATED entries (AC-R01-37/38) still accurate |
| 08-implementation-roadmap | No | Statuses unaffected by merge |

## Notes
- New post-merge backend routes (`/exams/*`, `/qa/*`, `/reports/*`,
  `/reading-presets/*`, `/peer-reviews/*`, `/protocols`) are clinical-role scoped
  (R06/R12/R05), NOT admin-managed — intentionally NOT added to the R01 API surface.
