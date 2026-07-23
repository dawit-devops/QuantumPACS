import { test, expect } from '@playwright/test';

const BASE = 'http://localhost:5173';

test.describe('Login', () => {
  test('renders login page with QuantumPACS branding', async ({ page }) => {
    await page.goto(BASE);
    await page.waitForSelector('text=Sign in to your account', { timeout: 15000 });
    await expect(page).toHaveTitle(/QuantumPACS/);
    await expect(page.getByText('QuantumPACS v1.0')).toBeVisible();
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
  });

  test('logs in with admin credentials', async ({ page }) => {
    await page.goto(BASE);
    await page.waitForSelector('text=Sign in', { timeout: 15000 });
    await page.getByPlaceholder('Username').fill('admin');
    await page.getByPlaceholder('Password').fill('pa55w0rd');
    await page.getByRole('button', { name: /sign in/i }).click();
    await page.waitForTimeout(3000);
    await expect(page.getByText('Password is not correct')).toBeHidden({ timeout: 15000 });
  });

  test('rejects wrong password with error message', async ({ page }) => {
    await page.goto(BASE);
    await page.waitForSelector('text=Sign in', { timeout: 15000 });
    await page.getByPlaceholder('Username').fill('admin');
    await page.getByPlaceholder('Password').fill('wrongpass');
    await page.getByRole('button', { name: /sign in/i }).click();
    await expect(page.getByText('Password is not correct')).toBeVisible({ timeout: 15000 });
  });
});
