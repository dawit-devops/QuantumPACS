// Phase 1 probe 2 — care_coordinator real-patient + dead-end verification.
const { chromium } = require('playwright');
const OUT = 'docs/user-feature-review/care-coordinator/evidence';
const errors = [];
let shot = 4;

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
      page.waitForURL('**/reading', { timeout: 20000 }).catch(() => {}),
      page.click('button[type="submit"]'),
    ]);
    await page.waitForTimeout(2500);

    // Real patient page (id 13 exists)
    await page.goto('http://localhost:5173/patients/13', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);
    await snap('14-patient-real');
    const pat = await page.locator('body').innerText();
    console.log('patient13:', pat.slice(0, 220).replace(/\n+/g, ' | '));

    // Files page error state
    await page.goto('http://localhost:5173/', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);
    await snap('15-files-state');
    const files = await page.locator('body').innerText();
    console.log('files state:', files.slice(0, 200).replace(/\n+/g, ' | '));

    // Schedule board dead end
    await page.goto('http://localhost:5173/schedule-board', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);
    await snap('16-schedule-board');
    const sb = await page.locator('body').innerText();
    console.log('schedule board:', sb.slice(0, 250).replace(/\n+/g, ' | '));

    // Reading worklist — what can they do here?
    await page.goto('http://localhost:5173/reading', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);
    const wl = await page.locator('body').innerText();
    console.log('reading actions:', wl.slice(0, 300).replace(/\n+/g, ' | '));

    console.log('errors:', errors.length ? errors.slice(0, 6) : 'none');
  } catch (e) {
    console.log('FAIL', e.message.split('\n')[0]);
    await page.screenshot({ path: `${OUT}/99-fail.png` });
  } finally {
    await browser.close();
  }
})();
