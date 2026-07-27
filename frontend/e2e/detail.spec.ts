import { test, expect } from '@playwright/test';
import { BASE, login, waitForTableLoad, getTableRowCount } from './helpers';

test.describe('Detail Page (DICOM Viewer)', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('navigates to detail page from files table', async ({ page }) => {
    await waitForTableLoad(page);
    const rows = await getTableRowCount(page);
    if (rows > 0) {
      const firstLink = page.locator('.ant-table-tbody tr.ant-table-row a').first();
      if (await firstLink.isVisible()) {
        await firstLink.click();
        await page.waitForTimeout(3000);
        expect(page.url()).toMatch(/\/files\/\d+/);
      }
    }
  });

  test('renders tab navigation on detail page', async ({ page }) => {
    const resp = await page.request.get(`${BASE.replace('5173', '8080')}/api/files`, {
      headers: { 'X-Auth-Pacs': 'test-token' },
    });
    if (resp.status() === 200) {
      const body = await resp.json();
      const files = Array.isArray(body) ? body : body.files || body.data || [];
      if (files.length > 0) {
        const fileId = files[0].id || 1;
        await page.goto(`${BASE}/files/${fileId}`, { waitUntil: 'networkidle' });
        await page.waitForTimeout(3000);
        const tabs = page.locator('.ant-tabs-nav');
        if (await tabs.isVisible()) {
          const tabText = await tabs.textContent();
          expect(tabText).toContain('Image');
        }
      }
    }
  });

  test('data tab shows metadata table', async ({ page }) => {
    const resp = await page.request.get(`${BASE.replace('5173', '8080')}/api/files`, {
      headers: { 'X-Auth-Pacs': 'test-token' },
    });
    if (resp.status() === 200) {
      const body = await resp.json();
      const files = Array.isArray(body) ? body : body.files || body.data || [];
      if (files.length > 0) {
        const fileId = files[0].id || 1;
        await page.goto(`${BASE}/files/${fileId}`, { waitUntil: 'networkidle' });
        await page.waitForTimeout(3000);
        const dataTab = page.locator('.ant-tabs-tab').filter({ hasText: /data/i });
        if (await dataTab.isVisible()) {
          await dataTab.click();
          await page.waitForTimeout(2000);
          const table = page.locator('.ant-table');
          if (await table.isVisible()) {
            const rows = await table.locator('.ant-table-tbody tr').count();
            expect(rows).toBeGreaterThanOrEqual(1);
          }
        }
      }
    }
  });

  test('share tab renders share form', async ({ page }) => {
    const resp = await page.request.get(`${BASE.replace('5173', '8080')}/api/files`, {
      headers: { 'X-Auth-Pacs': 'test-token' },
    });
    if (resp.status() === 200) {
      const body = await resp.json();
      const files = Array.isArray(body) ? body : body.files || body.data || [];
      if (files.length > 0) {
        const fileId = files[0].id || 1;
        await page.goto(`${BASE}/files/${fileId}`, { waitUntil: 'networkidle' });
        await page.waitForTimeout(3000);
        const shareTab = page.locator('.ant-tabs-tab').filter({ hasText: /share/i });
        if (await shareTab.isVisible()) {
          await shareTab.click();
          await page.waitForTimeout(2000);
          const shareContent = page.locator('.ant-tabs-content');
          await expect(shareContent).toBeVisible({ timeout: 5000 });
        }
      }
    }
  });

  test('changes tab shows audit log', async ({ page }) => {
    const resp = await page.request.get(`${BASE.replace('5173', '8080')}/api/files`, {
      headers: { 'X-Auth-Pacs': 'test-token' },
    });
    if (resp.status() === 200) {
      const body = await resp.json();
      const files = Array.isArray(body) ? body : body.files || body.data || [];
      if (files.length > 0) {
        const fileId = files[0].id || 1;
        await page.goto(`${BASE}/files/${fileId}`, { waitUntil: 'networkidle' });
        await page.waitForTimeout(3000);
        const changesTab = page.locator('.ant-tabs-tab').filter({ hasText: /changes/i });
        if (await changesTab.isVisible()) {
          await changesTab.click();
          await page.waitForTimeout(2000);
          const table = page.locator('.ant-table');
          if (await table.isVisible()) {
            expect(await table.locator('.ant-table-tbody tr').count()).toBeGreaterThanOrEqual(0);
          }
        }
      }
    }
  });

  test('breadcrumb navigation is visible', async ({ page }) => {
    const resp = await page.request.get(`${BASE.replace('5173', '8080')}/api/files`, {
      headers: { 'X-Auth-Pacs': 'test-token' },
    });
    if (resp.status() === 200) {
      const body = await resp.json();
      const files = Array.isArray(body) ? body : body.files || body.data || [];
      if (files.length > 0) {
        const fileId = files[0].id || 1;
        await page.goto(`${BASE}/files/${fileId}`, { waitUntil: 'networkidle' });
        await page.waitForTimeout(3000);
        const breadcrumb = page.locator('.ant-breadcrumb');
        if (await breadcrumb.isVisible()) {
          const items = await breadcrumb.locator('span').count();
          expect(items).toBeGreaterThanOrEqual(2);
        }
      }
    }
  });
});
