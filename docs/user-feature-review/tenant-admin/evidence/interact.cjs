// Interact: click dashboard Interface "Open" buttons as tenant_admin; probe
// tenant Usage and Tenants actions; check console errors.
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
  page.on("console", (m) => { if (m.type() === "error") errs.push(m.text()); });

  await page.goto(BASE + "/login", { waitUntil: "domcontentloaded" });
  await page.getByPlaceholder("Username").fill("test.tenant_admin");
  await page.getByPlaceholder("Password").fill("Test@123456");
  await page.getByRole("button", { name: /sign in/i }).click();
  await sleep(4000);

  // Dashboard: click each Interface "Open" button, record where it lands.
  const openBtns = page.locator(".dashboard-panel button", { hasText: "Open" });
  const n = await openBtns.count().catch(() => 0);
  log(`INTERFACE OPEN BUTTONS on dashboard: ${n}`);
  for (let i = 0; i < n; i++) {
    const btn = openBtns.nth(i);
    const rowText = await btn.locator("..").innerText().catch(() => "");
    await btn.click();
    await sleep(2000);
    log(`  click "${rowText.trim().slice(0, 40)}" -> landed ${page.url()}`);
    await page.screenshot({ path: path.join(SHOTS, `30-interface-${i}.png`), fullPage: true });
    // back to dashboard
    await page.goto(BASE + "/admin", { waitUntil: "domcontentloaded" });
    await sleep(2000);
  }

  // Health strip pills (Open dashboard aria-labels)
  const pills = page.locator("button[aria-label^='Open ']");
  const pn = await pills.count().catch(() => 0);
  log(`HEALTH PILLS with Open label: ${pn}`);
  for (let i = 0; i < pn; i++) {
    const label = await pills.nth(i).getAttribute("aria-label").catch(() => "");
    await pills.nth(i).click();
    await sleep(2000);
    log(`  click "${label}" -> landed ${page.url()}`);
    await page.goto(BASE + "/admin", { waitUntil: "domcontentloaded" });
    await sleep(2000);
  }

  // Tenants page: Usage action + any enabled danger actions
  await page.goto(BASE + "/tenants", { waitUntil: "domcontentloaded" });
  await sleep(3000);
  const usageBtn = page.getByRole("button", { name: /Usage/i }).first();
  if (await usageBtn.isVisible().catch(() => false)) {
    await usageBtn.click();
    await sleep(2500);
    log(`TENANT Usage click -> landed ${page.url()}, url contains usage: ${page.url().includes("usage")}`);
    await page.screenshot({ path: path.join(SHOTS, "31-tenant-usage.png"), fullPage: true });
  } else {
    log("TENANT Usage button not visible");
  }

  // Tenant stats via API (METERING_READ held?)
  await page.goto(BASE + "/admin", { waitUntil: "domcontentloaded" });
  await sleep(2000);
  log(`CONSOLE ERRORS: ${errs.length}`);
  errs.slice(0, 5).forEach((e) => log(`  ${e.slice(0, 120)}`));
  await browser.close();
  log("interact complete");
})().catch((e) => { console.error(e); process.exit(1); });
