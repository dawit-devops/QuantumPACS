# Dependabot Dependency Audit — 2026-08-11

**Date:** 2026-08-11
**Scope:** `frontend/package.json` + `package-lock.json`, `backend/requirements.lock.txt`, CI workflows
**Sources:** GitHub Dependabot API (10 open alerts on `main`), `npm audit`, `pip-audit` (OSV)

---

## Summary

The GitHub push banner reported 11 vulnerabilities (5 high / 6 moderate) on the default
branch. Investigation confirmed the Dependabot alerts are computed against **`main`'s**
manifests, which lag `v3-dev`. Local scans were used to reconcile true exposure.

**After this remediation pass:**

| Surface | Before | After |
|---|---|---|
| Frontend (`npm audit`) | 8 (5 high, 3 moderate) | **2 moderate** (both NO-FIX, accepted — see below) |
| Backend (`pip-audit`) | 2 | **0** |
| GitHub open alerts (recomputed on merge) | 10 | pending rescan; 2 already fixed on `v3-dev` |

---

## 1. Fixed — frontend (`npm audit fix` + cornerstone bump)

| Package | Severity | Chain | Fix applied |
|---|---|---|---|
| brace-expansion (×2 GHSA) | high | typescript-eslint, eslint-plugin-react (dev) | `npm audit fix` → 1.1.18 / 5.0.9 |
| undici (5 GHSA) | high + 4 medium | jsdom (dev/test-only) | `npm audit fix` → 7.29.0 |
| postcss | medium | vite + vtk.js→autoprefixer (prod) | `npm audit fix` → 8.5.26 |
| js-yaml | high | vtk.js→xmlbuilder2 (**prod viewer**) + eslint | `npm audit fix` → 4.3.1 |
| fast-uri | high | workbox-build→ajv (build-time) | `npm audit fix` → 3.1.5 |
| nanoid | high | vite→postcss (dev) | `npm audit fix` → 3.3.18 |
| @cornerstonejs/core / tools / dicom-image-loader | — | — | **5.6.10 → 5.7.2** (upstream fixes) |

**Validation:** `tsc` clean · 24/24 vitest viewer tests · production build succeeds.

## 2. Fixed — already handled on `v3-dev` (alert is `main`-only)

| Package | Severity | Why fixed on v3-dev |
|---|---|---|
| react-router | high | v3-dev pins `^8.3.0`; `main` has 7.18.1 (vulnerable). Closes when v3-dev merges to main |
| adm-zip | high | v3-dev adds `overrides: { "adm-zip": "0.6.0" }`; `main` has 0.5.17 |

## 3. Fixed — backend (`requirements.lock.txt`)

| Package | Version | Advisory | Fix |
|---|---|---|---|
| aiohttp | 3.14.2 | CVE-2026-69244 — OOB heap read in C HTTP parser (DoS) | → **3.14.3** |
| cryptography | 49.0.0 | CVE-2026-69247 — Bleichenbacher oracle in PKCS#7 | → **50.0.0** (already the intended `requirements.txt` pin; lock was stale) |

## 4. CI hygiene

- `aquasecurity/trivy-action@master` → **`@v0.36.0`** (supply-chain: never pin actions to a
  mutable branch).

---

## 5. Accepted risk — uuid (NO FIX available) ⚠️

**Remaining after this pass:** 2 moderate npm alerts, both from the same root cause.

| Package | Severity | Advisory |
|---|---|---|
| uuid 9.0.1 | moderate | GHSA-w5hq-g745-h8pq — missing buffer bounds check in **v3/v5/v6** when `buf` is provided |
| @cornerstonejs/dicom-image-loader | moderate | inherits the above |

**Why we accept this (rationale for dismiss):**

1. **No upstream fix exists.** `@cornerstonejs/dicom-image-loader` pins `uuid: "9.0.1"`
   **exactly** (verified in 5.6.10 *and* the latest 5.7.2). No npm override can patch the
   pinned version within the loader's declared range, and forcing `uuid@11` via
   `overrides` would violate the loader's exact pin (untested API-compat risk against the
   whole DICOM pipeline).
2. **Exploitability is effectively nil in this app.** The advisory only affects the
   `v3()`/`v5()`/`v6()` generators **when a caller-supplied buffer** is passed. The loader
   uses `uuid.v4()` for generated IDs with no attacker-controlled buffers.
3. **Exposure is client-side only.** The loader runs in the browser; a hypothetical
   exploit would corrupt a caller-provided buffer in the viewer, not the backend or PHI.

**Tracking:** re-check on each cornerstone upgrade (`npm audit` gate in CI will surface
it the moment a fixed loader version ships). Revisit the `overrides` option at the next
major cornerstone bump (6.x), where uuid 11 support is expected upstream.

---

## Validation commands (re-run after any future dep change)

```bash
cd frontend && npm audit && npx tsc --noEmit && npx vitest run src/test/CornerstoneElement.test.tsx src/test/MeasurementPanel.test.tsx
cd backend && python3 -m py_compile api/files.py  # lock-level sanity
```
