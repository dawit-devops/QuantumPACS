// Debug the click timeout: how many matches, are they visible, any overlay?
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  page.on('pageerror', (e) => console.log('PAGEERROR:', e.message.slice(0, 200)));
  page.on('console', (m) => { if (m.type() === 'error') console.log('CONSOLE:', m.text().slice(0, 150)); });

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

    const all = page.locator('button', { hasText: 'Flag Critical' });
    console.log('matches:', await all.count());
    for (let i = 0; i < await all.count(); i++) {
      const b = all.nth(i);
      console.log(`  [${i}] visible:`, await b.isVisible().catch(() => 'err'), '| disabled:', await b.isDisabled().catch(() => 'err'));
    }
    // click via nth(0)
    await all.first().click({ timeout: 5000 }).then(() => console.log('CLICK OK')).catch((e) => console.log('CLICK ERR:', e.message.split('\n')[0]));
    await page.waitForTimeout(1000);
    console.log('modal count:', await page.locator('.ant-modal').count());
    console.log('modal title:', await page.locator('.ant-modal-title').innerText().catch(() => '(none)'));
  } catch (e) {
    console.log('FAIL', e.message.split('\n')[0]);
  } finally {
    await browser.close();
  }
})();
