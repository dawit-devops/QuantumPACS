// Phase 3 verification — as test.technologist with the canonical 15 grants
// (post migration 062): denial routes must bounce, new UI must render.
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message.slice(0, 150)));

  try {
    await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' });
    await page.fill('#username', 'test.technologist');
    await page.fill('#password', 'Test@123456');
    await Promise.all([
      page.waitForURL('**/exams', { timeout: 20000 }),
      page.click('button[type="submit"]'),
    ]);
    await page.waitForTimeout(2500);
    console.log('landing:', page.url());

    // 1. Denials — the drift fix must make these bounce to /exams
    for (const d of ['/reading', '/qa/queue', '/admin', '/portal', '/metrics', '/users']) {
      await page.goto('http://localhost:5173' + d, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(1800);
      const u = page.url().replace('http://localhost:5173', '');
      console.log(`DENY ${d} -> ${u} ${u === d ? 'STILL THERE (BAD)' : 'bounced OK'}`);
    }

    // 2. Worklist — new UI: summary headline, read-state column, claim button
    await page.goto('http://localhost:5173/exams', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2500);
    const body = await page.locator('body').innerText();
    console.log('summary line:', body.includes('ready') ? 'present' : 'MISSING');
    const readStateCol = await page.locator('th:has-text("Read State")').count();
    console.log('Read State column:', readStateCol);
    const claimBtns = await page.locator('button:has-text("Claim")').count();
    console.log('Claim buttons:', claimBtns);
    const unassigned = await page.getByText('Unassigned', { exact: true }).count();
    console.log('Unassigned tags:', unassigned);
    await page.screenshot({ path: 'docs/user-feature-review/technologist/evidence/21-worklist-new.png' });

    // 3. Exam console — Flag Critical button + next-patient + prior screenings
    const firstRow = page.locator('.ant-table-tbody tr.ant-table-row').first();
    const acc = await firstRow.locator('td').nth(1).innerText().catch(() => '');
    await firstRow.locator('button:has-text("Open Exam")').click();
    await page.waitForURL('**/exams/*', { timeout: 15000 });
    await page.waitForTimeout(2500);
    console.log('exam:', page.url());
    const flagBtn = await page.locator('button:has-text("Flag Critical")').count();
    console.log('Flag Critical button:', flagBtn);
    const nextLine = await page.getByText('Next:', { exact: false }).count();
    console.log('Next-patient line:', nextLine);
    const prior = await page.getByText('Prior screenings').count();
    console.log('Prior screenings:', prior);
    await page.screenshot({ path: 'docs/user-feature-review/technologist/evidence/22-console-new.png' });

    // 4. Open the flag modal
    if (flagBtn) {
      await page.locator('button:has-text("Flag Critical")').click();
      await page.waitForTimeout(800);
      const modalTitle = await page.locator('.ant-modal-title').innerText().catch(() => '');
      console.log('flag modal:', modalTitle);
      await page.screenshot({ path: 'docs/user-feature-review/technologist/evidence/23-flag-modal.png' });
      await page.locator('.ant-modal button:has-text("Cancel")').click().catch(() => {});
    }

    // 5. Reading worklist critical tag — as a radiologist (who sees flags)
    await page.context().clearCookies();
    await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' });
    await page.fill('#username', 'test.radiologist');
    await page.fill('#password', 'Test@123456');
    await Promise.all([
      page.waitForURL('**/reading', { timeout: 20000 }).catch(() => {}),
      page.click('button[type="submit"]'),
    ]);
    await page.waitForTimeout(2500);
    const flagCol = await page.locator('th:has-text("Flag")').count();
    console.log('Reading worklist Flag column:', flagCol);
    const flagTag = await page.locator('.ant-tag', { hasText: /CRITICAL|LOW/ }).count();
    console.log('flag tags in reading list:', flagTag);
    await page.screenshot({ path: 'docs/user-feature-review/technologist/evidence/24-reading-flag-col.png' });

    console.log('pageerrors:', errors.length ? errors.slice(0, 3) : 'none');
  } catch (e) {
    console.log('FAIL', e.message.split('\n')[0]);
    await page.screenshot({ path: 'docs/user-feature-review/technologist/evidence/99-verify-fail.png' });
  } finally {
    await browser.close();
  }
})();
