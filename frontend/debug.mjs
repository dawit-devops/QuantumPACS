import { chromium } from 'playwright';

const BASE = 'http://localhost:5173';

async function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();

  // Clear all localStorage before starting
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => localStorage.clear());

  page.on('console', msg => {
    if (msg.type() === 'error') console.log(`[BROWSER ${msg.type()}] ${msg.text()}`);
  });
  page.on('pageerror', err => console.log(`[PAGE ERROR] ${err.message}`));

  // LOGIN
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
  await sleep(2000);
  await page.locator('#username').fill('admin');
  await page.locator('#password').fill('pa55w0rd');
  await page.locator('button[type="submit"]').click();
  await sleep(3000);

  const url1 = page.url();
  console.log('\n=== AFTER LOGIN SUBMIT ===');
  console.log('URL:', url1);
  console.log('Token in localStorage:', await page.evaluate(() => localStorage.getItem('token') ? 'YES' : 'NO'));

  // Check if we're on the login page or on the main app
  const bodyText = await page.locator('body').innerText();
  const onLoginPage = bodyText.includes('Sign in to your account');

  if (onLoginPage) {
    console.log('=> STILL ON LOGIN PAGE');
    console.log('Body:', bodyText.substring(0, 400));
  } else {
    console.log('=> LOGIN OK');
    console.log('Body snippet:', bodyText.substring(0, 200));

    // Navigate to metrics directly
    await page.goto(`${BASE}/metrics`, { waitUntil: 'networkidle' });
    await sleep(3000);
    console.log('\n=== METRICS PAGE ===');
    console.log('URL:', page.url());
    if (page.url().includes('/login')) {
      console.log('=> REDIRECTED TO LOGIN');
    } else {
      const statTitles = await page.locator('.ant-statistic-title').allTextContents();
      console.log('Stats:', statTitles.join(', '));
    }
  }

  await page.screenshot({ path: '/tmp/eval-debug.png', fullPage: true });
  await browser.close();
}

main().catch(e => {
  console.error('FAILED:', e.message);
  process.exit(1);
});
