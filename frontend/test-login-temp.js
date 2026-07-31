const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();

  const apiCalls = [];

  page.on('response', (resp) => {
    const u = resp.url();
    if (u.includes('/api/') && !u.includes('ws_token')) {
      apiCalls.push({ method: resp.request().method(), url: u.replace('http://localhost:8080', ''), status: resp.status() });
    }
  });

  console.log('=== Login ===');
  await page.goto('http://localhost:5173/login', { waitUntil: 'networkidle' });
  await page.fill('input[type="text"], input#username', 'admin');
  await page.fill('input[type="password"], input#password', 'pa55w0rd');
  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 8000 });
  await page.waitForTimeout(2000);
  console.log('✓ Logged in');

  async function visit(path, label) {
    apiCalls.length = 0;
    console.log(`\n=== ${label}: ${path} ===`);
    await page.goto(`http://localhost:5173${path}`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);
    const heading = await page.locator('h1, h2, h3, h4, .ant-page-header-heading-title, .ant-typography').allTextContents();
    const buttons = await page.locator('button, .ant-btn').allTextContents();
    const bodyText = await page.locator('body').innerText();
    console.log('Title heading(s):', heading.slice(0, 5));
    console.log('Body snippet:', bodyText.slice(0, 200).replace(/\n+/g, ' | '));
    console.log('Buttons:', buttons.filter(b => b.trim()).slice(0, 8));
    console.log('API calls:');
    for (const a of apiCalls) console.log(`  ${a.status} ${a.method} ${a.url}`);
    await page.screenshot({ path: `/tmp/page-${path.replace(/\//g, '_')}.png` });
  }

  await visit('/files', 'Files');
  await visit('/worklist', 'Worklist (Phase 1)');
  await visit('/service-keys', 'Service Keys (Phase 2)');
  await visit('/routing', 'Routing (Phase 3)');
  await visit('/tenants', 'Tenants (Phase 4)');
  await visit('/account', 'Account');
  await visit('/logs', 'Logs');

  await browser.close();
  console.log('\nDone.');
})().catch((e) => { console.error('Test error:', e); process.exit(1); });
