// Regression probe — super_admin on shared surfaces modified by the
// tenant_admin review (dashboard HealthStrip/Interfaces, Users tenant
// column, Roles lock hints, notification prefs, Files search alert).
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));

  const login = async () => {
    await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' });
    await page.fill('#username', 'test.super_admin');
    await page.fill('#password', 'Test@123456');
    await Promise.all([
      page.waitForURL('**/admin', { timeout: 20000 }),
      page.click('button[type="submit"]'),
    ]);
  };

  try {
    await login();
    console.log('PASS login -> /admin');

    // 1. Dashboard — dead-end check: super_admin holds SYSTEM_ADMIN so
    // FHIR's Open button should be present (regression: the guard must not
    // hide legit surfaces), and clicking it must navigate (not bounce).
    await page.waitForTimeout(2000);
    const openBtns = page.locator('button:has-text("Open")');
    const openCount = await openBtns.count();
    console.log('dashboard Open buttons (expect 4: storage/dicom/hl7/fhir):', openCount);
    if (openCount > 0) {
      const href = await page.locator('a:has-text("Open")').last().getAttribute('href').catch(() => null);
      await Promise.all([
        page.waitForURL('**/fhir/**', { timeout: 15000 }).catch(() => {}),
        openBtns.last().click({ timeout: 5000 }).catch(() => {}),
      ]);
      console.log('dashboard Open navigates off /admin:', !page.url().includes('/admin'));
      await page.goto('http://localhost:5173/admin', { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(1500);
    }

    // 2. Users — tenant column must render for super_admin (who sees all tenants).
    await page.goto('http://localhost:5173/users', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);
    const hasTenantCol = await page.locator('th:has-text("Tenant")').count();
    const tenantCells = await page.locator('table tbody tr td:nth-child(4)').allTextContents();
    console.log('users Tenant column present:', hasTenantCol > 0, '| sample cells:', JSON.stringify(tenantCells.slice(0, 4)));

    // 3. Roles — lock hints: immutable anchors show disabled Edit.
    await page.goto('http://localhost:5173/roles', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);
    const disabledEdits = await page.locator('button:has-text("Edit")[disabled]').count();
    console.log('roles disabled Edit buttons (immutable anchors):', disabledEdits);

    // 4. Notification prefs — route is /account/notifications.
    await page.goto('http://localhost:5173/account/notifications', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);
    const prefsHeading = await page.locator('text=Notification Preferences').count();
    const prefsSwitches = await page.locator('.ant-switch').count();
    console.log('prefs page reachable:', prefsHeading > 0, '| toggles:', prefsSwitches);

    // 5. Files — page loads with search banner logic (ES up here -> no alert).
    await page.goto('http://localhost:5173/files', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);
    const fileRows = await page.locator('table.ant-table tbody tr').count();
    console.log('files page rows:', fileRows);

    console.log('console/page errors:', errors.length ? errors.slice(0, 5) : 'none');
  } catch (e) {
    console.log('FAIL', e.message.split('\n')[0]);
    await page.screenshot({ path: 'docs/user-feature-review/tenant-admin/evidence/90-regress-fail.png' });
  } finally {
    await browser.close();
  }
})();
