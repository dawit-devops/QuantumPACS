const { chromium } = require("playwright");
const fs = require("fs");
const LOG = "docs/user-feature-review/super-admin/evidence/walkthrough.log";
const log = (s) => { console.log(s); fs.appendFileSync(LOG, s + "\n"); };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  await page.goto("http://localhost:5173/login", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(500);
  await page.getByPlaceholder("Username").fill("test.super_admin");
  await page.getByPlaceholder("Password").fill("Test@123456");
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.getByRole("menuitem", { name: /Account/ }).waitFor({ state: "visible", timeout: 15000 });

  const targets = ["/admin", "/dicomweb", "/metrics", "/files", "/hl7", "/fhir/monitoring", "/service-keys", "/users", "/roles", "/logs"];
  for (const path of targets) {
    const msgs = [];
    const handler = (m) => { if (m.text().includes("key") || m.text().includes("deprecated") || m.type() === "error") msgs.push(m.text().slice(0, 200)); };
    page.on("console", handler);
    await page.goto("http://localhost:5173" + path, { waitUntil: "domcontentloaded" });
    await sleep(2500);
    page.off("console", handler);
    if (msgs.length) log(`\n[${path}] ${msgs.join("\n")}`);
  }
  await browser.close();
  log("\nKEYWARNING PROBE DONE");
})();
