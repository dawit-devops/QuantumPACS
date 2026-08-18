// Identify the anonymous DIV covering the modal OK button.
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

    await page.locator('button', { hasText: 'Flag Critical' }).first().evaluate((el) => el.click());
    await page.waitForTimeout(1200);

    const ok = page.locator('.ant-modal button:has-text("Flag for Immediate Read")');
    const box = await ok.boundingBox();
    const cx = box.x + box.width / 2, cy = box.y + box.height / 2;
    const info = await page.evaluate(([x, y]) => {
      const el = document.elementFromPoint(x, y);
      if (!el) return 'none';
      let chain = [];
      let n = el;
      while (n && chain.length < 4) {
        chain.push(`${n.tagName.toLowerCase()}.${(n.className || '').toString().slice(0, 70)}`);
        n = n.parentElement;
      }
      const r = el.getBoundingClientRect();
      return { chain, rect: { x: r.x, y: r.y, w: r.width, h: r.height }, z: getComputedStyle(el).zIndex, pos: getComputedStyle(el).position };
    }, [cx, cy]);
    console.log('center element chain:', JSON.stringify(info, null, 1));
    // Also check the button's own center via its inner span
    const okSpan = ok.locator('span').last();
    console.log('button inner span count:', await okSpan.count());
  } catch (e) {
    console.log('FAIL', e.message.split('\n')[0]);
  } finally {
    await browser.close();
  }
})();
