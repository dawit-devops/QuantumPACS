// Trace remaining 403s — which endpoints still fail for care_coordinator.
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  const fails = [];
  page.on('response', (r) => {
    if (r.status() >= 400) fails.push(`${r.status()} ${r.url().replace('http://localhost:5173', '')}`);
  });

  try {
    await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' });
    await page.fill('#username', 'test.care_coordinator');
    await page.fill('#password', 'Test@123456');
    await Promise.all([
      page.waitForURL('**/orders', { timeout: 20000 }).catch(() => {}),
      page.click('button[type="submit"]'),
    ]);
    await page.waitForTimeout(2500);
    fails.length = 0;

    for (const [label, url, wait] of [
      ['orders', '/orders', 2500],
      ['schedule-board', '/schedule-board', 3500],
      ['files', '/', 3500],
      ['patient', '/patients/13', 2500],
      ['reading', '/reading', 2500],
    ]) {
      await page.goto('http://localhost:5173' + url, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(wait);
      console.log(`[${label}]`, fails.length ? fails.join(' | ') : 'no 4xx');
      fails.length = 0;
    }
  } catch (e) {
    console.log('FAIL', e.message.split('\n')[0]);
  } finally {
    await browser.close();
  }
})();
