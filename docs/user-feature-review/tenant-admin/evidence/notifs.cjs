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

  // unread count from the API
  const unread = await page.evaluate(async () => {
    const r = await fetch("/api/v2/notifications/unread-count", { credentials: "include" });
    return r.json();
  }).catch((e) => ({ err: String(e) }));
  log(`UNREAD COUNT: ${JSON.stringify(unread)}`);

  // Open the bell drawer
  const bell = page.getByRole("button", { name: /Notifications/ }).first();
  if (await bell.isVisible().catch(() => false)) {
    await bell.click();
    await sleep(2500);
    const drawer = page.locator(".ant-drawer, .ant-popover");
    const text = await drawer.first().innerText().catch(() => "");
    log(`BELL CONTENT: ${text.slice(0, 500).replace(/\n+/g, " | ")}`);
    await page.screenshot({ path: path.join(SHOTS, "33-bell.png"), fullPage: true });
  } else {
    log("bell not visible");
  }
  await browser.close();
  log("notifs complete");
})().catch((e) => { console.error(e); process.exit(1); });
