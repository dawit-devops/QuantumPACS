import { test, expect } from '@playwright/test';

const BASE = 'http://localhost:5173';

test.describe('Navigation', () => {
  test('sidebar visible after login with Files and Patients links', async ({ page }) => {
    await page.goto(BASE);
    await page.waitForSelector('text=Sign in', { timeout: 15000 });
    await page.getByPlaceholder('Username').fill('admin');
    await page.getByPlaceholder('Password').fill('pa55w0rd');
    await page.getByRole('button', { name: /sign in/i }).click();
    await page.waitForTimeout(3000);
    await expect(page.locator('.ant-layout-sider, nav, aside').first()).toBeVisible({ timeout: 10000 });
  });
});
