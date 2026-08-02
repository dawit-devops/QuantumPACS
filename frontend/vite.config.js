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
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      // WS upgrade support: the socket lives under /api/ws and the backend
      // rejects non-upgrade requests, so this must be ws-capable.
      "/api": {
        target: "http://localhost:8080",
        ws: true,
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
    testTimeout: 120000,
    hookTimeout: 60000,
    exclude: ["node_modules/**", "e2e/**", "dist/**"],
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
    maxForks: 4,
    minForks: 1,
    fileParallelism: true,
    maxConcurrency: 4,
    retry: 0,
  },
  define: {
    "process.env": {},
  },
});
