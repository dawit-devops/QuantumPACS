// Dump the overlay div's HTML to identify it.
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
    const html = await page.evaluate(([x, y]) => {
      const el = document.elementFromPoint(x, y);
      return el ? el.outerHTML.slice(0, 600) : 'none';
    }, [cx, cy]);
    console.log('overlay HTML:', html);
    // List all direct children of ant-app that overlap the button rect
    const overlaps = await page.evaluate(([x, y]) => {
      const out = [];
      document.querySelectorAll('.ant-app > div').forEach((el) => {
        const r = el.getBoundingClientRect();
        if (r.x <= x && x <= r.x + r.width && r.y <= y && y <= r.y + r.height) {
          out.push(el.outerHTML.slice(0, 200));
        }
      });
      return out;
    }, [cx, cy]);
    console.log('overlapping ant-app children:', JSON.stringify(overlaps, null, 1));
  } catch (e) {
    console.log('FAIL', e.message.split('\n')[0]);
  } finally {
    await browser.close();
  }
})();
