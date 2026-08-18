// Verify Orders row click → patient page (tour disabled).
const { chromium } = require('playwright');
const OUT = 'docs/user-feature-review/care-coordinator/evidence';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await ctx.addInitScript(() => {
    localStorage.setItem('quantumpacs-tour-done', '1');
  });
  const page = await ctx.newPage();

  try {
    await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' });
    await page.fill('#username', 'test.care_coordinator');
    await page.fill('#password', 'Test@123456');
    await Promise.all([
      page.waitForURL('**/orders', { timeout: 20000 }).catch(() => {}),
      page.click('button[type="submit"]'),
    ]);
    await page.waitForTimeout(3000);

    await page.locator('.ant-table-row').first().click({ timeout: 8000 });
    await page.waitForTimeout(2000);
    console.log('row click ->', page.url());
    await page.screenshot({ path: `${OUT}/22-orders-row-click.png` });
    const body = await page.locator('body').innerText();
    console.log('patient page ok:', /Patient ID: SMOKE001/.test(body), '| reports card:', /Reports & Results/.test(body));
  } catch (e) {
    console.log('FAIL', e.message.split('\n')[0]);
    await page.screenshot({ path: `${OUT}/99-fail.png` });
  } finally {
    await browser.close();
  }
})();
