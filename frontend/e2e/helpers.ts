import { Page } from '@playwright/test';

// CI serves the built app via vite preview; local runs use the dev server.
export const BASE = process.env.E2E_BASE_URL || 'http://localhost:5173';

export async function clearAndGo(page: Page, path = '') {
  await page.goto(BASE + path, { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); });
  await page.goto(BASE + path, { waitUntil: 'networkidle' });
}

export async function loginAsAdmin(page: Page) {
  await loginAs(page, 'admin', 'pa55w0rd');
}

export async function loginAs(page: Page, username: string, password: string) {
  await clearAndGo(page);
  await page.getByPlaceholder('Username').fill(username);
  await page.getByPlaceholder('Password').fill(password);
  await page.getByRole('button', { name: /sign in/i }).click();
  await page.getByText('Search Studies').first().waitFor({ state: 'visible', timeout: 20000 });
  await page.waitForTimeout(2000);
}
