// Phase 3 verification — care_coordinator implementation.
const { chromium } = require('playwright');
const OUT = 'docs/user-feature-review/care-coordinator/evidence';
const errors = [];
let shot = 7;

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text().slice(0, 140)); });
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message.slice(0, 140)));
  const snap = async (name) => {
    shot += 1;
    await page.screenshot({ path: `${OUT}/${String(shot).padStart(2, '0')}-${name}.png` });
  };

  try {
    await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' });
    await page.fill('#username', 'test.care_coordinator');
    await page.fill('#password', 'Test@123456');
    await Promise.all([
      page.waitForURL('**/orders', { timeout: 20000 }).catch(() => {}),
      page.click('button[type="submit"]'),
    ]);
    await page.waitForTimeout(2500);
    console.log('landing:', page.url());

    // Sidebar inventory — Coordination section must exist.
    const menu = await page.locator('.ant-menu').innerText().catch(() => '');
    console.log('SIDEBAR:', menu.replace(/\n+/g, ' | ').slice(0, 400));
    await snap('17-orders-landing');

    // Schedule Board — must load data now (no "Failed to load schedule").
    await page.goto('http://localhost:5173/schedule-board', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);
    await snap('18-schedule-board');
    const sb = await page.locator('body').innerText();
    console.log('schedule board:', sb.slice(0, 220).replace(/\n+/g, ' | '));
    console.log('schedule-failed?', /Failed to load schedule/.test(sb));

    // Files — must load list now (no "Missing permission: FILE_READ").
    await page.goto('http://localhost:5173/', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);
    await snap('19-files');
    const files = await page.locator('body').innerText();
    console.log('files dead-end?', /Missing permission: FILE_READ/.test(files));
    console.log('files body:', files.slice(0, 180).replace(/\n+/g, ' | '));

    // Patient page — Reports & Results card (REPORT_READ).
    await page.goto('http://localhost:5173/patients/13', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);
    await snap('20-patient-reports');
    const pat = await page.locator('body').innerText();
    console.log('reports card?', /Reports & Results/.test(pat), '| empty?', /No reports yet/.test(pat));

    console.log('errors:', errors.length ? errors.slice(0, 5) : 'none');
  } catch (e) {
    console.log('FAIL', e.message.split('\n')[0]);
    await page.screenshot({ path: `${OUT}/99-fail.png` });
  } finally {
    await browser.close();
  }
})();
