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

  await page.goto(BASE, { waitUntil: 'networkidle' });
  await sleep(2000);
  await page.getByPlaceholder('Username').fill('admin');
  await page.getByPlaceholder('Password').fill('wrongpass');
  await page.getByRole('button', { name: /sign in/i }).click();
  await sleep(3000);

  console.log('\n=== PAGE HTML (body) ===');
  const html = await page.locator('body').innerHTML();
  console.log(html.substring(0, 2000));

  // Check ant-message
  const antMessage = await page.locator('.ant-message').count();
  console.log('\nant-message elements:', antMessage);
  if (antMessage > 0) {
    const msgHtml = await page.locator('.ant-message').innerHTML();
    console.log('Message HTML:', msgHtml);
  }

  // Check all text
  const bodyText = await page.locator('body').innerText();
  console.log('\n=== BODY TEXT ===');
  console.log(bodyText);

  await page.screenshot({ path: '/tmp/eval-wrong-pw.png', fullPage: true });
  await browser.close();
}

main().catch(e => {
  console.error('FAILED:', e.message);
  process.exit(1);
});
