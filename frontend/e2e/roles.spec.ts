import { test, expect } from '@playwright/test';
import { loginAsAdmin } from './helpers';

test.describe('Role Management', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('roles page loads via admin menu', async ({ page }) => {
    await page.getByText('Admin').first().click();
    await page.getByText('Roles').first().click();
    await expect(page).toHaveURL(/\/roles/, { timeout: 10000 });
    await expect(page.locator('body')).not.toBeEmpty({ timeout: 15000 });
  });

  test('roles page has Create Role button', async ({ page }) => {
    await page.getByText('Admin').first().click();
    await page.getByText('Roles').first().click();
    await expect(page).toHaveURL(/\/roles/, { timeout: 10000 });
    const addBtn = page.getByRole('button', { name: /add|create|new/i }).first();
    await expect(addBtn).toBeVisible({ timeout: 10000 });
  });
});
