import { test, expect } from '@playwright/test';
import { clearAndGo, loginAsAdmin } from './helpers';

const API_BASE = 'http://localhost:8080';

test.describe('Admin UI', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('sidebar contains navigation items after login', async ({ page }) => {
    await expect(page.getByText('Files').first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Logout').first()).toBeVisible({ timeout: 5000 });
  });

  test('full session flow: login, browse files, logout', async ({ page }) => {
    await expect(page.getByText('Files').first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Account').first()).toBeVisible();

    await page.getByText('Account').first().click();
    await expect(page).toHaveURL(/\/account/, { timeout: 10000 });

    await page.getByText('Files').first().click();
    await expect(page).toHaveURL(/\/$/, { timeout: 10000 });

    await page.getByText('Logout').first().click();
    await expect(page).toHaveURL(/\/login/, { timeout: 15000 });
    await expect(page.getByText('Sign in to your account')).toBeVisible({ timeout: 10000 });
  });

  test('admin submenu navigation', async ({ page }) => {
    await page.getByText('Admin').first().click();
    const items = ['Replicas', 'Users', 'Logs', 'Roles'];
    for (const item of items) {
      await expect(page.getByText(item).first()).toBeVisible({ timeout: 5000 });
    }

    await page.getByText('Users').first().click();
    await expect(page).toHaveURL(/\/users/, { timeout: 10000 });
  });
});

test.describe('API Integration', () => {
  test('health endpoint returns 200', async ({ page }) => {
    const resp = await page.request.get(`${API_BASE}/api/health`);
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(['ok', 'degraded']).toContain(body.status);
  });

  test('CORS headers present on API response', async ({ page }) => {
    const resp = await page.request.get(`${API_BASE}/api/health`);
    expect(resp.headers()['access-control-allow-origin']).toBeTruthy();
  });

  test('API rejects unauthenticated requests with 401', async ({ page }) => {
    const resp = await page.request.get(`${API_BASE}/api/files`);
    expect(resp.status()).toBe(401);
  });

  test('API accepts X-Auth-Pacs header with valid token', async ({ page }) => {
    const resp = await page.request.post(`${API_BASE}/api/login`, {
      data: { username: 'admin', password: 'pa55w0rd' },
    });
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body).toHaveProperty('token');

    const filesResp = await page.request.get(`${API_BASE}/api/files`, {
      headers: { 'X-Auth-Pacs': body.token },
    });
    expect(filesResp.status()).toBe(200);
  });
});
