// Complete the flag flow after dismissing the onboarding tour overlay.
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  page.on('pageerror', (e) => console.log('PAGEERROR:', e.message.slice(0, 200)));

  try {
    await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' });
    // Dismiss onboarding before it can overlay anything
    await page.evaluate(() => {
      try {
        localStorage.setItem('onboarding-done', '1');
        localStorage.setItem('tour-completed', '1');
      } catch {}
    });
    await page.fill('#username', 'test.technologist');
    await page.fill('#password', 'Test@123456');
    await Promise.all([
      page.waitForURL('**/exams', { timeout: 20000 }),
      page.click('button[type="submit"]'),
    ]);
    await page.waitForTimeout(2000);
    await page.goto('http://localhost:5173/exams/cbf6baeb-5519-4f35-a015-c370e754495a', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);

    // Close any tour popup if present
    const tourDismiss = page.locator('button:has-text("Skip"), button:has-text("Done"), button:has-text("Close")').first();
    if (await tourDismiss.count().catch(() => 0)) {
      await tourDismiss.click({ timeout: 3000 }).catch(() => {});
      await page.waitForTimeout(500);
    }

    await page.locator('button', { hasText: 'Flag Critical' }).first().evaluate((el) => el.click());
    await page.waitForTimeout(1200);
    await page.locator('.ant-modal textarea').fill('live verification of critical flag flow');
    await page.locator('.ant-modal button:has-text("Flag for Immediate Read")').click({ timeout: 10000 });
    await page.waitForTimeout(2500);
    const badge = await page.locator('[data-testid="critical-flag-badge"]').count();
    const badgeText = await page.locator('[data-testid="critical-flag-badge"]').innerText().catch(() => '');
    console.log('badge:', badge, '| text:', badgeText.trim());
    if (badge) await page.screenshot({ path: 'docs/user-feature-review/technologist/evidence/27-flag-badge.png' });
    const toasts = await page.locator('.ant-message-notice').allTextContents();
    console.log('toasts:', JSON.stringify(toasts));
  } catch (e) {
    console.log('FAIL', e.message.split('\n')[0]);
  } finally {
    await browser.close();
  }
})();
