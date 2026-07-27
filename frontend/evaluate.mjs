import { chromium } from 'playwright';
import { writeFileSync } from 'fs';

const BASE = 'http://localhost:5173';

async function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();

  const logs = [];
  page.on('console', msg => logs.push(`[${msg.type()}] ${msg.text()}`));
  page.on('pageerror', err => logs.push(`[PAGE ERROR] ${err.message}`));

  // LOGIN
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
  await sleep(1500);
  await page.locator('#username').fill('admin');
  await page.locator('#password').fill('pa55w0rd');
  await page.locator('button[type="submit"]').click();
  await sleep(3000);
  console.log('1. LOGIN — URL:', page.url());
  await page.screenshot({ path: '/tmp/eval-01-after-login.png', fullPage: true });

  if (page.url().includes('/login')) {
    console.log('   ❌ STILL ON LOGIN PAGE');
    const body = await page.locator('body').innerText();
    console.log('   Body:', body.substring(0, 300));
    await browser.close();
    return;
  }

  // FILES PAGE
  const sidebarLinks = await page.locator('.ant-menu-item a').all();
  for (const link of sidebarLinks) {
    const href = await link.getAttribute('href');
    const text = await link.innerText();
    if (text) console.log('2. SIDEBAR LINK:', text.trim(), '->', href);
  }
  await page.screenshot({ path: '/tmp/eval-02-files.png', fullPage: true });

  // METRICS (visit directly via URL)
  await page.goto(`${BASE}/metrics`, { waitUntil: 'networkidle' });
  await sleep(3000);
  console.log('\n3. METRICS — URL:', page.url());
  if (page.url().includes('/login')) {
    console.log('   ❌ REDIRECTED TO LOGIN');
  } else {
    const statTitles = await page.locator('.ant-statistic-title').allTextContents();
    console.log('   Stats:', statTitles.join(', '));
    const canvases = await page.locator('canvas').count();
    console.log('   Charts:', canvases);
    await page.screenshot({ path: '/tmp/eval-03-metrics.png', fullPage: true });
  }

  // USERS
  await page.goto(`${BASE}/users`, { waitUntil: 'networkidle' });
  await sleep(2000);
  console.log('\n4. USERS — URL:', page.url());
  if (page.url().includes('/login')) {
    console.log('   ❌ REDIRECTED TO LOGIN');
  } else {
    const rows = await page.locator('.ant-table-tbody tr.ant-table-row').count();
    console.log('   Table rows:', rows);
    await page.screenshot({ path: '/tmp/eval-04-users.png', fullPage: true });
  }

  // ROLES
  await page.goto(`${BASE}/roles`, { waitUntil: 'networkidle' });
  await sleep(2000);
  console.log('\n5. ROLES — URL:', page.url());
  if (page.url().includes('/login')) {
    console.log('   ❌ REDIRECTED TO LOGIN');
  } else {
    const rows = await page.locator('.ant-table-tbody tr.ant-table-row').count();
    console.log('   Table rows:', rows);
    await page.screenshot({ path: '/tmp/eval-05-roles.png', fullPage: true });
  }

  // TENANTS
  await page.goto(`${BASE}/tenants`, { waitUntil: 'networkidle' });
  await sleep(2000);
  console.log('\n6. TENANTS — URL:', page.url());
  if (page.url().includes('/login')) {
    console.log('   ❌ REDIRECTED TO LOGIN');
  } else {
    const rows = await page.locator('.ant-table-tbody tr.ant-table-row').count();
    console.log('   Table rows:', rows);
    await page.screenshot({ path: '/tmp/eval-06-tenants.png', fullPage: true });
  }

  // ACCOUNT
  await page.goto(`${BASE}/account`, { waitUntil: 'networkidle' });
  await sleep(2000);
  console.log('\n7. ACCOUNT — URL:', page.url());
  if (page.url().includes('/login')) {
    console.log('   ❌ REDIRECTED TO LOGIN');
  } else {
    await page.screenshot({ path: '/tmp/eval-07-account.png', fullPage: true });
  }

  // DICOM viewer (no studies to load, but should render)
  await page.goto(`${BASE}/detail/0`, { waitUntil: 'networkidle' });
  await sleep(3000);
  console.log('\n8. VIEWER — URL:', page.url());
  if (page.url().includes('/login')) {
    console.log('   ❌ REDIRECTED TO LOGIN');
  } else {
    await page.screenshot({ path: '/tmp/eval-08-viewer.png', fullPage: true });
  }

  // LOGOUT
  await page.goto(`${BASE}/logout`, { waitUntil: 'networkidle' });
  await sleep(2000);
  console.log('\n9. LOGOUT — URL:', page.url());
  await page.screenshot({ path: '/tmp/eval-09-logout.png', fullPage: true });

  // Console summary
  const errors = logs.filter(l => l.includes('[error]') && !l.includes('Failed to load resource: the server responded'));
  console.log('\n=== CONSOLE ERRORS ===');
  console.log(errors.length ? errors.join('\n') : 'None');
  console.log('\n=== NET ERRORS ===');
  const netErrors = logs.filter(l => l.includes('Failed to load resource: the server responded'));
  console.log(netErrors.length ? netErrors.join('\n') : 'None');
  writeFileSync('/tmp/eval-logs.json', JSON.stringify(logs, null, 2));
  await browser.close();
}

main().catch(e => {
  console.error('FAILED:', e.message);
  process.exit(1);
});
