import { test, expect } from '@playwright/test';
import { loginAsAdmin } from './helpers';

test.describe('Study Viewer', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('search page loads with search bar', async ({ page }) => {
    await expect(page.getByPlaceholder(/search/i).first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Search Studies')).toBeVisible();
  });

  test('sidebar navigation links visible', async ({ page }) => {
    await expect(page.getByText('Files').first()).toBeVisible();
    await expect(page.getByText('Metrics').first()).toBeVisible();
    await expect(page.getByText('Account').first()).toBeVisible();
  });
});
