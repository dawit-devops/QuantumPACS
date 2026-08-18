// Phase 3 verification: dashboard dead-ends gone, tenant card counts, users
// tenant column, roles lock hint, permissions grouping on Account.
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

  // 1. Dashboard: Interfaces "Open" buttons should now be gone (dead-end fix)
  await page.goto(BASE + "/admin", { waitUntil: "domcontentloaded" });
  await sleep(3000);
  const openBtns = page.locator(".dashboard-panel button", { hasText: "Open" });
  const n = await openBtns.count().catch(() => 0);
  log(`P1-1 DASHBOARD Interface Open buttons: ${n} (expect 0 for tenant_admin)`);
  // Health pills: only Storage should still be an Open button
  const pills = page.locator("button[aria-label^='Open ']");
  const pn = await pills.count().catch(() => 0);
  const pillLabels = [];
  for (let i = 0; i < pn; i++) {
    pillLabels.push(await pills.nth(i).getAttribute("aria-label").catch(() => "?"));
  }
  log(`P1-1 DASHBOARD Open pills: ${JSON.stringify(pillLabels)} (expect only Storage)`);
  await page.screenshot({ path: path.join(SHOTS, "40-dashboard-fixed.png"), fullPage: true });

  // 2. Tenants: real counts, no "?"
  await page.goto(BASE + "/tenants", { waitUntil: "domcontentloaded" });
  await sleep(3000);
  const ten = await page.locator("body").innerText().catch(() => "");
  log(`P2-1 TENANTS has "? users": ${ten.includes("? users")} | "23 users": ${ten.includes("23 users")} | "17 studies": ${ten.includes("17 studies")}`);
  await page.screenshot({ path: path.join(SHOTS, "41-tenants-counts.png"), fullPage: true });

  // 3. Users: tenant column present
  await page.goto(BASE + "/users", { waitUntil: "domcontentloaded" });
  await sleep(3000);
  const usr = await page.locator("body").innerText().catch(() => "");
  log(`P2-2 USERS has "Tenant" column header: ${usr.includes("Tenant")}`);
  await page.screenshot({ path: path.join(SHOTS, "42-users-tenant.png"), fullPage: true });

  // 4. Roles: lock hint visible for immutable anchor (tenant_admin row)
  await page.goto(BASE + "/roles", { waitUntil: "domcontentloaded" });
  await sleep(3000);
  const rolesBody = await page.locator("body").innerText().catch(() => "");
  log(`P2-3 ROLES shows lock tooltip text: ${rolesBody.includes("Cannot modify immutable built-in role") || rolesBody.includes("Only the platform admin")}`);
  await page.screenshot({ path: path.join(SHOTS, "43-roles-lock.png"), fullPage: true });

  // 5. Account: grouped permissions
  await page.goto(BASE + "/account", { waitUntil: "domcontentloaded" });
  await sleep(3000);
  const acc = await page.locator("body").innerText().catch(() => "");
  log(`P1-2 ACCOUNT grouped: "Tenant & platform ops": ${acc.includes("Tenant & platform ops")} | "roadmap": ${acc.includes("roadmap")}`);
  await page.screenshot({ path: path.join(SHOTS, "44-account-grouped.png"), fullPage: true });

  await browser.close();
  log("verify complete");
})().catch((e) => { console.error(e); process.exit(1); });
