# Phase 2B: Performance & Scalability Analysis — QuantumPACS Frontend

Target: `frontend/` (React 19, Vite 8/Rolldown, Ant Design v6, Cornerstone3D 5.6, TypeScript).
Method: static analysis of `src/` (all 105 files scanned for timers/events/WS/`Promise.all`/hooks usage), plus a **real production build** executed to `/tmp/opencode/qvite-build` to measure bundle composition. All sizes below are measured, not estimated.

---

## CRITICAL

### C1. Cornerstone3D is NOT actually isolated behind the lazy boundary — 3.5 MB ships in the initial load graph
**Location:** `frontend/vite.config.js:33-37` (manualChunks), `src/detail/Detail.tsx:34` (`React.lazy`)
**Evidence (measured build):** `index.html` loads `index-*.js` which statically imports `vendor-cornerstone-DHG3GV0z.js` (3,586 kB / **985 kB gzip**). The entry chunk (`index-CP4_6dN5.js`) contains `import{w as _}from"./vendor-cornerstone..."` and uses it as the dynamic-import preload helper: `w.lazy(()=>_(()=>import('./Login-...'), __vite__mapDeps([...])))`. Rolldown emitted the shared `__vitePreload` helper *into* the cornerstone vendor chunk, so the entry — and therefore every first page load — pulls the entire Cornerstone engine, dicom-parser, and hammerjs.

**Impact:** Every app visit (including `/login` and pages that never touch DICOM) downloads and executes 985 kB gzip of Cornerstone3D. Initial JS graph ≈ **5.15 MB min / 1.49 MB gzip** (index 25 kB + vendor-react 220 kB + vendor-antd 1,305 kB + vendor-cornerstone 3,586 kB + runtime/helpers ~40 kB), of which ~78% belongs to routes the user may never open. On hospital LAN this is seconds of parse + main-thread cost before first paint; on remote/tele-radiology links it is a real bandwidth tax.

**Fix (evidence-based):** give the preload helper its own chunk so it stops anchoring vendor-cornerstone to the entry:
```js
manualChunks(id) {
  if (id.includes('__vite/preload')) return 'vendor-preload';   // ~1 kB helper
  if (id.includes('node_modules/react')) return 'vendor-react';
  ...
}
```
Then re-verify with `vite build` that `vendor-cornerstone` disappears from `index.html`'s module graph and is only imported by `Detail-*.js`/`CornerstoneElement-*.js`. Also raise `build.chunkSizeWarningLimit` and add a bundle-size CI check (e.g., `rollup-plugin-visualizer` or `vite-bundle-analyzer`).

### C2. chart.js (~200 kB min / ~70 kB gzip) is bundled into `vendor-react` — the initial chunk
**Location:** `src/metrics/Metrics.tsx:36-47` (only importer), `vite.config.js:34`
**Evidence (measured):** `vendor-react-DHUacnVc.js` (220.5 kB) contains chart.js runtime code (`getChart`, `drawOnChartArea`, `category` scale strings); the lazy `Metrics-*.js` chunk is only 7.4 kB. `manualChunks` has no rule for `chart.js`, and `react-chartjs-2` (its only importer) is pulled into `vendor-react` via the `node_modules/react` rule, dragging the whole chart engine into the initial bundle.
**Impact:** Every first load pays ~70 kB gzip for a chart library used only on `/metrics`. The Phase-1 context's claim is confirmed by measurement.
**Fix:**
```js
if (id.includes('node_modules/chart.js') || id.includes('node_modules/react-chartjs-2')) return 'vendor-chart';
```
(Also consider a lighter alternative for admin dashboards, e.g. `visx`/`@ant-design/charts`, but the one-line chunk fix suffices.)

---

## HIGH

### H1. WS reconnect storm: unbounded, no backoff, no cap — token request per iteration
**Location:** `src/ws.ts:19-21` (`close` → `init()`), `src/ws.ts:8-12` (fresh `ws_token` HTTP request per attempt)
**Impact:** When the backend is down or the socket is dropped, `close` fires and `init()` immediately issues `POST /ws_token` + a new `WebSocket` — as fast as TCP fails (sub-second on localhost, a few seconds across networks). Sustained: **1+ auth-token HTTP request and 1 WS connect/teardown per second, indefinitely**, hammering auth + the asyncpg pool, and flooding logs. Every browser tab does this independently.
**Fix:** capped exponential backoff + jitter, terminate after N attempts, and gate on `navigator.onLine`:
```ts
let attempts = 0, retryTimer: number | null = null;
function scheduleReconnect() {
  attempts += 1;
  const delay = Math.min(1000 * 2 ** Math.min(attempts - 1, 6), 60000) + Math.random() * 500;
  retryTimer = setTimeout(init, delay);
  if (attempts > 10) return;               // give up, wait for next page load / login
}
// in close handler: scheduleReconnect(); on open: attempts = 0;
```

### H2. WS subscriber registry is a single-slot, overwritten, leak-prone global
**Location:** `src/ws.ts:36-42` (`messageFunc = func` + extra `message` listener appended per call), `src/ws.ts:28-34` (`onOpenFunc` overwritten; a *new* listener attached to the current socket each call)
**Impact:** (a) Only ONE consumer can ever receive WS messages — the last `addEventListener` caller wins; every `CornerstoneElement` mount calls `ws.addEventListener(this.onStateUpdate)` (`CornerstoneElement.tsx:730`), so the second viewer silently kills the first's annotation sync. (b) Each mount also appends a permanent `message` listener to the current socket — listeners accumulate per mount and are never removed (`componentWillUnmount` doesn't unsubscribe). (c) After a reconnect, only the last-registered callback survives, so multi-viewer collaboration breaks silently. Each WS frame is also parsed N times (N mounts) on the main thread.
**Fix:** real subscriber set with unsubscribe:
```ts
const subs = new Set<(data: any) => void>();
export function addEventListener(fn) { subs.add(fn); return () => subs.delete(fn); }
// message handler: for (const f of subs) f(JSON.parse(event.data));
```
`CornerstoneElement.componentWillUnmount` should call the returned unsubscribe.

### H3. 401-refresh thundering herd: N parallel `/auth/refresh` calls with a token write race
**Location:** `src/helpers.ts:146-169` (`request` catch → `tryRefreshToken()` per failing request), `src/helpers.ts:101-117` (`tryRefreshToken` has no in-flight dedup)
**Impact:** At token expiry, every concurrent in-flight request fails 401 and each independently fires `POST /auth/refresh` (also subject to the 4× retry on 5xx). A page that fires 8 parallel calls (e.g., Detail, Hl7Dashboard, Metrics) generates 8–32 refresh attempts. Each response writes `localStorage` tokens; the slowest stale response can clobber newer tokens, causing a cascade of failed refreshes → forced logout (`navigate("/login")`) in the middle of a work session. With `fetchWithRetry` retrying 5xx on `/auth/refresh` itself, a down DB turns into a request burst.
**Fix:** single-flight refresh with a module-level promise:
```ts
let refreshPromise: Promise<boolean> | null = null;
export function tryRefreshToken() {
  if (!refreshPromise) refreshPromise = doRefresh().finally(() => { refreshPromise = null; });
  return refreshPromise;
}
```

### H4. `fetchWithRetry` retries 5xx up to 4× on EVERY request — including mutations — multiplying backend load
**Location:** `src/helpers.ts:31-48` (`retries = 3` → up to 4 attempts), used by every `request()` (`helpers.ts:143`)
**Impact:** When the backend returns 5xx (pool exhaustion, DB lock, upgrade in progress), every request is re-issued 3 more times with backoff (1s, 2s, 4s up to 8s). A page with 8 parallel calls becomes **up to 32 HTTP requests** to a server that is already failing — exactly when the pool is most fragile. Because it wraps mutations (`worklist` DELETE/POST, `notifications/read-all`, `files` edits), a POST that *was* applied but returned 5xx is re-applied (double mark-performed, duplicated side effects). Errors are then partially swallowed (`Worklist.tsx:240` `.catch(()=>{})`).
**Fix:** retry only idempotent GETs, never 4xx, cap at 2 attempts, honor `Retry-After`, and return the final error:
```ts
async function fetchWithRetry(url, options, retries = 2) {
  for (let i = 0; i <= retries; i++) {
    const resp = await fetch(url, options);
    if (resp.ok || resp.status < 500) return resp;
    if (i === retries || (options.method && options.method !== 'GET')) return resp;
    await sleep(Math.min(500 * 2 ** i, 4000));
  }
}
```

### H5. Replicas page polls full table every 2 seconds, forever, no pagination
**Location:** `src/replicas/Replicas.tsx:58-64` (`setInterval(..., 2000)`), `Replicas.tsx:81-96` (unpaginated `request("replicas")`)
**Impact:** **0.5 requests/s sustained** while the page is open; 1,800 req/h per admin tab. Each response replaces `data` → full Table re-render every 2 s. Multiple admins with the page open = continuous DB scan + asyncpg pool churn. This is the single heaviest poller in the app.
**Fix:** poll at 15–30 s, or better, subscribe to the existing WS `replica.sync_status_changed`/`notify_event` channel and refetch only on events; add `AbortController` to cancel stale in-flight fetches; render counts with stable keys.

### H6. Worklist: request parameters silently dropped — every fetch is an unfiltered GET /worklist
**Location:** `src/worklist/Worklist.tsx:73-103` (`request("worklist", query)`), `helpers.ts:119-141` (only `options.query`/`options.data` are honored; anything else is ignored)
**Impact:** `{ status, station_ae_title, search, date_from, date_to, page, per_page }` are all dead — **the server never receives status filters or pagination**. Consequences: (a) every tab/search/date filter re-fetches the same default page-1 dataset (client-side filtering over 20 rows → wrong tab badges, the Phase-1 bug); (b) clicking page 2+ returns identical data (pagination is a no-op → repeated identical requests); (c) search input `onChange` (`Worklist.tsx:479-481`) calls `setSearchQuery` which is in `fetch`'s deps → **one full /worklist request per keystroke**, un-debounced.
**Fix:** build the query correctly and debounce:
```ts
request("worklist", { query: { status, page, per_page, search, date_from, date_to } })
// + 300ms debounce on searchQuery, and a request-version guard to drop stale responses
```

### H7. Detail opens: same DICOM instance fetched 2–3× (wadouri → wadors transition + remount hack)
**Location:** `src/detail/Detail.tsx:62,73,91,101-108,122-128` (remount hack `setTimeout(() => setKey(2), 500)`), `CornerstoneElement.tsx:202` (`image: props.wadoRsImage || props.image`), `CornerstoneElement.tsx:744-760` (`componentDidUpdate` re-`setStack` on wadouri→wadors switch)
**Impact:** Every `/files/:id` visit: (1) initial mount stacks `wadouri:` URL; (2) metadata arrives → `wadoRsImage` set → `componentDidUpdate` sees URL change → `setStack([wadors...])` → **second download of the same instance**; (3) the `setKey(2)` hack forces a full viewer remount → `enableElement` + `setStack` again → **third fetch/decode** (GPU texture re-upload, viewport re-created). For a 30–100 MB CT instance this is 2–3× network bytes and decode CPU per view, and the 500 ms remount causes a visible flicker/loading flash.
**Fix:** delete the remount hack; mount `CornerstoneElement` only after metadata is resolved (or pass a stable `image` that prefers wadors immediately); change `componentDidUpdate` to update the *existing* stack in place only when the SOP UID actually changes.

### H8. `checkReady` 100 ms polling loop: never cancelled, no unmount guard, infinite on failure
**Location:** `src/detail/CornerstoneElement.tsx:716-725`
**Impact:** If `voiRange` never appears (failed/deferred load, hidden viewport via `display:none`), the chained `setTimeout(checkReady, 100)` runs **10×/s forever**, even after `componentWillUnmount` (no `this.mounted` check inside the closure — the loop also calls `restoreToolState`/`emitAnnotations` and `setState` on a detached component). While it spins, each iteration touches the annotation manager. On a study with many quick navigation steps, overlapping loops from multiple mounts keep firing.
**Fix:** bound attempts and gate on mount state + document visibility:
```ts
let attempts = 0;
const checkReady = () => {
  if (!that.mounted || attempts++ > 50) return;   // give up after ~5s
  const vp = that.getViewport();
  if (vp && (vp as any).voiRange) { that.restoreToolState(...); that.emitAnnotations(); }
  else that._readyTimer = setTimeout(checkReady, 100);
};
```
Clear `_readyTimer` in `componentWillUnmount`.

---

## MEDIUM

### M1. NotificationBell polls every 30 s despite a real-time WS channel existing
**Location:** `src/notifications/NotificationBell.tsx:65-71`, infra: `ws.ts` + backend LISTEN/NOTIFY `notify_event()`
**Impact:** 2 requests/min/user/tab on `GET /notifications/unread-count` — a full DB COUNT per poll, forever, across all open tabs. 100 logged-in users ≈ **3.3 req/s of pure idle traffic**. The backend already pushes events over `/ws` (same channel `CornerstoneElement` uses).
**Fix:** subscribe to WS events (`study.arrived`, `share.accessed`, `system.alert`, …) and call `fetchUnread()` on event, keeping a 60 s fallback poll. Clear subscription on unmount.

### M2. Logs live-tail: unbounded DOM growth while streaming
**Location:** `src/logs/Logs.tsx:164-175, 212-246` (5 s cursor poll, `setData(prev => [...newItems, ...prev])`)
**Impact:** Good news: polling is cursor-based and only fetches new rows (no N+1, no refetch of the page). Bad news: with streaming on, prepended rows are never trimmed — a long-lived session grows `data` and the Table DOM without bound (50-row page size, but `total` and rows keep climbing; antd Table is not virtualized). Memory + render cost creep over hours. The `newEventIds` Set is cleaned (2 s timeout) — good.
**Fix:** cap prepended backlog (e.g., keep last 200 prepended, drop older), or switch to a virtualized table (`rc-virtual-list`/`@tanstack/react-virtual`) for the live view.

### M3. Files.tsx: duplicate fetch on mount + stale-closure pagination
**Location:** `src/files/Files.tsx:144-155` (two mount effects both calling `fetch()`), `Files.tsx:117-142,168-210` (stale `pagination` closure), `Files.tsx:242-249` (search resets `current:1` in state but not in the URL)
**Impact:** (a) Every Files visit issues **2 identical requests** (QIDO `v2/dicomweb/studies` or `POST /files`) — ×4 each if the server is 5xx (up to 8 requests on mount). (b) The URL carries `page`, so typing a search while on page 3 re-fetches page 3 of the new query while the UI claims page 1 (`handleSearchChange` resets state only) → misleading results + repeated page-N fetches. (c) `fetch` reads `pagination` from a stale render closure inside `setPagination` callbacks — future page resets land in a dead object.
**Fix:** single mount effect (`useEffect(() => { fetch(); }, [])` is not enough — use `useRef` for first-run guard), derive `page` from the URL (single source of truth), wrap `fetch` in `useCallback` with real deps, and reset the URL page param when the query changes.

### M4. QIDO search results are unbounded and unfilterable client-side
**Location:** `src/files/Files.tsx:157-166` (`fetchQidoResults` — no limit/pagination), `Files.tsx:193-199` (renders ALL results into an antd Table; mobile renders every row as a Card)
**Impact:** A broad query (any patient-level search without study-level narrowing) returns the entire matching set; `dicomJsonToFlat` maps every row synchronously on the main thread, then antd renders all rows (no virtualization). Thousands of studies → multi-second main-thread block + massive DOM. Backend side: full scan per query. Also double-fires on mount (see M3).
**Fix:** add `limit`/`offset` (QIDO `limit=100`) to the request, paginate server-side, and/or virtualize the table.

### M5. ThumbnailStrip eagerly fetches every thumbnail; token in URL defeats HTTP cache
**Location:** `src/detail/ThumbnailStrip.tsx:52-59` (an `Image()` per file in the series, all fired on mount, no `loading="lazy"`/IntersectionObserver, no local cache)
**Impact:** Opening a 200-instance series fires **200 thumbnail GETs** (with per-file DB/thumbnail-generation work) regardless of scroll position. Because the URL carries `?token=` and tokens rotate, browser caching is unreliable → repeated downloads on re-visits.
**Fix:** lazy-load via IntersectionObserver (or `loading="lazy"` on real `<img>`), keep a module-level LRU cache keyed by file id, and use an httpOnly cookie/session-based auth for image endpoints instead of query tokens.

### M6. Column/Table config objects rebuilt on every render (Files, Worklist, Logs, FhirMonitoring)
**Location:** `Files.tsx:380-439`, `Worklist.tsx:301-411`, `Logs.tsx:326-382`, `FhirMonitoring.tsx:97-128` (arrays created inline each render; `getColumnSearchProps` closes over `searchText`/`globSearch`)
**Impact:** Every keystroke/state change rebuilds column descriptors and all cell renderers; antd re-derives rows because the props identity changed. For 1,000-row QIDO results this multiplies render cost per interaction. Worklist's per-keystroke fetch (H6) makes this worse.
**Fix:** `useMemo` the columns; hoist stable `render` functions; only the highlight `searchWords` needs to be reactive (pass via a memoized `customRender`).

### M7. Worklist batch ops: N concurrent requests, errors swallowed, success reported regardless
**Location:** `src/worklist/Worklist.tsx:235-267` (`Promise.all(ids.map(request...catch(()=>{})))`)
**Impact:** 20 selected rows = 20 simultaneous DELETE/POSTs against the asyncpg pool — no concurrency cap; with H4's retries, a failing backend turns one click into **up to 80 requests**. `.catch(()=>{})` discards failures → "Cancelled N entries" toast even when every request failed. Then `fetch()` re-fires (H6).
**Fix:** add a backend batch endpoint (`POST /worklist/batch`), or cap concurrency (e.g., `p-limit`-style worker of 4) and return per-id results: `const results = await Promise.allSettled(...); if (results.some(r => r.status === 'rejected')) message.warning('N failed')`.

### M8. `document.title` side effect in render — 15 files
**Location:** e.g. `Detail.tsx:49`, `Logs.tsx:128`, `Worklist.tsx:49`, `Metrics.tsx:130`, `Login.tsx:63`, `Replicas.tsx:49`, `Tenants.tsx`, `Users.tsx`, `Roles.tsx`, `Account.tsx`, `Patient.tsx`, `Share.tsx`, `Management.tsx`, `RoutingRules.tsx`, `ServiceKeys.tsx`
**Impact:** Under React 19 concurrent rendering, render can be replayed/abandoned; writing `document.title` during render mutates global state from a non-committed render, causes title flicker on aborted renders, and runs on every re-render (not just mount). Cheap individually, but a systematic violation; with `ConcurrentRoot` upgrades it can display wrong titles for the current route.
**Fix:** `useEffect(() => { document.title = "..."; }, [])` (or a `<Route title>`-driven effect in one place).

### M9. Memory: Cornerstone image cache never purged; engine is a never-destroyed singleton
**Location:** `CornerstoneElement.tsx:666-678` (`RenderingEngine(ENGINE_ID)` created once, `disableElement` on unmount but engine and global tool group persist), no `imageCache.purgeCache()` anywhere
**Impact:** Decoded pixel data accumulates in Cornerstone's global image cache across studies for the whole tab lifetime; with default cache sizing (up to ~1.5 GB), a long radiology session browsing many large studies can pin hundreds of MB–GB of RAM; the GPU context/engine survives logout. Worker pools (`computeWorker` 2.8 MB, decode workers, wasm modules) are instantiated per decode need but never explicitly released.
**Fix:** `imageCache.purgeCache()` on study change/unmount (keep current study), call `renderingEngine.destroy()` (or at least purge) in a global "study session ended" hook, and consider an LRU cap tuned to series size.

### M10. Hl7Dashboard fetches all 4 admin endpoints on mount (inactive tabs included)
**Location:** `src/hl7/Hl7Dashboard.tsx:120-131`
**Impact:** Each visit issues messages + metrics + config + status (4 requests, ~2 of them expensive aggregation queries) even when the user only looks at the Messages tab; metrics aggregation (`period=24h`) runs on an idle tab.
**Fix:** fetch per-tab on first activation (lazy tab loading), or gate `fetchMetrics` on tab switch.

### M11. Worklist/station-AE and per-keystroke secondary fetches
**Location:** `Worklist.tsx:107-112` (station-aes on every mount — fine), `Worklist.tsx:479-481` (see H6) — merged into H6.

---

## LOW

### L1. `init()` WS connection is attempted on every app load, including `/login`
**Location:** `src/index.tsx:57-59`, `ws.ts:8-26`
A `ws_token` request + WS handshake happen before authentication, for every visitor including unauthenticated ones. Guard with auth state; H1's backoff caps the failure churn.

### L2. Detail: `parseAnnotations` recomputed on every render
**Location:** `src/detail/Detail.tsx:75` (un-memoized parse of the full annotation set per render, re-run on every tab/menu/badge state change)
Memoize on `[rawAnnotations, imageUrl]`; the annotations array can be large for a study with many measurements.

### L3. `request()` mutates caller's `options` object (`options.headers = new Headers(...)`)
**Location:** `helpers.ts:126-137`
Shared options objects across concurrent calls can leak headers between requests (mostly benign today, but a hazard once caching/abort is added). Clone options at entry.

### L4. Login lockout ticker + Share/Upload timers fire `setState` after unmount
**Location:** `Login.tsx:129-137` (cleared — fine), `UploadZone.tsx:125-249` (numerous `setTimeout(() => removeFile(id), ...)` chains with no cleanup on unmount)
No crash in React 18+ (no-op warning-free), but queues of dead timers pile up during upload storms. Clear timers in an effect cleanup.

---

## Verified Good (measured/checked)

- **Route-level code splitting:** all 21 routes use `React.lazy` + one shared `Suspense` fallback (`src/index.tsx:18-39,70-83`); per-route chunks are small (5–19 kB). ✅
- **Decoders/workers load on demand:** `computeWorker` (2.9 MB), `openjphjs.wasm` (2 MB), openjpeg/libjpeg wasm, `decodeImageFrameWorker` are emitted as separate assets, fetched only when image decoding starts — not part of the initial graph. ✅
- **`vendor-antd` (1.3 MB) and `vendor-react` (220 kB) are cached chunks with long-lived names** — the cache-busting cost is paid once; acceptable for an internal LAN app. ✅
- **Logs polling is cursor-based and incremental** (`Logs.tsx:212-246`, `latestIdRef`), no full-page refetch in live mode; `newEventIds` highlight set is self-cleaning. ✅
- **All interval/timer users except H5/H1/H8 clear their intervals on unmount** (NotificationBell, Metrics, FhirMonitoring, Logs, Login, Replicas). ✅
- **Files search is debounced (300 ms)** (`Files.tsx:245-249`). ✅
- **`AuthContext` value memoized, `hasPermission`/`signIn`/`signOut` are `useCallback`'d** (`AuthContext.tsx:75-133`) — no context re-render storms. ✅
- **ThemeProvider media-query listener has proper add/remove cleanup** (`ThemeProvider.tsx:55-56`). ✅
- **UploadZone uses XHR with progress + abort propagation** (`UploadZone.tsx:26-45`). ✅
- **ThumbnailStrip images are created in `useEffect` (not render)** and keyed by `file.id`. ✅ (eager fetch is the issue — M5)
- **Login throttling exists client-side (exponential lockout, 429-aware)** (`Login.tsx:24-56`). ✅
- **`Worklist` uses `useMemo` for `filteredData`/`calendarEntries`/`countedTabs`** (correct in isolation; the server-side params bug H6 is the real issue). ✅
- **`VitePWA` `selfDestroying: true`** avoids the stale-service-worker trap in dev. ✅
- **No unbounded `useMemo` caches, no `setInterval` in reducers, no synchronous heavy work in render** outside `dicomJsonToFlat` (M4) and `parseAnnotations` (L2). ✅

---

## Priority Fix Order

1. **C1 + C2** — chunk fixes; reclaim ~1.05 MB gzip from the initial load (one-line config change, re-verify with build).
2. **H1 + H2** — WS reconnection backoff and real subscriber registry (also fixes multi-viewer sync).
3. **H3 + H4** — single-flight refresh and GET-only, capped retries (protects the asyncpg pool exactly when it's failing).
4. **H5** — Replicas polling (2 s → event-driven/30 s).
5. **H6** — Worklist query plumbing (correctness + per-keystroke storms).
6. **H7 + H8** — Detail double/triple image fetch and the never-cancelled ready loop.
7. Then M1–M10 (notification WS, log trim, Files duplicates, QIDO limit, thumbnails, memoized columns, batch ops, title effects, cache purge, Hl7 lazy tabs).
