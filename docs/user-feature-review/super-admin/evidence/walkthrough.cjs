// Live walkthrough for user-feature-review super_admin (Phase 1) — v2.
// Defensive: per-page hard timeouts, try/catch everywhere, progress flushed
// to a log file so a hang never loses prior evidence.
const { chromium } = require("playwright");
const fs = require("fs");

const BASE = "http://localhost:5173";
const EVIDENCE = "docs/user-feature-review/super-admin/evidence";
const LOG = `${EVIDENCE}/walkthrough.log`;
const USER = "test.super_admin";
const PASS = "Test@123456";

fs.mkdirSync(EVIDENCE, { recursive: true });
const log = (s) => {
  console.log(s);
  fs.appendFileSync(LOG, s + "\n");
};

const SURFACES = [
  ["02-admin-dashboard", "/admin", "Admin Dashboard"],
  ["03-users", "/users", "Users"],
  ["04-roles", "/roles", "Roles"],
  ["05-tenants", "/tenants", "Tenants"],
  ["06-replicas", "/replicas", "Replicas"],
  ["07-logs", "/logs", "Logs"],
  ["08-service-keys", "/service-keys", "Service Keys"],
  ["09-routing", "/routing", "Routing"],
  ["10-fhir-config", "/fhir/config", "FHIR Config"],
  ["11-fhir-monitoring", "/fhir/monitoring", "FHIR Monitoring"],
  ["12-fhir-docs", "/fhir/docs", "FHIR Docs"],
  ["13-integrations", "/integrations", "Integrations"],
  ["14-hl7", "/hl7", "HL7"],
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
];

const withTimeout = (p, ms, label) =>
  Promise.race([
    p,
    new Promise((_, rej) => setTimeout(() => rej(new Error(`timeout ${label}`)), ms)),
  ]);

async function snapshot(page, label, path) {
  const url = page.url();
  const title = await page.title().catch(() => "");
  const heading = await page
    .locator("h1, h2")
    .first()
    .textContent()
    .catch(() => "");
  const alerts = await page
    .locator(".ant-alert, .ant-message, .ant-notification-notice")
    .allTextContents()
    .catch(() => []);
  const main = await page
    .locator("main, .ant-layout-content, body")
    .first()
    .textContent()
    .catch(() => "");
  const bodyText = (main || "").replace(/\s+/g, " ").trim().slice(0, 1100);
  const hasSpinner = await page.locator(".ant-spin-spinning").count().catch(() => 0);
  log(`\n=== ${label} (${path}) ===`);
  log("URL: " + url);
  log("Title: " + title);
  log("Heading: " + (heading || "").trim());
  log("Alerts: " + JSON.stringify(alerts.map((a) => a.trim())));
  log("Spinner visible: " + (hasSpinner > 0));
  log("Body: " + bodyText.slice(0, 500));
  await page.screenshot({ path: `${EVIDENCE}/${label}.png`, fullPage: false }).catch(() => {});
}

(async () => {
  fs.writeFileSync(LOG, "=== super_admin walkthrough v2 ===\n" + new Date().toISOString() + "\n");
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
    if (r.status() >= 400 && !r.url().includes("/api/login")) badResponses.push(`${r.status()} ${r.url()}`);
  });
  page.on("requestfailed", (r) =>
    badResponses.push("FAILED " + r.url() + (r.failure() ? " :: " + r.failure().errorText : "")),
  );

  // ---- Login ----
  try {
    await withTimeout(page.goto(BASE + "/login", { waitUntil: "domcontentloaded" }), 20000, "goto login");
    await page.waitForTimeout(800);
    await page.getByPlaceholder("Username").fill(USER);
    await page.getByPlaceholder("Password").fill(PASS);
    await page.getByRole("button", { name: /sign in/i }).click();
    await withTimeout(
      page.getByRole("menuitem", { name: /Account/ }).waitFor({ state: "visible", timeout: 20000 }),
      25000,
      "shell wait",
    );
    await page.waitForTimeout(1500);
    log("LOGIN OK, landed at: " + page.url());
    await snapshot(page, "01-landing", page.url());
    const menuItems = await page
      .locator(".ant-menu-item, .ant-menu-submenu-title")
      .allTextContents()
      .catch(() => []);
    log("SIDEBAR ITEMS: " + JSON.stringify(menuItems.map((t) => t.trim()).filter(Boolean)));
    await page.screenshot({ path: `${EVIDENCE}/01-sidebar.png`, fullPage: false }).catch(() => {});
  } catch (e) {
    log("LOGIN FAILED: " + e.message.slice(0, 300));
    await page.screenshot({ path: `${EVIDENCE}/00-login-failed.png` }).catch(() => {});
    await browser.close();
    process.exit(1);
  }

  // ---- Walk surfaces ----
  for (const [label, path, name] of SURFACES) {
    try {
      await withTimeout(page.goto(BASE + path, { waitUntil: "domcontentloaded" }), 20000, `goto ${path}`);
      await page.waitForTimeout(2500);
      await snapshot(page, label, path);
    } catch (e) {
      log(`\n=== ${label} (${name}) === FAILED: ${e.message.slice(0, 200)}`);
      await page.screenshot({ path: `${EVIDENCE}/${label}.png` }).catch(() => {});
    }
  }

  // ---- Denied surfaces ----
  log("\n---- ADMIN-SCOPE DENIAL PROBES ----");
  for (const [label, path] of DENIED) {
    try {
      await withTimeout(page.goto(BASE + path, { waitUntil: "domcontentloaded" }), 15000, `goto ${path}`);
      await page.waitForTimeout(1800);
      log(`${label}: ${path} -> ${page.url()}`);
    } catch (e) {
      log(`${label}: ${path} -> ERR ${e.message.slice(0, 150)}`);
    }
  }

  log("\n---- CONSOLE ERRORS ----");
  log(consoleErrors.length ? consoleErrors.join("\n") : "(none)");
  log("\n---- 4xx/5xx + FAILED REQUESTS ----");
  log(badResponses.length ? badResponses.join("\n") : "(none)");

  await browser.close();
  log("\nDONE");
})();
