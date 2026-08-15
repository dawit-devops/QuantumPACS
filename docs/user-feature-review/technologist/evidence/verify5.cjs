// Complete the critical-flag flow: open modal, fill, submit, verify badge.
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  page.on('pageerror', (e) => console.log('PAGEERROR:', e.message.slice(0, 150)));

  try {
    await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' });
    await page.fill('#username', 'test.technologist');
    await page.fill('#password', 'Test@123456');
    await Promise.all([
      page.waitForURL('**/exams', { timeout: 20000 }),
      page.click('button[type="submit"]'),
    ]);
    await page.waitForTimeout(2000);
    await page.goto('http://localhost:5173/exams/cbf6baeb-5519-4f35-a015-c370e754495a', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3500);

    await page.locator('button:has-text("Flag Critical")').click();
    await page.waitForSelector('.ant-modal', { timeout: 5000 });
    await page.waitForTimeout(800);
    await page.locator('.ant-modal textarea').fill('live verification of critical flag flow');
    await page.locator('.ant-modal button:has-text("Flag for Immediate Read")').click();
    await page.waitForTimeout(2500);
    const badge = await page.locator('[data-testid="critical-flag-badge"]').count();
    const badgeText = await page.locator('[data-testid="critical-flag-badge"]').innerText().catch(() => '');
    console.log('badge:', badge, '| text:', badgeText.trim());
    await page.screenshot({ path: 'docs/user-feature-review/technologist/evidence/27-flag-badge.png' });
  } catch (e) {
    console.log('FAIL', e.message.split('\n')[0]);
    await page.screenshot({ path: 'docs/user-feature-review/technologist/evidence/99-fail.png' });
  } finally {
    await browser.close();
  }
})();
