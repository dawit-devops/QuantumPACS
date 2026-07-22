# Dependency Audit Report — OpenPACS

Generated: 2026-07-21
Project: OpenPACS (Python/Starlette backend + React/antd frontend)

---

## Executive Summary

OpenPACS has **29 direct dependencies** across its stack (17 Python, 12 JS). Of these, **22 are outdated**, **6 are severely outdated**, **3 are deprecated/abandoned**, and **3 infrastructure services are past EOL**. The codebase is frozen in a 2019-era dependency landscape with zero upgrades since initial release.

---

## 1. Backend — Python Dependencies

### Dependency Status Table

| Dependency | Installed | Latest | Status | Risk | Priority |
|---|---|---|---|---|---|
| starlette | 0.12.8 | 1.3.1 | ❌ Severely outdated | High | P0 |
| uvicorn | 0.8.6 | 0.34.x | ❌ Severely outdated | Medium | P0 |
| gunicorn | 19.9.0 | 23.0.0 | ❌ Severely outdated | Medium | P0 |
| asyncpg | 0.18.3 | 0.30.x | ⚠ Outdated | Medium | P1 |
| aiobotocore | 0.10.3 | 2.x | ❌ Severely outdated | High | P0 |
| b2sdk | 1.0.0rc1 | 2.x | ❌ Release candidate | High | P0 |
| elasticsearch-async | 6.2.0 | (archived) | 🚨 Deprecated/EOL | Critical | P0 |
| pydicom | 1.3.0 | 3.0.2 | ❌ Severely outdated | Medium | P1 |
| pynetdicom | 1.4.1 | 3.0.4 | ❌ Severely outdated | Medium | P1 |
| PyJWT | 1.7.1 | 2.10.x | ❌ Severely outdated | High | P0 |
| PyPika | 0.35.2 | 0.48.x | ⚠ Outdated | Low | P2 |
| PyYAML | 5.1.2 | 6.x | ⚠ Outdated | Low | P2 |
| python-dateutil | 2.8.0 | 2.9.x | ⚠ Outdated | Low | P2 |
| python-multipart | 0.0.5 | 0.0.20 | ⚠ Outdated | Low | P2 |
| aiofiles | 0.4.0 | 24.x | ⚠ Outdated | Low | P2 |
| ujson | 1.35 | 5.x | ⚠ Outdated | Low | P2 |
| email-validator | 1.0.4 | 2.x | ⚠ Outdated | Low | P3 |

### Risk Classification

**🚨 Security Critical (immediate action required):**
- `elasticsearch-async==6.2.0` — Library is archived/unmaintained. ES 6.x line has known vulnerabilities. Elasticsearch 7.3.0 container is also outdated (current: 8.x).
- `PyJWT==1.7.1` — Multiple CVEs in PyJWT <2.0.0 (CVE-2022-39227, algorithm confusion). HS256 still used; no RS256/ES256 support.

**❌ Deprecated / High Risk (upgrade within 1 sprint):**
- `starlette==0.12.8` — Requires Python 3.10+ for modern versions. Huge API surface change from 0.12 → 1.x.
- `aiobotocore==0.10.3` — Breaking API changes in aiobotocore 2.x. S3 storage will break.
- `b2sdk==1.0.0rc1` — A release candidate from 2019. Not production-grade.
- `gunicorn==19.9.0` — Dropped Python 3.7 support. Multiple security fixes in later releases.
- `uvicorn==0.8.6` — Requires Python 3.8+ for modern versions.

**⚠️ Supported but Outdated (schedule within 2-3 sprints):**
- `asyncpg`, `pydicom`, `pynetdicom`, `PyPika`, `PyYAML`, `python-dateutil`, `python-multipart`, `aiofiles`, `ujson`, `email-validator`

---

## 2. Frontend — JavaScript Dependencies

### Dependency Status Table

| Dependency | Declared | Resolved | Latest | Status | Risk | Priority |
|---|---|---|---|---|---|---|
| react | ^16.8.6 | 16.8.6 | 19.x | ❌ Severely outdated | High | P0 |
| react-dom | ^16.8.6 | 16.8.6 | 19.x | ❌ Severely outdated | High | P0 |
| react-scripts | ^3.0.1 | 3.0.1 | CRA sunset | 🚨 Abandoned | Critical | P0 |
| antd | ^3.21.0 | 3.21.2 | 5.29.x | ❌ Severely outdated | High | P0 |
| react-router-dom | ^5.0.1 | 5.0.1 | 7.x | ❌ Severely outdated | Medium | P1 |
| cornerstone-core | ^2.3.0 | 2.3.0 | 2.x | ✅ Stable | Low | P3 |
| cornerstone-tools | ^3.18.3 | 3.18.3 | 6.x/7.x | ⚠ Breaking changes | Medium | P2 |
| cornerstone-math | ^0.1.8 | 0.1.8 | (merged) | ❌ Deprecated | Low | P2 |
| cornerstone-wado-image-loader | ^3.0.0 | 3.0.0 | 4.x | ⚠ Outdated | Medium | P2 |
| cornerstone-web-image-loader | ^2.1.1 | 2.1.1 | (unmaintained) | ⚠ Outdated | Low | P3 |
| dicom-parser | ^1.8.3 | 1.8.3 | 1.x | ✅ Stable | Low | P3 |
| hammerjs | ^2.0.8 | 2.0.8 | 2.x | ✅ Stable | Low | P3 |
| react-highlight-words | ^0.16.0 | 0.16.0 | 0.20.x | ⚠ Outdated | Low | P3 |

### Risk Classification

**🚨 Security Critical (immediate action required):**
- `react-scripts@3.0.1` — **Create React App is officially deprecated/sunset by React team (Feb 2025).** Uses Webpack 4 (current: 5), Babel 7.x with proposal plugins (merged to transforms). 100+ transitive deprecation warnings including `har-validator`, `request`, `svgo@1.x`. No security patches. No React 18/19 support. **Must migrate to Vite or Next.js.**

**❌ Deprecated / High Risk (upgrade within 1 sprint):**
- `antd@3.21.2` — Three major versions behind (3→4→5). Each has breaking changes: v4 dropped IE, v5 replaced Moment.js with Dayjs, switched from Less to CSS-in-JS. No security patches for v3.
- `react@16.8.6` / `react-dom@16.8.6` — Three major versions behind. No concurrent mode, no Suspense, no streaming SSR. All security patches are in 18.x+.
- `react-router-dom@5.0.1` — v5 uses static route config. v6 uses element-based routing with `<Routes>` and `<Route element={}>`. Breaking API change.

**⚠️ Supported but Outdated:**
- `cornerstone-tools@3.18.3` — v6/v7 introduced breaking API changes. The entire cornerstone library ecosystem has been in flux (merged into OHIF's cornerstone3D).
- `cornerstone-wado-image-loader@3.0.0` — v4 uses different configuration API.

---

## 3. Infrastructure Dependencies

### Service Status Table

| Service | Installed | Latest | Status | Risk | Priority |
|---|---|---|---|---|---|
| Python | 3.7.4 | 3.13 | 🚨 EOL (Jun 2023) | Critical | P0 |
| PostgreSQL | 11.4 | 17 | 🚨 EOL (Nov 2023) | Critical | P0 |
| Elasticsearch | 7.3.0 | 8.x | ❌ Outdated (7.x EOL 2024) | High | P0 |

**Python 3.7 EOL impact:** No security patches since June 2023. The Dockerfile uses `python:3.7.4-alpine` which has known CVEs in the base image. All modern dependency versions (starlette 1.x, uvicorn 0.30+) require Python >=3.8, with most requiring >=3.10.

**PostgreSQL 11.4 EOL impact:** No security patches since November 2023. Missing performance improvements from v12-17 (incremental backup, parallel query, logical replication improvements). Migration to 16.x LTS recommended.

**Elasticsearch 7.3.0 impact:** 7.x line reached EOL. Missing 8.x features (vector search, improved aggregations, TLS by default). The `elasticsearch-async` library for 6.x is doubly problematic — it targets the 6.x API while the container runs 7.3.0.

---

## 4. Critical Findings Summary

| # | Finding | Severity | Effort | Impact |
|---|---|---|---|---|
| 1 | Python 3.7 EOL — blocks all dep upgrades | 🚨 Critical | High | Blocking |
| 2 | CRA/react-scripts abandoned — must migrate build system | 🚨 Critical | High | Blocking |
| 3 | PyJWT 1.7.1 known CVEs (algorithm confusion) | 🚨 Critical | Low | Auth bypass |
| 4 | elasticsearch-async archived — ES client needs rewrite | 🚨 Critical | Medium | Search outage |
| 5 | antd 3.x — three major versions behind, no patches | ❌ High | High | UI breaking |
| 6 | aiobotocore 0.x — S3 connectivity will break | ❌ High | Medium | Storage outage |
| 7 | b2sdk RC — Backblaze API may have changed | ❌ High | Medium | Storage outage |
| 8 | PostgreSQL 11.4 EOL — no security patches | ❌ High | Medium | DB security |
| 9 | starlette 0.12 → 1.x huge API surface change | ❌ High | Medium | API breakage |
| 10 | React 16 → 19 — concurrent mode, hooks changes | ❌ High | High | UI regression |
