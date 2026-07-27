import { chromium } from 'playwright';

const BASE = 'http://localhost:5173';

async function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();

  page.on('console', msg => console.log(`[BROWSER ${msg.type()}] ${msg.text()}`));
  page.on('pageerror', err => console.log(`[BROWSER ERROR] ${err.message}`));

  // LOGIN
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
  await sleep(1500);
  await page.locator('#username').fill('admin');
  await page.locator('#password').fill('pa55w0rd');
  await page.locator('button[type="submit"]').click();
  await sleep(3000);

  const currentUrl = page.url();
  console.log('CURRENT URL:', currentUrl);
  console.log('CONTAINS LOGIN:', currentUrl.includes('/login'));
  console.log('BODY SNIPPET:', (await page.locator('body').innerText()).substring(0, 200));

  if (currentUrl.includes('/login')) {
    console.log('=> STILL ON LOGIN PAGE');
  } else {
    console.log('=> LOGIN SUCCESSFUL, NAVIGATED AWAY');
    // Check sidebar
    const menuItems = await page.locator('.ant-menu-item').all();
    console.log('Menu items found:', menuItems.length);
    for (const item of menuItems) {
      const text = await item.innerText();
      console.log('  -', text.trim());
    }
  }

  await page.screenshot({ path: '/tmp/eval-final.png', fullPage: true });
  await browser.close();
}

main().catch(e => {
  console.error('FAILED:', e.message);
  process.exit(1);
});
