// Reading Worklist: the flagged FLAG-PROBE-ACC-1 row shows a red CRITICAL tag.
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  page.on('pageerror', (e) => console.log('PAGEERROR:', e.message.slice(0, 200)));

  try {
    await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' });
    await page.evaluate(() => {
      try { localStorage.setItem('onboarding-done', '1'); localStorage.setItem('tour-completed', '1'); } catch {}
    });
    await page.fill('#username', 'test.radiologist');
    await page.fill('#password', 'Test@123456');
    await Promise.all([
      page.waitForURL('**/reading', { timeout: 20000 }).catch(() => {}),
      page.click('button[type="submit"]'),
    ]);
    await page.waitForTimeout(3000);
    const row = page.locator('.ant-table-tbody tr.ant-table-row').filter({ hasText: 'FLAG-PROBE-ACC-1' });
    console.log('flagged row count:', await row.count());
    if (await row.count()) {
      const tag = row.locator('.ant-tag', { hasText: 'CRITICAL' });
      console.log('CRITICAL tag in row:', await tag.count());
      const tagText = await tag.innerText().catch(() => '');
      console.log('tag text:', tagText.trim());
      await page.screenshot({ path: 'docs/user-feature-review/technologist/evidence/29-reading-flag-tag.png' });
    }
  } catch (e) {
    console.log('FAIL', e.message.split('\n')[0]);
  } finally {
    await browser.close();
  }
})();
