import { chromium } from 'playwright';

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

  page.on('pageerror', err => console.log('PAGE ERROR:', err.message, err.stack?.substring(0, 300)));

  await page.goto('http://localhost:5173/login', { waitUntil: 'networkidle' });
  await new Promise(r => setTimeout(r, 3000));

  console.log('URL:', page.url());
  console.log('Body:', await page.locator('body').innerText().then(t => t.substring(0, 300)));

  // Take screenshot
  await page.screenshot({ path: '/tmp/eval-load.png', fullPage: true });

  // Now try to login with wrong password  
  await page.getByPlaceholder('Username').fill('admin');
  await page.getByPlaceholder('Password').fill('wrongpass');
  await page.getByRole('button', { name: /sign in/i }).click();
  await new Promise(r => setTimeout(r, 5000));

  console.log('\nAfter wrong login:');
  console.log('URL:', page.url());
  const bodyText = await page.locator('body').innerText();
  console.log('Body:', bodyText.substring(0, 500));

  // Check for login-error
  const errorEl = page.locator('[data-testid="login-error"]');
  const errorVisible = await errorEl.isVisible();
  console.log('Error element visible:', errorVisible);
  if (errorVisible) {
    console.log('Error text:', await errorEl.innerText());
  }

  await page.screenshot({ path: '/tmp/eval-wrong-login.png', fullPage: true });
  await browser.close();
}

main().catch(e => console.error(e));
