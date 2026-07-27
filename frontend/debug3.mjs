import { chromium } from 'playwright';

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  
  page.on('console', msg => {
    if (msg.type() === 'error') console.log(`[ERROR] ${msg.text()}`);
    if (msg.type() === 'warning') console.log(`[WARN] ${msg.text()}`);
  });

  await page.goto('http://localhost:5173/login', { waitUntil: 'networkidle' });
  await new Promise(r => setTimeout(r, 2000));

  // Fill wrong password and submit
  await page.getByPlaceholder('Username').fill('admin');
  await page.getByPlaceholder('Password').fill('wrongpass');
  await page.getByRole('button', { name: /sign in/i }).click();
  await new Promise(r => setTimeout(r, 3000));

  // Check entire DOM for message-related elements
  console.log('\n=== FULL DOM INSPECTION ===');
  
  const antMessage = await page.locator('[class*=ant-message]').count();
  console.log('[class*=ant-message] count:', antMessage);
  
  const antNotice = await page.locator('[class*=ant-notice]').count();
  console.log('[class*=ant-notice] count:', antNotice);
  
  // Check document.body children
  const bodyChildren = await page.evaluate(() => {
    return Array.from(document.body.children).map(function(e) {
      return {
        tag: e.tagName,
        id: e.id,
        className: e.className ? e.className.substring(0, 100) : '',
        innerText: (e.innerText || '').substring(0, 100),
      };
    });
  });
  console.log('\nBody children:', JSON.stringify(bodyChildren, null, 2));

  const bodyText = await page.locator('body').innerText();
  console.log('\nBody text:', bodyText);

  await page.screenshot({ path: '/tmp/eval-message-debug.png', fullPage: true });
  await browser.close();
}

main().catch(e => console.error(e));
