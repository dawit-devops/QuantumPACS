---
name: cornerstone3d-viewer
description: Cornerstone3D DICOM viewer development for React — rendering-engine bootstrap, stack viewports, WADO-RS loading with auth, tool groups (pan/zoom/window-level, length, ROI, angle, arrow, eraser), camera operations (rotate/flip/invert), annotation state management + persistence, multi-viewport layouts, reading presets, and DICOMweb integration. Use when building, modifying, or debugging a Cornerstone3D image viewer, implementing tools or annotations, wiring WADO-RS image loading, or working with the frontend/src/detail/viewer modules. Pairs with dicom-web-query and pacs-workflow for the backend/query side.
---

# Cornerstone3D DICOM Viewer

You are a Cornerstone3D expert working inside a React (Vite + Ant Design) codebase. These are the proven patterns from this project's viewer (`frontend/src/detail/viewer/` + `frontend/src/detail/CornerstoneElement.tsx`) — follow them when writing or changing viewer code.

## Package Stack

| Package | Role |
|---|---|
| `@cornerstonejs/core` | Rendering engine, viewports, camera, events (`Enums`, `eventTarget`, `EVENTS`, `cache`) |
| `@cornerstonejs/tools` | ToolGroupManager, tools, `annotation` state, `Enums as ToolsEnums` |
| `@cornerstonejs/dicom-image-loader` | WADO-RS/WADO-URI loading with XHR hooks |

## 1. Global One-Time Init (`viewer/setup.ts`)

Never re-init per viewport. `ensureGlobalInit()` is called once, guarded by a module-level `globalInitCalled` flag so concurrent mounts are safe.

1. `initDicomImageLoader({ beforeSend })` — **required for auth**: the loader's XHR must carry the same headers as the rest of the app or every image fetch 401s:
   ```ts
   beforeSend: (xhr: XMLHttpRequest) => {
     const token = localStorage.getItem("access_token");
     if (token) xhr.setRequestHeader("X-Auth-Pacs", token);
     const tenantId = localStorage.getItem("tenant_id");
     if (tenantId) xhr.setRequestHeader("X-Tenant-ID", tenantId);
     xhr.setRequestHeader("X-CSRF-Token", "1");
   }
   ```
2. `await csCoreInit(); await csToolsInit();`
3. `addTool(...)` every tool class once (Pan, Zoom, WindowLevel, Length, RectangleROI, Angle, ArrowAnnotate, EllipticalROI, Eraser, StackScroll, CobbAngle, Probe, CircleROI).
4. Create one shared tool group (`ToolGroupManager.createToolGroup(TOOL_GROUP_ID)`) and add every tool to it.

### Mouse-button bindings (keep these consistent)

| Tool | Button | Purpose |
|---|---|---|
| Pan | left (mask 1) | Primary nav |
| Zoom | right (mask 2) | Also `touchPinchCallback: true` |
| WindowLevel | middle (mask 4) | WW/WC drag |
| StackScroll | wheel / touch drag | Series scrolling |

Note the any-cast: the code extracts `const setActive = (tg as any).setToolActive` and invokes it with `setActive.call(tg, ...)` because the typed signature is narrower than the runtime API.

## 2. Viewport Lifecycle (`CornerstoneElement.tsx`)

### Mount

1. Assign a unique `viewportId` per element (`stack-viewport-${random}`) and keep it in a ref — the engine is shared app-wide (`ENGINE_ID`).
2. Get or create the shared `RenderingEngine`, then:
   ```ts
   await renderingEngine.enableElement({
     viewportId, type: Enums.ViewportType.STACK,
     element, defaultOptions: { background: [0, 0, 0] },
   });
   const tg = getToolGroup(); if (tg) tg.addViewport(viewportId, ENGINE_ID);
   const viewport = renderingEngine.getViewport(viewportId) as StackViewport;
   await viewport.setStack([imageUrl]);
   ```
3. Subscribe on the shared `eventTarget` (not the element):
   - `EVENTS.IMAGE_RENDERED` + `EVENTS.STACK_NEW_IMAGE` → `onImageRendered` (loading state + info overlay)
   - `ToolsEnums.Events.ANNOTATION_ADDED/MODIFIED/REMOVED/COMPLETED` → `saveToolState`
4. Listen to `window.resize` → `renderingEngine.resize()`.
5. Poll for viewport readiness with a bounded loop (≤50 attempts × 100 ms) — when `(vp as any).voiRange` exists, restore persisted annotations and auto-apply the default W/L preset.

### Teardown (critical — leak prevention)

Every async continuation must bail on a `disposedRef.current` check. In the cleanup:

- `cancelAnimationFrame` any pending frame
- remove all `eventTarget` + window + ws listeners
- `re.disableElement(viewportId)` and `tg.removeViewports(ENGINE_ID, viewportId)`

### Switching images (same viewport, new URL)

```ts
imageRef.current = imageUrl;
cache.purgeCache();          // P-M10: drop the previous series' decoded pixels or RAM grows unbounded
vp.setStack([imageUrl]).then(() => { /* clear error, restore annotations */ });
```

## 3. Camera Operations (`viewer/camera.ts`)

| Op | Implementation | Note |
|---|---|---|
| Read info | `vp.getZoom()`; `voiRange` → `ww = upper-lower`, `wc = (upper+lower)/2` | `voiRange` is on the any-cast |
| Rotate 90° | `(vp as any).setRotationCPU((camera.rotation + 90) % 360)` | |
| Flip | `(vp as any).setFlipCPU({ flipHorizontal, flipVertical })` | |
| Invert | `vp.setProperties({ invert: !(vp as any).invert })` | |
| Zoom by factor | `vp.setZoom(vp.getZoom() * factor)` | |

## 4. Tool Activation (`viewer/tools.ts`)

`setPrimaryTool` demotes Pan then promotes the target on left button. ⚠️ **It does NOT demote sibling annotation tools** — switching Length → Rectangle leaves Length active on button 1 too. Only `activateDrag()` (Pan) demotes *all* annotation tools first. Preserve this exact behavior when copying the pattern, and be aware of the latent issue if you ever want true exclusivity:

```ts
// setPrimaryTool — demotes Pan only
const setActive = (tg as any).setToolActive;
tg.setToolPassive(PanTool.toolName);
setActive.call(tg, toolName, { mouseButtonMask: 1 });
```

Expose one `activateX()` function per tool — the UI and keyboard handler call these, never the tool group directly.

## 5. Annotation State (`viewer/useAnnotationSync.ts`)

- Source of truth is `csAnnotation.state.getAnnotationManager().getAllAnnotations()`.
- **Restore**: remove all current annotations, then `state.addAnnotation(annotation, imageUrl)` for each saved one. Persisted shape is the raw annotation array stored as `file.tools_state`.
- **Persist**: `request(\`files/${file.id}\`, { data: { tools_state: annotations } })`.
- **Probe** differs from shape tools: stats live at `cachedStats[targetId].value` (scalar, or array for multi-value ECG/US modalities) plus `modalityUnit` (e.g. `"HU"`) — format `value.toFixed(1)` joined by `" / "` for arrays, append the unit. ToolName is `Probe`.
- **ROI family** (RectangleROI / EllipticalROI / CircleROI) share one stats shape: `area` (top-level, `mm²`), `mean`, `stdDev` — one parse case covers all three; type derives from `toolName`.
- **Real-time sync**: versioned `send_state` messages over the shared `ws` channel (every 500 ms, only when the version advanced). Remote `send_state` for the same `file` restores into this viewer.
- **Focus annotation** (measurement-panel click → camera): average the handle points, translate camera `focalPoint` + `position` by the delta, `viewport.render()`.
- Keep state in refs, not React state — a 500 ms send loop must not re-render the component.

## 6. Multi-Viewport Layouts & Presets (`viewer/presets.ts`, `CompanionViewportGrid.tsx`)

- Layout presets are `rows × cols` (`1x1`, `1x2`, `2x2`); render the primary cell plus N-1 `CompanionViewportGrid` cells on the same engine.
- Companions `setStack([imageUrl])` and mirror the primary viewport's `voiRange` + `invert` via `setProperties` whenever the primary fires `IMAGE_RENDERED` (covers both preset applies and interactive WW/WC drags). ⚠️ They do **not** mirror zoom/camera — only W/L + invert (despite what the component's own comment claims).
- The grid container uses `display: contents` so the cells slot into the parent CSS grid as normal items — preserve this when changing layout CSS or tiling breaks.
- Each companion viewport gets its own id; teardown disables every id (shared-engine leak prevention).
- Standard clinical W/L values ship as the empty-modality default set — e.g. Brain 40/80, Subdural 80/200, Stroke 40/40, Bone 400/2000, Lung −600/1500, Abdomen/Pelvis 50/400. Use these when defining modality defaults.

## 7. DICOMweb Integration (`api/studies.ts`)

- Build WADO-RS URLs with the `wadors:` scheme so the image loader routes through it:
  ```ts
  `wadors:${API_URL}/dicomweb/studies/${studyUid}/series/${seriesUid}/instances/${instanceUid}`
  ```
- All DICOMweb fetches (WADO + STOW + archive) need `X-CSRF-Token: 1`, `X-Auth-Pacs: <token>`, `X-Tenant-ID: <tenant_id>`.
- STOW-RS upload: assemble `multipart/related; type=application/dicom; boundary=...` by hand (FormData would re-encode the files). Each part header carries `Content-Type: application/dicom` + `Content-Length`.
- QIDO-RS responses are mapped through tag-key accessors: `raw["0020000D"]?.Value?.[0]` with snake_case DB column fallbacks (`study_instance_uid`).

## 8. Performance & Robustness Rules (all verified in this codebase)

1. **Coalesce render events** — `IMAGE_RENDERED` fires per frame during cine/WL drags. Use `requestAnimationFrame` with a "pending" guard to collapse bursts to ≤1 `setState`/frame.
2. **Write transient overlays straight to the DOM** — zoom / WW/WC readouts are `ref.textContent` updates, and React state only commits when the *rounded* value actually changes (screen readers hear meaningful transitions, not per-frame noise).
3. **`cache.purgeCache()` on stack swap** — decoded pixels must not accumulate across series.
4. **`disposedRef` guards everywhere** — every async continuation, interval, and poll checks it before touching the engine.
5. **Bounded polling** — never loop forever for viewport readiness; cap attempts and bail on unmount.
6. **Never steal keys from overlays** — the keyboard handler ignores input/`contentEditable` targets and elements inside `.ant-select, .ant-drawer, .ant-collapse, [role='dialog'], [role='menu']`.
7. **Surface load failures with the error overlay** — `setStack` rejection and init failure set `viewportError` (rendered as a `role="alert"` overlay with the close icon); clear it on the next successful stack load.

## Keyboard Shortcuts (match these)

| Key | Action | Key | Action |
|---|---|---|---|
| `1`–`6` | Pan / Length / Rect / Ellipse / Angle / Arrow | `r` (also `R`) | Rotate 90° |
| `7` / `e` | Eraser | `8` | Cobb angle (scoliosis) |
| `9` | Probe (pixel value readout) | `0` | Circle ROI |
| `h` / `v` | Flip horizontal / vertical | | |
| `i` | Invert | `p` | Cycle W/L preset |
| `l` | Cycle layout | `s` | Save annotations |
| `c` | Clear annotations | `f` / `Esc` | Fullscreen toggle |
| `←` / `→` | Prev / next image | `+` / `-` | Zoom in / out |
| `?` | Help | | |

## Common Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| All image fetches 401 | Loader XHR missing auth | `beforeSend` in `initDicomImageLoader` (Section 1) |
| Memory grows browsing a study | Decoded pixels retained | `cache.purgeCache()` before `setStack` (Section 2) |
| Leaked viewports / double renders after unmount | Async continuations not guarded | `disposedRef` + remove every listener (Section 2) |
| Keyboard shortcuts fire while typing in a Select | Key handler steals keys | Skip `INPUT`/`TEXTAREA`/antd-overlay targets (Section 8) |
| WW/WC drag is janky | `setState` per render event | rAF coalescing + DOM overlay writes (Section 8) |
| Annotations lost on reload | Not persisted | `persistToolsState` → `files/{id}` `tools_state` (Section 5) |
| Tool group never receives events | Viewport not added to group | `tg.addViewport(viewportId, ENGINE_ID)` (Section 2) |

## Related Skills

- **dicom-web-query**: DICOMweb QIDO/WADO/STOW REST operations (backend/protocol side)
- **pacs-workflow**: PACS query/retrieve, worklists, modality workflows
- **pydicom**: Server-side DICOM parsing, metadata, anonymization
