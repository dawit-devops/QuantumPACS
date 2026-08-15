// Step-by-step debug of the critical-flag flow.
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  page.on('pageerror', (e) => console.log('PAGEERROR:', e.message.slice(0, 200)));

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
    await page.waitForTimeout(4000);
    console.log('step: page loaded', page.url());

    const flagBtn = page.locator('button', { hasText: 'Flag Critical' }).first();
    console.log('flag button count:', await flagBtn.count(), 'visible:', await flagBtn.isVisible().catch(() => 'err'));
    await flagBtn.evaluate((el) => el.click());
    console.log('step: dispatched click');
    await page.waitForTimeout(1200);
    console.log('modal count:', await page.locator('.ant-modal').count());
    console.log('modal titles:', JSON.stringify(await page.locator('.ant-modal-title').allTextContents()));
    const modal = page.locator('.ant-modal').first();
    console.log('modal visible:', await modal.isVisible().catch(() => 'err'));

    await page.locator('.ant-modal textarea').fill('live verification of critical flag flow');
    console.log('step: filled textarea');
    const okBtns = page.locator('.ant-modal button');
    console.log('modal buttons:', JSON.stringify(await okBtns.allTextContents()));
    await page.locator('.ant-modal button:has-text("Flag for Immediate Read")').click({ timeout: 8000 });
    console.log('step: submitted');
    await page.waitForTimeout(2500);
    const badge = await page.locator('[data-testid="critical-flag-badge"]').count();
    console.log('badge:', badge);
    if (badge) {
      console.log('badge text:', (await page.locator('[data-testid="critical-flag-badge"]').innerText()).trim());
      await page.screenshot({ path: 'docs/user-feature-review/technologist/evidence/27-flag-badge.png' });
    }
  } catch (e) {
    console.log('FAIL at:', e.message.split('\n')[0]);
    await page.screenshot({ path: 'docs/user-feature-review/technologist/evidence/99-fail.png' });
  } finally {
    await browser.close();
  }
})();
