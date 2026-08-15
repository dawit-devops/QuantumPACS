const { chromium } = require("playwright");
const fs = require("fs");
const BASE = "http://localhost:5173";
const LOG = "docs/user-feature-review/super-admin/evidence/walkthrough.log";
const log = (s) => { console.log(s); fs.appendFileSync(LOG, s + "\n"); };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  await page.goto(BASE + "/login", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(600);
  await page.getByPlaceholder("Username").fill("test.super_admin");
  await page.getByPlaceholder("Password").fill("Test@123456");
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.getByRole("menuitem", { name: /Account/ }).waitFor({ state: "visible", timeout: 15000 });
  await sleep(1500);

  // Notification bell: button with aria-label "Notifications"
  await page.getByRole("button", { name: "Notifications" }).click();
  await sleep(2000);
  const drawerText = await page.locator(".ant-drawer").last().innerText().catch(() => "");
  log("NOTIFICATIONS DRAWER:\n" + drawerText.replace(/\s+/g, " ").slice(0, 1200));
  await page.screenshot({ path: "docs/user-feature-review/super-admin/evidence/21-notifications.png" }).catch(() => {});
  await browser.close();
})();
