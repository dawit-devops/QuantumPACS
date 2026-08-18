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
    const modal = page.locator(".ant-modal");
    const modalVisible = await modal.isVisible().catch(() => false);
    const modalText = modalVisible ? await modal.innerText().catch(() => "") : "";
    log(`USAGE MODAL visible=${modalVisible} text=${modalText.slice(0, 400).replace(/\n+/g, " | ")}`);
    await page.screenshot({ path: path.join(SHOTS, "32-usage-modal.png"), fullPage: true });
  } else {
    log("Usage button NOT visible");
  }
  await browser.close();
  log("usage probe complete");
})().catch((e) => { console.error(e); process.exit(1); });
