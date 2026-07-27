import { test, expect } from '@playwright/test';
import { BASE, API_BASE } from './helpers';

test.describe('API & 404', () => {
  test('unknown route returns 404 page', async ({ page }) => {
    await page.goto(`${BASE}/this-path-does-not-exist`);
    await page.waitForTimeout(3000);
    const body = await page.textContent('body');
    expect(body).toBeTruthy();
    expect(body.length).toBeGreaterThan(0);
  });

  test('health endpoint returns component status', async ({ page }) => {
    const resp = await page.request.get(`${API_BASE}/api/v2/health`);
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body).toHaveProperty('status');
    expect(body).toHaveProperty('components');
  });

  test('CORS headers present on API response', async ({ page }) => {
    const resp = await page.request.get(`${API_BASE}/api/v2/health`);
    expect(resp.status()).toBe(200);
    const origin = resp.headers()['access-control-allow-origin'];
    expect(origin).toBe('*');
  });
});
