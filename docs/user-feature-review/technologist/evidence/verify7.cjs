// Submit the critical flag flow and verify the badge renders.
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

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

    const flagBtn = page.locator('button', { hasText: 'Flag Critical' }).first();
    await flagBtn.scrollIntoViewIfNeeded().catch(() => {});
    await page.waitForTimeout(300);
    await flagBtn.click({ timeout: 10000, force: true }).catch(async () => {
      // Fallback: dispatch a click if the button shifted under the cursor.
      await flagBtn.evaluate((el) => el.click());
    });
    await page.waitForSelector('.ant-modal', { timeout: 5000 });
    await page.waitForTimeout(500);
    await page.locator('.ant-modal textarea').fill('live verification of critical flag flow');
    await page.locator('.ant-modal button:has-text("Flag for Immediate Read")').click();
    await page.waitForTimeout(2500);
    const badge = await page.locator('[data-testid="critical-flag-badge"]').count();
    const badgeText = await page.locator('[data-testid="critical-flag-badge"]').innerText().catch(() => '');
    console.log('badge:', badge, '| text:', badgeText.trim());
    await page.screenshot({ path: 'docs/user-feature-review/technologist/evidence/27-flag-badge.png' });
    // toast
    const toasts = await page.locator('.ant-message-notice').allTextContents();
    console.log('toasts:', JSON.stringify(toasts));
  } catch (e) {
    console.log('FAIL', e.message.split('\n')[0]);
  } finally {
    await browser.close();
  }
})();
