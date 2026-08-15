// Denial probes for tenant_admin — one fresh context per route so a redirect
// loop / ERR_ABORTED on one probe can't kill the rest.
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

(async () => {
  const browser = await chromium.launch({ headless: true });
  for (const [name, route, why] of denied) {
    const ctx = await browser.newContext({ viewport: { width: 1366, height: 850 } });
    const page = await ctx.newPage();
    try {
      // Login in this context
      await page.goto(BASE + "/login", { waitUntil: "domcontentloaded" });
      await page.getByPlaceholder("Username").fill("test.tenant_admin");
      await page.getByPlaceholder("Password").fill("Test@123456");
      await page.getByRole("button", { name: /sign in/i }).click();
      await sleep(3500);
      await page.goto(BASE + route, { waitUntil: "domcontentloaded", timeout: 15000 }).catch(() => {});
      await sleep(2500);
      const url = page.url();
      log(`DENIED ${name} ${route} (${why}) -> landed: ${url}`);
      await page.screenshot({ path: path.join(SHOTS, `20-denied-${name}.png`), fullPage: true }).catch(() => {});
    } catch (e) {
      log(`DENIED ${name} ${route} -> ERROR ${e.message.split("\n")[0]}`);
    } finally {
      await ctx.close().catch(() => {});
    }
  }
  await browser.close();
  log("denials complete");
})().catch((e) => { console.error(e); process.exit(1); });
