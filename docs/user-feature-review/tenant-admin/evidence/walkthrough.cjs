// tenant_admin live walkthrough — Phase 1 evidence.
// Logs in as test.tenant_admin / Test@123456, walks every reachable surface,
// probes denied surfaces, screenshots each, and writes walkthrough.log.
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const BASE = "http://localhost:5173";
const OUT = path.join(__dirname, "..");
const LOG = path.join(__dirname, "walkthrough.log");
const SHOTS = path.join(__dirname);

const log = (m) => {
  const line = `[${new Date().toISOString()}] ${m}`;
  console.log(line);
  fs.appendFileSync(LOG, line + "\n");
};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1366, height: 850 } });
  const errors = [];
  const failedReqs = [];
  page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(`console: ${m.text()}`);
  });
  page.on("requestfailed", (r) => failedReqs.push(`${r.method()} ${r.url()}`));

  log("=== tenant_admin walkthrough start ===");

  // Login
  await page.goto(BASE + "/login", { waitUntil: "domcontentloaded" });
  await page.getByPlaceholder("Username").fill("test.tenant_admin");
  await page.getByPlaceholder("Password").fill("Test@123456");
  await page.getByRole("button", { name: /sign in/i }).click();
  await sleep(4000);
  log(`after login url: ${page.url()}`);
  await page.screenshot({ path: path.join(SHOTS, "00-landing.png"), fullPage: true });

  // Reachable surfaces
  const surfaces = [
    ["admin", "/admin"],
    ["users", "/users"],
    ["tenants", "/tenants"],
    ["roles", "/roles"],
    ["logs", "/logs"],
    ["service-keys", "/service-keys"],
    ["replicas", "/replicas"],
    ["files", "/"],
    ["metrics", "/metrics"],
    ["account", "/account"],
  ];
  for (const [name, route] of surfaces) {
    try {
      await page.goto(BASE + route, { waitUntil: "domcontentloaded" });
      await sleep(2500);
      const body = await page.locator("body").innerText().catch(() => "");
      const h1 = await page.locator("h1,h2").first().innerText().catch(() => "(none)");
      log(`SURFACE ${name} ${route} -> url=${page.url()} h1="${h1}" bodyChars=${body.length}`);
      await page.screenshot({ path: path.join(SHOTS, `10-${name}.png`), fullPage: true });
    } catch (e) {
      log(`SURFACE ${name} ${route} -> ERROR ${e.message.split("\n")[0]}`);
    }
  }

  // Denial probes — routes tenant_admin should NOT reach
  const denied = [
    ["routing", "/routing", "INTERFACE_ADMIN held but gate is ROUTING_READ"],
    ["hl7", "/hl7", "INTERFACE_MONITOR/ADMIN held but gate is HL7_READ"],
    ["dicomweb", "/dicomweb", "STORAGE_ADMIN held but gate is DICOMWEB_READ"],
    ["maintenance", "/admin/maintenance", "SYSTEM_ADMIN only"],
    ["backups", "/admin/backups", "SYSTEM_ADMIN only"],
    ["settings", "/admin/settings", "SYSTEM_ADMIN only"],
    ["fhir", "/fhir/config", "SYSTEM_ADMIN only"],
    ["integrations", "/integrations", "SYSTEM_ADMIN only"],
    ["reading", "/reading", "clinical workspace hidden"],
    ["exams", "/exams", "clinical workspace hidden"],
    ["qa", "/qa/queue", "clinical workspace hidden"],
    ["frontdesk", "/frontdesk/registration", "non-admin workspace"],
    ["portal", "/portal", "non-admin workspace"],
  ];
  for (const [name, route, why] of denied) {
    try {
      await page.goto(BASE + route, { waitUntil: "domcontentloaded" });
      await sleep(2000);
      log(`DENIED ${name} ${route} (${why}) -> landed: ${page.url()}`);
      await page.screenshot({ path: path.join(SHOTS, `20-denied-${name}.png`), fullPage: true });
    } catch (e) {
      log(`DENIED ${name} ${route} -> ERROR ${e.message.split("\n")[0]}`);
    }
  }

  // Sidebar inventory — what menu items are visible
  await page.goto(BASE + "/admin", { waitUntil: "domcontentloaded" });
  await sleep(2500);
  const items = await page
    .locator(".ant-menu-item, .ant-menu-submenu-title")
    .allInnerTexts()
    .catch(() => []);
  log(`SIDEBAR ITEMS: ${JSON.stringify(items)}`);

  log(`PAGE ERRORS: ${errors.length}`);
  errors.forEach((e) => log(`  ${e}`));
  log(`FAILED REQUESTS: ${failedReqs.length}`);
  failedReqs.forEach((r) => log(`  ${r}`));
  log("=== walkthrough complete ===");

  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
