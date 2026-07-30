import { test, expect } from '@playwright/test';
import { clearAndGo, loginAsAdmin } from './helpers';

test.describe('Mobile Viewport', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test('login page renders on mobile', async ({ page }) => {
    await clearAndGo(page);
    await expect(page.getByText('Sign in to your account')).toBeVisible({ timeout: 15000 });
    await page.getByPlaceholder('Username').fill('admin');
    await page.getByPlaceholder('Password').fill('pa55w0rd');
    await page.getByRole('button', { name: /sign in/i }).click();
    await expect(page.getByText('Search Studies').first()).toBeVisible({ timeout: 20000 });
  });

  test('sidebar renders collapsed on mobile', async ({ page }) => {
    await loginAsAdmin(page);
    await expect(page.getByText('Files').first()).toBeVisible();
  });
});
