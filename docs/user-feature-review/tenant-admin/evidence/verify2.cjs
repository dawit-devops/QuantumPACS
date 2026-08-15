const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");
const BASE = "http://localhost:5173";
const LOG = path.join(__dirname, "walkthrough.log");
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

  // FHIR row in Interfaces panel should have NO Open button (SYSTEM_ADMIN)
  await page.goto(BASE + "/admin", { waitUntil: "domcontentloaded" });
  await sleep(3000);
  const panel = page.locator(".dashboard-panel").filter({ hasText: "Interfaces" });
  const fhirRow = panel.locator(".ant-space").filter({ hasText: /FHIR/ }).first();
  const fhirOpen = await fhirRow.locator("button", { hasText: "Open" }).count().catch(() => 0);
  const hl7Row = panel.locator(".ant-space").filter({ hasText: /HL7/ }).first();
  const hl7Open = await hl7Row.locator("button", { hasText: "Open" }).count().catch(() => 0);
  log(`P1-1 FHIR row Open buttons: ${fhirOpen} (expect 0 — SYSTEM_ADMIN gated)`);
  log(`P1-1 HL7 row Open buttons: ${hl7Open} (expect 1 — HL7_READ now held)`);

  // Click HL7 Open -> should land on /hl7 (real, not dead-end)
  await hl7Row.locator("button", { hasText: "Open" }).click();
  await sleep(2500);
  log(`P1-1 click HL7 Open -> landed ${page.url()} (expect /hl7)`);
  await page.goto(BASE + "/admin", { waitUntil: "domcontentloaded" });
  await sleep(2500);

  // Roles: the tenant_admin row Edit button should be disabled (immutable)
  await page.goto(BASE + "/roles", { waitUntil: "domcontentloaded" });
  await sleep(3000);
  const rows = page.locator(".ant-table-tbody tr");
  const rc = await rows.count().catch(() => 0);
  for (let i = 0; i < rc; i++) {
    const row = rows.nth(i);
    const text = await row.innerText().catch(() => "");
    if (text.includes("Tenant Admin") || text.includes("tenant_admin")) {
      const editBtn = row.locator("button", { hasText: "Edit" });
      const disabled = await editBtn.isDisabled().catch(() => false);
      log(`P2-3 tenant_admin row Edit disabled: ${disabled} (expect true)`);
      await editBtn.hover().catch(() => {});
      await sleep(800);
      const tip = await page.locator(".ant-tooltip").innerText().catch(() => "");
      log(`P2-3 tooltip: "${tip.slice(0, 60)}"`);
      break;
    }
  }
  await browser.close();
  log("verify2 complete");
})().catch((e) => { console.error(e); process.exit(1); });
