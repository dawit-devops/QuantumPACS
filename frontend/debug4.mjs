import { chromium } from 'playwright';

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

  const allLogs = [];
  page.on('console', msg => {
    allLogs.push({ type: msg.type(), text: msg.text() });
  });
  page.on('pageerror', err => {
    allLogs.push({ type: 'pageerror', text: err.message, stack: err.stack });
  });

  await page.goto('http://localhost:5173/login', { waitUntil: 'networkidle' });
  await new Promise(r => setTimeout(r, 5000));

  console.log('ALL CONSOLE OUTPUT:');
  for (const log of allLogs) {
    console.log(`[${log.type}] ${log.text}`);
    if (log.stack) console.log(log.stack.substring(0, 500));
  }

  await page.screenshot({ path: '/tmp/eval-crash.png', fullPage: true });
  await browser.close();
}

main().catch(e => console.error(e));
