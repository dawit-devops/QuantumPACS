// Debug: what does the super_admin dashboard + users page actually render?
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));

  try {
    await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' });
    await page.fill('#username', 'test.super_admin');
    await page.fill('#password', 'Test@123456');
    await Promise.all([
      page.waitForURL('**/admin', { timeout: 20000 }),
      page.click('button[type="submit"]'),
    ]);
    await page.waitForTimeout(2500);
    console.log('URL after login:', page.url());
    await page.screenshot({ path: 'docs/user-feature-review/tenant-admin/evidence/90-regress-admin.png', fullPage: false });

    // dump visible buttons + pills
    const buttons = await page.locator('button').allTextContents();
    console.log('buttons:', JSON.stringify(buttons.slice(0, 20)));
    const bodyText = await page.locator('body').innerText();
    console.log('body head:', bodyText.slice(0, 600).replace(/\n+/g, ' | '));

    await page.goto('http://localhost:5173/users', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);
    console.log('URL users:', page.url());
    await page.screenshot({ path: 'docs/user-feature-review/tenant-admin/evidence/90-regress-users.png' });
    const ubody = await page.locator('body').innerText();
    console.log('users body head:', ubody.slice(0, 500).replace(/\n+/g, ' | '));
    console.log('console errors:', errors.slice(0, 5));
  } catch (e) {
    console.log('FAIL', e.message.split('\n')[0]);
    await page.screenshot({ path: 'docs/user-feature-review/tenant-admin/evidence/90-regress-fail.png' });
  } finally {
    await browser.close();
  }
})();
