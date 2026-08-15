const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");
const BASE = "http://localhost:5173";
const LOG = path.join(__dirname, "walkthrough.log");
const log = (m) => { const l = `[${new Date().toISOString()}] ${m}`; console.log(l); fs.appendFileSync(LOG, l + "\n"); };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1366, height: 850 } });
  await page.goto(BASE + "/login", { waitUntil: "domcontentloaded" });
  await page.getByPlaceholder("Username").fill("test.tenant_admin");
  await page.getByPlaceholder("Password").fill("Test@123456");
  await page.getByRole("button", { name: /sign in/i }).click();
  await sleep(4000);
  await page.goto(BASE + "/roles", { waitUntil: "domcontentloaded" });
  await sleep(3500);
  const rows = page.locator(".ant-table-tbody tr");
  const rc = await rows.count().catch(() => 0);
  log(`ROWS: ${rc}`);
  for (let i = 0; i < Math.min(rc, 8); i++) {
    const text = (await rows.nth(i).innerText().catch(() => "")).replace(/\n+/g, " | ");
    const disabledBtns = await rows.nth(i).locator("button:disabled").count().catch(() => 0);
    log(`  row[${i}]: ${text.slice(0, 90)} | disabledBtns=${disabledBtns}`);
  }
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
