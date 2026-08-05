import { test, expect } from '@playwright/test';
import { loginAsAdmin } from './helpers';

test.describe('Worklist (MWL)', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('worklist page loads via admin submenu', async ({ page }) => {
    await page.getByText('Admin').first().click();
    await page.getByText('Worklist').first().click();
    await expect(page).toHaveURL(/\/worklist/, { timeout: 10000 });
    await expect(page.locator('body').first()).toBeVisible({ timeout: 10000 });
  });

  test('worklist page has content after navigation', async ({ page }) => {
    await page.getByText('Admin').first().click();
    await page.getByText('Worklist').first().click();
    await expect(page).toHaveURL(/\/worklist/, { timeout: 10000 });
    const bodyText = await page.locator('body').innerText({ timeout: 15000 });
    expect(bodyText.length).toBeGreaterThan(50);
  });

  test('worklist API requires auth token', async ({ page }) => {
    const resp = await page.request.post('http://localhost:8080/api/worklist', {
      headers: { 'Content-Type': 'application/json' },
      data: {
        patient_name: 'E2E^Test',
        patient_id: `E2E-${Date.now()}`,
        accession_number: `ACC-${Date.now()}`,
        modality: 'CT',
        scheduled_ae_title: 'E2E_TEST',
        status: 'scheduled',
      },
    });
    expect(resp.status()).toBe(401);
  });
});
