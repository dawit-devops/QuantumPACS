// Reading Worklist: Flag column + flagged exam surfaced (as radiologist).
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
    console.log('radiologist landing:', page.url());
    const flagCol = await page.locator('th:has-text("Flag")').count();
    console.log('Flag column:', flagCol);
    // RES-ACC-001 was flagged CRITICAL in the verify12 run and is in_progress
    // (not completed) — it may not be on the reading list (which shows
    // completed exams). Check whether any flag tag renders regardless.
    const flagTags = await page.locator('.ant-tag', { hasText: /CRITICAL|HIGH|MEDIUM|LOW/ }).count();
    console.log('flag tags on list:', flagTags);
    await page.screenshot({ path: 'docs/user-feature-review/technologist/evidence/24-reading-flag-col.png' });
  } catch (e) {
    console.log('FAIL', e.message.split('\n')[0]);
  } finally {
    await browser.close();
  }
})();
