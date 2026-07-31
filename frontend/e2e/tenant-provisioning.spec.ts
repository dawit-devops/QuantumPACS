import { test, expect } from '@playwright/test';
import { loginAsAdmin } from './helpers';

test.describe('Tenant Provisioning', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('tenants page loads via admin menu', async ({ page }) => {
    await page.getByText('Admin').first().click();
    await expect(page.getByText('Tenants').first()).toBeVisible({ timeout: 5000 });
    await page.getByText('Tenants').first().click();
    await expect(page).toHaveURL(/\/tenants/, { timeout: 10000 });
  });

  test('roles page loads via admin menu', async ({ page }) => {
    await page.getByText('Admin').first().click();
    await page.getByText('Roles').first().click();
    await expect(page).toHaveURL(/\/roles/, { timeout: 10000 });
  });
});
