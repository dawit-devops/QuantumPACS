// Phase 1 walkthrough — care_coordinator (test.care_coordinator / Test@123456).
const { chromium } = require('playwright');
const OUT = 'docs/user-feature-review/care-coordinator/evidence';
const errors = [];
let shot = 0;

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text().slice(0, 180)); });
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message.slice(0, 180)));

  const snap = async (name) => {
    shot += 1;
    await page.screenshot({ path: `${OUT}/${String(shot).padStart(2, '0')}-${name}.png` });
  };
  const probe = async (url) => {
    await page.goto('http://localhost:5173' + url, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1800);
    return page.url().replace('http://localhost:5173', '');
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
    console.log('landing:', page.url());

    // Sidebar inventory
    const menu = await page.locator('.ant-menu').innerText().catch(() => '');
    console.log('SIDEBAR:', menu.replace(/\n+/g, ' | ').slice(0, 500));

    // 1. Reading worklist
    await snap('10-reading-worklist');
    const wl = await page.locator('body').innerText();
    console.log('reading body:', wl.slice(0, 300).replace(/\n+/g, ' | '));
    const wlRows = await page.locator('.ant-table-tbody tr.ant-table-row').count();
    console.log('reading rows:', wlRows);

    // 2. Patient page (PATIENT_READ + CHART_READ)
    await probe('/patients/1');
    await page.waitForTimeout(1500);
    await snap('11-patient');
    const pat = await page.locator('body').innerText();
    console.log('patient page:', pat.slice(0, 250).replace(/\n+/g, ' | '));

    // 3. Files + viewer (STUDY_READ / VIEWER_READ)
    await probe('/');
    await page.waitForTimeout(1500);
    await snap('12-files');
    const files = await page.locator('body').innerText();
    console.log('files page:', files.slice(0, 200).replace(/\n+/g, ' | '));

    // 4. Account
    await probe('/account');
    await page.waitForTimeout(1000);
    await snap('13-account');

    // 5. Denial probes — surfaces this role must NOT reach
    const denied = ['/exams', '/worklist', '/qa/queue', '/admin', '/metrics',
      '/frontdesk/registration', '/frontdesk/queue', '/portal', '/roles',
      '/users', '/tenants', '/logs', '/replicas', '/dicomweb', '/schedule-board'];
    for (const d of denied) {
      const landed = await probe(d);
      console.log(`probe ${d} -> ${landed} ${landed === d ? '(RENDERED)' : '(bounced)'}`);
    }

    console.log('errors:', errors.length ? errors.slice(0, 5) : 'none');
  } catch (e) {
    console.log('FAIL', e.message.split('\n')[0]);
    await page.screenshot({ path: `${OUT}/99-fail.png` });
  } finally {
    await browser.close();
  }
})();
