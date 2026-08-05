import { test, expect } from '@playwright/test';
import { clearAndGo } from './helpers';

test.describe('Login Flow', () => {
  test('renders login page with branding', async ({ page }) => {
    await clearAndGo(page);
    await expect(page.getByText('Sign in to your account')).toBeVisible({ timeout: 15000 });
    await expect(page).toHaveTitle(/QuantumPACS/);
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
  });

  test('logs in with admin credentials and lands on files page', async ({ page }) => {
    await clearAndGo(page);
    await page.getByPlaceholder('Username').fill('admin');
    await page.getByPlaceholder('Password').fill('pa55w0rd');
    await page.getByRole('button', { name: /sign in/i }).click();
    await expect(page).toHaveURL(/\/$/, { timeout: 15000 });
    await expect(page.getByText('Search Studies').first()).toBeVisible({ timeout: 15000 });
  });

  test('stays on login page with wrong password', async ({ page }) => {
    await clearAndGo(page);
    await page.getByPlaceholder('Username').fill('admin');
    await page.getByPlaceholder('Password').fill('wrongpass');
    await page.getByRole('button', { name: /sign in/i }).click();
    await page.waitForTimeout(5000);
    await expect(page).toHaveURL(/\/login/, { timeout: 15000 });
    await expect(page.getByText('Sign in to your account')).toBeVisible();
  });

  test('redirects unauthenticated user to login', async ({ page }) => {
    await page.goto('http://localhost:5173/users', { waitUntil: 'networkidle' });
    await expect(page).toHaveURL(/\/login/, { timeout: 15000 });
  });
});
