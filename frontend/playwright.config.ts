import { defineConfig } from "@playwright/test";

// Prefer E2E_BASE_URL in CI (the job may serve a built preview); fall back to
// the dev server the webServer block starts (or reuses) locally.
const baseURL = process.env.E2E_BASE_URL || "http://localhost:5173";

const chromiumArgs = [
  "--no-sandbox",
  "--disable-setuid-sandbox",
  "--disable-dev-shm-usage",
];

export default defineConfig({
  testDir: "./e2e",
  // Backend logins run PBKDF2-SHA256 with 600k iterations (~3.5s per call on
  // a slow dev box); several specs log in concurrently, so the budget must
  // cover the serialized CPU-bound hash time plus page hydration.
  timeout: 90000,
  retries: 1,
  // Two workers keep the suite gentle on 3-core dev boxes (three chromium
  // instances + desktop apps saturate it); CI keeps the default (one worker
  // per core of the runner).
  workers: process.env.CI ? undefined : 2,
  fullyParallel: true,
  reporter: "line",
  expect: {
    timeout: 10000,
  },
  use: {
    baseURL,
    headless: true,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    actionTimeout: 15000,
    launchOptions: {
      args: chromiumArgs,
    },
  },
  // Start (or reuse) the Vite dev server so specs never depend on a manually
  // running server; CI reuses it too and only needs the backend booted. The
  // `preview` project below overrides this with the production build.
  webServer: {
    command: "npm run start",
    url: baseURL,
    reuseExistingServer: true,
    timeout: 120000,
  },
  projects: [
    {
      name: "chromium",
      use: {
        browserName: "chromium",
        viewport: { width: 1280, height: 720 },
        launchOptions: {
          args: chromiumArgs,
        },
      },
    },
    {
      // CI runs --project=preview: it builds the app and serves the built
      // artifact via `vite preview` (preview inherits server.proxy, so /api
      // still reaches the backend), then waits on port 4173. Local dev
      // workflow keeps the 5173 dev server via the default `chromium` project.
      name: "preview",
      use: {
        browserName: "chromium",
        baseURL: "http://localhost:4173",
        viewport: { width: 1280, height: 720 },
        launchOptions: {
          args: chromiumArgs,
        },
      },
      webServer: {
        command: "npm run build && npm run preview",
        url: "http://localhost:4173",
        reuseExistingServer: false,
        // Build takes ~1 min on CI runners; give it generous headroom.
        timeout: 300000,
      },
    },
    {
      // Optional extra coverage — CI gates on chromium/preview only; run
      // locally with `npm run test:e2e:all` (requires `npx playwright install
      // firefox`).
      name: "firefox",
      use: {
        browserName: "firefox",
        viewport: { width: 1280, height: 720 },
      },
    },
  ],
});
