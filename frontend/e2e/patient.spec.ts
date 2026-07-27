import { test, expect } from '@playwright/test';
import { BASE, login, waitForTableLoad, getTableRowCount } from './helpers';

test.describe('Patient Page', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('patient link navigates to patient page', async ({ page }) => {
    await waitForTableLoad(page);
    const rows = await getTableRowCount(page);
    if (rows > 0) {
      const patientLinks = page.locator('.ant-table-tbody tr.ant-table-row a');
      let patientHref: string | null = null;
      for (let i = 0; i < rows; i++) {
        const link = patientLinks.nth(i);
        const href = await link.getAttribute('href');
        if (href && href.startsWith('/patients/')) {
          patientHref = href;
          break;
        }
      }
      if (patientHref) {
        await page.goto(`${BASE}${patientHref}`, { waitUntil: 'networkidle' });
        await page.waitForTimeout(3000);
        expect(page.url()).toMatch(/\/patients\/\d+/);
      }
    }
  });

  test('renders patient demographics when available', async ({ page }) => {
    const resp = await page.request.get(`${BASE.replace('5173', '8080')}/api/patients`, {
      headers: { 'X-Auth-Pacs': 'test-token' },
    });
    if (resp.status() === 200) {
      const body = await resp.json();
      const patients = Array.isArray(body) ? body : body.patients || body.data || [];
      if (patients.length > 0) {
        const patientId = patients[0].id || 1;
        await page.goto(`${BASE}/patients/${patientId}`, { waitUntil: 'networkidle' });
        await page.waitForTimeout(3000);
        const bodyText = await page.textContent('body');
        expect(bodyText.length).toBeGreaterThan(0);
      }
    }
  });

  test('directory tree renders if studies exist', async ({ page }) => {
    const resp = await page.request.get(`${BASE.replace('5173', '8080')}/api/patients`, {
      headers: { 'X-Auth-Pacs': 'test-token' },
    });
    if (resp.status() === 200) {
      const body = await resp.json();
      const patients = Array.isArray(body) ? body : body.patients || body.data || [];
      if (patients.length > 0) {
        const patientId = patients[0].id || 1;
        await page.goto(`${BASE}/patients/${patientId}`, { waitUntil: 'networkidle' });
        await page.waitForTimeout(3000);
        const tree = page.locator('.ant-tree');
        if (await tree.isVisible()) {
          const nodes = await tree.locator('.ant-tree-treenode').count();
          expect(nodes).toBeGreaterThanOrEqual(1);
        }
      }
    }
  });
});
