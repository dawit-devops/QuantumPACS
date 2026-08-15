// Drift consequence probe: with 92 grants the technologist can reach QA,
// Reading, Admin, etc. Verify QA queue renders and the exam console acquire
// flow works (EXAM_WRITE is canonical anyway).
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

    // QA queue (drift: QA_READ is NOT canonical for technologist)
    await page.goto('http://localhost:5173/qa/queue', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);
    console.log('QA URL:', page.url());
    const qa = await page.locator('body').innerText();
    console.log('QA body:', qa.slice(0, 350).replace(/\n+/g, ' | '));
    await page.screenshot({ path: 'docs/user-feature-review/technologist/evidence/20-qa-queue-drift.png' });

    // Exam console — acquire flow on the E2E completed exam (verify write UI)
    await page.goto('http://localhost:5173/exams/cbf6baeb-5519-4f35-a015-c370e754495a', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);
    const body = await page.locator('body').innerText();
    const isComplete = body.includes('Acquisition complete') || body.includes('handed off');
    console.log('exam completed-state banner:', isComplete);
    const acquireDisabled = await page.locator('button:has-text("Acquire Image")').count();
    console.log('Acquire Image visible on completed exam:', acquireDisabled);

    console.log('pageerrors:', errors.length ? errors.slice(0, 3) : 'none');
  } catch (e) {
    console.log('FAIL', e.message.split('\n')[0]);
  } finally {
    await browser.close();
  }
})();
