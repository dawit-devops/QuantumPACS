import { test, expect } from '@playwright/test';

const BASE = 'http://localhost:5173';

test.describe('Protected Routes', () => {
  test('redirects unauthenticated users to login for /', async ({ page }) => {
    await page.goto(BASE, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);
    await expect(page).toHaveURL(/\/login/);
  });

  test('redirects unauthenticated users to login for /metrics', async ({ page }) => {
    await page.goto(`${BASE}/metrics`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);
    await expect(page).toHaveURL(/\/login/);
  });

  test('redirects unauthenticated users to login for /users', async ({ page }) => {
    await page.goto(`${BASE}/users`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);
    await expect(page).toHaveURL(/\/login/);
  });

  test('redirects unauthenticated users to login for /roles', async ({ page }) => {
    await page.goto(`${BASE}/roles`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);
    await expect(page).toHaveURL(/\/login/);
  });

  test('redirects unauthenticated users to login for /tenants', async ({ page }) => {
    await page.goto(`${BASE}/tenants`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);
    await expect(page).toHaveURL(/\/login/);
  });
});
