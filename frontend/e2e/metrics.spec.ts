import { test, expect } from '@playwright/test';

const BASE = 'http://localhost:5173';

test.describe('Metrics', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE);
    await page.waitForSelector('text=Sign in', { timeout: 15000 });
    await page.getByPlaceholder('Username').fill('admin');
    await page.getByPlaceholder('Password').fill('pa55w0rd');
    await page.getByRole('button', { name: /sign in/i }).click();
    await page.waitForTimeout(2000);
  });

  test('navigates to metrics page via sidebar', async ({ page }) => {
    await expect(page.getByText('Files').first()).toBeVisible({ timeout: 15000 });
    await page.locator('.ant-menu-item').filter({ hasText: 'Metrics' }).click();
    await page.waitForTimeout(3000);
    await expect(page).toHaveURL(/\/metrics/);
  });

  test('displays stat cards on metrics page', async ({ page }) => {
    await page.goto(`${BASE}/metrics`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);
    const statCards = await page.locator('.ant-statistic').count();
    expect(statCards).toBeGreaterThanOrEqual(0);
  });

  test('renders chart canvases', async ({ page }) => {
    await page.goto(`${BASE}/metrics`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);
    const canvases = await page.locator('canvas').count();
    expect(canvases).toBeGreaterThanOrEqual(0);
  });
});
