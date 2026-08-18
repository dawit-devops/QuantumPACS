Multi-agent team review finding

 Reviewer-1 (Frontend) — Skill-Harnessing Review Findings

**Target**: QuantumPACS `frontend/src/**` (branch `v3-dev`, commit `d4abc25`)
**Stack**: React 19.2.8, antd 6.5.1, react-router 8.3.0, Cornerstone3D 5.6.10, Vite 8.1.5, TS 6.0.3, Vitest 4.1.10
**Skills applied**: frontend-react-best-practices (33 rules: bundle/perf/re-render/state) + web-design-guidelines (accessibility: aria-labels, labeled controls, focus, headings, skip link, color-scheme, reduced motion, form semantics)
**Mode**: read-only review — no code modified

---

## Severity Summary

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High     | 5 |
| Medium   | 10 |
| Low      | 9 |
| **Total** | **24** |

---

## HIGH — Must Fix

### H1. Notification bell is not keyboard/screen-reader accessible
**Location**: `frontend/src/notifications/NotificationBell.tsx:155-158, 202`
**Skill**: web-design-guidelines — icon-only buttons need aria-label; interactive elements need keyboard handlers

`<BellOutlined onClick={...}>` renders a bare span with click handler — no role, no tabindex, no aria-label, invisible to keyboard and screen readers. It lives in the Sidebar menu (always mounted for every user) that keyboard users navigate via the Menu — the bell is never reachable. Drawer list items are `List.Item onClick` divs (line 202) — also not keyboard-navigable.

**Fix**: wrap in `Button type="text" icon={<BellOutlined />} aria-label="Notifications" />`, and make list items real buttons (or use `Menu` items) so keyboard + enter works.

### H2. Viewer re-renders the full 974-line component on every rendered frame
**Location**: `frontend/src/detail/CornerstoneElement.tsx:222-234, 508`
**Skill**: frontend-react-best-practices (rerender-use-ref-transient-values, render churn)

`setZoom/setWw/setWc` are called from the `EVENTS.IMAGE_RENDERED` subscription — one setState per displayed frame during window-level drag, stack scrolling, and cine. Each setState re-renders the entire component (toolbar, sliders, overlays, keyboard bindings). Cine and WL drag are the hottest interaction paths in a PACS viewer.

**Fix**: write transient overlay values straight to ref'd DOM nodes (skip React state), or throttle with `requestAnimationFrame` and only `setState` when the value actually changed.

### H3. Dark-mode flash (FOUC) on every load
**Location**: `frontend/src/common/ThemeProvider.tsx:44-46`
**Skill**: web-design-guidelines (color-scheme dark) / rendering-hydration-no-flicker (react-best-practices R1 family)

`document.documentElement.setAttribute("data-theme", theme)` runs in `useEffect` — after first paint. Dark-mode users see a light flash on every page load. No `color-scheme` CSS property exists anywhere in `frontend/src` (grep: zero matches), so native scrollbars/inputs/theme-color also stay light in dark mode.

**Fix**: inline boot script in `index.html` `<head>`: read `localStorage.theme` + `matchMedia('(prefers-color-scheme: dark)')`, set `data-theme` before hydration; add `color-scheme: dark` under `[data-theme="dark"]` in `tokens.css`.

### H4. Skip link renders but its target is missing on the most-used pages
**Location**: `frontend/src/common/base.tsx:29-30` (link) vs `frontend/src/files/Files.tsx:510`, `frontend/src/detail/Detail.tsx:210`
**Skill**: web-design-guidelines — skip link on all pages, target must exist

`<a href="#main-content">Skip to content</a>` is rendered by the shared `base.tsx` wrapper on every page, but only 12 of ~24 route surfaces define `id="main-content"` (grep confirmed: Files, Detail, Account, Metrics, Logs, Login, Portal desktop, Registration, etc. are missing it). On core pages the skip link is a no-op dead anchor.

**Fix**: put `id="main-content"` once in the shared wrapper (`base.tsx` `Comp` container or `MainLayout` content div) instead of per-page — single point of truth.

### H5. Study cards on mobile navigate via non-interactive div onClick
**Location**: `frontend/src/files/Files.tsx:593`
**Skill**: web-design-guidelines — navigation must use real links: `<a>`/`<Link>` (keyboard, Cmd/Ctrl+click, middle click, screen reader)

`<Card onClick={() => navigate(\`/files/${item.id}\`)}>` on the mobile branch — no role, no keyboard access, no link semantics, middle-click breaks.

**Fix**: wrap title in `<Link to={/files/${id}}>` or make the card an antd Card with `actions` containing a real button/link.

---

## MEDIUM — Should Fix

### M1. Empty-href anchors used as action buttons
**Location**: `frontend/src/detail/Detail.tsx:167-171, 185-189`
**Skill**: web-design-guidelines (buttons for actions; no `href=""`)

`<a href="" onClick={() => ...}>` in the study/series breadcrumb dropdowns. `href=""` is itself a navigation (reload current URL); an `<a>` with no href alternative is not focusable. Use `Button type="text"` or `Menu items` with `onClick`.

### M2. Login form controls have no accessible labels
**Location**: `frontend/src/Login.tsx` — see `frontend/src/login/Login.tsx:225-237, 258-269`
**Skill**: web-design-guidelines (WCAG 1.3.1: visible or aria-hidden labels on all inputs; placeholder is not a label)

`Form.Item name="username"` with no `label` prop and no `aria-label` — the only non-placeholder hint is the `Form.Item` name text drawn by antd (a label-less pseudo-label), and placeholder text vanishes on focus. Screen readers announce nothing.

**Fix**: `label="Username"` with `labelCol`/visually-hidden style, or `aria-label` on the `Input`.

### M3. In-place mutation of state rows
**Location**: `frontend/src/files/Files.tsx:393-416`
**Skill**: frontend-react-best-practices (functional updates, immutable updates of state)

`advancedFields[i][0] = "patientId"; setAdvancedFields([...advancedFields])` mutates the row objects in place inside all three `onAdvancedSearchChange*` handlers. If a memoized child keyed on `advancedFields` ref-equality existed it would miss the change; also violates React immutability contract.

**Fix**: `setAdvancedFields(prev => prev.map((f, j) => j === i ? [key, value] : f))`.

### M4. Derived state computed inside effects
**Location**: `frontend/src/detail/KeyValueTable.tsx:36-49`
**Skill**: frontend-react-best-practices (rerender-derived-state-no-effect)

`metaToDatasource()` + `filterKey` are applied in two `useEffect`s that `setDataSources` — double render pass, duplicate computation (`metaToDatasource()` called in both), and the file-apply effect also does `setSearchValue("")` (line 44) which resets user search on every new file. `react-hooks/exhaustive-deps` disabled at 39 and 48 to tolerate this.

**Fix**: `const rows = useMemo(() => filter(metaToDatasource(), search), [file, search])` — derive in render, no effects.

### M5. Slider is both controlled and uncontrolled
**Location**: `frontend/src/detail/CornerstoneElement.tsx:753-760`
**Skill**: frontend-react-best-practices (rerender-derived-state; antd warns on value+defaultValue)

`<Slider value={zoom} defaultValue={zoom} ...>` — antd emits a dev warning and behavior is ambiguous. Pass only `value` (parent owns `zoom` via `changeFile`).

### M6. Mobile worklist renders up to 100 cards with a stagger animation, no virtualization
**Location**: `frontend/src/files/Files.tsx:585-637`; `frontend/src/index.css:206-209`
**Skill**: web-design-guidelines (lists >50: virtualize or content-visibility); react-best-practices (render churn)

Desktop uses antd `Table` with pagination (20/page); the mobile branch renders ALL results (up to `QIDO_RESULT_CAP = 100`) as Cards — DOM scope visible ("Viewing 1–X of Y", the map is unconditional), every one with `.stagger-enter` + `animation-delay` up to 3s, re-triggered on every data change. This is a multi-second animation storm on each search.

**Fix**: paginate or virtualize on mobile; drop the per-row stagger (animate the container once).

### M7. Heading hierarchy broken on core pages
**Location**: `frontend/src/files/Portal.tsx:191` (h2 "My Records" with no h1), `frontend/src/frontdesk/WaitingQueue.tsx:61` (h2 with no h1), Files/Detail have no page headings at all
**Skill**: web-design-guidelines (headings strictly hierarchical h1-h6; never skip levels)

Pages start at h2 (Portal, WaitingQueue) or expose heading-less tables (Files, Detail). Screen-reader page summaries have no top-level landmark.

**Fix**: single h1 per page (reuse `PageHeader` pattern used on admin surfaces).

### M8. Test-only demo usernames shipped in production login UI
**Location**: `frontend/src/login/Login.tsx:30, 239-246`
**Skill**: web-design-guidelines (no dev artifacts in prod); security hygiene

`demoUsernames` datalist renders `test.*` accounts in the prod bundle — advertises the test-account surface, and `LOGIN_RETRY_KEY` backoff data persists in localStorage (fine) but the datalist itself is a prod leak.

**Fix**: gate the datalist on `import.meta.env.DEV`.

### M9. Thumbnail strip listbox role without keyboard list semantics
**Location**: `frontend/src/detail/ThumbnailStrip.tsx:19-33, 92-100`
**Skill**: web-design-guidelines (listbox requires arrow-key roving tabindex)

`role="listbox"` on a container of `role="option"` buttons that rely on natural tab order — screen readers announce a listbox but there is no arrow-key navigation contract (Read W3C listbox pattern). Feels like a listbox but behaves like a plain group.

**Fix**: either drop the listbox role (plain tab order, add `aria-label`) or implement roving tabindex + arrow keys.

### M10. Low coverage thresholds for a HIPAA-adjacent product
**Location**: `frontend/vite.config.js:148-153` (`test: { coverage: { thresholds: { lines: 42, functions: 32, ... } } }` — verify exact numbers)
**Skill**: frontend-react-best-practices / testing expectation for regulated domain

Sub-50% line/function gates on a PACS with PHI. Fine for internal velocity, too loose for release gates on a medical product.

**Fix**: raise thresholds progressively and require coverage on auth/route-gate modules (tests already exist and are good).

---

## LOW — Track in Backlog

### L1. Dead async wrapper
`frontend/src/detail/useReadingPresets.ts:104-109` — `applyWl` is `async` and always returns early after `if (!applyPresetToViewport(...)) return;`. Remove `async`/dead `await` path (Lint rule about floating promises is being papered over).

### L2. Interval recreated every tick
`frontend/src/login/Login.tsx:152-160` — lockout countdown effect depends on `lockoutSeconds`, re-creating `setInterval` every second. Derive from a single timestamp instead.

### L3. Dead code
`frontend/src/login/Login.tsx:132` — unused `errorRef`.

### L4. useFetch mutates caller's options object
`frontend/src/api/useFetch.ts:42-51` — `exec` replaces `options.headers` on the caller's object each call; a shared `options` reused across calls loses custom headers; also `exec` is a new closure every render. Make headers merged internally, cache `exec` in `useCallback`/ref.

### L5. Document-level viewer shortcuts leak into other focus contexts
`frontend/src/detail/CornerstoneElement.tsx:332-468` — keydown handlers guard only `INPUT/TEXTAREA/contentEditable`; a focused antd `Select`/`Drawer`/`Collapse` button still triggers viewer hotkeys (e.g. "s" → persist). Constrain via `document.activeElement` containment check.

### L6. Viewport element min-width squeezes small windows
`frontend/src/detail/CornerstoneElement.css:25-30` — `.viewportElement { min-width: 700px }` at `@media (min-width: 768px)` → horizontal overflow in 768–992px viewports (zero-width sider range). Prefer `flex-basis`/percentage without hard min.

### L7. PWA precache vs 6MB cap
`frontend/vite.config.js:27-30` — workbox `globPatterns` with `maximumFileSizeToCacheInBytes: 6MB`; vendor-cornerstone chunk likely exceeds → viewer chunk never precached. Also `chunkSizeWarningLimit: 1200` (line 34) masks the big-chunk warning. Verified offline-capability briefly — PWA installs, but stale-SW and cache-cap behavior should be re-tested after chunking (known gotcha per CLAUDE.md "PWA service worker cache").

### L8. Inline arrow in prop position
`frontend/src/index.tsx` OnboardingTour `onComplete={() => {}}` — new function identity per render defeats any memo on the child (minor).

### L9. Global focus-visible outline is the only focus cue
`frontend/src/index.css:85` — `:focus-visible` outline exists; custom interactive rows (`.fd-queue-item`, `.fd-slot`, `.thumbnail-item`, `.schedule-block` — `:hover` only in their CSS) rely on it. Add `.focus-visible` on the few custom clickable cards, and `outline-offset` for the skip link (present).

---

## Strengths Verified (keep as-is)

- Route gating is layered and tested: `ProtectedRoute` → `PermissionRoute` (shared gate sets `VIEWER_ROUTE_PERMISSIONS` etc. imported by both app and `src/test/route-gates.test.tsx`) plus `ClinicalRoute` excluding admin-scoped role slugs; sidebar items gated by the same constants. Consistent across desktop sidebar, mobile nav, and route table.
- Bundle hygiene: route-level `React.lazy` for every page + `React.lazy` CornerstoneElement; manual chunk split `vendor-react` / `vendor-antd` / `vendor-cornerstone`.
- `QIDO_RESULT_CAP = 100` hard cap on worklist fetches; desktop table paginated.
- IntersectionObserver lazy thumbnail loading (`ThumbnailStrip.tsx`); refs-pattern hooks (`useTenantRefetch` R1-06, `useVisibilityGatedInterval` — polling pauses when hidden).
- Single module-level WebSocket w/ capped exponential reconnect (`ws.ts`), event-dispatch subscription pattern via CustomEvents.
- PHI projection: `WaitingQueue` renders initials + MRN last-4 only; client clip: `comment` sanitized to 240 chars (`api/client.ts` `sanitizeMessage`).
- 3-layer design tokens (primitive/semantic/component) + `data-theme` dark mode; `prefers-reduced-motion` honored (index.css:95, TechnologistWorklist.css:49).
- Accessibility spot-good: MobileToolbar `role="toolbar"` + aria-label, HelpButton aria-label, viewer overlay `aria-live` zoom/ww readout, global `:focus-visible` outline, `touch-action: manipulation` (mobile tap zoom), `overscroll-behavior: none`.
- Session security: access token in localStorage only, refresh token in HttpOnly cookie (`session.ts`), 25-min refresh timer with single-flight `refreshPromise`.

---

## Top 10 (by product impact)

1. **H2** per-frame re-render in viewer (WL/cine) — CornerstoneElement.tsx:222
2. **H1** notification bell keyboard-dead — NotificationBell.tsx:155
3. **H4** skip link dead on Files/Detail — base.tsx:30
4. **H3** dark-mode FOUC + missing color-scheme — ThemeProvider.tsx:44
5. **M6** mobile 100-card stagger animation storm — Files.tsx:585
6. **M5** controlled+uncontrolled Slider — CornerstoneElement.tsx:753
7. **M4** derived state via effects (search clobbered on file switch) — KeyValueTable.tsx:36
8. **M3** state row mutation — Files.tsx:393
9. **H5** div-navigation on mobile cards — Files.tsx:593
10. **M7** broken heading hierarchy — Portal.tsx:191 / WaitingQueue.tsx:61

*Fix effort: H2,M6,M5 = medium; all others small. Recommend bundling H1+H5+H3 (a11y + theme) and H4+M7 (page shell) into two PR-sized batches.*
Thought: 1.8s
The findings file is written. Now I need to return the compact summary ≤40 lines with severity counts + 10 most impactful findings, per my task instructions ("return a compact summary ≤40 lines: counts by severity + 10 most impactful findings with file:line + one-line fixes"). The full report is in /tmp/opencode/skill-review/reviewer-1-frontend.md.
Review complete. Full findings written to /tmp/opencode/skill-review/reviewer-1-frontend.md (24 findings: 5 High / 10 Medium / 9 Low, zero Critical). No code modified.
Severity counts: Critical 0 · High 5 · Medium 10 · Low 9
Top 10 most impactful findings:
H2 — CornerstoneElement.tsx:222 re-renders the whole 974-line viewer setZoom/setWw/setWc on every IMAGE_RENDERED frame (WL drag/cine hot path). Fix: write overlays to ref'd DOM or rAF-throttle setState.
H1 — NotificationBell.tsx:155 bell is a bare <BellOutlined onClick> span — no role/tabindex/aria-label; drawer items are onClick divs (202). Keyboard + screen-reader dead end in the always-mounted sidebar. Fix: Button text + aria-label; list items as real buttons.
H4 — base.tsx:30 renders "Skip to content" on every page but only 12/24 surfaces define id="main-content" — dead anchor on Files/Detail/Account. Fix: one id in the shared wrapper.
H3 — ThemeProvider.tsx:44 sets data-theme in useEffect → light flash for dark users on every load; zero color-scheme anywhere. Fix: inline boot script in index.html head.
M6 — Files.tsx:585 mobile branch renders up to 100 cards with per-row stagger-enter animation (index.css:206) re-triggered on each search — animation storm. Fix: paginate/virtualize mobile list; animate container once.
M5 — CornerstoneElement.tsx:753 Slider gets both value and defaultValue — controlled+uncontrolled warning. Fix: pass only value.
M4 — KeyValueTable.tsx:36-49 derives dataSource in two effects — double render, and line 44 resets user search on every file switch; exhaustive-deps disabled x2. Fix: useMemo derive-in-render.
M3 — Files.tsx:393-416 mutates advancedFields[i][0] before setState in all three search handlers. Fix: functional prev.map.
H5 — Files.tsx:593 mobile Card onClick navigate — no keyboard/link semantics, middle-click broken. Fix: wrap title in Link.
M7 — Heading hierarchy: Portal.tsx:191 and WaitingQueue.tsx:61 start at h2; Files/Detail have no page h1. Fix: reuse PageHeader h1 pattern on all surfaces.
Strengths (no change needed): layered gating (ProtectedRoute → PermissionRoute w/ shared gate sets + ClinicalRoute role exclusion) mirrored in route-gates tests; lazy routes + lazy viewer + vendor manualChunks; QIDO_RESULT_CAP=100; IntersectionObserver thumbnails; refs-pattern hooks (useTenantRefetch/useVisibilityGatedInterval); single shared WS with capped reconnect; PHI projection (initials+MRN last-4, 240-char comment cap); 3-layer tokens; prefers-reduced-motion honored; HttpOnly refresh cookie + 25-min single-flight refresh.
Two fixed-price batches for the parent: (a) a11y+theme: H1, H3, H4, H5, M1, M2, M7, M9, M10; (b) render-path perf: H2, M3, M4, M5, M6, L1, L2.
	
	# Reviewer-2 — Auth / IAM / OAuth Review — QuantumPACS

**Commit**: d4abc25 (v3-dev) · **Role**: reviewer-2 (skill-harnessing: auth0, iam-audit, oauth)
**Severity counts**: Critical 0 · High 7 · Medium 9 · Low 8 (total 24)

Positive controls confirmed first:
- `config.local.yaml` exists with non-default `secret`/`superadmin_pass`, is gitignored (`/backend/config.local.yaml`) and untracked (verified via `git check-ignore` / `git ls-files`). Good.
- PKCE S256 + one-time Redis state (300s TTL, deleted on consume, bound to `provider_id`) — oauth.py:58-86.
- `token_version` bumps on deactivate/reset/role change (db/users.py:183-219); refresh re-reads DB rows (users.py:348-377).
- API keys: SHA-256 hash, prefix lookup, expiry + `enabled` revoke (db/api_keys.py:73-91); raw key shown once.
- X-Tenant-ID gated by `can_access_tenant` (permission + explicit grant) with cross-tenant audit (auth.py:28-50, tenant_middleware.py:57-87).

---

## HIGH

### H1 — Refresh tokens are valid bearer credentials for every endpoint (14 days)
- **Location**: backend/api/tokens.py:162-169 (`verify_token`), consumed at backend/api/auth.py:268 and auth.py:296 (WS)
- **Skill**: auth0/pattern-token-handling — access vs refresh separation
- **Current**: `verify_token()` only requires `exp`; nothing rejects `type == 'refresh'`. Refresh tokens (14-day, include `admin` claim) pass TokenAuth for all HTTP + WS paths — the 1-hour access design is bypassed entirely.
- **Fix**:
```python
def verify_token(token):
    data = _decode_any(token, {'require': ['exp'], 'verify_exp': True})
    if data.get('type') == 'refresh':
        raise _jwt.InvalidTokenError('Refresh token is not an access token')
    return data
```

### H2 — `auto_provision=False` is ignored — SSO users are always JIT-provisioned
- **Location**: backend/api/oauth.py:136-176 (`_find_or_create_user`), schema backend/api/schemas/oauth_providers.py:13
- **Skill**: iam-audit — lifecycle / joiner controls; OAuth least privilege
- **Current**: The `auto_provision` column/flag is never read. Providers configured with `auto_provision=False` (intended: logins only for pre-provisioned accounts) still silently create users.
- **Fix**: in `oauth_callback` before `_find_or_create_user`: `if provider.get('auto_provision') is False and not user_exists: return api_error('ACCOUNT_UNKNOWN', 'No account linked to this identity', 403)`

### H3 — JIT-provisioned users get a clinical/billing role by default (least privilege failure)
- **Location**: backend/api/oauth.py:147 (`role_slug = provider.get('default_role') or config.get('oauth_default_role', 'cashier')`); schemas/oauth_providers.py:17 (default `'cashier'`); config.py:46 (default `'radiologist'` — the *more* privileged default when the DB row has no default_role)
- **Skill**: iam-audit — "Privileged access is JIT, not standing"; default-deny; per-tenant isolation
- **Current**: A self-registering SSO identity is granted `cashier` = biller = `BILLING_READ/BILLING_WRITE`, `REPORT_READ`, `CHART_READ`, `RESULTS_READ`, `PATIENT_READ`. Config default `'radiologist'` is worse (`REPORT_SIGN`, `STUDY_EXPORT`, `CROSS_TENANT_READ`). Three default sources disagree (schema/DB/config). No email domain allowlist, no tenant scoping.
- **Fix**: Default to a restricted role (e.g. `patient`/`PORTAL_READ` or `None` → no role) and fail closed: `role_slug = provider.get('default_role') or 'patient'`; remove the `'radiologist'` config default; add per-provider `allowed_email_domains`.

### H4 — Token blocklist is fail-open: revocation silently no-ops when Redis is down
- **Location**: backend/api/tokens.py:41-49, 88-108; consumed auth.py:273 (`is_blocked`)
- **Skill**: auth0 debug-rate-limit/pattern — revocation must fail closed for auth decisions
- **Current**: Redis outage → `_get_blocklist_redis()` returns None → `is_blocked` returns False (also on any exception). Logout/`RevokeToken` become no-ops with only a throttled log line; stolen tokens stay valid for their full lifetime (14d refresh).
- **Fix**: Make `is_blocked` fail-*closed* for a bounded outage window (local denylist cache with TTL), or surface a 503 `auth_unavailable` when the blocklist backend is confirmed down; at minimum persist a last-connection-time and refuse token acceptance after N seconds of Redis unavailability.

### H5 — OAuth login mints a 14-day access token; no refresh token issued
- **Location**: backend/api/oauth.py:307-322 (`create_token(...)` without expire → tokens.py:66-67 default `{'days': 14}`)
- **Skill**: iam-audit — session lifetime appropriate to sensitivity; OAuth token lifetimes
- **Current**: The SSO cookie/JSON token is a 14-day bearer credential vs. 1-hour access tokens in the password flow; no rotation mechanism exists for it (every 14 days a silent re-run of the whole IdP flow).
- **Fix**: `create_token(..., expire={'hours': 1})` + `create_token_pair(...)` with a rotated refresh token (cookie `secure=True`), mirroring Login.

### H6 — Logout cannot revoke the refresh token (cookie path mismatch)
- **Location**: backend/api/users.py:190-195 vs cookie set at users.py:142-149
- **Skill**: oauth/session handling — logout must kill the session server-side
- **Current**: `refresh_token` cookie is scoped `path='/api/auth/refresh'`; `Logout` (at `/api/auth/logout`) never receives that cookie, so `request.cookies.get('refresh_token')` is always None from browsers — the server-side blocklist entry is never written for browser sessions. The (unrevoked) refresh token remains usable if exfiltrated.
- **Fix**: On logout read the refresh token from the body/header fallback too, or set the cookie at `path='/api'` and restrict rotation instead; also `block_token` the refresh token when the client supplies it via body.

### H7 — OAuth callback token cookie missing `secure=True` (inconsistent with Login)
- **Location**: backend/api/oauth.py:322 vs backend/api/users.py:137 (secure=True)
- **Skill**: auth0/pattern-token-handling — HttpOnly+Secure+SameSite for cookies
- **Current**: `resp.set_cookie('token', ..., httponly=True, samesite='strict', path='/api')` — no `secure` flag. On any non-localhost HTTP deployment (Vite advertises `0.0.0.0` LAN access) the bearer token cookie transits cleartext with no Secure.

---

## MEDIUM

### M1 — Provider `enabled` flag is not enforced at login/callback
- **Locations**: backend/api/db/oauth_providers.py:60-73 (`get_by_slug` — no enabled filter) + oauth.py:205-224, 260-272
- Only the *public list* filters `enabled` (oauth_providers.py:37). A disabled provider remains fully usable via `?idp=<slug>` and via its stored `provider_id` in state. Fix: check `provider.get('enabled', True)` in both `oauth_login` and `oauth_callback` → 403.

### M2 — Role create/update lacks permission-subset validation (inconsistent with users/_can_assign_role and api_keys)
- **Locations**: backend/api/roles.py:24-47 (post), 60-93 (put), 95-117 (delete)
- Any `ROLE_WRITE` holder (tenant_admin) can store arbitrary permission lists — including codes they don't hold, unknown codes, or `ADMIN` — on custom roles; `put` can add permissions to an existing custom role with no cap (defense in depth is only at *assignment* for non-admins via users.py:40-53). Fix: validate `Permission` membership + subset-of-caller in `RolesHandler.post`/`RoleHandler.put`.

### M3 — Single app secret protects three different secrets domains
- **Locations**: backend/api/tokens.py:145-147 (HS256 fallback key), backend/api/encryption.py:15-23 (Fernet derived from `oauth_secret_encryption_key` *or* `config['secret']`), jwt_keys.py (separate RSA PEM)
- One compromised secret (e.g. `SECRET` env leak) yields both unlimited HS256 token forgery *and* the ability to decrypt every stored OAuth client_secret. Fix: require distinct `oauth_secret_encryption_key` (fail closed when absent — not silently derive), and plan HS256 fallback removal once the rotation window closes.

### M4 — No `nonce` in the authorization request or id_token check
- **Locations**: backend/api/oauth.py:231-241 (params — PKCE `code_challenge` present, `nonce` absent), _verify_id_token oauth.py:119-123
- OIDC Core recommends nonce binding for code flow to kill callback-CSRF/auth-injection beyond state. Add `nonce` to the authorization URL and require+verify it from the id_token.

### M5 — OIDC discovery document over-claims what this server is
- **Locations**: backend/api/oauth.py:179-202
- Advertises `issuer: {base}/api`, HS256+RS256 id_token algs (OIDC anti-pattern for symmetric algs without secret-bound keys), but minted tokens carry **no `iss`/`aud`/`typ` claims** (tokens.py:52-79) — third-party RPs cannot validate them against the advertised issuer; `userinfo_endpoint`/`end_session_endpoint` absent. Either mint full OIDC-conforming tokens (add `iss`, `aud`, `iat`, `typ:'at+jwt'`) or remove the public discovery doc.

### M6 — Unbounded request bodies on unauthenticated endpoints (memory exhaustion)
- **Locations**: backend/api/schemas/auth.py:4-6 (`LoginRequest` — no max_length), parse_body → `request.json()` (validate.py:13) with no body size cap anywhere in middleware
- 2 GB JSON body to `/api/login` or `/api/oauth/token` buffers fully in memory. Fix: `password: str = Field(max_length=512)`, `username: str = Field(max_length=255)` + enforce a global body limit (e.g. `request.stream()` wrapper or uvicorn `h11_max_incomplete_event_size`/proxy).

### M7 — `groups_claim` is dead code; no group→role mapping
- **Location**: backend/api/oauth.py:143-145 — groups are fetched (as `user.get('groups')`, never written to DB at provision: line 159-161 writes no groups column) and never evaluated. If groups are meant to drive role/tenant assignment, implement it; otherwise remove to avoid false security assumptions.

### M8 — `assert_production_secret()` does not cover `db_password` default
- **Location**: backend/config.py:8 (`'pa55w0rd'`), 115-125
- The known default DB password is never asserted; a prod deployment inheriting `db_password: pa55w0rd` (default_config) boots fine. Fix: reject `_DEFAULT_DB_PASSWORD` in `assert_production_secret()`.

### M9 — Refresh-token grant on `/api/oauth/token` has no client authentication or rate limit
- **Location**: backend/api/oauth.py:326-379
- RFC 6749 §6 recommends authenticating the client on refresh; the endpoint is public (auth.py:187) and un-throttled. Add rate limiting (IP-based, like login_bucket) and rotate/deny refresh tokens minted for body use when presented from unknown origins.

---

## LOW

1. **RSA key rotation** — backend/api/jwt_keys.py:27-68: single static PEM, no key history/exp; regenerating the file invalidates every outstanding token; rotation ads no `x5c`/`exp`. Document a rotation procedure or keep two kids.
2. **Password policy** — backend/api/schemas/account.py:10: only min_length=8; no breach-list or complexity guard (NIST SP 800-63 minimum), no re-prompt/MFA on privileged changes.
3. **RBAC tests are data-only** — backend/tests/test_rbac_matrix.py: pure catalog assertions (lines 40-320); no endpoint-enforcement tests (cashier → 403 on report read), no `can_access_tenant`/grant-row tests, no oauth flow tests (state/verifier/auto_provision enabled=false).
4. **`scope` column in user_tenant_grants ignored** — db/user_tenant_grants.py:50-57 writes `scope` but auth.py:50 `can_access_tenant` never reads it; all cross-tenant access is read/read — enforce or drop the column.
5. **`get_role_permissions` silently falls back to cashier** — backend/api/rbac.py:99-102 / db_auth_service.py:47: unknown/missing role → biller grants in the service authorize path.
6. **`'*'` wildcard honored** — backend/api/rbac.py:40-42: any user whose permissions list contains `'*'` passes every guard; keep only for seeded fixtures, or drop.
7. **Provider URL fields unvalidated** — backend/api/schemas/oauth_providers.py:5-9: `issuer/jwks_uri/token_url/redirect_uri` accept arbitrary strings (admin-only surface, but a typo/SSRF-prone config should be validated with `HttpUrl`).
8. **`decrypt_secret` silently returns ciphertext on failure** — backend/api/encryption.py:61-62: after key change, stored secrets "decrypt" to raw ciphertext which is then sent to the IdP as `client_secret`; log-and-fail instead.
Thought: 580ms
The report is written. Now the compact summary (≤40 lines).
Full report written. Summary:
Reviewer-2 summary — Auth/IAM/OAuth (commit d4abc25)
Counts: Critical 0 · High 7 · Medium 9 · Low 8 (24 total)
Top 10 most impactful findings
backend/api/tokens.py:162-169 (H1, High) — verify_token accepts type=='refresh' tokens as bearer credentials on all HTTP+WS paths (auth.py:268,296); 14-day refresh tokens bypass the 1h-access design. Fix: reject data.get('type') == 'refresh' in verify_token.
backend/api/oauth.py:136-176 (H2, High) — auto_provision=False never read; SSO always JIT-provisions users. Fix: fail 403 when the flag is False and no oauth_sub row exists.
backend/api/oauth.py:147 + config.py:46 (H3, High) — default JIT role 'cashier' (=biller: BILLING_WRITE, REPORT_READ, CHART_READ, RESULTS_READ) over-grants self-registering identities; config default 'radiologist' is worse; three default sources disagree. Fix: default to minimal patient/no-role + per-provider email-domain allowlist.
backend/api/tokens.py:99-108 (H4, High) — blocklist fail-open on Redis outage; logout/revoke silently no-op. Fix: fail closed with a bounded local denylist/503.
backend/api/oauth.py:307-322 (H5, High) — SSO login mints a 14-day access token, no refresh rotation. Fix: expire={'hours':1} + create_token_pair.
backend/api/users.py:190-195 vs 142-149 (H6, High) — refresh cookie scoped to /api/auth/refresh never reaches POST /logout; browser refresh tokens are never blocklisted. Fix: read refresh token from body/header fallback at logout.
backend/api/oauth.py:322 (H7, High) — SSO token cookie missing secure=True (Login sets it); cleartext bearer cookie on LAN/HTTP. Fix: add secure=True (or set COOKIE_SECURE from config).
backend/api/roles.py:24-47,60-93 (M2) — role create/update validates no permission-subset of caller (unlike users.py _can_assign_role); tenant_admin can store arbitrary grants. Fix: subset + enum validation on post/put.
backend/api/oauth.py:205-224,260-272 (M1) — provider enabled flag enforced only on the public listing; disabled IdPs still log in via ?idp=. Fix: check enabled in login + callback.
backend/api/oauth.py:179-202 + tokens.py:52-79 (M5) — discovery advertises issuer {base}/api + HS256 but minted JWTs carry no iss/aud; self-OP contract broken. Fix: add iss/aud/iat to payloads or drop the discovery doc.
Also Medium: single-secret reuse for HS256/Fernet (tokens.py:145, encryption.py:16); no nonce/email_verified check (oauth.py:231,119); unbounded login body (schemas/auth.py:4); db_password default unchecked (config.py:8); refresh grant unauthenticated (oauth.py:326). Low: no key rotation history (jwt_keys.py), policy-only RBAC tests (test_rbac_matrix.py), '*' wildcard honored (rbac.py:40), grant scope ignored (user_tenant_grants.py). Positives: config.local.yaml untracked/gitignored w/ custom secrets; PKCE+one-time state; token_version bumps; key hashing/expiry; X-Tenant-ID double-gated with audit. No code modified.


# Reviewer-3 — API Design & Security Review (QuantumPACS, v3-dev @ d4abc25)

**Reviewer-3 scope:** REST API surfaces (routes, response/validation helpers, schemas), endpoint security across users/files/patients/tenants/roles/notifications/worklist/exams/reports/dicomweb/fhir/hl7/webhooks/api-keys/billing/equipment/portal/frontdesk/telemetry/oauth, middleware (auth dependency usage, CORS, TrustedHost, security headers), error contract, input validation, pagination, rate limiting, secrets/logging hygiene, versioning, OpenAPI accuracy.

**Skills loaded:** `rest-api-design`, `security-fastapi`. Read-only review — no code modified.

---

## Finding Summary

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High     | 6 |
| Medium   | 10 |
| Low      | 6 |
| **Total**| **22** |

---

## HIGH FINDINGS

### H-1. OAuth callback auth cookie missing `secure=True`
- **Location:** `backend/api/oauth.py:365-367`
- **Violation:** security-fastapi (cookie security) / secrets-in-transit hygiene; inconsistent with the login endpoint which sets `secure=True` (`backend/api/users.py:132-139`).
- **Current behavior:** `resp.set_cookie(key='token', value=token, httponly=True, samesite='strict', path='/api')` — no `secure` flag. When deployed behind HTTPS, the OAuth-minted session token cookie is sent over plaintext HTTP, enabling side-channel theft.
- **Fix:**
```python
resp.set_cookie(key='token', value=token, httponly=True, samesite='strict',
                secure=True, path='/api')
```

### H-2. v2 alias builder drops per-route `methods` restrictions
- **Location:** `backend/api/routes.py:331` (and 322-335)
- **Violation:** rest-api-design (HTTP method semantics / versioning consistency). The v1 route uses default `methods=None` handling differently than the explicit `methods=[...]` routes.
- **Current behavior:** `aliases.append(type(r)(_alias_path(r.path), endpoint=r.endpoint))` — the `methods` kwarg is never copied. `/api/v2/oauth/token` (v1 declared `methods=['POST']`, route at routes.py:136) becomes an all-methods route; a plain-function endpoint like `oauth_token_exchange` responds to GET/PUT/DELETE — GET hits `await request.json()` unguarded (`backend/api/oauth.py:345`) → unhandled `JSONDecodeError` → 500 instead of 405. Same for `/api/v2/patients` POST-only and `/api/v2/portal/scope/{id}` DELETE-only routes (routes.py:144, 304).
- **Fix:**
```python
methods = getattr(r, 'methods', None)
if methods is None and isinstance(r, Route):
    # keep HTTPEndpoint-defined methods (that class raises 405 itself)
    kwargs = {}
else:
    kwargs = {'methods': methods}
aliases.append(type(r)(_alias_path(r.path), endpoint=r.endpoint, **kwargs))
```
Also wrap `oauth_token_exchange`'s `await request.json()` in try/except to return 400.

### H-3. Share-link flow has broken/missing positive authorization
- **Location:** `backend/api/auth.py:254-265` + `backend/api/files.py:407,472` (`ServeFile`/`ServeThumbnail` decorate `@requires_permission(Permission.FILE_READ)`)
- **Violation:** security-fastapi (auth dependency coverage), rest-api-design (authorization semantics).
- **Current behavior:** share-viewer sessions (share key in `?token=`, `User` built at auth.py:263 with `id=share-key, permissions=[]`) can *never* pass `requires_permission(FILE_READ)` → every share download returns 403. There is no positive authorization path that grants the share holder access to exactly the shared file (`SharedFiles.check` result is discarded except as a path-prefix matcher). The prefix match `path.startswith(f'/api/files/{file_id}')` (auth.py:262) is also a loose prefix (file id `7` also matches `/api/files/79/...`). Functional break (share links dead) plus an authorization model that silently depends on permission checks that share sessions fail.
- **Fix:** add a dedicated share download endpoint (`GET /api/files/{id}/shared-data`) that authorizes against `SharedFiles.check(token)` and the file id, boundary-validates the token→file mapping (`file_id == int(path id)`), and returns the DICOM payload without requiring FILE_READ.

### H-4. Share duration: schema says seconds, implementation uses hours — unbounded
- **Location:** `backend/api/schemas/files.py:9-10` (docstring "Share link lifetime in seconds") vs `backend/db/share_files.py:33` (`relativedelta(hours=duration)`), create path `backend/api/files.py:432-440`
- **Violation:** rest-api-design (request validation / input bounds), input validation coverage.
- **Current behavior:** `ShareRequest.duration: int` (no `lt`/`gt` bounds). `duration=3600` (a client following the schema's "seconds" contract and wanting 1 hour) produces a **150-day** share. `duration` up to any 32-bit int → effectively permanent shares. Negative/zero → instantly-expired or broken rows. Additionally `ShareFilesHandler.post` never verifies the target file belongs to `effective_tenant(request)` (compare `get_file_by_id`, files.py:336-345) — a `FILE_WRITE` user in tenant A can mint share tokens for tenant B files.
- **Fix:**
```python
class ShareRequest(BaseModel):
    duration: int = Field(ge=60, le=2592000, description="Share lifetime in seconds")
```
and `expires = now + relativedelta(seconds=duration)`; check `_outside_effective_tenant` before `SharedFiles.share`.

### H-5. `POST /api/hl7` has no permission requirement and no input caps
- **Location:** `backend/api/hl7.py:10-14`; route `backend/api/routes.py:208`
- **Violation:** security-fastapi (route-level authz), principle of least privilege.
- **Current behavior:** `Hl7Receiver.post` has no `@requires_permission`; `default_handler(body)` is invoked on the raw body with no size limit and no rate limiting, and the result is stored/persisted (`services/ingestion/hl7_server.py:97-110` stores the message to DB). Any authenticated user of *any* role — including a front-desk or portal-only account — can inject arbitrary HL7 messages (ADT/ORM/ORU) into the ingestion pipeline. CSRF is bypassable by design (constant token, see M-8) and this path is not in the machine-CSRF exemption list either, so it is exposed to browser clients too.
- **Fix:**
```python
class Hl7Receiver(HTTPEndpoint):
    @requires_permission(Permission.HL7_WRITE)
    async def post(self, request):
        body = await request.body()
        if len(body) > 10 * 1024 * 1024:
            return PlainTextResponse(b'ERR: message too large', status_code=413)
        ...
```
plus per-IP rate limiting alongside the MLLP whitelist.

### H-6. WebhookTestHandler SSRF guard is easily bypassable
- **Location:** `backend/api/webhooks.py:87-140`
- **Violation:** SSRF defense (OWASP), input validation.
- **Current behavior:** The private-range check only applies when the URL host is an **IP literal** and the list (webhooks.py:99-105) omits `169.254.0.0/16` (cloud metadata `169.254.169.254`!), `0.0.0.0/8`, `100.64.0.0/10` (CGNAT), `198.18.0.0/15`, `192.0.0.0/24`, `240.0.0.0/4`. Hostnames (e.g. `internal.db`, or a DNS name resolving to an internal IP) raise `ValueError` → `pass` → request proceeds. `httpx.AsyncClient` follows redirects by default → DNS-rebind/redirect pivot. The response body is returned to the caller (up to 500 chars) → internal response exfiltration. SYSTEM_ADMIN-gated, so impact is "compromised-admin/kick-off" — still a real SSRF.
- **Fix:** resolve the hostname (or use `httpx` `follow_redirects=False` + blocking transport) and reject if the *resolved* address is in RFC1918, link-local, loopback, CGNAT, or metadata ranges:
```python
import socket as _socket
try:
    ip = ipaddress.ip_address(host)
except ValueError:
    ip = ipaddress.ip_address(_socket.gethostbyname(host))
private = [ipaddress.ip_network(r) for r in (
    '10.0.0.0/8','172.16.0.0/12','192.168.0.0/16','127.0.0.0/8',
    '169.254.0.0/16','100.64.0.0/10','192.0.0.0/24','198.18.0.0/15',
    '0.0.0.0/8','240.0.0.0/4','::1/128','fe80::/10'])]
if any(ip in net for net in private):
    return api_error('SSRF_BLOCKED', 'Private/reserved address', status=400)
```

---

## MEDIUM FINDINGS

### M-1. Public allowlist inconsistencies: docs/metrics
- **Location:** `backend/api/auth.py:177-198` (`_PUBLIC_PATHS`) vs `backend/api/routes.py:104-109,122-125`
- **Violation:** security-fastapi (public allowlist correctness); OpenAPI accessibility.
- **Current behavior:** `/api/docs` and `/api/docs/openapi.json` are **not** in `_PUBLIC_PATHS` and can only be opened by logged-in users (a browser hitting /api/docs unauthenticated receives a 401 JSON). `/api/metrics` (`routes.py:123`) is protected while `/api/health` is public — whichever is intended for Prometheus/kube probes, the pair is inconsistent. `metrics_endpoint` (telemetry.py:148-151) additionally calls `is_admin` → non-admin authenticated users get a bare 403.
- **Fix:** decide the posture per endpoint and encode it explicitly: add `/api/docs`, `/api/docs/openapi.json`, `/api/v2/docs` to `_PUBLIC_PATHS` (docs are safe, non-PHI), and either make `/api/metrics` public (restrict via `prometheus_enabled` config + network policy) or keep it auth'd but align `/api/health` to the same policy.

### M-2. WebSocket file-channel access control missing
- **Location:** `backend/api/ws.py:151-208` (`on_receive` 'open' / 'send_state')
- **Violation:** security-fastapi (no authz on routes), least privilege; tenant isolation.
- **Current behavior:** any authenticated user can `open` any file channel (`state.local_clients[f]` keyed by client-supplied `data['file']`) and `send_state` (publish viewer state to `channel:file:{f}` via Redis pubsub, ws.py:186-192). No `FILE_READ` check, no tenant check, no file-exists check. Cross-tenant viewer-state leakage and message spoofing (a user can plant fake viewer state into another user's tile). `data['file']` mis-keyed → `KeyError` aborts the socket handler (unhandled).
- **Fix:** on `open`, resolve the file via `get_file_by_id(request-agnostic)` / tenant check; only register the socket after authorization; echo the decision in `on_receive`; wrap `data['file']` access with `.get('file', '')`.

### M-3. Refresh token usable as an access token (no `type` check) + missing `iat`/`sub`
- **Location:** `backend/api/tokens.py:111-131,162-169`; `backend/api/auth.py:268`
- **Violation:** rest-api-design (JWT claims best practices: `iss`, `sub`, `iat`).
- **Current behavior:** `create_token` payload has only `jti/id/admin/exp` (tokens.py:53-70) — no `iat`, `iss`, `aud`. `verify_token` does not reject tokens whose `type == 'refresh'`, so the 14-day refresh token (tokens.py:125) is a fully valid access bearer for any API — the 1-hour access expiry is bypassable with the leaked refresh token, on top of the fail-open blocklist (tokens.py:99-108).
- **Fix:** in `verify_token` (and the auth.py call path) reject `data.get('type') == 'refresh'`; add `iat` (and `aud='quantumpacs'` checked on verify).

### M-4. Public health endpoint leaks internals
- **Location:** `backend/api/telemetry.py:306-334` (+ `_check_*` at 163-303)
- **Violation:** information disclosure in error responses; security-fastapi hardening.
- **Current behavior:** unauthenticated `/api/health` returns component `message` fields with raw exception text (`str(e) or type(e).__name__` truncated to 200 chars — e.g. telemetry.py:169, 185, 200, 215), internal ports (`dicom_cstore_port` 11112, `hl7_mllp_port`, telemetry.py:220-253), storage backend types, and the token-blocklist fail-open degradation state → free recon for attackers; also gives an availability oracle.
- **Fix:** strip `message` from public responses (keep `status`/`latency_ms`), log detail server-side only.

### M-5. Error envelope is inconsistent across the API
- **Location:** `backend/api/response.py:44-53,85-90` (`not_found`/`validation_error`/`unauthorized`/`forbidden`/`server_error` return `{"error": "string"}`) vs `response.py:117-128` + `backend/api/validate.py:38-47` (`api_error` returns `{"error": {"code","message","details"}}`); `backend/app.py:137-139` (HTTPException handler rebuilds `{"error": detail}`).
- **Violation:** rest-api-design (error contract consistency; error payload shape).
- **Current behavior:** two coexisting error shapes depending on the code path; `http_exception` embeds raw exception details in the body (app.py:138) and copies `exc.detail` verbatim — e.g. `requires_permission`'s `detail='Missing permission: X'` and internal `ValueError`s. Clients must sniff `error` being str or dict. Status semantics also drift: `validation_error()` returns 400 while pydantic `_ValidationException` returns 422, `not_found` 404 — reasonable individually, incoherent as a whole.
- **Fix:** retire the bare-string helpers; route all errors through `api_error(code, message, details, status)`; sanitize `exc.detail`; add `request_id` (already present for 5xx) to 4xx too.

### M-6. Unbounded / unvalidated pagination and list parameters → 500s
- **Location:** `backend/api/users.py:224-233` (`limit` unclamped; `limit=0` → `ZeroDivisionError` at users.py:233), `backend/api/files.py:247,276` (`request.query_params['ids']` → `KeyError` → 500), `files.py:305-306` (`per_page` unclamped), `frontdesk.py:117-118`, `logs.py:22-23` (correctly clamps 10..200 — the pattern to copy).
- **Violation:** rest-api-design (pagination patterns; input bounds); error-contract semantics (should be 400).
- **Current behavior:** `int()` of non-numeric query params raises `ValueError` (unhandled 500); `limit=0` → 500; `limit=10**9` → unbounded DB result sets; missing `ids` → 500.
- **Fix:** centralize a `pagination_params(request, default_per_page=20, max_per_page=200)` helper that clamps and 400s on garbage; validate `ids` presence/format.

### M-7. Upload buffers entire file in RAM
- **Location:** `backend/api/files.py:127-148` (`remaining = file.read()` + `io.BytesIO(content)`), allowed up to `max_upload_size_mb` (default 500) → multi-hundred-MB peaks (~1.5–2× file size with pydicom parse).
- **Violation:** performance/availability hardening (memory-fix DoS surface).
- **Current behavior:** concurrent uploads of near-limit files can exhaust worker memory; no `Content-Length` chunked streaming.
- **Fix:** stream the file to a tempfile with a byte counter (spooled temp file via `starlette`'s spooled upload is already a tempfile at `up.file` — read `hash_file`/`parse_dcm` from the tempfile in bounded chunks instead of `file.read()`).

### M-8. CSRF "token" is a constant (`'1'`) — protection is only SameSite=Strict
- **Location:** `backend/app.py:104-134` (`request.headers.get('X-CSRF-Token') != '1'`)
- **Violation:** OWASP CSRF; security-fastapi hardening.
- **Current behavior:** any script/bot can set the constant header, so the anti-CSRF layer adds zero independent value; cookie-based sessions rely solely on `SameSite=Strict` (users.py:136, 145 — good) and `HttpOnly`. Meanwhile legitimate machine/browser flows that forget the header (or v2-alias oauth token, app.py:105-112 list omits `/api/v2/oauth/token` and `/api/oauth/token`) get 403s.
- **Fix:** either (a) mint a real per-session CSRF token (double-submit cookie) for the browser cookie flow, or (b) document/accept SameSite as the only defense and drop the misleading constant check.

### M-9. Stale, incomplete OpenAPI spec (13 of ~120 paths) and no v2 documentation
- **Location:** `backend/static/openapi.json` (paths: /login, /users, /files*, /patients/{id}, /replicas, /logs, /health, /change_password only), served by `backend/api/routes.py:124-125`
- **Violation:** rest-api-design (OpenAPI documentation for every endpoint).
- **Current behavior:** spec version 2.0.0, 13 paths, zero coverage of dicomweb, fhir, hl7, tenants, roles, billing, equipment, portal, exams, reports, worklist, oauth, api-keys — the entire PACS/clinical surface is undocumented; no response schemas for 4xx/5xx; no rate-limit scope; v2 aliases absent; live routes change continuously while the static file drifts.
- **Fix:** generate OpenAPI from the route table (or maintain the spec alongside `routes.py` in CI with a diff gate).

### M-10. Unvalidated raw-JSON passthrough to Elasticsearch
- **Location:** `backend/api/files.py:316-321` (`FilesHandler.post` → `es.search(data)` with `await request.json()`)
- **Violation:** rest-api-design (request validation), OWASP input validation.
- **Current behavior:** arbitrary client JSON is forwarded verbatim to the ES search indexer with no schema, no size cap, and no allowlist of query keys; in deployments with ES enabled this is an unvalidated query surface (also a 500 on non-dict bodies).
- **Fix:** define a `SearchRequest` pydantic schema (query/filters/facets fields with bounds) in `schemas/files.py` and validate via `parse_body`.

---

## LOW FINDINGS

### L-1. 204 responses carry a JSON body
- **Location:** `backend/api/response.py:40-41` (`no_content()` returns body `{}` with 204)
- **Violation:** rest-api-design (204 No Content must not include a body per RFC 9110 §15.3.5; some clients treat bodies on 204 as protocol errors).
- **Fix:** `return Response(status_code=204)`.

### L-2. Legacy HS256 token acceptance window
- **Location:** `backend/api/tokens.py:134-147` (`_decode_any` falls back to HS256 with the shared `config['secret']`)
- **Current behavior:** documented rotation window (R2-11); acceptance of HS256 tokens signed with the shared secret means any process holding the secret can forge full-access tokens until the window closes. `oidc_discovery` also advertises `id_token_signing_alg_values_supported: ['HS256','RS256']` (oauth.py:190) while `_verify_id_token` only accepts RS256 — discovery lies.
- **Fix:** keep the rotation window but add a configured expiry date; align discovery to `['RS256']` + rotate `secret`.

### L-3. Plaintext password returned by user-provisioning endpoints
- **Location:** `backend/api/users.py:266` (`ok({'password': result['password'], ...})`), `users.py:306` (`UsersNewPassword.post` returns generated password)
- **Current behavior:** admin-provisioned passwords are returned in the API response body (and print to the caller's console). Acceptable for provisioning flows, but the password also lands in any proxy/audit capture of the response.
- **Fix:** consider returning a one-time link/expiring secret instead, or document that these endpoints are admin-only and TLS-mandatory.

### L-4. Token prefix (16 chars) written to audit log on revocation
- **Location:** `backend/api/users.py:210` (`resource_id=body.token[:16]`)
- **Current behavior:** the first 16 chars of a JWT are its static base64 header (HS256/RS256 header is identical across tokens from the same issuer) — no practical leak; keep or trim to `body.token[:8]` for clarity.

### L-5. `Login`/`ChangePassword` schemas lack max-length bounds
- **Location:** `backend/api/schemas/auth.py:4-7` (`LoginRequest.username/password` unlimited), `backend/api/schemas/account.py:10-17` (passwords bounded 8-128, good)
- **Current behavior:** unbounded `username`/`password` strings reach PBKDF2 (600k iterations over attacker-chosen length) → CPU-amplification vector on the login path (rate limiter is per-IP 50/60s, mitigates but doesn't cap size).
- **Fix:** `username: str = Field(min_length=1, max_length=255)`; `password: str = Field(min_length=1, max_length=1024)`.

### L-6. `oauth_token_exchange` body parse and grant handling harden
- **Location:** `backend/api/oauth.py:345-348` (`await request.json()` unguarded; `authorization_code` grant with `code` returns 400 "use the callback endpoint" — dead code path), public endpoint (auth.py:187) with no rate limit on refresh-token minting.
- **Fix:** try/except JSON parse → 400; either implement the code grant properly (client_id/secret verification via `client_secret_basic/post` as advertised in discovery) or return 501; add a per-IP bucket here.

---

## Positive observations (verify, don't regress)
- **Auth coverage:** every route outside `_PUBLIC_PATHS` (auth.py:177-198) requires a valid token/API key — the allowlist is short and exact; WS requires query token (auth.py:291-300); OPTIONS passes (auth.py:206).
- **CORS:** explicit origins by default (config.py:31 `http://localhost:5173`), `allow_credentials=True` paired with explicit origins — correct per security-fastapi; `apply_cors_headers` (response.py:67-82) correctly mirrors CORS on error paths outside the middleware stack. `TrustedHostMiddleware` present (app.py:220). Security headers middleware sets HSTS/CSP/XFO/nosniff (app.py:49-58).
- **Permission gating:** `requires_permission` decorator used consistently across dicomweb (DICOMWEB_READ/WRITE), fhir (PATIENT_READ/WRITE, FILE_READ), portal, logs, tenants, roles, api-keys, hl7-admin, billing/equipment/qa/exams/reports; RBAC alias resolution (rbac.py:14-47) and privilege-escalation guards for role assignment (`_can_assign_role`, users.py:40-53) and API-key scope caps (api_keys.py:18-32).
- **Tenant isolation:** TenantMiddleware (tenant_middleware.py:36-141) gates X-Tenant-ID via `can_access_tenant` + `user_tenant_grants`; fail-closed on unknown claimed tenant (403); `_outside_effective_tenant` in files.py:324-345 and per-tenant request pools; audit logging of cross-tenant access.
- **Rate limiting:** login per-IP bucket with DB recording (users.py:58-61, ratelimit.py), change-password bucket, API-key bucket (auth.py:209-218), STOW per-IP bucket (dicomweb.py:471-479); all with graceful Redis-less fallback — but every fallback is per-process (multi-worker deployments dilute it).
- **Password storage:** PBKDF2-HMAC-SHA256 600k iterations, per-user salt, `hmac.compare_digest` (db/users.py:20-27, 58-65), generic login errors + audit trail (users.py:77-91).
- **Cookie hygiene:** login/refresh cookies HttpOnly + SameSite=strict + Secure + scoped path (users.py:132-149); refresh rotation blocks old tokens (users.py:357, oauth.py:383).
- **Logging hygiene:** tokens never logged; request logging uses `request.url.path` (no query string) in CustomMiddleware (app.py:89-96) and TracingMiddleware records only `scope['path']` (tracing_middleware.py:24); share keys in query params restricted to `/api/files/*` + `/api/ws_token` paths (auth.py:262).
Thought: 714ms
Report written. Now return only the compact summary (≤40 lines): counts by severity + 10 most impactful findings with file:line + one-line fix.
Full report: /tmp/opencode/skill-review/reviewer-3-api-security.md
Counts: Critical 0 · High 6 · Medium 10 · Low 6 (22 total)
Top 10 most impactful findings:
H-1 api/oauth.py:365 — OAuth callback cookie lacks secure=True (login sets it). Fix: add secure=True.
H-2 api/routes.py:331 — v2 alias builder drops methods=; /api/v2/oauth/token accepts GET/PUT/DELETE → 500s. Fix: copy methods kwarg (append H-1/H-2 as 5-line patch group).
H-3 api/auth.py:262 + api/files.py:407 — share-key sessions can never pass FILE_READ ⇒ share downloads always 403; prefix match is loose. Fix: dedicated share endpoint authorizing via SharedFiles.check.
H-4 schemas/files.py:10 vs db/share_files.py:33 — duration documented as seconds, implemented as hours; unbounded → 150-day/infinite shares; no tenant check. Fix: Field(ge=60, le=2592000) + relativedelta(seconds=...).
H-5 api/hl7.py:10 — POST /api/hl7 has no permission: any authenticated role can inject HL7 into ingestion. Fix: @requires_permission(Permission.HL7_WRITE) + size cap.
H-6 api/webhooks.py:99-109 — SSRF guard checks only IP literals; misses 169.254.0.0/16 (cloud metadata), hostnames pass. Fix: resolve DNS, block full private/link-local list, follow_redirects=False.
M-1 api/auth.py:177 — /api/docs & /api/docs/openapi.json require auth; metrics/health public-policy inconsistent. Fix: add docs paths to public allowlist; align metrics posture.
M-3 api/tokens.py:162 — verify_token accepts type=refresh tokens as access tokens (14-day bearer); no iat/aud. Fix: reject type=='refresh'.
M-2 api/ws.py:151-208 — WS file channels have zero authz (subscribe/publish any file: channel cross-tenant). Fix: authorize file via tenant check before sub_lock registration.
M-5/M-6 api/response.py:44-53 — two error envelopes ({"error": str} vs {"error":{code,...}}); unbounded limit/per_page + missing ids → 500s (users.py:233, files.py:247). Fix: single api_error envelope + clamped pagination helper.
Strengths noted: near-universal @requires_permission coverage, explicit CORS origins + TrustedHost, tenant middleware fail-closed, PBKDF2-600k passwords, cookie flags tight (except H-1), no tokens in logs.



# Reviewer-4: Testing Review — QuantumPACS @ d4abc25 (v3-dev)

Scope: backend tests (unit + integration), pytest config, frontend Vitest/RTL suite, Playwright E2E specs, CI workflows.
Skills applied: e2e-testing-patterns, frontend-testing-best-practices.

## Findings by severity

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High     | 5 |
| Medium   | 9 |
| Low      | 4 |
| Total    | 18 |

Good signals first: navigator.test.ts is an exemplary table-driven pure-function suite (skill: unit tests for pure functions); setup.ts:32-35 clears localStorage/sessionStorage per test and setup.ts:118-122 makes unmocked fetch throw (fail-loud); rate-limit tests are hermetic (test_ratelimit_redis_fallback.py:8-12 patches `_get_rate_redis`); redis-dependent integration tests skip when Redis absent (test_redis_streams.py:19); blocklist fail-open paths are well covered (test_token_blocklist.py:236-329).

---

## HIGH

### H1 — CI real-stack E2E gate cannot run: nonexistent `management.seed_rbac` module
- **Location**: `.github/workflows/ci.yml:94` vs `backend/management/` (only `__init__.py`, `tenant_migrate.py`)
- **Recommendation violated**: E2E pipeline must be runnable/stable in CI (e2e-testing-patterns).
- **Current behavior**: `python -m management.seed_rbac` is executed in the `e2e` job's "Init DB + seed roles" step. The module does not exist anywhere in backend (verified by grep + ls at commit d4abc25). The step fails, so the job aborts before uvicorn starts.
- **Fix**: Create `backend/management/seed_rbac.py` (call `Roles(conn).seed_built_in_roles()`) or replace with `./manage db init`, which runs `lifecycle.setup(sync_db=True)` (backend/db_init.py:11).

### H2 — Admin login pinned to `pa55w0rd` while CI seeds a different password (and no admin exists at all)
- **Location**: `frontend/e2e/pages/LoginPage.ts:28` (loginAsAdmin → `login("admin", "pa55w0rd")`) vs `.github/workflows/ci.yml:81` (`SUPERADMIN_PASS: quantumpacs-ci-e2e-superadmin-not-for-any-prod`)
- **Recommendation violated**: E2E tests must share a single source of truth for credentials; deterministic CI.
- **Current behavior**: `app.py:178` calls `lifecycle.setup(services=registry)` with `sync_db=False` (lifecycle.py:208 default), so `add_superadmin()` (lifecycle.py:302) is **not** invoked in CI. The CI postgres service is fresh; the e2e job's steps create no user. Even a manual run would create admin with the env password, not `pa55w0rd`. Every spec using `loginAsAdmin` (login.spec.ts, role-based-access.spec.ts, integration.spec.ts, worklist-flow.spec.ts, a11y.spec.ts, navigation, study-viewer, share-link...) fails with 401.
- **Fix**: In the CI job, run `python -m manage db init` (or otherwise seed admin) and pass the password to specs via `E2E_ADMIN_PASS` env (read in LoginPage.ts), keeping one constant.

### H3 — `test_tenant_lifecycle_e2e` canary test guaranteed to fail in CI postgres service
- **Location**: `backend/tests/integration/test_tenant_lifecycle_e2e.py:242-247` + `backend/db/tenant_provisioner.py:32-34`
- **Recommendation violated**: Hermetic tests must pass in CI; environment drift must not flip gates red.
- **Current behavior**: `TenantProvisioner.create_database` hardcodes `user='postgres'` as superuser. The CI `test-backend` job (ci.yml:39-43) uses `POSTGRES_USER: quantumpacs`, where the `postgres` role does not exist. The fixture falls back, and the canary (`assert tenant_env['provisioned_via'] == 'provisioner'`) then fails → entire `test-backend` job red. Same failure on dev boxes whose container superuser isn't `postgres`.
- **Fix**: Make `create_database` use `config['db_user']` with a `postgres` override only when available, or have the CI service also create a `postgres` superuser role (`CREATE ROLE postgres SUPERUSER LOGIN`); re-run the canary meaningfully either way.

### H4 — Tautological RBAC test: mocks itself, asserts nothing about behavior
- **Location**: `backend/tests/integration/test_phase2_integration.py:246-253` (`test_role_patch_without_permissions_skips_bulk`) and 232-244
- **Recommendation violated**: Tests must assert behavior (frontend-testing-best-practices: test behavior, not implementation; no tautologies).
- **Current behavior**: The test patches `Users.bulk_increment_token_version_by_role` as an `AsyncMock`, then calls that same mocked method directly and asserts it "was awaited once". It never exercises `Roles.patch()` or the actual skip decision — it would pass even if role patching always incremented token versions (a token-invalidation security regression would go green). It also literally duplicates the mocking mechanics between the two tests, so both pass for the wrong reason.
- **Fix**: Drive the real `Roles(conn).patch()` code path with a mocked `conn`, assert `bulk_increment_token_version_by_role` is/ isn't called based on whether `permissions` changed; or move to integration with a real DB.

### H5 — `test:fast` references deleted test files; script always fails
- **Location**: `frontend/package.json:52`
- **Recommendation violated**: Developer feedback loops must work (frontend-testing, CI gates).
- **Current behavior**: `test:fast` lists `src/test/hooks.test.ts` and `src/test/App.test.tsx`, neither exists at d4abc25 (verified via ls). Vitest run mode with unmatched filters exits 1 ("No test files found"), so the fast loop is broken on every invocation.
- **Fix**: Remove the two stale paths from the script (their coverage has since moved to AuthContext.test.tsx / NotFound.test.tsx etc.).

---

## MEDIUM

### M1 — "QA user API calls are authenticated" asserts the opposite of what it claims
- **Location**: `frontend/e2e/qa.spec.ts:63-66`
- **Recommendation violated**: Meaningful assertions (e2e-testing-patterns: meaningful assertions).
- **Current behavior**: `page.request.get(API_BASE + "/api/files")` sends no auth header (page.request does not read localStorage tokens; the seeded `e2e-qa-token` is never attached). Asserting 200 does not prove authentication — it proves `/api/files` tolerates anonymous requests. If the backend correctly 401s, this test would fail while the seeded UI sessions stay stubbed-green.
- **Fix**: Attach the token via the request context (`extraHTTPHeaders: { "X-Auth-Pacs": token }`) and assert 401 without it / 200 with it — an actual positive + negative auth pair.

### M2 — Non-admin "E2E" suite runs entirely on forged localStorage sessions + blanket 200 stubs
- **Location**: `frontend/e2e/helpers.ts:186-212 (seedTechnologist), 220-250, 258-307, 316-355, 362-392`; every `/api/**` route fulfilled 200 with synthetic bodies
- **Recommendation violated**: E2E = real system, minimize mocking (both skills; helpers.ts seeds bypass the backend entirely, so no real token, no real RBAC 403, no real response shape).
- **Current behavior**: ~60 role-access test cases assert frontend routing with tokens that no backend would issue. Backend contract drift (renamed endpoints, changed shapes, strict token validation) would keep these green while production breaks. Only admin-login specs touch the real backend.
- **Fix**: Add at least one real non-admin login spec per role family (backend users seeded via a `seed_test_users`-style management command with known passwords); keep localStorage seeding only for the pure route-gating cases, and have `stubApiRoutes` 401 when no valid session shape is present so the stub can't mask auth gaps.

### M3 — BLOCKED_ON_S1 skips hide unimplemented tenant security paths behind green CI
- **Location**: `backend/tests/integration/test_tenant_lifecycle_e2e.py:296-300` (registry-DB admin with `users.tenant = slug`), `:451-452` (tenant_usage_daily), `:464-468` (default tenant seed)
- **Recommendation violated**: No silent skips for critical security/data paths; visible backlog signal.
- **Current behavior**: Three tests silently `pytest.skip` when upstream ADR-026 items are missing. CI stays green while the registry-admin tenant claim (the basis of cross-tenant gating!) is untested at this layer. A skip count is invisible in the `-v` CI log.
- **Fix**: Convert to `xfail(strict=... )`? No — better: keep them failing (xfail as known-fails with a tracked ticket) or implement the provisioner path so they run; at minimum grep-gate CI on skip counts.

### M4 — Coverage gates are lax or absent on both stacks
- **Location**: `frontend/vite.config.js:148-153` (lines 42%, branches 31%, functions 32%, statements 38%) and `.github/workflows/ci.yml:51`/`:59`/`:139`
- **Recommendation violated**: Coverage gates must protect critical paths — for a PACS, 42% line coverage is a weak floor, and the `test-frontend` job (ci.yml:59) doesn't run coverage at all (only `build-gate` does, with the low thresholds). Backend `test-backend` runs `pytest tests/ -v` with `--cov` absent, despite `[tool.coverage]` sections in pyproject.toml.
- **Fix**: Add `--cov --cov-fail-under=70` to backend CI; raise frontend thresholds toward 70+/65+/60+; run coverage in `test-frontend` (or merge with build-gate) so it gates PRs.

### M5 — No per-test timeout for backend pytest; a hung integration test stalls the job
- **Location**: `backend/pyproject.toml:1-12` (no `timeout` / `--timeout` plugin) with `tests/integration/**` that pull Docker images via testcontainers (test_e2e.py:12-20) and provision databases
- **Recommendation violated**: Deterministic, self-terminating suites.
- **Current behavior**: A stuck testcontainer pull or deadlocked pool hangs the whole `test-backend` job until the GitHub 6-hour default — expensive CI and delayed merges.
- **Fix**: Add `pytest-timeout` with `timeout: 300` (and a stricter `timeout: 60` for unit tests via marker), plus `-p no:cacheprovider` for CI.

### M6 — ResourceWarnings suppressed instead of fixed
- **Location**: `backend/pyproject.toml:8-11` — ignores "unclosed socket", "unclosed transport", "unclosed event loop", "coroutine 'handle_find_async' was never awaited"
- **Recommendation violated**: Test diagnosis honesty (hermetic ≠ warn-hidden).
- **Current behavior**: Cross-loop socket leaks (the very issue conftest.py:65-78 `_close_redis_pool` was created to solve) are masked globally, so new leaks won't surface in CI.
- **Fix**: Keep specific ignores only where provably benign (jwt/httpx), delete the socket/loop/coroutine ones, and fix the underlying un-awaited coroutines.

### M7 — Brittle CSS-class selector in RTL test
- **Location**: `frontend/src/test/FrontDesk.test.tsx:278-285` — `document.querySelector(".ant-picker input")`
- **Recommendation violated**: role > label > text > testid; never CSS/DOM structure (e2e-selectors).
- **Current behavior**: The date-picker test depends on antd's DOM class; an antd major bump (v6 present) can silently break the selector while the rest of the suite passes.
- **Fix**: Use `screen.getByRole("textbox")` within the picker container or add `aria-label`/`data-testid` to the picker input.

### M8 — E2E runs against the vite dev server while CI comments promise a production preview; `networkidle` adds flake risk
- **Location**: `frontend/playwright.config.ts:39-44` (`command: "npm run start"` → vite dev) vs `.github/workflows/ci.yml:61-63` comment ("production build served by vite preview"); `helpers.ts:29` and `login.spec.ts:37` use `waitUntil: "networkidle"`
- **Recommendation violated**: Test the artifact you ship; avoid `networkidle` (can hang/overshoot on keep-alive connections).
- **Current behavior**: CI exercises development-mode JS (no minification, no prod chunking, no SW), so prod-only breakage (e.g., the documented stale-SW issue, chunk-load order) is invisible; `networkidle` with the app's proxied WS/keep-alive can increase flake.
- **Fix**: Serve the `dist` build in CI via `E2E_BASE_URL` pointing at `vite preview` (or `npm run build && npm run preview`) with `reuseExistingServer: false`; use `domcontentloaded` + explicit element waits instead of `networkidle`.

### M9 — Patient portal (R19) has thin frontend coverage: 3 fully-mocked RTL tests, no real-backend E2E
- **Location**: `frontend/src/test/Portal.test.tsx:77-116` (whole `api/portal` module mocked) — contrasted with `portal-api.test.ts` contract pins (good)
- **Recommendation violated**: Prefer E2E for critical user flows; portal is a patient-facing PHI surface.
- **Current behavior**: The portal renders (empty state, one bundle, one out-of-scope warning) under mocks; there is no test that a shared record actually appears over the real backend, and `share-link.spec.ts` doesn't cover the portal patient view.
- **Fix**: Add one Playwright spec: login as the provider, share a record via the real API, then log in as the patient and assert the report/orders render (mirroring worklist-flow.spec.ts's real-backend pattern).

---

## LOW

### L1 — "Integration" suite is mostly unit-style with heavy mocks
- **Location**: `backend/tests/integration/test_phase2_integration.py` (all classes patch `api.auth`/`api.oauth`/`Users`), `test_observability.py` (AsyncMock DB/ES everywhere)
- Tests still have value (auth/oauth unit coverage of phase-2 logic), but the directory label inflates the pyramid's integration tier and can excuse the absence of real middleware-to-DB tests. Rename to `tests/unit/` or add one true end-to-end OAuth/JWT test per class using TestClient + real TokenAuth (already done in part via `_make_auth_app`).

### L2 — Duplicated mock boilerplate
- **Location**: `backend/tests/integration/test_phase2_integration.py:36-106` — the identical 6-line patch block appears in all four token-version tests.
- Extract a helper fixture that sets up `get_conn`/`is_blocked`/`Users` mocks (conftest.py already has `auth_headers` and `db_conn`).

### L3 — Vitest retry:2 + 240s timeout masks flakiness
- **Location**: `frontend/vite.config.js:108-114`
- Retries absorb antd/jsdom contention, but 240s per test means a genuinely broken test spends 12 minutes retrying before CI fails. Tighten to `testTimeout: 60_000`, keep `retry: 2`.

### L4 — `test:slow`/`test:fast` split invites coverage gaps
- **Location**: `frontend/package.json:52-53`
- Splitting by reputation (fast vs slow) without a marker means a test moved to "slow" isn't tracked; CI runs everything, so drift is only latent. Add `--testNamePattern`-based tags or an explicit `vitest --project` split if granularity is needed.

---

## Checklist notes (skill compliance)

- Test pyramid: decent unit base (navigator, api-client contract tests, backend unit) + real integration (tenant lifecycle, DICOMweb) + E2E; but E2E layer is mostly frontend-shell-with-stubs (M2), and one "integration" layer is mock-based (L1).
- E2E selectors: mostly role/text-based and keyed stubs (helpers.ts:95-111) — good; exceptions M7, and `.ant-table`/`body` locators in a11y.spec.ts:25 and qa.spec.ts:59 (acceptable for axe/smoke).
- Auto-wait: strict timeouts + expect retries used; `networkidle` exceptions noted (M8).
- Mocking: helper stubs are blanket (M2, M1); RTL suites often carry 3+ module mocks (FrontDesk.test.tsx mocks api + helpers + hooks + antd) — skill says 3+ mocks ⇒ prefer E2E; pragmatic here since E2E exists, but the boundaries should be rebalanced (M9).
- Hermeticity: backend good (rate-limit, redis client reload, skip-if-absent); frontend good (setup.ts clears storage, loud fetch); CI-level admit gaps (H1-H3) break hermeticity at the gate.
- Coverage of critical paths: auth / token_version (H4 blocks confidence), tenant gating (H3 + M3 skips), blocklist fail-open (excellent), RS256/JWKS (test_oauth.py, test_auth_v2.py exist), cross-tenant read isolation (test_tenant_isolation.py) — but tenant lifecycle E2E can never pass in CI today, so those green-checked paths are not actually gated.
Review complete. Report written to /tmp/opencode/skill-review/reviewer-4-testing.md.
Reviewer-4 Summary: Testing
Counts: Critical 0 · High 5 · Medium 9 · Low 4 (18 total)
Top 10 findings
High .github/workflows/ci.yml:94 — python -m management.seed_rbac module doesn't exist (backend/management/ has only __init__, tenant_migrate). E2E job dies at init. Fix: add the module or use ./manage db init.
High frontend/e2e/pages/LoginPage.ts:28 vs ci.yml:81 — hardcoded pa55w0rd ≠ CI SUPERADMIN_PASS, and app.py:178 runs sync_db=False so no admin is ever seeded in CI; every loginAsAdmin spec 401s. Fix: seed admin in CI, read password from E2E_ADMIN_PASS env.
High test_tenant_lifecycle_e2e.py:242-247 + db/tenant_provisioner.py:32 — canary requires superuser role postgres, which CI's postgres service (POSTGRES_USER: quantumpacs) lacks → test-backend job red. Fix: use config['db_user'] with override.
High test_phase2_integration.py:246-253 — tautological test: mocks bulk_increment_token_version_by_role, calls the mock directly, passes regardless of Roles.patch() behavior (token-invalidation regression stays green). Fix: drive real patch() with mocked conn.
High frontend/package.json:52 — test:fast lists deleted hooks.test.ts/App.test.tsx; vitest exits 1 every time. Fix: drop stale paths.
Medium e2e/qa.spec.ts:63-66 — "QA API calls are authenticated" sends no token via page.request; proves /api/files tolerates anonymous, not auth. Fix: assert 401 without / 200 with attached token.
Medium e2e/helpers.ts:186-392 — non-admin E2E runs on forged localStorage tokens + blanket /api/** 200 stubs; backend contract/auth drift invisible. Fix: add one real non-admin login spec per role family.
Medium test_tenant_lifecycle_e2e.py:296-300,451-452,464-468 — BLOCKED_ON_S1 skips hide unimplemented registry-admin-tenant-claim, usage-metering, default-tenant paths behind green CI. Fix: xfail-with-ticket or implement.
Medium Coverage gates: no backend --cov in CI (ci.yml:51), frontend thresholds 31-42% (vite.config.js:148-153), test-frontend job doesn't run coverage at all. Fix: add --cov-fail-under, raise thresholds.
Medium playwright.config.ts:39-44 — E2E runs vite dev server while ci.yml:61-63 claims prod preview; networkidle waits (helpers.ts:29) add flake; prod-only breakage untested. Fix: serve dist via preview in CI, use element waits.
Positives: hermetic rate-limit/Redis tests, loud-fetch RTL setup, excellent blocklist fail-open coverage, table-driven navigator tests, real-backend worklist-flow spec.


# Reviewer-5 — Multi-Tenancy + PACS Workflow Findings (tenant isolation & PACS correctness)

Review target: commit d4abc25, branch v3-dev, QuantumPACS.
Skills applied: multi-tenant-saas (DB-per-tenant isolation model, tenant resolution hygiene, HIPAA-grade leakage vectors), pacs-workflow (MWL C-FIND, study completeness, worklist semantics).

Severity: **2 Critical, 4 High, 6 Medium, 3 Low**.

---

## CRITICAL

### [CR-1] Elasticsearch is a single shared, tenant-blind index — cross-tenant search leakage and document collision (violates DB-per-tenant isolation / HIPAA)

- **Where**: `backend/es/es.py:64-67` (index), `backend/es/es.py:85-137` (search), `backend/api/files.py:316-321` (FilesHandler.post → `es.search(data)`), `backend/es/mapping.py` (no tenant field).
- **Current behavior**: One global index `quantumpacs`. `index()` stores documents keyed `id=str(data['id'])` where `data['id']` is the **per-tenant SERIAL** files.id. `search()` builds `multi_match`/`match_all` with **no tenant filter** and `FilesHandler.post` hands raw user input straight to it. No `tenant` field exists in the mapping.
- **Impact**: (a) Any authenticated `FILE_READ` user in any tenant can list/search other tenants' indexed patient/study metadata (PHI); (b) tenant A file id=5 and tenant B file id=5 collide on the same ES `_id` — one tenant's document silently overwrites the other's (retrieval cross-linkage and data loss in search results). ES is dev-disabled, so this is latent, but the code path is live wherever ES runs.
- **Fix**: add `tenant` to the mapping + `index_file()` payload (`es/es.py:140`), and constrain every `search()` with a `term` filter:
```python
async def search(data, tenant_slug=None):
    es_q = {"bool": {"must": [es_q]}}
    if tenant_slug:
        es_q["bool"]["filter"] = [{"term": {"tenant": tenant_slug}}]
```
and pass `effective_tenant(request)` from `FilesHandler.post`.

### [CR-2] DICOM SCP listeners (C-STORE / MWL C-FIND / Q/R C-FIND) are not tenant-scoped — all live traffic lands in the `default` tenant database

- **Where**: `backend/dcm/server.py:25-34` (store → store_instance without tenant args), `backend/dcm/server.py:103-149` (MWL handler uses `get_conn()`), `backend/dcm/server.py:209-219` (Q/R C-FIND), `backend/dcm/store.py:22-42` (`_resolve_tenant`: `slug = tenant_slug or 'default'`).
- **Current behavior**: The SCP handlers run outside any HTTP request; `_request_tenant_pool` ContextVar is `None` on the DICOM thread, so `get_conn()` resolves to the **main database** (the `default` tenant). `_resolve_tenant` hard-codes the fallback to `'default'`. There is no AE-title → tenant mapping, so a modality configured for tenant B stores into the default tenant's schema, and an MWL query returns the default tenant's scheduled entries to any calling AE.
- **Impact**: With DB-per-tenant semantics, cross-tenant data contamination: tenant B exams are persisted into tenant A's (default's) study/patient tables via C-STORE and are then visible to default-tenant clinicians; MWL C-FIND serves the wrong tenant's worklist; Q/R C-FIND queries the wrong database. In the reverse direction, a tenant-DB modality can *never* see its own worklist.
- **Fix**: add per-tenant AE-title routing in the store/find entry points:
```python
# dcm/server.py handle_store
tenant_slug = config_tenant_for_calling_aet(event.assoc.requestor.calling_ae_title)  # or "default"
future = asyncio.run_coroutine_threadsafe(
    _handle_store_async(ds, dst, tenant_slug=tenant_slug), _loop)
```
and thread `tenant_slug` through `store()` → `store_instance()`; for C-FIND, scope `Worklist.search()` / `QueryRetrieve` to the resolved tenant pool (set the ContextVar inside the bridged coroutine before `get_conn()`).

---

## HIGH

### [HI-1] Cross-tenant grants (`CROSS_TENANT_READ` + user_tenant_grants row) unlock the full write/delete data plane of the target tenant — `scope='read'` is never enforced

- **Where**: `backend/api/tenant_middleware.py:55-74` (header gate only via `can_access_tenant`), `backend/api/auth.py:28-50` (permission+row check, no method/scope dimension), `backend/db/user_tenant_grants.py:50-57` (`scope='read'` written, never read), `backend/api/dicomweb.py:658-697` (delete), `backend/api/worklist.py:123-137` (cancel), `backend/api/files.py:379-394` (file delete).
- **Current behavior**: Once `X-Tenant-ID` passes the read gate, the middleware sets the tenant pool for the whole request, and every handler — including `DICOMWEB_WRITE` deletes, worklist cancellation, file deletion, exam/report mutation — runs on that pool. A teleradiologist granted read-only access can destroy data in the target tenant.
- **Fix**: enforce method-level scope in the middleware (or a permission wrapper): read-only verbs (GET/HEAD) allowed under `CROSS_TENANT_READ` grants; any mutating verb requires an explicit write grant:
```python
cross_tenant = not user.admin and user.tenant != header_slug
if cross_tenant and request.method not in ('GET', 'HEAD'):
    # require scope in ('read','write')/method mapping from the grant row
    return _forbidden()
```

### [HI-2] `_outside_effective_tenant` in api/files.py is dead code — `files` has no `tenant` column, so the scope guard always passes

- **Where**: `backend/api/files.py:324-333` (guard), `:343` (get_file_by_id), `:422` (ServeFile), `:487` (ServeThumbnail); schema `backend/db/files.py:37-56`; migrations — only `users.tenant` (011_tenant_column.py:34), never `files.tenant`.
- **Current behavior**: `file.get('tenant')` is always `None` (column doesn't exist, and `get_extra` never selects it), so `_outside_effective_tenant` unconditionally returns `False`. The intended row-level check "Files without a tenant stay accessible exactly as before" is actually "all files pass the check".
- **Impact**: Defense-in-depth for file reads/downloads/thumbnails is inert; isolation rests solely on the pool routing. A future refactor that moves file rows into a shared table would silently expose all tenants' files.
- **Fix**: either drop the dead guard or make it real — add `tenant TEXT` to `files` (migration + `sync_db`), populate on insert from the resolved slug, and keep the comparison.

### [HI-3] Repointing a tenant's `db_*` config via PUT does not invalidate the live pool — traffic continues to the OLD database

- **Where**: `backend/api/tenants.py:140-157` (pool closed only when `status` ∈ gating set), `backend/db/tenants.py:137-144` (`patch` allows db_host/db_port/db_user/db_password for platform admin).
- **Current behavior**: Platform admin re-points tenant X to a new host/database; `TenantConnectionPool._pools[slug]` still serves connections to the old endpoint until LRU eviction (up to 300s TTL / 50-pool cap). The registry and the live data plane disagree.
- **Fix**: close the pool whenever any `db_*` field or `status` changes:
```python
if status in _GATING_STATUSES or (set(data) & {'db_name', 'db_host', 'db_port', 'db_user', 'db_password'}):
    await TenantConnectionPool.close(tenant['slug'])
```

### [HI-4] Replica sync LISTEN/NOTIFY bridge is wired to the main DB only — tenant-DB replica events never propagate

- **Where**: `backend/lifecycle.py:249-256` (`PgNotifyBridge(create_conn=db.conn.create_conn)` — main DB), `backend/db/replica.py:46-75` (`notify_event` trigger on `replicas`), `backend/services/pg_notify_bridge.py:26-28`.
- **Current behavior**: The `notify_event()` trigger fires per database, but the bridge listens on a single main-DB connection. Replica insert/update/delete events in tenant databases are never observed by the ingestion pipeline, so tenant-DB replica sync (Redis `events:ingestion` / mirroring) silently never happens.
- **Fix**: extend the bridge (or add one bridge per tenant) to attach `add_listener('events', ...)` on each open tenant pool connection, or have `store_instance`/`ReplicasHandlers` publish the event explicitly.

---

## MEDIUM

### [ME-1] Study completeness counter is a non-atomic read-modify-write — lost updates under concurrent C-STORE

- **Where**: `backend/dcm/store.py:91-106` (`received = row['received_instances'] + 1`).
- **Impact**: Two modems storing instances of the same study concurrently both read `received_instances=N` and both write N+1 — study can be marked `complete` early or stuck at an undercount. Worklist `mark_in_progress` (store.py:45-64) has a similar window.
- **Fix**: atomic increment with RETURNING:
```sql
UPDATE studies SET received_instances = received_instances + 1,
       study_status = <computed> WHERE study_instance_uid = $1 RETURNING received_instances
```

### [ME-2] `TenantConnectionPool.get` is racy and LRU eviction can close an in-use pool

- **Where**: `backend/db/tenants.py:18-41` (two concurrent misses both `create_pool` — orphaned pool never closed), `:56-61` (`_evict_lru` picks oldest `last_used`, which may be the pool of an in-flight request; `create_task` without a held reference → "Task was destroyed but it is pending").
- **Fix**: guard creation with an `asyncio.Lock` per slug (class-level), and skip eviction of pools with outstanding leases (`pool._holders`, or track in-flight acquire count), tracking eviction tasks in a module-level set.

### [ME-3] `CREATE DATABASE "{db_name}"` uses string interpolation with no format validation on `slug`/`db_name`

- **Where**: `backend/db/tenant_provisioner.py:41`, schemas `backend/api/schemas/tenants.py:4-12` (no pattern constraints).
- **Impact**: A crafted `db_name` (embedded quotes/hyphens/reserved words) escapes the identifier or silently creates a differently-named database; a bad `slug` poisons pool keys and registry rows. Multi-statement execution is blocked by asyncpg, bounding exploitability, but provisioning reliability/availability is affected.
- **Fix**: validate in the schema (`Field(pattern=r'^[a-z0-9_]{1,63}$')`) and quote identifiers with `asyncpg`'s `conn.execute` of a pre-validated constant, rejecting anything non-conforming.

### [ME-4] JWT-carried `permissions` create up-to-14-day revocation lag; `routing.py` records the claim tenant instead of `effective_tenant`

- **Where**: `backend/api/tokens.py:62-63` (claim carries role permissions snapshot), `backend/api/auth.py:48` (permission check reads the snapshot), `backend/api/routing.py:53` (`getattr(request.user,'tenant') or X-Tenant-ID`).
- **Impact**: (a) Removing `CROSS_TENANT_READ` from a role does not bind until token reissue (grant *row* removal is live, so worst case is limited); (b) a granted radiologist operating under tenant B creates routing rules stamped `tenant_id = <home tenant A>` while the rule row lives in B's DB — audit/ownership mismatch with `effective_tenant` used everywhere else.
- **Fix**: re-fetch role permissions per request for grant gate decisions (cheap cache), and use `effective_tenant(request)` at routing.py:53.

### [ME-5] `_resolve_tenant` swallows errors and silently falls back to un-scoped ingestion — quota enforcement bypassed

- **Where**: `backend/dcm/store.py:40-41` (`except Exception: ... stays un-scoped`), quota gate `:139-147` is conditional on `tenant_slug`.
- **Impact**: Any transient registry/tenant-DB error during C-STORE/STOW resolves to `tenant_slug=''` and `tenant_info={}` → the 90%-quota and hard-quota gates are skipped for that ingest.
- **Fix**: fail the store when tenant resolution fails for a non-default slug (return `False` / 503) instead of degrading to un-scoped.

### [ME-6] `get_tenant_conn` re-reads raw `X-Tenant-ID` without the `can_access_tenant` gate — latent privilege escalation if ever wired up

- **Where**: `backend/api/tenant_middleware.py:156-177` (no auth check on header), currently zero callers.
- **Fix**: delete it, or make it `effective_tenant`-based with the same gate as the middleware.

---

## LOW

### [LO-1] `notify_event` publishes entire row JSON (PHI: patient name, IDs) on the `events` LISTEN channel with no tenant tag

- **Where**: `backend/db/replica.py:57-62`. Any subscriber on the channel sees full PHI rows; payload lacks tenant context for routing/filtering.
- **Fix**: whitelist columns in the payload (IDs + a `tenant` marker only), or move publish to an app-level explicit event.

### [LO-2] Audit/log visibility for cross-tenant operators is home-tenant only

- **Where**: `backend/api/logs.py:31`, `backend/api/dicomweb_logging.py:106-127`. A granted operator working in tenant B cannot read tenant B's audit logs via the API (they query by home-tenant slug).
- **Fix**: use `effective_tenant(request)` for log scoping, gated by the same grant checks.

### [LO-3] Tenant middleware metering hook degrades silently (`except Exception: pass`) and resets the tenant ContextVar even for un-scoped requests

- **Where**: `backend/api/tenant_middleware.py:126-139`. Acceptable but hides metering outages; no action required beyond logging at debug.

---

## Positive notes
- JWT-claim-first resolution with fail-closed 403 for unknown/decommissioned claim tenants (tenant_middleware.py:88-105) and `_INVISIBLE_STATUSES` 404 masking are correct per tenant-resolution hygiene.
- `can_access_tenant` (auth.py:28-50) implements strict least-privilege ordering (claim, then permission AND grant row) — grant rows are inert without the permission.
- Tenant pool is created with per-tenant creds from the registry (db/tenants.py:29-38) and audit rows record `effective_tenant` — consistent R5-05 behavior.
- Non-HTTP `_resolve_tenant` documents its default-tenant fallback (store.py:22-28), which is the right *documented* behavior for single-tenant installs — the missing piece is per-AE tenant routing (CR-2).
- QIDO-RS filters are fully parameterized; `_mwl_like` strips `%`/`_` before LIKE translation (db/worklist.py:6-8, dcm/server.py:69-77) — no injection found.
Thought: 433ms
Now the compact summary (≤40 lines): counts + top 10 findings with file:line and one-line fix.
Summary — Reviewer-5: Multi-Tenancy + PACS Workflow
Counts: 2 Critical, 4 High, 6 Medium, 3 Low (full report: /tmp/opencode/skill-review/reviewer-5-tenant-pacs.md)
Top 10 findings:
Critical es/es.py:64-137 + api/files.py:316-321 — ES index is global with no tenant field, and search() has no tenant filter; per-tenant SERIAL file ids collide on ES _id. Fix: add tenant to mapping/payload and enforce a term filter in every search.
Critical dcm/server.py:25-34,103-149,209-219 + dcm/store.py:31-34 — C-STORE/MWL/Q/R SCPs run outside request context (ContextVar=None) and hard-fallback to default, with no AE-title→tenant mapping. Tenant B modems store into / query tenant A's DB. Fix: resolve tenant from calling AE title and scope the bridged coroutine's pool before get_conn().
High tenant_middleware.py:55-74 + auth.py:28-50 + user_tenant_grants.py:50 — scope='read' never enforced; a read grant unlocks DELETE/writes (dicomweb.py:658, worklist.py:123, files.py:379). Fix: deny non-GET/HEAD to cross-tenant granted requests unless a write grant exists.
High api/files.py:324-333,343,422,487 — file.get('tenant') is always None (files has no tenant column; only users.tenant per 011_tenant_column.py:34) — the scope guard is dead code. Fix: add files.tenant + populate on insert, or delete the guard.
High api/tenants.py:140-157 — pool closed only on gating statuses; re-pointing db_host/port/user/password leaves the stale pool serving the old DB. Fix: also close the pool on any db_* change.
High lifecycle.py:249-256 + db/replica.py:46-75 — PgNotifyBridge listens on the main DB only; tenant-DB replica LISTEN/NOTIFY events never propagate to the ingestion pipeline. Fix: attach a listener per tenant pool connection or publish explicitly from store paths.
Medium dcm/store.py:91-106 — received_instances read-modify-write races under concurrent C-STORE → wrong completeness/completed status. Fix: atomic received_instances = received_instances + 1 ... RETURNING.
Medium db/tenants.py:18-41,56-61 — concurrent pool creation orphan-leaks; LRU eviction can close an in-flight pool; unheld create_task. Fix: per-slug asyncio.Lock + skip eviction of pools with active leases.
Medium db/tenant_provisioner.py:41 + api/schemas/tenants.py:4-12 — CREATE DATABASE "{db_name}" interpolated without slug/db_name format validation. Fix: regex-validate slug/db_name in Pydantic schema.
Medium api/routing.py:53 + api/tokens.py:62-63 — routing rules stamped with home-tenant claim instead of effective_tenant; JWT permission snapshot lags revocation up to 14 days. Fix: use effective_tenant(request); re-check role permissions per request.
