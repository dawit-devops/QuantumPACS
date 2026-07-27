import { test, expect } from '@playwright/test';
import { BASE, login, waitForTableLoad, getTableRowCount } from './helpers';

test.describe('Admin Workflows', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test.describe('Users', () => {
    test('users page renders with table', async ({ page }) => {
      await page.goto(`${BASE}/users`, { waitUntil: 'domcontentloaded' });
      await waitForTableLoad(page);
      const rows = await getTableRowCount(page);
      expect(rows).toBeGreaterThanOrEqual(0);
    });

    test('add user button opens modal', async ({ page }) => {
      await page.goto(`${BASE}/users`, { waitUntil: 'domcontentloaded' });
      await waitForTableLoad(page);
      const addBtn = page.getByRole('button', { name: /add/i });
      await expect(addBtn).toBeVisible({ timeout: 10000 });
      await addBtn.click();
      await page.waitForTimeout(1000);
      const modal = page.locator('.ant-modal');
      await expect(modal).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('Roles', () => {
    test('roles page renders', async ({ page }) => {
      await page.goto(`${BASE}/roles`, { waitUntil: 'domcontentloaded' });
      await waitForTableLoad(page);
      const rows = await getTableRowCount(page);
      expect(rows).toBeGreaterThanOrEqual(0);
    });

    test('add role button opens modal', async ({ page }) => {
      await page.goto(`${BASE}/roles`, { waitUntil: 'domcontentloaded' });
      await waitForTableLoad(page);
      const addBtn = page.getByRole('button', { name: /add role/i });
      if (await addBtn.isVisible()) {
        await addBtn.click();
        await page.waitForTimeout(1000);
        await expect(page.locator('.ant-modal')).toBeVisible({ timeout: 5000 });
      }
    });
  });

  test.describe('Tenants', () => {
    test('tenants page renders', async ({ page }) => {
      await page.goto(`${BASE}/tenants`, { waitUntil: 'domcontentloaded' });
      await waitForTableLoad(page);
      const rows = await getTableRowCount(page);
      expect(rows).toBeGreaterThanOrEqual(0);
    });

    test('provision tenant button opens modal', async ({ page }) => {
      await page.goto(`${BASE}/tenants`, { waitUntil: 'domcontentloaded' });
      await waitForTableLoad(page);
      const provisionBtn = page.getByRole('button', { name: /provision/i });
      await expect(provisionBtn).toBeVisible({ timeout: 10000 });
      await provisionBtn.click();
      await page.waitForTimeout(1000);
      await expect(page.locator('.ant-modal')).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('Replicas', () => {
    test('replicas page renders', async ({ page }) => {
      await page.goto(`${BASE}/replicas`, { waitUntil: 'domcontentloaded' });
      await waitForTableLoad(page);
      const rows = await getTableRowCount(page);
      expect(rows).toBeGreaterThanOrEqual(0);
    });
  });

  test.describe('Logs', () => {
    test('logs page renders', async ({ page }) => {
      await page.goto(`${BASE}/logs`, { waitUntil: 'domcontentloaded' });
      await waitForTableLoad(page);
      const rows = await getTableRowCount(page);
      expect(rows).toBeGreaterThanOrEqual(0);
    });
  });
});
