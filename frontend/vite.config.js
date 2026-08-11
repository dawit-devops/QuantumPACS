/// <reference types="vitest" />
import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  // xmlbuilder2 in the Cornerstone3D dependency graph extends Node's
  // EventEmitter at module scope; Vite externalizes Node builtins to an
  // empty proxy, which makes the class declaration throw and kills the whole
  // prebundled cornerstone chunk. Alias the builtin to the bundled polyfill
  // (src/vendor/events.js) so both the dev optimizer and the build resolve it.
  resolve: {
    alias: {
      events: fileURLToPath(new URL("./src/vendor/events.js", import.meta.url)),
    },
  },
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      selfDestroying: true,
      includeAssets: ["pwa-192x192.png", "pwa-512x512.png"],
      manifest: {
        name: "QuantumPACS",
        short_name: "QuantumPACS",
        description: "Medical Image Management System",
        theme_color: "#1677ff",
        background_color: "#f8f9fa",
        display: "standalone",
        scope: "/",
        start_url: "/",
        icons: [
          { src: "pwa-192x192.png", sizes: "192x192", type: "image/png" },
          { src: "pwa-512x512.png", sizes: "512x512", type: "image/png" },
        ],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,png,svg}"],
        maximumFileSizeToCacheInBytes: 6 * 1024 * 1024,
      },
    }),
  ],
  build: {
    // Keep the default 500 kB signal so oversized chunks surface as
    // warnings instead of being silently tolerated (the previous 1200
    // masked the 3.6MB eager cornerstone chunk now removed). antd still
    // exceeds it, and the lazy CornerstoneElement chunk (see below) will
    // warn too — that one is EXPECTED: it only loads on the Detail route,
    // so do not "fix" it by re-adding an eager vendor-cornerstone chunk.
    chunkSizeWarningLimit: 500,
    rollupOptions: {
      output: {
        // Rolldown's native chunking. Two group kinds are combined:
        //   1. test-based groups (priority, force capture) — used ONLY for the
        //      preload helper, because plain manualChunks cannot move Vite's
        //      \0-virtual modules (assignments are silently ignored).
        //   2. a single name-function group that mirrors the classic
        //      manualChunks() API for everything else — verified to produce
        //      the exact 4-way cornerstone split and the react/antd/icons
        //      vendor chunks.
        // This hybrid exists because each mechanism alone is insufficient
        // (both verified empirically on this project):
        //   - test-groups alone: the cornerstone packages are only reachable
        //     from the lazy Detail route, and Rolldown's default chunking
        //     treats such lazy-only modules as shared, merging the whole
        //     stack into one 3MB loader chunk (the core/tools/loader/codecs
        //     split collapses).
        //   - manualChunks alone: Vite's \0-virtual preload helper lands in a
        //     cornerstone chunk, and the eager entry needs it, so all four
        //     sub-chunks get statically imported into the eager modulepreload
        //     graph (the original ~1MB-gzip-on-every-page regression).
        // The priority-100 test group forces the helper out; the name-function
        // group preserves the proven 4-way split for everything else.
        codeSplitting: {
          groups: [
            // Vite's __vitePreload helper is needed by BOTH the eager entry
            // (for every lazy route) and lazy chunks that dynamically import
            // further chunks (the codec workers). If it lands inside a vendor
            // chunk, the entry must statically import that chunk to reach the
            // helper — dragging the ENTIRE chunk into the eager modulepreload
            // graph (the loader chunk once pulled all four cornerstone
            // sub-chunks onto every page load). Force it into a tiny
            // dedicated chunk so eager pages only ever fetch that ~1kB helper.
            {
              name: "vendor-runtime",
              test: (id) =>
                id.includes("preload-helper") ||
                id.includes("modulepreload-polyfill"),
              priority: 100,
            },
            // Everything else: same logic as the manualChunks() function this
            // config previously used. Returns a chunk name per module, or
            // null to leave the module to automatic chunking (chart.js and
            // the lazy routes' own code ride their route chunks).
            {
              name: (id) => {
                if (
                  id.includes("node_modules/react") ||
                  id.includes("node_modules/react-dom") ||
                  id.includes("node_modules/react-router")
                )
                  return "vendor-react";
                if (id.includes("node_modules/antd")) return "vendor-antd";
                // Icons are a large share of antd's surface and change far
                // less often than components — a dedicated chunk improves
                // cache reuse (icon updates don't invalidate the antd chunk).
                if (id.includes("node_modules/@ant-design/icons"))
                  return "vendor-antd-icons";
                // Cornerstone3D stack: split into four sub-chunks along the
                // same package boundaries the npm modules ship as (core <-
                // tools, core <- dicom-image-loader <- codecs). All four are
                // only reachable from the lazy Detail route's
                // CornerstoneElement graph, so none of them appear in
                // index.html's eager modulepreload list — the browser fetches
                // them in parallel when the viewer opens, and a codec/tools
                // update no longer invalidates the core chunk's cache.
                // Do NOT merge these back into one vendor-cornerstone chunk:
                // that recreates a 3.6MB single download and re-triggers the
                // helper-allocation bug that dragged it eagerly onto every
                // page.
                if (id.includes("node_modules/@cornerstonejs/codec-"))
                  return "vendor-cornerstone-codecs";
                if (
                  id.includes(
                    "node_modules/@cornerstonejs/dicom-image-loader",
                  ) ||
                  id.includes("node_modules/dicom-parser")
                )
                  return "vendor-cornerstone-loader";
                if (
                  id.includes("node_modules/@cornerstonejs/tools") ||
                  id.includes("node_modules/hammerjs")
                )
                  return "vendor-cornerstone-tools";
                if (
                  id.includes("node_modules/@cornerstonejs/core") ||
                  id.includes("node_modules/@cornerstonejs/utils") ||
                  id.includes("node_modules/@cornerstonejs/metadata") ||
                  id.includes("node_modules/@cornerstonejs/calculate-suv")
                )
                  return "vendor-cornerstone-core";
                // chart.js/react-chartjs-2: only AdminDashboard and Metrics
                // (both lazy routes) import them, so no manual chunk — letting
                // them ride in the route chunks keeps them off the eager
                // graph entirely.
                return null;
              },
            },
          ],
        },
        // Keep an eye on index.html's modulepreload list after any future
        // codeSplitting tweak — shared runtime helpers may land in a big
        // vendor chunk and silently drag it (and everything it imports) into
        // the eager graph again. A regression shows up as a cornerstone chunk
        // appearing in the modulepreload list.
      },
    },
  },
  // Pre-bundle the heavy ESM vendor tree once at dev-server start so first
  // page loads (and cold transforms) don't pay per-import costs for antd and
  // the Cornerstone3D stack.
  optimizeDeps: {
    include: [
      "react",
      "react-dom",
      "react-router",
      "antd",
      "@ant-design/icons",
      "@cornerstonejs/core",
      "@cornerstonejs/tools",
      "@cornerstonejs/dicom-image-loader",
      "dicom-parser",
      "hammerjs",
      // Emscripten codec factory modules (decodewasmjs) are UMD bundles with
      // no ESM `default` export. The decode worker imports them bare, so they
      // must go through the dep optimizer's CJS->ESM interop instead of being
      // served raw from node_modules (raw serving kills the worker module
      // graph with "does not provide an export named 'default'").
      "@cornerstonejs/codec-libjpeg-turbo-8bit/decodewasmjs",
      "@cornerstonejs/codec-charls/decodewasmjs",
      "@cornerstonejs/codec-openjpeg/decodewasmjs",
      "@cornerstonejs/codec-openjph/wasmjs",
    ],
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      // WS upgrade support: the socket lives under /api/ws and the backend
      // rejects non-upgrade requests, so this must be ws-capable.
      "/api": {
        target: "http://localhost:8080",
        ws: true,
        // Rewrite Host to the target so TrustedHostMiddleware (localhost-only)
        // accepts proxied requests from any dev origin (LAN/docker IPs).
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    environmentOptions: {
      jsdom: {
        pretendToBeVisual: true,
      },
    },
    setupFiles: "./src/test/setup.ts",
    // Heavy antd+jsdom suite flakes under parallel CPU load (waitFor 1s
    // defaults); retry absorbs contention without weakening assertions.
    retry: 2,
    // Memory-constrained dev box: 2 forks instead of 3, compensated with a
    // generous per-test timeout so slow-but-correct tests never flake.
    maxForks: 2,
    minForks: 1,
    maxConcurrency: 2,
    testTimeout: 240000,
    hookTimeout: 120000,
    exclude: ["node_modules/**", "e2e/**", "dist/**"],
    // jsdom tests never assert on real CSS; skipping the transform avoids
    // re-parsing the antd stylesheet tree per fork (major time sink).
    css: false,
    // Speed: match the dep optimizer cache to the dev server and let jsdom
    // reuse the pre-bundled antd/cornerstone graph instead of re-transforming
    // it in every fork.
    server: {
      deps: {
        optimizer: {
          web: {
            include: [
              "react",
              "react-dom",
              "react-router",
              "antd",
              "@ant-design/icons",
              "@cornerstonejs/core",
              "@cornerstonejs/tools",
              "@cornerstonejs/dicom-image-loader",
              "dicom-parser",
              "hammerjs",
            ],
          },
        },
      },
    },
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      include: ["src/**"],
      exclude: ["src/test/**", "src/types.d.ts"],
      // M4: measured 2026-08-10 — lines 60.35%, statements 58.17%,
      // functions 52.09%, branches 50.22% (543 tests, 67 files). Thresholds
      // sit ~2 points under the local measurement to absorb CI runner
      // variance while still gating well above the old 42/31/32/38 floor.
      thresholds: {
        functions: 50,
        lines: 58,
        branches: 48,
        statements: 56,
      },
    },
    pool: "forks",
    singleFork: false,
    // Memory-constrained boxes: 2 forks, generous timeouts, retries absorb
    // the antd+jsdom waitFor flakes that appear under parallel load.
    fileParallelism: true,
  },
  define: {
    "process.env": {},
  },
});
