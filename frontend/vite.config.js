/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
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
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (
            id.includes("node_modules/react") ||
            id.includes("node_modules/react-dom") ||
            id.includes("node_modules/react-router")
          )
            return "vendor-react";
          if (
            id.includes("node_modules/antd") ||
            id.includes("node_modules/@ant-design")
          )
            return "vendor-antd";
          if (
            id.includes("node_modules/cornerstone") ||
            id.includes("node_modules/@cornerstonejs") ||
            id.includes("node_modules/dicom-parser") ||
            id.includes("node_modules/hammerjs")
          )
            return "vendor-cornerstone";
          if (
            id.includes("node_modules/chart.js") ||
            id.includes("node_modules/react-chartjs-2")
          )
            return "vendor-chart";
        },
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
      thresholds: {
        functions: 32,
        lines: 42,
        branches: 31,
        statements: 38,
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
