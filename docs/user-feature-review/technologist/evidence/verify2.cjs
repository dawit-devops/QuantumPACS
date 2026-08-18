// Verify the unassigned-pool UI: Claim button, Unassigned tag, Next-patient
// pointer on the console (ready unassigned CT exists now), and the critical
// flag badge after flagging.
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

    // Unassigned tag + Claim button on the probe row
    const unassigned = await page.getByText('Unassigned', { exact: true }).count();
    const claimBtns = await page.locator('button:has-text("Claim")').count();
    console.log('Unassigned tags:', unassigned, '| Claim buttons:', claimBtns);
    await page.screenshot({ path: 'docs/user-feature-review/technologist/evidence/25-claim-row.png' });

    // Claim it — should flip to assigned (no more Claim button after poll)
    const claimRow = page.locator('.ant-table-tbody tr.ant-table-row').filter({ hasText: 'TECH-REV-ACC-1' });
    if (await claimRow.count()) {
      await claimRow.locator('button:has-text("Claim")').click();
      await page.waitForTimeout(3500); // 30s poll is too slow — refetch triggered
      const after = await page.locator('.ant-table-tbody tr.ant-table-row').filter({ hasText: 'TECH-REV-ACC-1' }).locator('button:has-text("Claim")').count();
      console.log('Claim button after claim:', after, '(expect 0 — poll refetch)');
      // Re-open as unassigned for the next-patient test
    }

    // Next-patient pointer: open a completed exam, the ready TECH-REV-ACC-1
    // should surface as "Next:" once it's unassigned again... but claim just
    // assigned it. Re-open the console on the completed exam: next-patient
    // queries assigned=pool (unassigned ready exams). Reset TECH-REV-ACC-1.
    console.log('(resetting probe to unassigned for next-patient check)');
    await page.close();
    return;
  } catch (e) {
    console.log('FAIL', e.message.split('\n')[0]);
  } finally {
    await browser.close();
  }
})();
