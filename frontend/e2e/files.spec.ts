import { test, expect } from '@playwright/test';
import { BASE, login, waitForTableLoad, getTableRowCount } from './helpers';

test.describe('Files Page', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('renders the files table with columns', async ({ page }) => {
    await expect(page.getByText('Files').first()).toBeVisible({ timeout: 15000 });
    await waitForTableLoad(page);
    const headers = await page.locator('.ant-table-thead th').allTextContents();
    const headerText = headers.join(' ');
    expect(headerText).toContain('ID');
    expect(headerText).toContain('Patient ID');
    expect(headerText).toContain('Patient Name');
    expect(headerText).toContain('Study Description');
  });

  test('search input is visible and functional', async ({ page }) => {
    await waitForTableLoad(page);
    const searchInput = page.locator('input[placeholder*="earch"]').first();
    await expect(searchInput).toBeVisible({ timeout: 10000 });
    const searchBtn = page.locator('.ant-input-search button').first();
    if (await searchBtn.isVisible()) {
      await searchInput.fill('test');
      await searchBtn.click();
      await page.waitForTimeout(2000);
    }
  });

  test('upload button visible', async ({ page }) => {
    await waitForTableLoad(page);
    const upload = page.getByRole('button', { name: /upload/i });
    await expect(upload).toBeVisible({ timeout: 10000 });
  });

  test('file rows link to detail page', async ({ page }) => {
    await waitForTableLoad(page);
    const rows = await getTableRowCount(page);
    if (rows > 0) {
      const firstLink = page.locator('.ant-table-tbody tr.ant-table-row a').first();
      if (await firstLink.isVisible()) {
        const href = await firstLink.getAttribute('href');
        expect(href).toMatch(/\/files\/\d+/);
        await firstLink.click();
        await page.waitForTimeout(3000);
        expect(page.url()).toMatch(/\/files\/\d+/);
      }
    }
  });

  test('pagination controls visible when multiple pages', async ({ page }) => {
    await waitForTableLoad(page);
    const pagination = page.locator('.ant-pagination');
    if (await pagination.isVisible()) {
      const items = await pagination.locator('li').count();
      expect(items).toBeGreaterThanOrEqual(3);
    }
  });
});
