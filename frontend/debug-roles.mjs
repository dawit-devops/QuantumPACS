import { chromium } from 'playwright';

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  
  page.on('console', msg => {
    if (msg.type() === 'error') console.log(`[ERROR] ${msg.text()}`);
  });

  // Login first
  await page.goto('http://localhost:5173/login', { waitUntil: 'networkidle' });
  await new Promise(r => setTimeout(r, 2000));
  await page.getByPlaceholder('Username').fill('admin');
  await page.getByPlaceholder('Password').fill('pa55w0rd');
  await page.getByRole('button', { name: /sign in/i }).click();
  await new Promise(r => setTimeout(r, 3000));

  // Navigate to roles
  await page.goto('http://localhost:5173/roles', { waitUntil: 'networkidle' });
  await new Promise(r => setTimeout(r, 3000));
  
  console.log('URL:', page.url());
  
  const bodyText = await page.locator('body').innerText();
  console.log('Body:', bodyText.substring(0, 1000));

  const rows = await page.locator('.ant-table-tbody tr.ant-table-row').count();
  console.log('Table rows:', rows);

  const anyRows = await page.locator('table tr').count();
  console.log('All table rows:', anyRows);

  const hasSpinner = await page.locator('.ant-spin').count();
  console.log('Spinners:', hasSpinner);

  await page.screenshot({ path: '/tmp/eval-roles.png', fullPage: true });
  await browser.close();
}

main().catch(e => console.error(e));
