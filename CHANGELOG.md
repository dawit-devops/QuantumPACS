# Changelog

All notable changes to QuantumPACS are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Sprint 7 — Docs (in progress)

- Fixed README inaccuracies (test paths, E2E counts, Docker quick start,
  credentials, repo structure, architecture diagram).
- `docs/version-3 plans/` removed — stale duplicates of `docs/PRD-v3.md` and
  `docs/ROADMAP-v3.md`.
- `CLAUDE.md` refreshed for current stack (Ant Design v6, plain CSS files,
  Elasticsearch 9, full-stack docker-compose runtime).
- Added ADRs 023–025 (WebSocket design, share-link tempKey auth, token
  storage).
- New `CHANGELOG.md` (this file).

### Sprint 6 — Test-gap closure + ops hardening

- Frontend test suite grew to 246 tests across 35 files (T-M1..M4, T-L1..L4):
  useFetch suite, permission-contract tests, error/empty paths, shared
  `renderWithApp` helper, notification contract typed per backend payload.
- Ops: docker-compose now a runnable full-stack runtime (redis/backend/frontend,
  env-var secrets via `.env`), systemd backup timer + failure-notify units,
  `backup_db.sh` discovers the live container port/password, `docker-smoke`
  CI job.
- Two latent Docker bugs fixed (uvicorn entrypoint, static dir mount).

### Sprint 5 — Hardening & reliability

- Phase 0 hardening: SQL-injection fix, Secure cookie flag, CORS tightening,
  ES atomicity, Cornerstone code-splitting, k6 load scaffolds.
- Auth token moved to httpOnly cookie; `logout` clears the cookie; AuthContext
  tests updated accordingly.
- Notification bell now renders typed backend events (event_type/title/body/link).
- Permission contract: forged localStorage admin cannot mask 403s; no token
  refresh on 403.

### Frontend modernization (A-4, H-10, A-5..A-7, M1/M2/M4)

- `withRouter` HOC removed; migrated to router hooks.
- `message.*` statics migrated to `antd` `App.useApp()`.
- Auth routing, WebSocket endpoint, and share-token security consolidated
  (typed API modules for auth/notifications/logs/user admin/FHIR/files).
- DICOM viewer: Cornerstone3D + progressive loading.

## [2.x] — 2025

### Added

- DICOM viewer (Cornerstone3D + cornerstone-wado-image-loader).
- Multi-tenant PostgreSQL (intarray/citext) with LISTEN/NOTIFY replica sync.
- JWT auth (Bearer + X-Auth-Pacs), rate-limited login, CORS.
- Elasticsearch search (optional, disabled gracefully when unreachable).
- File manager, DICOM router, replicator, backup/restore.

### Notes

- Pre-2.0 history was not tracked in this changelog; see git history.
