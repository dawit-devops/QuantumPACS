# E2E Test Plan — Playwright UI Test Suite

**Document:** cross-cutting (PACS-first, platform-wide) · **Version:** 1.0 · **Date:** 2026-08-04
**Sources:** `requrements/PACS/04_uiux_requirements.md` (PAC-UI-*), `requrements/PACS/06_acceptance_criteria.md` (PAC-AC-*), `requrements/PACS/05_metrics_and_slas.md` (PAC-SL-*), `requrements/PACS/RELEASE_PLAN.md` (§2 gates G1–G7), `requrements/qa_test_strategy.md` (API/service pytest layer), `docs/specs/worklist_design.md`, `research/pacs-ris-viewer-integration-spec.md`
**Method:** Playwright (TypeScript) — cross-browser (Chromium/Firefox/WebKit + mobile), Page Object Model, storage-state auth, network mocking; every spec maps to a named `PAC-UI-*` requirement and an exit gate.

> **One-line rule:** every MVP-scope `PAC-UI-*` has a named Playwright spec; every gate that touches a screen (G3 viewer, G4 storage, G5 queue, G6 admin/audit, G7 UAT) is verified by a defined spec set; the same specs are the executable UAT scripts at go-live.

---

## 1. Purpose & Scope

This document is the **browser-level complement to `qa_test_strategy.md`**. The pytest catalog (`T-PAC-AC-*` / `T-SL-*`) verifies the API/service layer; this plan verifies the **rendered UI against real browsers** — the surfaces the personas actually touch:

| Surface | Primary personas | PAC-UI range |
| :--- | :--- | :--- |
| Reading worklist | Radiologist, Technologist | PAC-UI-08…13 |
| Diagnostic viewer | Radiologist, Teleradiologist | PAC-UI-14…22 |
| Acquisition / QC UI | Technologist | PAC-UI-23…25 |
| PACS admin console | PACS Administrator, Informatics | PAC-UI-26…33 |
| Tenant & ops dashboards | Tenant Admin, Super Admin | PAC-UI-34…38 |
| Viewer launch & sharing | Referring MD, ED MD | PAC-UI-39…41 |
| Mobile / responsive | Referring MD, ED MD | PAC-UI-42…43 |

**What this plan covers:** functional UI flows, role-gated access, accessibility (WCAG AA), responsive behavior, loading/error states, and cross-browser consistency.

**Scope out:** pixel-perfect visual regression is included only as an optional pattern (`@visual`); API/backend behavior lives in `qa_test_strategy.md`; manual UAT script authoring remains in `sprint7_hardening_detail.md` — but the E2E specs are the **automated backbone of the UAT pack**.

---

## 2. Playwright Project Layout

```
e2e/
├── playwright.config.ts          # projects, baseURL, retries, reporters
├── fixtures/
│   ├── pages/                    # Page Object Model (POM)
│   │   ├── LoginPage.ts
│   │   ├── WorklistPage.ts
│   │   ├── ViewerPage.ts
│   │   ├── HangingProtocols.ts
│   │   ├── AcquisitionStatusPage.ts
│   │   ├── AdminConsolePage.ts
│   │   ├── ModalityRegistryPage.ts
│   │   ├── QueueMonitorPage.ts
│   │   ├── StorageDashboardPage.ts
│   │   ├── RetentionPolicyEditor.ts
│   │   ├── ExceptionWorklistPage.ts
│   │   ├── AuditLogViewerPage.ts
│   │   ├── TenantOpsDashboardPage.ts
│   │   └── ShareLinkPage.ts
│   ├── auth.setup.ts             # persona storage states (radiologist, technologist, admin…)
│   └── mocks/                    # QIDO/WADO/HL7 route interception fixtures
├── specs/
│   ├── worklist.spec.ts          # PAC-UI-08…13
│   ├── viewer.spec.ts            # PAC-UI-14…22
│   ├── acquisition.spec.ts       # PAC-UI-23…25
│   ├── admin-console.spec.ts     # PAC-UI-26…32
│   ├── dashboards.spec.ts        # PAC-UI-34…38
│   ├── launch-share.spec.ts      # PAC-UI-39…41
│   ├── mobile.spec.ts            # PAC-UI-42…43
│   └── cross-cutting.spec.ts     # PAC-UI-01…07 (tokens, keyboard, a11y, resilience)
├── playwright-report/
└── test-results/
```

**Config essentials** (per the Playwright skill):

```typescript
export default defineConfig({
  testDir: './specs',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'https://staging.platform.example.com', // production-shaped staging (Sprint 7)
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'setup', testMatch: /auth\.setup\.ts/ },
    { name: 'chromium', use: { ...devices['Desktop Chrome'], storageState: 'fixtures/.auth/radiologist.json' }, dependencies: ['setup'] },
    { name: 'firefox', use: { ...devices['Desktop Firefox'], storageState: 'fixtures/.auth/radiologist.json' }, dependencies: ['setup'] },
    { name: 'webkit', use: { ...devices['Desktop Safari'], storageState: 'fixtures/.auth/radiologist.json' }, dependencies: ['setup'] },
    { name: 'Mobile Chrome', use: { ...devices['Pixel 5'], storageState: 'fixtures/.auth/referring.json' }, dependencies: ['setup'] },
  ],
  webServer: { command: 'npm run start', url: 'https://staging.platform.example.com', reuseExistingServer: !process.env.CI },
});
```

---

## 3. Spec Catalog (PAC-UI → Playwright spec)

Test IDs `T-UI-<PAC-UI-id>`; spec function names follow `test_<ui_id>_<scenario>`; tags drive filtering. **Declared tags** (all `@`-prefixed): `@smoke @critical @desired @optional @viewer @admin @mobile @a11y @visual @perf`. Priority-tagged specs (`@desired`/`@optional`) are **not gate-blocking**; `@perf` feeds the progressive-render assertion used alongside the pytest perf suite.

### 3.1 Reading worklist (PAC-UI-08…13) → gate G3 (+ G7 UAT)

| Spec ID | Scenario (Given/When/Then) | PAC-UI | PAC-AC | Tags | Project |
| :--- | :--- | :-: | :-: | :--- | :--- |
| T-UI-08 | Worklist rows render all required columns; patient name is masked per policy | 08 | P01-01 | smoke, critical | chromium, firefox, webkit |
| T-UI-09 | Default sort STAT > inpatient > outpatient by study date; filters (modality/site/date/status/unread) apply; filter set persists across sessions | 09 | P01-01 | critical | chromium |
| T-UI-10 | Search by MRN/accession returns server-total results with working pagination (no client-side count) | 10 | P01-01 | critical | chromium |
| T-UI-11 | Batch actions enabled only for valid status transitions ("Mark Performed" disabled + tooltip on unscheduled rows) | 11 | P01-01 | critical | chromium, webkit |
| T-UI-12 | Row click opens study in viewer; double-click opens new tab (side-by-side) | 12 | P01-08 | desired | chromium |

> **Deferred UI (v1.1/v2.0, mirroring `qa_test_strategy.md` §3.7):** PAC-UI-15 priors panel (v1.1 — spec row above is `@desired`, not gate-blocking), PAC-UI-18 AI overlay (v1.1, O priority — spec T-UI-18 to be added with the AI epic), PAC-UI-33 migration tool (v1.1, D priority — T-UI-33 deferred), PAC-UI-39 SMART launch (v2.0 — `@desired`), PAC-UI-42/43 mobile (PAC-UI-42 v2.0 `@mobile`; PAC-UI-43 ships MVP).
| T-UI-13 | Critical-finding badge persists until acknowledged; acknowledgment records time | 13 | P01-06 | smoke, critical | chromium |

### 3.2 Diagnostic viewer (PAC-UI-14…22) → gate G3 (+ G7 UAT)

| Spec ID | Scenario (Given/When/Then) | PAC-UI | PAC-AC | Tags | Project |
| :--- | :--- | :-: | :-: | :--- | :--- |
| T-UI-14 | CT-chest opens with default hanging protocol (2×4, lung+mediastinum); override saved and reapplied per user/anatomy; unknown anatomy falls back to generic | 14 | P01-02 | smoke, critical | chromium |
| T-UI-15 | Priors panel: side-by-side current vs. prior with synchronized scroll; thumbnails; one-click swap — **v1.1** (per release plan priors prefetch; PAC-AC-P01-03 deferred in `qa_test_strategy.md` §3.7) | 15 | P01-03 (v1.1) | desired, viewer | chromium |
| T-UI-16 | Toolbar renders the **MVP subset** (window/level presets, zoom, pan, measure, annotate, cine, invert, reset); each acts on the active viewport. MPR/MIP/3D/fusion are v1.1 (PAC-AC-P01-04 advanced subset deferred in `qa_test_strategy.md` §3.7) | 16 | P01-04 (MVP subset) | critical | chromium |
| T-UI-17 | Key-image star bookmarks an instance; bookmark thumbnail appears and links into the report template | 17 | P01-07 | desired | chromium |
| T-UI-19 | Series navigator lists series with labels; series with no images shows a warning, not a blank tile | 19 | P01-08/10 | critical | chromium |
| T-UI-20 | First frames render progressively (skeleton → frames); failed series shows explicit error + Retry; rest of study remains usable | 20 | P01-08/10 | smoke, critical | chromium, firefox |
| T-UI-21 | Multi-monitor workspace spans displays; layout persisted per user | 21 | P01-02 | desired | chromium |
| T-UI-22 | Measurements persist with the study and are visible to co-readers | 22 | P01-04 | desired | chromium |
| T-UI-01 | Viewer never waits for full download before first frames (progressive) — feeds the perf-suite assertion (T-SL-10/11) | 01 | P01-10 | perf | chromium |

### 3.3 Acquisition / QC UI (PAC-UI-23…25) → gates G1, G2 (+ G7 UAT)

| Spec ID | Scenario (Given/When/Then) | PAC-UI | PAC-AC | Tags | Project |
| :--- | :--- | :-: | :-: | :--- | :--- |
| T-UI-23 | Ingest status panel shows per-series progress; failure shows reason + retry; duplicate upload shows "already stored — duplicate" | 23 | P02-03 | critical | chromium |
| T-UI-24 | QC screen marks series Adequate/Inadequate; Inadequate requires reject reason code | 24 | P02-06 (v1.1) | desired | chromium |
| T-UI-25 | Storage Commitment confirmation renders green "Archived — safe to purge" only after SC success; failure path shows no purge prompt | 25 | P02-02 | smoke, critical | chromium |

### 3.4 PACS admin console (PAC-UI-26…32) → gates G4, G5, G6 (+ G7 UAT)

| Spec ID | Scenario (Given/When/Then) | PAC-UI | PAC-AC | Tags | Project |
| :--- | :--- | :-: | :-: | :--- | :--- |
| T-UI-26 | Modality registry lists AE title/IP/tenant/model + status (online/offline/last seen); enable/disable and edit work | 26 | P04-01 | critical, admin | chromium |
| T-UI-27 | Routing-rules builder shows rule precedence; dry-run validation previews destination | 27 | P04-02 | desired, admin | chromium |
| T-UI-28 | Queue monitor shows depth, stuck-message detection, error counts; one-click retry/drain works | 28 | P04-08 | critical, admin | chromium |
| T-UI-29 | Storage dashboard color bar green <50% / orange 50–75% / red >75%; tier breakdown + growth trend render | 29 | P19-01 | critical, admin | chromium |
| T-UI-30 | Retention editor shows per-document clocks; legal-hold toggle requires reason + audit; dry-run purge previews exactly what would purge | 30 | P04-03 | critical, admin | chromium |
| T-UI-31 | Exception worklist lists failed studies with reason; merge/reassign actions available; mismatch highlighted | 31 | P04-05 | critical, admin | chromium |
| T-UI-32 | Audit viewer columns (time/actor/event/resource/tenant), filters, cursor pagination, CSV export match | 32 | P20-03 | critical, admin | chromium, webkit |

### 3.5 Tenant & ops dashboards (PAC-UI-34…38) → gates G6 (+ G7 UAT)

| Spec ID | Scenario (Given/When/Then) | PAC-UI | PAC-AC | Tags | Project |
| :--- | :--- | :-: | :-: | :--- | :--- |
| T-UI-34 | Usage metering dashboard renders studies/WADO bytes/MWL queries by tenant & period; CSV export matches on-screen data | 34 | P19-01 | critical | chromium |
| T-UI-35 | Invoice view shows plan, base, overage lines, status; drill-through to usage detail works | 35 | P20-02 | critical | chromium |
| T-UI-36 | Tenant card grid shows status badge + storage bar + counts; actions open the right flows | 36 | P19-01 | critical | chromium |
| T-UI-37 | Provisioning progress shows stage (QUEUED→…→READY); actions disabled until READY | 37 | P20-01 | smoke, critical | chromium |
| T-UI-38 | KPI charts render time-series with drill-down to outliers | 38 | P05-01 | desired | chromium |

### 3.6 Viewer launch & sharing (PAC-UI-39…41) → gate G3, G7

| Spec ID | Scenario (Given/When/Then) | PAC-UI | PAC-AC | Tags | Project |
| :--- | :--- | :-: | :-: | :--- | :--- |
| T-UI-39 | SMART-launch URL lands directly on the correct study with no search (no PHI in URL) | 39 | P06-01 (v2.0) | desired | chromium |
| T-UI-40 | Referring read-only mode shows report + key images + basic tools; dictation/editing controls absent | 40 | P06-03 | critical | chromium |
| T-UI-41 | Share-link view renders read-only; expired/invalid key shows friendly message (per `share_design.md`) | 41 | P20-03 | desired | chromium, webkit |

### 3.7 Mobile / responsive (PAC-UI-42…43) → gate G3

| Spec ID | Scenario (Given/When/Then) | PAC-UI | PAC-AC | Tags | Project |
| :--- | :--- | :-: | :-: | :--- | :--- |
| T-UI-42 | Tablet viewer responds to pinch zoom + swipe series; portrait/landscape adapts; limited toolset renders | 42 | P06-03 (v2.0) | mobile | Mobile Chrome |
| T-UI-43 | Session timeout + screen lock on blur; no PHI cached on device (devtools assert no localStorage persistence of PHI) | 43 | P06-03 | mobile, critical | Mobile Chrome |

### 3.8 Cross-cutting UX (PAC-UI-01…07) → all gates

| Spec ID | Scenario (Given/When/Then) | PAC-UI | PAC-AC | Tags | Project |
| :--- | :--- | :-: | :-: | :--- | :--- |
| T-UI-02 | Design tokens (color, spacing, typography) applied consistently across worklist/viewer/admin (spot-check via computed styles) | 02 | — | visual | chromium |
| T-UI-03 | Every common action (scroll, zoom, window/level, layout, next study, dictation toggle) is reachable by documented keyboard shortcut; shortcuts configurable per user | 03 | P01-01 | a11y, critical | chromium, webkit |
| T-UI-04 | Re-login restores worklist filters + WIP (open study, draft report) with no duplicate report | 04 | P01-09 | critical | chromium |
| T-UI-05 | WCAG 2.1 AA: full keyboard nav with visible focus; `getByRole`-based selectors find all controls; contrast ≥ 4.5:1; colorblind-safe (no color-only warnings) — run `@axe-core` per screen | 05 | P01-01 | a11y | chromium, firefox, webkit |
| T-UI-07 | Where policy requires, users can view the access/export trail for a study | 07 | P20-03 | optional | chromium |

---

## 4. Page Object Model (fixtures/pages)

| Page Object | Key locators (role-based) | Owned by |
| :--- | :--- | :--- |
| `LoginPage` | `getByLabel('Username'/'Password')`, `getByRole('button', { name: 'Log in' })`, error message | auth |
| `WorklistPage` | `getByRole('row')`, priority badge, filter controls, `getByTestId('pagination-total')` | worklist specs |
| `ViewerPage` | viewports (`getByTestId('viewport')`), toolbar (`getByRole('toolbar')`), series strip | viewer specs |
| `HangingProtocols` | layout switcher, override save dialog | viewer specs |
| `AcquisitionStatusPage` | upload progress rows, duplicate label, retry button, SC badge | acquisition specs |
| `AdminConsolePage` | nav to registry/queue/storage/retention/exceptions/audit | admin specs |
| `ModalityRegistryPage` | registry table, enable/disable toggle, edit dialog | admin specs |
| `QueueMonitorPage` | queue depth rows, stuck badges, retry/drain buttons | admin specs |
| `StorageDashboardPage` | usage bars (color states), tier breakdown | admin specs |
| `RetentionPolicyEditor` | clock rows, legal-hold toggle + reason, dry-run modal | admin specs |
| `ExceptionWorklistPage` | failed-study rows, merge/reassign actions | admin specs |
| `AuditLogViewerPage` | audit table, filters, CSV export | admin specs |
| `TenantOpsDashboardPage` | metering table, invoice lines, tenant card grid, provisioning stepper | dashboard specs |
| `ShareLinkPage` | read-only viewer, expired/invalid message | launch/share specs |

**POM rules (per the skill):** stable role/label-based locators only — no CSS `nth-child` chains; every method wraps auto-waiting assertions (`await expect(...).toBeVisible()`), never `waitForTimeout`; components (e.g., `NavigationComponent`) compose into pages.

---

## 5. Auth & Persona Fixtures

Persona storage states are produced once by `auth.setup.ts` and reused by project configs (no per-test login):

| Persona | storageState | Used by |
| :--- | :--- | :--- |
| Radiologist (`PAC-P01`) | `fixtures/.auth/radiologist.json` | worklist, viewer, cross-cutting |
| Technologist (`PAC-P02`) | `fixtures/.auth/technologist.json` | acquisition specs |
| PACS Admin (`PAC-P04`) | `fixtures/.auth/pacs-admin.json` | admin console, audit |
| Tenant Admin (`PAC-P19`) | `fixtures/.auth/tenant-admin.json` | dashboards |
| Super Admin (`PAC-P20`) | `fixtures/.auth/super-admin.json` | provisioning, cross-tenant grant UI |
| Referring MD (`PAC-P06`) | `fixtures/.auth/referring.json` | launch/share, mobile |

**Role-gate specs:** for each restricted screen, verify a *lower-privilege* persona sees the access-denied state — e.g., technologist cannot open the admin console (`getByRole('alert')` = "Access denied"), matching `RBAC_matrix_spec.md` endpoint→permission map and PAC-AC-P19-02 token-version bump (a role change mid-session invalidates the old token → forced re-login assertion).

---

## 6. Network Mocking & Data Strategy

- **Route interception for deterministic UIs:** specs that exercise UI logic (pagination, filters, queue depth, quota colors) use `page.route('**/api/qido/**', …)` / `page.route('**/api/interface/health/**', …)` with fixture JSON — per the skill's mock pattern. Real end-to-end contract specs (`@contract`) run against the staging tenant with the live API.
- **Deterministic DICOM sets:** the conformance-lab sets from `qa_test_strategy.md` §8 (`fx_conformance_*`) are served by the staging harness; viewer specs assert progressive first-frame, not full download.
- **Per-test isolation:** each spec provisions/disposes a disposable test tenant via API (`POST /api/tenants` from `auth.setup` super-admin state) so parallel workers never share state; unique names via `Date.now()` suffix (parallel-safe pattern).
- **PHI hygiene:** synthetic conformance-lab demographics only; specs assert **no PHI in URLs** (share/launch links are UID/key-based — `PAC-UI-39/41`) and **no PHI persisted in localStorage** on shared devices (`PAC-UI-43`).

---

## 7. CI Wiring & Tags

| Gate | Command | Fails when |
| :--- | :--- | :--- |
| PR (UI smoke) | `npx playwright test --grep @smoke` | any smoke spec fails |
| Nightly | `npx playwright test` (full, chromium + firefox) | any functional/a11y regression; visual drift over threshold |
| Pre-release (Sprint 7) | full suite all projects + `--grep @critical` as the gate | any G3/G4/G5/G6/G7 UI evidence missing |
| Quarterly | `npx playwright test --grep @visual` + mobile project | visual/regression drift on dashboards |

Sharding in CI: `npx playwright test --shard=1/4 … 4/4`; `forbidOnly` + `retries: 2` on CI; HTML report + trace artifacts uploaded on failure. Cross-browser coverage is mandatory for **smoke + critical** (chromium/firefox/webkit); full functional coverage runs chromium.

---

## 8. Coverage Targets

| Scope | Target | Note |
| :--- | :-: | :--- |
| MVP-scope PAC-UI-* (M priority) | **100%** have a named spec | Every row in §3.1–3.8 |
| Desired (D) / Optional (O) | spec exists, tagged `desired` / `optional` | Not gate-blocking |
| WCAG AA (PAC-UI-05) | axe-core scan on all screens, 0 serious/critical violations | `@a11y` tag |
| Gate screens (G3/G4/G5/G6/G7) | every gate criterion with a UI manifestation has a spec | Traceability §9 |
| `@smoke` | login → worklist → viewer first-frame → admin console, one flow per surface | PR gate |

---

## 9. Traceability — Gates → Specs (mirrors go-live-checklist.md + qa_test_strategy.md §7)

| Gate | Criterion (release plan §2) | UI specs (this plan) | API specs (qa_test_strategy §7) |
| :-: | :--- | :--- | :--- |
| **G1** | Ingestion < 5 min; SC 100%; 0 silent purges | T-UI-23, T-UI-25 | T-PAC-AC-P02-02/02b/03/05, T-SL-20/15 |
| **G2** | MWL ≥ 98%; MPPS drives status | T-UI-23 (status panel) | T-PAC-AC-P02-01/01b/04/04b, T-SL-14 |
| **G3** | Study opens < 3 s p95; progressive on multi-GB; never blank | T-UI-14/19/20 (blocking), T-UI-01 (blocking); T-UI-12 (desired, non-blocking) | T-PAC-AC-P01-08/10, T-SL-10/11/16/17 |
| **G4** | Retention/legal-hold honored; quota 75/90% | T-UI-29, T-UI-30 | T-PAC-AC-P04-03/04, T-SL-43/45 |
| **G5** | Interface delivery > 99.9%; alerts ≤ 5 min | T-UI-28 | T-PAC-AC-P04-05/08, T-SL-23 |
| **G6** | Provision < 15 min; RLS verified; 100% audit; cross-tenant denied | T-UI-32, T-UI-36/37, T-UI-41 | T-PAC-AC-P20-01/02/03, T-SL-50/51/60/61 |
| **G7** | No P0/P1 defects; UAT sign-off (3 personas) | UAT pack = full `@critical` + per-persona scripted runs of §3.1/3.3/3.4 | full pytest suite green |

**UAT equivalence:** the per-persona sign-off flows in `sprint7_hardening_detail.md` (S7-01…S7-05) run **these specs as their automated backbone** — radiologist (worklist→viewer→critical flag→key images), technologist (ingest→SC), PACS admin (registry→queue→retention→audit).

---

## 10. Adoption Plan

| When | What lands | Evidence |
| :--- | :--- | :--- |
| Sprint 1 (platform) | `auth.setup.ts` persona states, LoginPage, role-gate denial specs; T-UI-37 provisioning stepper | G6 pre-check UI |
| Sprint 2–3 (ingestion/archive) | AcquisitionStatusPage, T-UI-23/25 SC confirmation; admin console shell | G1/G2/G4 pre-check UI |
| Sprint 4 (DICOMweb/viewer) | WorklistPage, ViewerPage, HangingProtocols, T-UI-08…22, T-UI-01 progressive | G3 pre-check UI |
| Sprint 5 (admin/monitoring) | ModalityRegistry, QueueMonitor, StorageDashboard, RetentionEditor, ExceptionWorklist, AuditViewer; T-UI-26…32 | G4/G5 pre-check UI |
| Sprint 6 (dashboards/DR) | TenantOpsDashboardPage, T-UI-34…38; mobile launch/share T-UI-39…43 | G6 pre-check UI |
| Sprint 7 (hardening) | full cross-browser suite + `@a11y` + `@visual`; UAT pack runs §3 specs per persona | G1–G7 UI evidence, go/no-go |

---

## Traceability

| Section | Source |
| :--- | :--- |
| §3 spec catalog | `PACS/04_uiux_requirements.md` (PAC-UI-*), `PACS/06_acceptance_criteria.md` (PAC-AC-*) |
| §3 gates | `pacs_consolidated_sprint_roadmap.md` §4; `PACS/RELEASE_PLAN.md` §2 |
| §5 personas / RBAC | `requrements/RBAC_matrix_spec.md` §4–§6; `docs/specs/auth_design.md` |
| §6 data strategy | `qa_test_strategy.md` §8; `research/pacs-ris-viewer-integration-spec.md` |
| §9 gate traceability | `PACS/go-live-checklist.md` §3; `qa_test_strategy.md` §7 |
| §10 adoption | `pacs_consolidated_sprint_roadmap.md` §2/§5 |
