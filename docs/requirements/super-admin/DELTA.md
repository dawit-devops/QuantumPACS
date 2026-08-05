# Delta — Super Admin / PACS Admin (R01) — 2026-08-03

## Summary
- **Trigger**: re-verification after v3-dev merge 4d136e0 (no new admin/analytics endpoints; role-based route enforcement added)
- **Version change**: 1.2.0 → 1.2.1 (PATCH)
- **Stakeholder**: PACS requirements architect

## Changed Requirements
FR-R01-17 (global health dashboard) implemented: `GET /v2/dashboard/health`
(METRICS_READ) aggregates storage, DICOM listener, HL7, FHIR, auth + core
(db/es/redis/ingestion) status; System Health card rows on `/metrics` link to
area dashboards with time-scope passthrough and per-panel error isolation.
FR-R01-18 (backup/restore) remains GATED — backup is script-only
(`scripts/backup_db.sh`), no API.

## Impact on Existing Artifacts
| Artifact | Changed? | Summary |
|----------|----------|---------|
| README | Yes | FR-R01-17 moved to Implemented; `GET /v2/dashboard/health` added to API surface; Flagged Gaps list updated; version 1.3.0 |
| CHANGELOG | Yes | New `## [1.3.0] — 2026-08-05` entry (`### Added`/`### Changed`); FR-R01-18 remains backlog |
| 01-user-requirements | Yes | FR-R01-17 note replaced with implemented endpoint reference |
| 02-workflow-maps | Yes | Aggregate-health GAP note replaced with implementation summary |
| 03-user-stories | Yes | US-R01-15 GAP notes replaced with implementation references |
| 04-ui-ux-requirements | Yes | FR-R01-17 removed from GATED list; health-card drill-down + panel-isolation spec |
| 06-acceptance-criteria | Yes | AC-R01-37 → Pass (API + component test); AC-R01-38 remains GATED; achieved count 36 → 37 |
| 07-traceability | Yes | FR-R01-17 / AC-R01-37 marked covered/passing |
| 08-implementation-roadmap | Yes | FR-R01-17 moved to Implemented; Phase 2 item 1 done; only backup/restore blocking |

## Notes
- New post-merge backend routes (`/exams/*`, `/qa/*`, `/reports/*`,
  `/reading-presets/*`, `/peer-reviews/*`, `/protocols`) are clinical-role scoped
  (R06/R12/R05), NOT admin-managed — intentionally NOT added to the R01 API surface.
