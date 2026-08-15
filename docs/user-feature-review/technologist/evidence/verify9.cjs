// Inspect the modal OK button: disabled? covered? what's on top?
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  page.on('pageerror', (e) => console.log('PAGEERROR:', e.message.slice(0, 250)));

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

    await page.locator('button', { hasText: 'Flag Critical' }).first().evaluate((el) => el.click());
    await page.waitForTimeout(1200);

    const ok = page.locator('.ant-modal button:has-text("Flag for Immediate Read")');
    console.log('ok count:', await ok.count());
    console.log('ok disabled:', await ok.isDisabled().catch(() => 'err'));
    console.log('ok visible:', await ok.isVisible().catch(() => 'err'));
    const box = await ok.boundingBox();
    console.log('ok box:', JSON.stringify(box));
    // What element is at the center of the button?
    if (box) {
      const cx = box.x + box.width / 2, cy = box.y + box.height / 2;
      const top = await page.evaluate(([x, y]) => {
        const el = document.elementFromPoint(x, y);
        return el ? el.tagName + '.' + (el.className || '').toString().slice(0, 60) : 'none';
      }, [cx, cy]);
      console.log('element at center:', top);
    }
    // validation errors?
    const errs = await page.locator('.ant-form-item-explain-error').allTextContents();
    console.log('form errors:', JSON.stringify(errs));
    // spinner present anywhere?
    console.log('spinners:', await page.locator('.ant-spin').count());
    console.log('loading buttons:', await page.locator('button.ant-btn-loading').count());
    await page.screenshot({ path: 'docs/user-feature-review/technologist/evidence/28-modal-state.png' });
  } catch (e) {
    console.log('FAIL', e.message.split('\n')[0]);
  } finally {
    await browser.close();
  }
})();
