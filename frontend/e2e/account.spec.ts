import { test, expect } from '@playwright/test';

const BASE = 'http://localhost:5173';

test.describe('Account', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE);
    await page.waitForSelector('text=Sign in', { timeout: 15000 });
    await page.getByPlaceholder('Username').fill('admin');
    await page.getByPlaceholder('Password').fill('pa55w0rd');
    await page.getByRole('button', { name: /sign in/i }).click();
    await page.waitForTimeout(2000);
  });

  test('navigates to account page', async ({ page }) => {
    await page.getByText('Account').first().click();
    await page.waitForTimeout(3000);
    await expect(page).toHaveURL(/\/account/);
  });

  test('shows password change form', async ({ page }) => {
    await page.goto(`${BASE}/account`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);
    await expect(page.getByText('Change password').first()).toBeVisible({ timeout: 10000 });
  });

  test('account form has password fields', async ({ page }) => {
    await page.goto(`${BASE}/account`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);
    await expect(page.getByPlaceholder('Password').first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByPlaceholder('Password repeated').first()).toBeVisible({ timeout: 5000 });
    await expect(page.getByRole('button', { name: /change password/i })).toBeVisible({ timeout: 5000 });
  });
});
