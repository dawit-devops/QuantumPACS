// Investigate: why do some denied deep-links land on /login for tenant_admin?
// Watch console + network to see if a 401/403 force-logs-out.
const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");
const BASE = "http://localhost:5173";
const LOG = path.join(__dirname, "walkthrough.log");
const log = (m) => { const l = `[${new Date().toISOString()}] ${m}`; console.log(l); fs.appendFileSync(LOG, l + "\n"); };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const probes = ["/dicomweb", "/reading", "/fhir/config", "/exams"];

(async () => {
  const browser = await chromium.launch({ headless: true });
  for (const route of probes) {
    const ctx = await browser.newContext({ viewport: { width: 1366, height: 850 } });
    const page = await ctx.newPage();
    const net = [];
    const consoleMsgs = [];
    page.on("response", (r) => {
      if (r.status() >= 400 && r.url().includes("/api/")) net.push(`${r.status()} ${r.request().method()} ${r.url().replace("http://localhost:8080", "")}`);
    });
    page.on("console", (m) => { if (m.type() === "error") consoleMsgs.push(m.text()); });
    try {
      await page.goto(BASE + "/login", { waitUntil: "domcontentloaded" });
      await page.getByPlaceholder("Username").fill("test.tenant_admin");
      await page.getByPlaceholder("Password").fill("Test@123456");
      await page.getByRole("button", { name: /sign in/i }).click();
      await sleep(3500);
      await page.goto(BASE + route, { waitUntil: "domcontentloaded", timeout: 15000 }).catch(() => {});
      await sleep(3000);
      log(`DEEPLINK ${route} -> landed ${page.url()} | net4xx: ${JSON.stringify(net)} | consoleErr: ${consoleMsgs.length ? JSON.stringify(consoleMsgs.slice(0,3)) : "none"}`);
    } catch (e) {
      log(`DEEPLINK ${route} ERROR ${e.message.split("\n")[0]}`);
    }
    await ctx.close().catch(() => {});
  }
  await browser.close();
  log("deeplink probes complete");
})().catch((e) => { console.error(e); process.exit(1); });
