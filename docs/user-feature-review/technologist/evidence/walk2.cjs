// Phase 1 walkthrough v2 — the acquisition workspace as test.technologist
// (dev DB role is inflated to 92 grants; the walk documents both the
// intended surfaces and the drift consequence). Proper antd selectors.
const { chromium } = require('playwright');

const OUT = 'docs/user-feature-review/technologist/evidence';
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

  try {
    await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' });
    await page.fill('#username', 'test.technologist');
    await page.fill('#password', 'Test@123456');
    await Promise.all([
      page.waitForURL('**/exams', { timeout: 20000 }),
      page.click('button[type="submit"]'),
    ]);
    await page.waitForTimeout(2500);
    console.log('landing:', page.url());

    // Sidebar — visible top-level sections + items (inflation reveals admin items)
    const menu = await page.locator('.ant-menu').innerText().catch(() => '');
    console.log('SIDEBAR:', menu.replace(/\n+/g, ' | ').slice(0, 600));

    // 1. My Exams — rows, tabs, filters, elapsed
    const rows = await page.locator('.ant-table-tbody tr.ant-table-row').count();
    console.log('exams rows:', rows);
    const headers = await page.locator('.ant-table-thead th').allTextContents();
    console.log('exams columns:', headers.join(','));
    const firstRowText = await page.locator('.ant-table-tbody tr.ant-table-row').first().innerText().catch(() => '');
    console.log('first row:', firstRowText.replace(/\n+/g, ' | ').slice(0, 200));
    await snap('10-exams-worklist');

    // Filter: modality select + status tab click
    await page.locator('.fd-chip', { hasText: 'Completed' }).first().click();
    await page.waitForTimeout(1200);
    const completedRows = await page.locator('.ant-table-tbody tr.ant-table-row').count();
    console.log('completed filter rows:', completedRows);
    await snap('11-exams-completed-filter');
    await page.locator('.fd-chip', { hasText: 'All' }).first().click();
    await page.waitForTimeout(800);

    // 2. Open the first exam console
    await page.locator('.ant-table-tbody tr.ant-table-row').first().locator('button:has-text("Open Exam")').click();
    await page.waitForURL('**/exams/*', { timeout: 15000 });
    await page.waitForTimeout(2500);
    console.log('exam console:', page.url());
    await snap('12-exam-console');
    // Steps + actions visible
    const steps = await page.locator('.exam-steps').innerText().catch(() => '');
    console.log('steps:', steps.replace(/\n+/g, ' > ').slice(0, 150));
    const buttons = await page.locator('button').allTextContents();
    console.log('buttons:', JSON.stringify(buttons.filter((b) => b.trim()).slice(0, 25)));
    // Identity confirm + protocol + acquire + safety + complete affordances
    const writeActions = await page.locator('button:has-text("Confirm Patient"), button:has-text("Start Protocol"), button:has-text("Acquire Image"), button:has-text("Complete Exam"), button:has-text("Log Incident"), button:has-text("Emergency Override")').count();
    console.log('write-action buttons:', writeActions);
    // Dose + safety panels
    const dosePanel = await page.locator('.exam-dose').count();
    const safetyPanel = await page.locator('text=Safety Checks').count();
    console.log('dose panel:', dosePanel, '| safety panel:', safetyPanel);

    // 3. Back to worklist, then Modality Worklist
    await page.goBack();
    await page.waitForURL('**/exams', { timeout: 10000 });
    await page.waitForTimeout(1200);
    await page.goto('http://localhost:5173/worklist', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);
    console.log('modality worklist:', page.url());
    const mwl = await page.locator('body').innerText();
    console.log('MWL body:', mwl.slice(0, 350).replace(/\n+/g, ' | '));
    await snap('13-modality-worklist');

    // 4. Schedule Board
    await page.goto('http://localhost:5173/schedule-board', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);
    console.log('schedule:', page.url());
    await snap('14-schedule-board');
    const sched = await page.locator('body').innerText();
    console.log('schedule body:', sched.slice(0, 300).replace(/\n+/g, ' | '));

    // 5. Files (/) — with the inflated role this renders; note the ES state
    await page.goto('http://localhost:5173/', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);
    console.log('files:', page.url());
    await snap('15-files');

    // 6. Account — permissions list (inflated = 92 shown)
    await page.goto('http://localhost:5173/account', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);
    await snap('16-account');
    const acct = await page.locator('body').innerText();
    console.log('account perms count hint:', (acct.match(/permission/gi) || []).length, '| tags:', await page.locator('.ant-tag').count());

    console.log('console/page errors:', errors.length ? errors.slice(0, 6) : 'none');
  } catch (e) {
    console.log('FAIL', e.message.split('\n')[0]);
    await page.screenshot({ path: `${OUT}/99-fail.png` });
  } finally {
    await browser.close();
  }
})();
