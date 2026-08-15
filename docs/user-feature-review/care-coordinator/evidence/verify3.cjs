// Verify Orders page with seeded data + summary headline.
const { chromium } = require('playwright');
const OUT = 'docs/user-feature-review/care-coordinator/evidence';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  try {
    await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' });
    await page.fill('#username', 'test.care_coordinator');
    await page.fill('#password', 'Test@123456');
    await Promise.all([
      page.waitForURL('**/orders', { timeout: 20000 }).catch(() => {}),
      page.click('button[type="submit"]'),
    ]);
    await page.waitForTimeout(3000);

    const body = await page.locator('body').innerText();
    console.log('summary:', (body.match(/\d+ open · \d+ waiting >24h · \d+ reported today/) || ['none'])[0]);
    console.log('has row:', /Smoke\^Test/.test(body), '| status tag:', /requested/.test(body));
    console.log('has procedure:', /CT Abdomen with contrast/.test(body));

    // Filters render with aria-labels (P2-5 pattern).
    const statusFilter = await page.locator('#orders-status-filter').count();
    const modalityFilter = await page.locator('#orders-modality-filter').count();
    const patientFilter = await page.locator('#orders-patient-filter').count();
    console.log('filter aria ids:', statusFilter, modalityFilter, patientFilter);

    await page.screenshot({ path: `${OUT}/21-orders-row.png` });

    // Row click → patient page.
    await page.locator('.ant-table-row').first().click();
    await page.waitForTimeout(2000);
    console.log('row click ->', page.url());
    console.log('patient renders:', /Smoke\^Test/.test(await page.locator('body').innerText().then(t => t.slice(0, 300))));
  } catch (e) {
    console.log('FAIL', e.message.split('\n')[0]);
    await page.screenshot({ path: `${OUT}/99-fail.png` });
  } finally {
    await browser.close();
  }
})();
