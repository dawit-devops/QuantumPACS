import { test, expect } from '@playwright/test';
import { BASE } from './helpers';

const ADMIN = { username: 'admin', password: 'pa55w0rd' };

async function login(page: any) {
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); });
  await page.goto(BASE, { waitUntil: 'networkidle' });
  await page.getByPlaceholder('Username').fill(ADMIN.username);
  await page.getByPlaceholder('Password').fill(ADMIN.password);
  await page.getByRole('button', { name: /sign in/i }).click();
  await expect(page.getByText('Search Studies').first()).toBeVisible({ timeout: 15000 });
  // Let background fetches (notifications poll etc.) settle so no error
  // toast is left overlapping the sidebar.
  await page.waitForTimeout(2500);
}

test.describe('Admin Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('sidebar visible with Files link', async ({ page }) => {
    await expect(page.locator('.ant-layout-sider')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Files').first()).toBeVisible();
  });

  test('admin submenu expands with all items', async ({ page }) => {
    await page.getByText('Admin').first().click();
    await expect(page.getByText('Replicas').first()).toBeVisible();
    await expect(page.getByText('Users').first()).toBeVisible();
    await expect(page.getByText('Roles').first()).toBeVisible();
    await expect(page.getByText('Logs').first()).toBeVisible();
    await expect(page.getByText('Worklist').first()).toBeVisible();
    await expect(page.getByText('Service Keys').first()).toBeVisible();
    await expect(page.getByText('Routing').first()).toBeVisible();
    await expect(page.getByText('HL7').first()).toBeVisible();
    await expect(page.getByText('DICOMweb').first()).toBeVisible();
    await expect(page.getByText('Integrations').first()).toBeVisible();
  });

  test('navigates to Users page', async ({ page }) => {
    await page.getByText('Admin').first().click();
    await page.getByText('Users').first().click();
    await expect(page).toHaveURL(/\/users/, { timeout: 10000 });
    await expect(page.getByText('Username').first()).toBeVisible({ timeout: 10000 });
  });

  test('navigates to Roles page', async ({ page }) => {
    await page.getByText('Admin').first().click();
    await page.getByText('Roles').first().click();
    await expect(page).toHaveURL(/\/roles/, { timeout: 10000 });
    await expect(page.getByText('Create Role').first()).toBeVisible({ timeout: 10000 });
  });

  test('navigates to Worklist page', async ({ page }) => {
    await page.getByText('Admin').first().click();
    await page.getByText('Worklist').first().click();
    await expect(page).toHaveURL(/\/worklist/, { timeout: 10000 });
    await expect(page.getByText('Create Entry').first()).toBeVisible({ timeout: 10000 });
  });

  test('navigates to Replicas page', async ({ page }) => {
    await page.getByText('Admin').first().click();
    await page.getByText('Replicas').first().click();
    await expect(page).toHaveURL(/\/replicas/, { timeout: 10000 });
    await expect(page.getByText('Replicas').first()).toBeVisible({ timeout: 10000 });
  });

  test('navigates to Logs page', async ({ page }) => {
    await page.getByText('Admin').first().click();
    await page.getByText('Logs').first().click();
    await expect(page).toHaveURL(/\/logs/, { timeout: 10000 });
    // The page body renders the audit table (no "Audit Log" heading text).
    await expect(page.getByText('Event Type').first()).toBeVisible({ timeout: 10000 });
  });

  test('navigates to Service Keys page', async ({ page }) => {
    await page.getByText('Admin').first().click();
    await page.getByText('Service Keys').first().click();
    await expect(page).toHaveURL(/\/service-keys/, { timeout: 10000 });
    await expect(page.getByText('Generate Key').first()).toBeVisible({ timeout: 10000 });
  });

  test('navigates to Routing page', async ({ page }) => {
    await page.getByText('Admin').first().click();
    await page.getByText('Routing').first().click();
    await expect(page).toHaveURL(/\/routing/, { timeout: 10000 });
    await expect(page.getByText('Create Rule').first()).toBeVisible({ timeout: 10000 });
  });

  test('navigates to DICOMweb page', async ({ page }) => {
    await page.getByText('Admin').first().click();
    await page.getByText('DICOMweb').first().click();
    await expect(page).toHaveURL(/\/dicomweb/, { timeout: 10000 });
    await expect(page.getByText('DICOMweb').first()).toBeVisible({ timeout: 10000 });
  });

  test('navigates to Integrations page', async ({ page }) => {
    await page.getByText('Admin').first().click();
    await page.getByText('Integrations').first().click();
    await expect(page).toHaveURL(/\/integrations/, { timeout: 10000 });
    await expect(page.getByText('Webhooks').first()).toBeVisible({ timeout: 10000 });
  });

  test('navigates to Account page', async ({ page }) => {
    // Click the sidebar link by role so a transient toast cannot swallow
    // the pointer event on the menu item text span.
    await page.getByRole('link', { name: /account/i }).click();
    await expect(page).toHaveURL(/\/account/, { timeout: 10000 });
  });

  test('navigates to Metrics page', async ({ page }) => {
    await page.getByText('Metrics').first().click();
    await expect(page).toHaveURL(/\/metrics/, { timeout: 10000 });
  });

  test('logout navigates to login page', async ({ page }) => {
    await page.getByText('Logout').first().click();
    await expect(page).toHaveURL(/\/login/, { timeout: 15000 });
    await expect(page.getByText('Sign in to your account')).toBeVisible({ timeout: 10000 });
  });

  test('full session flow: login, browse, logout', async ({ page }) => {
    await page.getByText('Admin').first().click();
    await page.getByText('Users').first().click();
    await expect(page).toHaveURL(/\/users/, { timeout: 10000 });

    await page.getByText('Files').first().click();
    await expect(page).toHaveURL(/\/$/, { timeout: 10000 });

    await page.getByText('Account').first().click();
    await expect(page).toHaveURL(/\/account/, { timeout: 10000 });

    await page.getByText('Logout').first().click();
    await expect(page).toHaveURL(/\/login/, { timeout: 15000 });
  });
});
