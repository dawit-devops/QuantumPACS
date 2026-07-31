import { Page } from '@playwright/test';

const BASE = 'http://localhost:5173';

export async function clearAndGo(page: Page, path = '') {
  await page.goto(BASE + path, { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); });
  await page.goto(BASE + path, { waitUntil: 'networkidle' });
}

export async function loginAsAdmin(page: Page) {
  await clearAndGo(page);
  await page.getByPlaceholder('Username').fill('admin');
  await page.getByPlaceholder('Password').fill('pa55w0rd');
  await page.getByRole('button', { name: /sign in/i }).click();
  await page.getByText('Search Studies').first().waitFor({ state: 'visible', timeout: 20000 });
  await page.waitForTimeout(2000);
}
