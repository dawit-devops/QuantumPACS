// Probe tenant_admin: sidebar inventory, tenants page content, dashboard content.
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

  // Sidebar inventory
  await page.goto(BASE + "/admin", { waitUntil: "domcontentloaded" });
  await sleep(3000);
  const items = await page.locator(".ant-menu-item, .ant-menu-submenu-title").allInnerTexts().catch(() => []);
  log(`SIDEBAR ITEMS: ${JSON.stringify(items)}`);

  // Dashboard body
  const dash = await page.locator("body").innerText().catch(() => "");
  log(`DASHBOARD BODY: ${dash.slice(0, 800).replace(/\n+/g, " | ")}`);
  await page.screenshot({ path: path.join(SHOTS, "11-dashboard.png"), fullPage: true });

  // Tenants page
  await page.goto(BASE + "/tenants", { waitUntil: "domcontentloaded" });
  await sleep(3000);
  const ten = await page.locator("body").innerText().catch(() => "");
  log(`TENANTS BODY: ${ten.slice(0, 700).replace(/\n+/g, " | ")}`);
  await page.screenshot({ path: path.join(SHOTS, "12-tenants.png"), fullPage: true });

  // Users page
  await page.goto(BASE + "/users", { waitUntil: "domcontentloaded" });
  await sleep(3000);
  const usr = await page.locator("body").innerText().catch(() => "");
  log(`USERS BODY: ${usr.slice(0, 500).replace(/\n+/g, " | ")}`);

  // Service keys
  await page.goto(BASE + "/service-keys", { waitUntil: "domcontentloaded" });
  await sleep(3000);
  const sk = await page.locator("body").innerText().catch(() => "");
  log(`SERVICE KEYS BODY: ${sk.slice(0, 500).replace(/\n+/g, " | ")}`);

  // Replicas
  await page.goto(BASE + "/replicas", { waitUntil: "domcontentloaded" });
  await sleep(3000);
  const rep = await page.locator("body").innerText().catch(() => "");
  log(`REPLICAS BODY: ${rep.slice(0, 500).replace(/\n+/g, " | ")}`);

  // Files
  await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
  await sleep(3000);
  const files = await page.locator("body").innerText().catch(() => "");
  log(`FILES BODY: ${files.slice(0, 500).replace(/\n+/g, " | ")}`);

  // Metrics
  await page.goto(BASE + "/metrics", { waitUntil: "domcontentloaded" });
  await sleep(3000);
  const met = await page.locator("body").innerText().catch(() => "");
  log(`METRICS BODY: ${met.slice(0, 500).replace(/\n+/g, " | ")}`);

  // Account
  await page.goto(BASE + "/account", { waitUntil: "domcontentloaded" });
  await sleep(3000);
  const acc = await page.locator("body").innerText().catch(() => "");
  log(`ACCOUNT BODY: ${acc.slice(0, 500).replace(/\n+/g, " | ")}`);

  // Logs
  await page.goto(BASE + "/logs", { waitUntil: "domcontentloaded" });
  await sleep(3000);
  const logs = await page.locator("body").innerText().catch(() => "");
  log(`LOGS BODY: ${logs.slice(0, 500).replace(/\n+/g, " | ")}`);

  await browser.close();
  log("probe complete");
})().catch((e) => { console.error(e); process.exit(1); });
