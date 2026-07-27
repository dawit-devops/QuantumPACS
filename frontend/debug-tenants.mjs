import { chromium } from 'playwright';

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  page.on('console', msg => { if (msg.type() === 'error') console.log('[ERROR]', msg.text()); });

  await page.goto('http://localhost:5173/login', { waitUntil: 'networkidle' });
  await new Promise(r => setTimeout(r, 2000));
  await page.getByPlaceholder('Username').fill('admin');
  await page.getByPlaceholder('Password').fill('pa55w0rd');
  await page.getByRole('button', { name: /sign in/i }).click();
  await new Promise(r => setTimeout(r, 3000));

  await page.goto('http://localhost:5173/tenants', { waitUntil: 'networkidle' });
  await new Promise(r => setTimeout(r, 4000));
  
  const url = page.url();
  console.log('URL:', url);
  const body = await page.locator('body').innerText();
  console.log('Body:', body);
  
  await browser.close();
}

main().catch(e => console.error('FAILED:', e.message));
