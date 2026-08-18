// P1-2 AC3 regression check + P0-1 physician schedule access.
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await ctx.addInitScript(() => {
    localStorage.setItem('quantumpacs-tour-done', '1');
  });
  const page = await ctx.newPage();

  const login = async (username) => {
    await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' });
    await page.fill('#username', username);
    await page.fill('#password', 'Test@123456');
    await Promise.all([
      page.waitForURL('**/*', { timeout: 20000 }).catch(() => {}),
      page.click('button[type="submit"]'),
    ]);
    await page.waitForTimeout(2200);
    return page.url().replace('http://localhost:5173', '');
  };

  try {
    const landings = {};
    for (const role of ['physician', 'technologist', 'radiologist', 'receptionist']) {
      landings[role] = await login(`test.${role}`);
    }
    console.log('landings:', JSON.stringify(landings));

    // Physician schedule board — must load data now.
    await login('test.physician');
    await page.goto('http://localhost:5173/schedule-board', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);
    const sb = await page.locator('body').innerText();
    console.log('physician schedule failed?', /Failed to load schedule/.test(sb));
    console.log('physician schedule renders:', /Schedule Board/.test(sb));
  } catch (e) {
    console.log('FAIL', e.message.split('\n')[0]);
  } finally {
    await browser.close();
  }
})();
