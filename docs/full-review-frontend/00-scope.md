# Review Scope

## Target

Full review of the QuantumPACS frontend (`frontend/`) — React 19 + Vite 8 + Ant Design v6 + Cornerstone3D medical imaging viewer SPA, after the phase/11-ci-green pipeline fixes were merged into v3-dev.

## Files

- `frontend/src/**` (105 TS/TSX files: auth, account, common, detail, dicomweb, fhir, files, hl7, integrations, login, logs, metrics, notifications, patient, replicas, roles, routing, servicekeys, tenants, users, worklist, ws, helpers, hooks, navigator, withRouter, config, types.d.ts)
- `frontend/package.json`, `frontend/package-lock.json`
- `frontend/vite.config.js`, `frontend/tsconfig.json`, `frontend/tsconfig.node.json`
- `frontend/Dockerfile`, `frontend/nginx.conf` (added in phase/11-ci-green)
- `frontend/e2e/**` (Playwright specs)
- `frontend/src/test/**` (Vitest + RTL)
- `.github/workflows/ci.yml` (frontend jobs: lint-frontend, typecheck, test-frontend, docker-build)

## Flags

- Security Focus: no
- Performance Critical: no
- Strict Mode: no
- Framework: React 19 / Vite 8 / AntD v6 / Cornerstone3D 5.6 / TypeScript 6

## Review Phases

1. Code Quality & Architecture
2. Security & Performance
3. Testing & Documentation
4. Best Practices & Standards
5. Consolidated Report
