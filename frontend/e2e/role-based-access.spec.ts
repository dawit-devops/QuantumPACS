import { test, expect } from '@playwright/test';
import { loginAsAdmin, seedTechnologist, BASE } from './helpers';

// Every admin route gated by PermissionRoute in index.tsx. Shared by the denial
// suite (technologist must be bounced to "/") and the positive-control suite
// (admin must NOT be bounced) so the matrix stays in sync.
const ADMIN_ROUTES = [
  '/replicas',
  '/users',
  '/roles',
  '/tenants',
  '/logs',
  '/worklist',
  '/service-keys',
  '/routing',
  '/fhir/config',
  '/fhir/monitoring',
  '/fhir/docs',
  '/hl7',
  '/dicomweb',
  '/integrations',
];

test.describe('Role-Based Access', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('admin sees admin menu item', async ({ page }) => {
    await expect(page.getByText('Admin').first()).toBeVisible({ timeout: 5000 });
  });

  test('admin can navigate to Users page', async ({ page }) => {
    await page.getByText('Admin').first().click();
    await page.getByText('Users').first().click();
    await expect(page).toHaveURL(/\/users/, { timeout: 10000 });
  });

  test('account page loads', async ({ page }) => {
    await page.getByText('Account').first().click();
    await expect(page).toHaveURL(/\/account/, { timeout: 10000 });
  });

  test('metrics page loads', async ({ page }) => {
    await page.getByText('Metrics').first().click();
    await expect(page).toHaveURL(/\/metrics/, { timeout: 10000 });
  });
});

test.describe('Non-admin deep-link denial (PermissionRoute)', () => {
  // A technologist without those permissions must be redirected to "/" (Files)
  // rather than reaching the route.
  for (const path of ADMIN_ROUTES) {
    test(`technologist is denied deep-link ${path}`, async ({ page }) => {
      await seedTechnologist(page);
      await page.goto(BASE + path, { waitUntil: 'domcontentloaded' });
      await expect(page).toHaveURL(/\/$/, { timeout: 5000 });
    });
  }

  test('technologist can still reach always-visible Files', async ({ page }) => {
    await seedTechnologist(page);
    await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL(/\/$/, { timeout: 5000 });
  });
});

test.describe('Admin deep-link access (PermissionRoute positive control)', () => {
  // An admin user must NOT be bounced back to "/" — the route renders in place
  // (URL stays on the path). Admin pages hydrate slower than a redirect, so the
  // longer timeout covers the full page load.
  for (const path of ADMIN_ROUTES) {
    test(`admin is allowed deep-link ${path}`, async ({ page }) => {
      await loginAsAdmin(page);
      await page.goto(BASE + path, { waitUntil: 'domcontentloaded' });
      // Trailing-anchor match on the literal path, so /users matches /users and
      // not /users/x. Paths contain only letters and slashes (not regex specials).
      await expect(page).toHaveURL(new RegExp(path + '$'), {
        timeout: 10000,
      });
    });
  }
});
