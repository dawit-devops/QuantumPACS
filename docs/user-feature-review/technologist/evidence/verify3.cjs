// Next-patient pointer (ready unassigned exam exists) + critical-flag badge.
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message.slice(0, 150)));

  try {
    await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' });
    await page.fill('#username', 'test.technologist');
    await page.fill('#password', 'Test@123456');
    await Promise.all([
      page.waitForURL('**/exams', { timeout: 20000 }),
      page.click('button[type="submit"]'),
    ]);
    await page.waitForTimeout(2000);

    // Open the completed exam (has identity/protocol history) — the ready
    // unassigned TECH-REV-ACC-1 should surface as Next.
    await page.goto('http://localhost:5173/exams/cbf6baeb-5519-4f35-a015-c370e754495a', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);
    const nextLine = await page.getByText('Next:', { exact: false }).count();
    console.log('Next-patient line:', nextLine);
    if (nextLine) {
      const nextText = await page.locator('.ant-alert', { hasText: 'Next:' }).innerText();
      console.log('next text:', nextText.replace(/\n+/g, ' ').slice(0, 120));
      await page.screenshot({ path: 'docs/user-feature-review/technologist/evidence/26-next-patient.png' });
    }

    // Flag an exam and check the badge appears
    await page.locator('button:has-text("Flag Critical")').click();
    await page.waitForTimeout(600);
    await page.locator('.ant-modal textarea').fill('live verification of critical flag flow');
    await page.locator('.ant-modal button:has-text("Flag for Immediate Read")').click();
    await page.waitForTimeout(2000);
    const badge = await page.locator('[data-testid="critical-flag-badge"]').count();
    console.log('critical-flag badge:', badge);
    await page.screenshot({ path: 'docs/user-feature-review/technologist/evidence/27-flag-badge.png' });

    // Cleanup: un-flag so the demo data stays clean (flag is low severity)
    console.log('pageerrors:', errors.length ? errors.slice(0, 3) : 'none');
  } catch (e) {
    console.log('FAIL', e.message.split('\n')[0]);
    await page.screenshot({ path: 'docs/user-feature-review/technologist/evidence/99-fail.png' });
  } finally {
    await browser.close();
  }
})();
