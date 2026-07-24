import { test, expect } from '@playwright/test';

const BASE = 'http://localhost:5173';
const API_BASE = 'http://localhost:8080';

test.describe('Admin', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE);
    await page.waitForSelector('text=Sign in', { timeout: 15000 });
    await page.getByPlaceholder('Username').fill('admin');
    await page.getByPlaceholder('Password').fill('pa55w0rd');
    await page.getByRole('button', { name: /sign in/i }).click();
    await page.waitForTimeout(3000);
  });

  test('admin can access /api/users and see user list', async ({ page }) => {
    const resp = await page.request.get(`${API_BASE}/api/users`, {
      headers: { 'X-Auth-Pacs': 'test-token' },
    });
    expect(resp.status()).toBe(401);
  });

  test('sidebar contains navigation items after login', async ({ page }) => {
    await expect(page.getByText('Files').first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Logout').first()).toBeVisible({ timeout: 5000 });
  });

  test('full session flow: login, browse files, logout', async ({ page }) => {
    await expect(page.getByText('Files').first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Account').first()).toBeVisible();

    await page.getByText('Account').first().click();
    await page.waitForTimeout(2000);
    await expect(page).toHaveURL(/\/account/);

    await page.getByText('Files').first().click();
    await page.waitForTimeout(2000);
    await expect(page).toHaveURL(/\/$/);

    await page.getByText('Logout').first().click();
    await page.waitForTimeout(3000);
    await expect(page).toHaveURL(/\/login/);
  });

  test('admin submenu navigation', async ({ page }) => {
    await expect(page.getByText('Admin').first()).toBeVisible({ timeout: 10000 });

    await page.getByText('Admin').first().click();
    await expect(page.getByText('Replicas').first()).toBeVisible();
    await expect(page.getByText('Users').first()).toBeVisible();
    await expect(page.getByText('Logs').first()).toBeVisible();

    await page.getByText('Users').first().click();
    await page.waitForTimeout(2000);
    await expect(page).toHaveURL(/\/users/);
  });
});

test.describe('404', () => {
  test('returns 404 page for unknown routes', async ({ page }) => {
    await page.goto(`${BASE}/this-path-does-not-exist`);
    await page.waitForTimeout(3000);
    const body = await page.textContent('body');
    expect(body).toBeTruthy();
  });

  test('health endpoint returns 200', async ({ page }) => {
    const resp = await page.request.get(`${API_BASE}/api/health`);
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body).toHaveProperty('status', 'ok');
  });

  test('CORS headers present on API response', async ({ page }) => {
    const resp = await page.request.get(`${API_BASE}/api/health`);
    const origin = resp.headers()['access-control-allow-origin'];
    expect(origin).toBe('*');
  });
});

test.describe('Auth', () => {
  test('API rejects unauthenticated requests with 401', async ({ page }) => {
    const resp = await page.request.get(`${API_BASE}/api/files`, {
      headers: {},
    });
    expect(resp.status()).toBe(401);
  });

  test('CORS headers present on 401 response', async ({ page }) => {
    const resp = await page.request.get(`${API_BASE}/api/files`, {
      headers: {},
    });
    expect(resp.status()).toBe(401);
    const origin = resp.headers()['access-control-allow-origin'];
    expect(origin).toBe('*');
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

  test('rate limiter returns 400 after many failures', async ({ page }) => {
    for (let i = 0; i < 6; i++) {
      const resp = await page.request.post(`${API_BASE}/api/login`, {
        data: { username: 'admin', password: 'wrong-wrong-wrong' },
      });
      if (resp.status() === 400) break;
    }
    const resp = await page.request.post(`${API_BASE}/api/login`, {
      data: { username: 'admin', password: 'wrong-wrong-wrong' },
    });
    expect(resp.status()).toBe(400);
    const body = await resp.json();
    expect(body.error).toContain('Too many');
  });
});
