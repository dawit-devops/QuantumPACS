import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  // Full-session flows (login + browse + logout) exceed 60s when the suite
  // starts with all workers logging in at once; 90s keeps headroom without
  // masking real hangs.
  timeout: 90000,
  retries: 1,
  use: {
    browserName: 'chromium',
    headless: true,
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
    launchOptions: {
      args: ['--no-sandbox', '--disable-setuid-sandbox'],
    },
  },
  projects: [
    {
      name: 'chromium',
      use: {
        browserName: 'chromium',
        viewport: { width: 1280, height: 720 },
        launchOptions: {
          // CI installs the Playwright-bundled chromium; local runs reuse
          // the system chrome (which may be a different build).
          executablePath: process.env.CI ? undefined : '/usr/bin/google-chrome',
          args: ['--no-sandbox', '--disable-setuid-sandbox'],
        },
      },
    },
  ],
});
