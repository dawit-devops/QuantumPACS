// Debug: does Flag Critical render on RES-ACC-001 (in_progress)?
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
    const btn = await page.locator('button:has-text("Flag Critical")').count();
    console.log('Flag Critical count:', btn);
    const badge = await page.locator('[data-testid="critical-flag-badge"]').count();
    console.log('badge count:', badge);
    const hdrs = await page.locator('button').allTextContents();
    console.log('buttons:', JSON.stringify(hdrs.filter((b) => b.trim()).slice(0, 15)));
    const bodyHasFlag = (await page.locator('body').innerText()).includes('Flag Critical');
    console.log('body contains Flag Critical:', bodyHasFlag);
  } catch (e) {
    console.log('FAIL', e.message.split('\n')[0]);
  } finally {
    await browser.close();
  }
})();
