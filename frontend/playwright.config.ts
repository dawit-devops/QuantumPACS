import { existsSync } from 'node:fs';
import { defineConfig } from '@playwright/test';

// Dev machines install Google Chrome at a fixed path; CI installs Playwright's
// own Chromium instead, so only pin the system binary when it is present.
const hasSystemChrome = existsSync('/usr/bin/google-chrome');

export default defineConfig({
  testDir: './e2e',
  timeout: 60000,
  retries: 1,
  use: {
    browserName: 'chromium',
    headless: true,
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
    launchOptions: {
      executablePath: hasSystemChrome ? '/usr/bin/google-chrome' : undefined,
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
          executablePath: hasSystemChrome ? '/usr/bin/google-chrome' : undefined,
          args: ['--no-sandbox', '--disable-setuid-sandbox'],
        },
      },
    },
  ],
});
