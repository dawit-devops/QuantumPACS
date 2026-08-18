// Phase 1 live walkthrough — technologist (test.technologist / Test@123456).
// Walks every reachable surface, screenshots each, monitors console + network.
const { chromium } = require('playwright');
const path = require('path');

const OUT = 'docs/user-feature-review/technologist/evidence';
const results = [];
const errors = [];
let shot = 0;

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push('console: ' + m.text().slice(0, 200));
  });
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message.slice(0, 200)));
  page.on('requestfailed', (r) => errors.push('netfail: ' + r.url().slice(0, 120) + ' ' + (r.failure()?.errorText || '')));

  const snap = async (name) => {
    shot += 1;
    await page.screenshot({ path: `${OUT}/${String(shot).padStart(2, '0')}-${name}.png` });
  };
  const probe = async (url) => {
    await page.goto('http://localhost:5173' + url, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1500);
    const u = page.url();
    const ok = u.includes(url.split('?')[0]) && !u.includes('/login');
    results.push({ url, landed: u.replace('http://localhost:5173', ''), ok });
    return u;
  };

  try {
    // Login
    await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' });
    await page.fill('#username', 'test.technologist');
    await page.fill('#password', 'Test@123456');
    await Promise.all([
      page.waitForURL('**/exams', { timeout: 20000 }),
      page.click('button[type="submit"]'),
    ]);
    console.log('PASS login ->', page.url());
    await page.waitForTimeout(2000);
    await snap('00-landing-exams');

    // Sidebar inventory: which nav items are visible?
    const menuText = await page.locator('.ant-menu').innerText().catch(() => '(no menu)');
    console.log('MENU:', menuText.replace(/\n+/g, ' | ').slice(0, 400));

    // 1. My Exams (/exams) — filters, tabs, table
    const wlRows = await page.locator('table.ant-table tbody tr').count();
    console.log('worklist rows:', wlRows);
    const wlHeader = await page.locator('h2').first().innerText();
    results.push({ surface: 'My Exams', rows: wlRows, header: wlHeader });

    // open the first exam
    const firstRow = page.locator('table.ant-table tbody tr').first();
    if (await firstRow.count()) {
      const accession = await firstRow.locator('td').nth(1).innerText().catch(() => '');
      await firstRow.locator('button:has-text("Open Exam")').click();
      await page.waitForURL('**/exams/*', { timeout: 15000 });
      await page.waitForTimeout(2000);
      await snap('01-exam-console');
      const steps = await page.locator('.exam-steps').innerText().catch(() => '(no steps)');
      console.log('exam console URL:', page.url(), '| steps:', steps.replace(/\n+/g, '>').slice(0, 120));
      // exam actions available (EXAM_WRITE held)
      const writeBtns = await page.locator('button:has-text("Acquire Image"), button:has-text("Complete Exam"), button:has-text("Log Incident"), button:has-text("Emergency Override")').count();
      console.log('write actions visible:', writeBtns);
      results.push({ surface: 'ExamConsole', accession, writeActions: writeBtns });
      await page.goBack();
      await page.waitForTimeout(1200);
    }

    // 2. Modality Worklist (/worklist)
    await probe('/worklist');
    await page.waitForTimeout(1200);
    await snap('02-modality-worklist');

    // 3. Schedule Board (/schedule-board)
    await probe('/schedule-board');
    await page.waitForTimeout(1200);
    await snap('03-schedule-board');

    // 4. Files (/)
    await probe('/');
    await page.waitForTimeout(1500);
    await snap('04-files');

    // 5. Account (/account)
    await probe('/account');
    await page.waitForTimeout(1000);
    await snap('05-account');

    // Denial probes — surfaces the role must NOT reach
    const denied = ['/reading', '/qa/queue', '/qa/protocols', '/metrics', '/dicomweb',
      '/replicas', '/users', '/roles', '/tenants', '/logs', '/service-keys',
      '/routing', '/hl7', '/fhir/config', '/integrations', '/admin',
      '/frontdesk/registration', '/frontdesk/queue', '/portal', '/peer-review',
      '/reading/home', '/admin/maintenance', '/admin/backups'];
    for (const d of denied) {
      const landed = await probe(d);
      console.log(`deny ${d} -> ${landed.replace('http://localhost:5173', '')} ${landed.includes('/login') ? '(LOGIN!)' : ''}`);
    }

    console.log('\n=== RESULTS ===');
    for (const r of results) console.log(JSON.stringify(r));
    console.log('console/page/net errors:', errors.length ? errors.slice(0, 10) : 'none');
  } catch (e) {
    console.log('FAIL', e.message.split('\n')[0]);
    await page.screenshot({ path: `${OUT}/99-fail.png` });
  } finally {
    await browser.close();
  }
})();
