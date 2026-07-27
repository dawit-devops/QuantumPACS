import { Page, expect } from '@playwright/test';

export const BASE = 'http://localhost:5173';
export const API_BASE = 'http://localhost:8080';

async function getToken(page: Page): Promise<string> {
  const resp = await page.request.post(`${API_BASE}/api/login`, {
    data: { username: 'admin', password: 'pa55w0rd' },
  });
  expect(resp.status()).toBe(200);
  const body = await resp.json();
  return body.token;
}

export async function login(page: Page) {
  const token = await getToken(page);
  await page.addInitScript((storage) => {
    for (const [key, value] of Object.entries(storage)) {
      localStorage.setItem(key, value as string);
    }
  }, {
    token,
    userId: '1',
    username: 'admin',
    admin: 'true',
    role: 'admin',
    permissions: JSON.stringify([]),
  });
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('.ant-layout-sider', { timeout: 20000 });
}

export async function loginViaForm(page: Page) {
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('text=Sign in to your account', { timeout: 15000 });
  await page.getByPlaceholder('Username').fill('admin');
  await page.getByPlaceholder('Password').fill('pa55w0rd');
  await page.getByRole('button', { name: /sign in/i }).click();
  await page.waitForURL(/\/$/, { timeout: 15000 });
  await page.waitForSelector('.ant-layout-sider', { timeout: 20000 });
}

export async function waitForTableLoad(page: Page) {
  await page.waitForSelector('.ant-table', { timeout: 20000 });
}

export async function getTableRowCount(page: Page): Promise<number> {
  return page.locator('.ant-table-tbody tr.ant-table-row').count();
}
