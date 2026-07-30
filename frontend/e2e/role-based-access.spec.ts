import { test, expect } from '@playwright/test';
import { loginAsAdmin } from './helpers';

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
