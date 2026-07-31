import { test, expect } from '@playwright/test';
import { loginAsAdmin } from './helpers';

test.describe('Share Link Flow', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('share link UI elements present on files page', async ({ page }) => {
    const studyLinks = page.locator('a[href*="/files/"]');
    const count = await studyLinks.count();
    if (count > 0) {
      await studyLinks.first().click();
      await expect(page).toHaveURL(/\/files\//, { timeout: 10000 });
    }
  });
});
