import { Page } from '@playwright/test';

export const BASE = 'http://localhost:5173';

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

/**
 * Seeds an authenticated, non-admin technologist session directly in localStorage
 * (the same keys AuthContext reads on boot) and stubs every /api/** request so the
 * fake token can never 401-bounce to /login — which would mask the PermissionRoute
 * redirect we are asserting. Lets the deep-link denial suite run without a real
 * technologist user in the backend.
 */
export async function seedTechnologist(page: Page) {
  await page.route('**/api/**', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
  );
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
    localStorage.setItem('userId', 'tech-1');
    localStorage.setItem('username', 'technician');
    localStorage.setItem('admin', 'false');
    localStorage.setItem('role', 'technologist');
    localStorage.setItem(
      'permissions',
      JSON.stringify(['FILE_READ', 'STUDY_READ', 'PATIENT_READ']),
    );
    localStorage.setItem('access_token', 'e2e-technologist-token');
    localStorage.setItem('refresh_token', 'e2e-technologist-token');
  });
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
}
