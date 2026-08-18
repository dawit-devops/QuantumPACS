// Verify technologist denial behavior precisely: after navigating to a denied
// deep link, what URL does the app land on AND what content renders? Also
// inspect the worklist (why 0 rows showed in the first walkthrough).
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text().slice(0, 150)); });
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message.slice(0, 150)));

  try {
    await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' });
    await page.fill('#username', 'test.technologist');
    await page.fill('#password', 'Test@123456');
    await Promise.all([
      page.waitForURL('**/exams', { timeout: 20000 }),
      page.click('button[type="submit"]'),
    ]);
    await page.waitForTimeout(2500);

    // Worklist state check
    const body = await page.locator('body').innerText();
    const hasEmpty = body.includes('No exams assigned');
    const rows = await page.locator('table.ant-table tbody tr').count();
    const spin = await page.locator('.ant-spin').count();
    console.log(`worklist rows=${rows} emptyText=${hasEmpty} spinners=${spin}`);
    console.log('body slice:', body.slice(0, 500).replace(/\n+/g, ' | '));

    // Denial probes: final URL + heading/content after redirect settles
    const denied = [
      ['/reading', 'REPORT_READ'],
      ['/qa/queue', 'QA_READ'],
      ['/metrics', 'METRICS'],
      ['/dicomweb', 'DICOMWEB adminOnly'],
      ['/replicas', 'REPLICA'],
      ['/users', 'USER_READ'],
      ['/roles', 'ROLE_READ'],
      ['/tenants', 'TENANT_READ'],
      ['/logs', 'LOG_READ'],
      ['/service-keys', 'SERVICE_KEY'],
      ['/routing', 'ROUTING'],
      ['/hl7', 'HL7'],
      ['/fhir/config', 'SYSTEM_ADMIN'],
      ['/integrations', 'SYSTEM_ADMIN'],
      ['/admin', 'adminOnly'],
      ['/frontdesk/registration', 'REGISTRATION'],
      ['/frontdesk/queue', 'QUEUE_READ'],
      ['/portal', 'PORTAL'],
      ['/peer-review', 'PEER_REVIEW'],
      ['/admin/maintenance', 'SYSTEM_ADMIN'],
    ];
    for (const [url, why] of denied) {
      await page.goto('http://localhost:5173' + url, { waitUntil: 'domcontentloaded' });
      // redirect via Navigate is instant; give the landing a moment to render
      await page.waitForTimeout(1800);
      const finalUrl = page.url().replace('http://localhost:5173', '');
      const h2 = await page.locator('h2').first().innerText().catch(() => '');
      const missing = await page.getByText('Missing permission').count();
      console.log(`DENY ${url} (${why}) -> URL=${finalUrl} h2="${h2.slice(0, 40)}" missingPerm=${missing}`);
    }

    // Deep-link to an exam detail directly (allowed, EXAM_READ)
    await page.goto('http://localhost:5173/exams/cbf6baeb', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);
    const examUrl = page.url().replace('http://localhost:5173', '');
    console.log('deep-link /exams/:id ->', examUrl, '| console errors:', errors.length ? errors.slice(0, 3) : 'none');
  } catch (e) {
    console.log('FAIL', e.message.split('\n')[0]);
  } finally {
    await browser.close();
  }
})();
