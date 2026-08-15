// Probe: Files page content, notification bell, MWL Create Entry for
// test.technologist (inflated dev role — document drift consequence).
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message.slice(0, 150)));

  try {
    await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' });
    await page.fill('#username', 'test.technologist');
    await page.fill('#password', 'Test@123456');
    await Promise.all([
      page.waitForURL('**/exams', { timeout: 20000 }),
      page.click('button[type="submit"]'),
    ]);
    await page.waitForTimeout(2000);

    // Files page
    await page.goto('http://localhost:5173/', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);
    const files = await page.locator('body').innerText();
    console.log('FILES:', files.slice(0, 400).replace(/\n+/g, ' | '));
    await page.screenshot({ path: 'docs/user-feature-review/technologist/evidence/17-files.png' });

    // Open a study in the viewer (first file row) — the DICOM viewer
    const fileRows = await page.locator('.ant-table-tbody tr.ant-table-row').count();
    console.log('file rows:', fileRows);

    // Notification bell
    await page.goto('http://localhost:5173/exams', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1500);
    const bell = page.locator('[aria-label*="notification" i], .anticon-bell').first();
    console.log('bell present:', await bell.count());
    if (await bell.count()) {
      await bell.click().catch(() => {});
      await page.waitForTimeout(1200);
      await page.screenshot({ path: 'docs/user-feature-review/technologist/evidence/18-bell.png' });
      const pop = await page.locator('.ant-popover, .ant-dropdown, .ant-drawer').last().innerText().catch(() => '');
      console.log('bell popover:', pop.replace(/\n+/g, ' | ').slice(0, 250));
    }

    // MWL Create Entry (WORKLIST_WRITE held — can the tech create DICOM MWL?)
    await page.goto('http://localhost:5173/worklist', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);
    const createBtn = await page.locator('button:has-text("Create Entry")').count();
    console.log('MWL Create Entry button:', createBtn);
    if (createBtn) {
      await page.locator('button:has-text("Create Entry")').first().click();
      await page.waitForTimeout(1000);
      await page.screenshot({ path: 'docs/user-feature-review/technologist/evidence/19-mwl-create.png' });
      const modal = await page.locator('.ant-modal').last().innerText().catch(() => '');
      console.log('MWL create modal:', modal.replace(/\n+/g, ' | ').slice(0, 300));
      // Cancel to leave no residue
      await page.locator('.ant-modal button:has-text("Cancel")').click().catch(() => {});
    }

    console.log('pageerrors:', errors.length ? errors.slice(0, 3) : 'none');
  } catch (e) {
    console.log('FAIL', e.message.split('\n')[0]);
  } finally {
    await browser.close();
  }
})();
