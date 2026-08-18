// Probe specific pages that showed sparse/empty dumps; extract clean content
// text (content layout area or body minus style/script) + tabs + status tags.
const { chromium } = require("playwright");
const fs = require("fs");

const BASE = "http://localhost:5173";
const EVIDENCE = "docs/user-feature-review/super-admin/evidence";
const LOG = `${EVIDENCE}/walkthrough.log`;
const USER = "test.super_admin";
const PASS = "Test@123456";
const log = (s) => {
  console.log(s);
  fs.appendFileSync(LOG, s + "\n");
};

const TARGETS = ["/hl7", "/tenants", "/fhir/config", "/fhir/monitoring", "/fhir/docs", "/integrations", "/logs", "/dicomweb", "/metrics", "/replicas", "/roles"];

(async () => {
  log("\n=== probe === " + new Date().toISOString());
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const bad = [];
  page.on("response", (r) => { if (r.status() >= 400) bad.push(`${r.status()} ${r.url()}`); });
  page.on("pageerror", (e) => bad.push("PAGEERROR: " + e.message.slice(0, 200)));

  await page.goto(BASE + "/login", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(600);
  await page.getByPlaceholder("Username").fill(USER);
  await page.getByPlaceholder("Password").fill(PASS);
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.getByRole("menuitem", { name: /Account/ }).waitFor({ state: "visible", timeout: 15000 });

  for (const path of TARGETS) {
    try {
      await page.goto(BASE + path, { waitUntil: "domcontentloaded" });
      await page.waitForTimeout(2500);
      // Prefer the content layout; fall back to body minus style/script.
      const content = await page.evaluate(() => {
        const sel = document.querySelector("main, .ant-layout-content");
        if (sel) return (sel.innerText || "").trim();
        const clone = document.body.cloneNode(true);
        clone.querySelectorAll("style, script, svg, [aria-hidden='true']").forEach((n) => n.remove());
        return (clone.innerText || "").trim();
      });
      const tabs = await page.locator(".ant-tabs-tab").allTextContents().catch(() => []);
      const tags = await page.locator(".ant-tag").allTextContents().catch(() => []);
      log(`\n--- ${path} ---`);
      log("Tabs: " + JSON.stringify(tabs.map((t) => t.trim())));
      log("Tags: " + JSON.stringify(tags.map((t) => t.trim()).slice(0, 20)));
      log("Content: " + content.replace(/\s+/g, " ").slice(0, 900));
    } catch (e) {
      log(`--- ${path} --- ERR ${e.message.slice(0, 120)}`);
    }
  }
  log("\nBad responses/pageerrors: " + (bad.length ? bad.join("\n") : "(none)"));
  await browser.close();
  log("PROBE DONE");
})();
