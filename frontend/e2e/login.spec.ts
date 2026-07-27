import { test, expect } from '@playwright/test';
import { BASE, API_BASE, loginViaForm } from './helpers';

test.describe('Login', () => {
  test('renders login page with QuantumPACS branding', async ({ page }) => {
    await page.goto(BASE);
    await page.waitForSelector('text=Sign in to your account', { timeout: 15000 });
    await expect(page).toHaveTitle(/QuantumPACS/);
    await expect(page.getByText('QuantumPACS v1.0')).toBeVisible();
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
  });

  test('logs in with admin credentials and redirects to home', async ({ page }) => {
    await page.goto(BASE);
    await page.waitForSelector('text=Sign in', { timeout: 15000 });
    await page.getByPlaceholder('Username').fill('admin');
    await page.getByPlaceholder('Password').fill('pa55w0rd');
    await page.getByRole('button', { name: /sign in/i }).click();
    await expect(page.getByText('Files').first()).toBeVisible({ timeout: 20000 });
  });

  test('shows error on wrong password', async ({ page }) => {
    await page.goto(BASE);
    await page.waitForSelector('text=Sign in', { timeout: 15000 });
    await page.getByPlaceholder('Username').fill('admin');
    await page.getByPlaceholder('Password').fill('wrongpass');
    await page.getByRole('button', { name: /sign in/i }).click();
    await expect(page.locator('[data-testid="login-error"]')).toBeVisible({ timeout: 15000 });
    await expect(page.locator('[data-testid="login-error"]')).toContainText(/password/i);
  });

  test('logs out and redirects to login page', async ({ page }) => {
    await loginViaForm(page);
    await page.getByText('Logout').first().click();
    await page.waitForTimeout(2000);
    await expect(page).toHaveURL(/\/login/);
  });

  test('login API returns valid token', async ({ page }) => {
    const resp = await page.request.post(`${API_BASE}/api/login`, {
      data: { username: 'admin', password: 'pa55w0rd' },
    });
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body).toHaveProperty('token');
    expect(body).toHaveProperty('id');
    expect(body).toHaveProperty('admin', true);
  });

  test('API rejects unauthenticated requests with 401', async ({ page }) => {
    const resp = await page.request.get(`${API_BASE}/api/files`, { headers: {} });
    expect(resp.status()).toBe(401);
  });

  test('API accepts X-Auth-Pacs header with valid token', async ({ page }) => {
    const loginResp = await page.request.post(`${API_BASE}/api/login`, {
      data: { username: 'admin', password: 'pa55w0rd' },
    });
    const { token } = await loginResp.json();
    const filesResp = await page.request.get(`${API_BASE}/api/files`, {
      headers: { 'X-Auth-Pacs': token },
    });
    expect(filesResp.status()).toBe(200);
  });
});
