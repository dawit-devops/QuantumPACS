const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");
const BASE = "http://localhost:5173";
const LOG = path.join(__dirname, "walkthrough.log");
const SHOTS = path.join(__dirname);
const log = (m) => { const l = `[${new Date().toISOString()}] ${m}`; console.log(l); fs.appendFileSync(LOG, l + "\n"); };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1366, height: 850 } });
  const errs = [];
  page.on("pageerror", (e) => errs.push(e.message));
  await page.goto(BASE + "/login", { waitUntil: "domcontentloaded" });
  await page.getByPlaceholder("Username").fill("test.tenant_admin");
  await page.getByPlaceholder("Password").fill("Test@123456");
  await page.getByRole("button", { name: /sign in/i }).click();
  await sleep(4000);

  await page.goto(BASE + "/tenants", { waitUntil: "domcontentloaded" });
  await sleep(3000);
  const usageBtn = page.getByRole("button", { name: /Usage/i }).first();
  if (await usageBtn.isVisible().catch(() => false)) {
    await usageBtn.click();
    await sleep(3000);
    const drawer = page.locator(".ant-drawer");
    const vis = await drawer.isVisible().catch(() => false);
    const text = vis ? await drawer.innerText().catch(() => "") : "";
    log(`USAGE DRAWER visible=${vis} text=${text.slice(0, 300).replace(/\n+/g, " | ")}`);
    await page.screenshot({ path: path.join(SHOTS, "32-usage-drawer.png"), fullPage: true });
  } else {
    log("Usage button NOT visible");
  }
  log(`PAGE ERRORS: ${errs.length}`);
  await browser.close();
  log("usage2 complete");
})().catch((e) => { console.error(e); process.exit(1); });
