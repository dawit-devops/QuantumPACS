import { test, expect } from '@playwright/test';
import { loginAsAdmin } from './helpers';

test.describe('Service Worker', () => {
  test('admin can navigate to DICOMweb admin page', async ({ page }) => {
    await loginAsAdmin(page);
    await page.getByText('Admin').first().click();
    await page.getByText('DICOMweb').first().click();
    await expect(page).toHaveURL(/\/dicomweb/, { timeout: 10000 });
  });

  test('admin can navigate to HL7 dashboard page', async ({ page }) => {
    await loginAsAdmin(page);
    await page.getByText('Admin').first().click();
    await page.getByText('HL7').first().click();
    await expect(page).toHaveURL(/\/hl7/, { timeout: 10000 });
  });

  test('admin can navigate to Integrations page', async ({ page }) => {
    await loginAsAdmin(page);
    await page.getByText('Admin').first().click();
    await page.getByText('Integrations').first().click();
    await expect(page).toHaveURL(/\/integrations/, { timeout: 10000 });
  });
});
