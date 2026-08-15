// Continuation walkthrough — remaining surfaces + denial probes + action
// inventory (buttons/inputs per page). Evidence appends to walkthrough.log.
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

const SURFACES = [
  ["15-dicomweb", "/dicomweb", "DICOMweb Server"],
  ["16-dicomweb-store", "/dicomweb/store", "DICOMweb Store"],
  ["17-dicomweb-browser", "/dicomweb/browser", "DICOMweb Browser"],
  ["18-metrics", "/metrics", "Metrics"],
  ["19-files", "/", "Files"],
  ["20-account", "/account", "Account"],
];

const DENIED = [
  ["x-reading", "/reading"],
  ["x-exams", "/exams"],
  ["x-qa", "/qa/queue"],
  ["x-frontdesk", "/frontdesk/registration"],
  ["x-portal", "/portal"],
  ["x-worklist", "/worklist"],
  ["x-schedule", "/schedule-board"],
  ["x-peerreview", "/peer-review"],
];

const withTimeout = (p, ms, label) =>
  Promise.race([
    p,
    new Promise((_, rej) => setTimeout(() => rej(new Error(`timeout ${label}`)), ms)),
  ]);

async function inventory(page, label, path) {
  const url = page.url();
  const heading = await page
    .locator("h1, h2")
    .first()
    .textContent()
    .catch(() => "");
  const alerts = await page
    .locator(".ant-alert, .ant-message, .ant-notification-notice")
    .allTextContents()
    .catch(() => []);
  const buttons = await page
    .locator("button")
    .evaluateAll((els) =>
      els
        .map((b) => (b.textContent || "").trim() || b.getAttribute("aria-label") || b.getAttribute("title") || "")
        .filter(Boolean)
        .slice(0, 40),
    )
    .catch(() => []);
  const inputs = await page
    .locator("input, .ant-select-selection-item, textarea")
    .evaluateAll((els) =>
      els
        .map((e) => e.getAttribute("placeholder") || e.getAttribute("aria-label") || (e.textContent || "").trim())
        .filter(Boolean)
        .slice(0, 30),
    )
    .catch(() => []);
  const tables = await page.locator(".ant-table").count().catch(() => 0);
  const rows = await page.locator(".ant-table-tbody > tr").count().catch(() => 0);
  const spinners = await page.locator(".ant-spin-spinning").count().catch(() => 0);
  log(`\n=== ${label} (${path}) ===`);
  log("URL: " + url);
  log("Heading: " + (heading || "").trim());
  log("Alerts: " + JSON.stringify(alerts.map((a) => a.trim())));
  log("Tables: " + tables + " (" + rows + " data rows), spinners: " + spinners);
  log("Buttons: " + JSON.stringify([...new Set(buttons)]));
  log("Inputs/Selects: " + JSON.stringify([...new Set(inputs)]));
  await page.screenshot({ path: `${EVIDENCE}/${label}.png`, fullPage: false }).catch(() => {});
}

(async () => {
  log("\n=== walkthrough2 continuation === " + new Date().toISOString());
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const consoleErrors = [];
  const badResponses = [];
  page.on("console", (m) => {
    if (m.type() === "error") consoleErrors.push(m.text().slice(0, 250));
  });
  page.on("pageerror", (e) => consoleErrors.push("PAGEERROR: " + e.message.slice(0, 250)));
  page.on("response", (r) => {
    if (r.status() >= 400) badResponses.push(`${r.status()} ${r.url()}`);
  });
  page.on("requestfailed", (r) =>
    badResponses.push("FAILED " + r.url() + (r.failure() ? " :: " + r.failure().errorText : "")),
  );

  try {
    await withTimeout(page.goto(BASE + "/login", { waitUntil: "domcontentloaded" }), 15000, "goto login");
    await page.waitForTimeout(600);
    await page.getByPlaceholder("Username").fill(USER);
    await page.getByPlaceholder("Password").fill(PASS);
    await page.getByRole("button", { name: /sign in/i }).click();
    await withTimeout(
      page.getByRole("menuitem", { name: /Account/ }).waitFor({ state: "visible", timeout: 15000 }),
      20000,
      "shell wait",
    );
    log("LOGIN OK -> " + page.url());
  } catch (e) {
    log("LOGIN FAILED: " + e.message.slice(0, 200));
    await browser.close();
    process.exit(1);
  }

  for (const [label, path, name] of SURFACES) {
    try {
      await withTimeout(page.goto(BASE + path, { waitUntil: "domcontentloaded" }), 15000, `goto ${path}`);
      await page.waitForTimeout(2000);
      await inventory(page, label, path);
    } catch (e) {
      log(`\n=== ${label} (${name}) === FAILED: ${e.message.slice(0, 200)}`);
      await page.screenshot({ path: `${EVIDENCE}/${label}.png` }).catch(() => {});
    }
  }

  log("\n---- ADMIN-SCOPE DENIAL PROBES (cont) ----");
  for (const [label, path] of DENIED) {
    try {
      await withTimeout(page.goto(BASE + path, { waitUntil: "domcontentloaded" }), 12000, `goto ${path}`);
      await page.waitForTimeout(1500);
      log(`${label}: ${path} -> ${page.url()}`);
    } catch (e) {
      log(`${label}: ${path} -> ERR ${e.message.slice(0, 120)}`);
    }
  }

  log("\n---- CONSOLE ERRORS (cont) ----");
  log(consoleErrors.length ? consoleErrors.join("\n") : "(none)");
  log("\n---- 4xx/5xx + FAILED REQUESTS (cont) ----");
  log(badResponses.length ? badResponses.join("\n") : "(none)");

  await browser.close();
  log("DONE-2");
})();
