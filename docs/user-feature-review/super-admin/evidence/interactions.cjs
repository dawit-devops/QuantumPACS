// Phase 1 interaction probe: exercise primary actions on admin surfaces and
// record feedback (success/error messages, validation, confirmations).
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

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  log("\n=== interactions === " + new Date().toISOString());
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const feedback = [];
  page.on("response", (r) => { if (r.status() >= 400) feedback.push(`${r.status()} ${r.url()}`); });
  page.on("pageerror", (e) => feedback.push("PAGEERROR: " + e.message.slice(0, 200)));
  const msg = async (label) => {
    await sleep(700);
    const m = await page.locator(".ant-message-notice, .ant-message").allTextContents().catch(() => []);
    const alerts = await page.locator(".ant-alert").allTextContents().catch(() => []);
    log(`${label} -> message: ${JSON.stringify(m.map((t) => t.trim()))} alert: ${JSON.stringify(alerts.map((t) => t.trim()))}`);
    return m.concat(alerts).join(" | ");
  };

  // Login
  await page.goto(BASE + "/login", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(600);
  await page.getByPlaceholder("Username").fill(USER);
  await page.getByPlaceholder("Password").fill(PASS);
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.getByRole("menuitem", { name: /Account/ }).waitFor({ state: "visible", timeout: 15000 });

  // 1. Notifications — what does a platform admin get?
  await page.goto(BASE + "/admin", { waitUntil: "domcontentloaded" });
  await sleep(1200);
  await page.locator(".ant-badge, [aria-label*='notification' i], [class*='bell' i]").first().click().catch(async () => {
    // fallback: click the notifications menuitem
    await page.getByRole("menuitem", { name: /Notifications/ }).click().catch(() => {});
  });
  await sleep(1500);
  const notifItems = await page.locator("[class*='notification'] li, .ant-list-item").allTextContents().catch(() => []);
  const notifPanel = await page.evaluate(() => document.querySelector("[class*='notification'], .ant-popover")?.innerText || "").catch(() => "");
  log(`NOTIFICATIONS: ${notifPanel.replace(/\s+/g, " ").slice(0, 500)}`);
  await page.screenshot({ path: `${EVIDENCE}/21-notifications.png` }).catch(() => {});
  await page.keyboard.press("Escape").catch(() => {});

  // 2. Users -> Create user: invalid then valid
  await page.goto(BASE + "/users", { waitUntil: "domcontentloaded" });
  await sleep(1500);
  await page.getByRole("button", { name: /Create User|Add User/i }).first().click().catch(() => log("USERS: no create button found"));
  await sleep(800);
  const createModal = await page.locator(".ant-modal").last().isVisible().catch(() => false);
  log("USERS create modal visible: " + createModal);
  if (createModal) {
    await page.locator(".ant-modal").last().getByRole("button", { name: /Create|OK|Submit/i }).first().click().catch(() => {});
    await msg("USERS create with empty fields");
    // fill a valid username
    const usernameInput = page.locator(".ant-modal").last().locator("input").first();
    await usernameInput.fill("probe.user." + Date.now().toString().slice(-6));
    await page.locator(".ant-modal").last().getByRole("button", { name: /Create|OK|Submit/i }).first().click().catch(() => {});
    await sleep(1200);
    await msg("USERS create valid");
    await page.screenshot({ path: `${EVIDENCE}/22-users-create.png` }).catch(() => {});
    // close modal
    await page.keyboard.press("Escape").catch(() => {});
  }

  // 3. Service Keys -> create
  await page.goto(BASE + "/service-keys", { waitUntil: "domcontentloaded" });
  await sleep(1500);
  await page.getByRole("button", { name: /Create|New Key|Add/i }).first().click().catch(() => log("SERVICEKEYS: no create button"));
  await sleep(900);
  const skModal = await page.locator(".ant-modal").last().isVisible().catch(() => false);
  log("SERVICEKEYS modal visible: " + skModal);
  if (skModal) {
    const inputs = await page.locator(".ant-modal").last().locator("input").all();
    if (inputs.length) await inputs[0].fill("probe-key-" + Date.now().toString().slice(-6));
    await page.locator(".ant-modal").last().getByRole("button", { name: /Create|Save|OK/i }).first().click().catch(() => {});
    await sleep(1200);
    await msg("SERVICEKEYS create");
    await page.screenshot({ path: `${EVIDENCE}/23-servicekeys-create.png` }).catch(() => {});
    await page.keyboard.press("Escape").catch(() => {});
  }

  // 4. Roles — built-in super_admin edit disabled?
  await page.goto(BASE + "/roles", { waitUntil: "domcontentloaded" });
  await sleep(1500);
  const superRow = page.locator(".ant-table-tbody > tr", { hasText: "Super Admin" }).first();
  const editBtns = await superRow.locator("button").allTextContents().catch(() => []);
  const editDisabled = await superRow.locator("button").nth(0).isDisabled().catch(() => false);
  log(`ROLES Super Admin row buttons: ${JSON.stringify(editBtns)} disabled: ${editDisabled}`);
  const editBtn = superRow.locator("button", { hasText: /Edit/i }).first();
  await editBtn.click().catch(() => log("ROLES: super admin edit not clickable"));
  await sleep(900);
  const roleModal = await page.locator(".ant-modal").last().isVisible().catch(() => false);
  log("ROLES edit modal visible: " + roleModal);
  if (roleModal) {
    const modalText = await page.locator(".ant-modal").last().innerText().catch(() => "");
    log("ROLES modal text: " + modalText.replace(/\s+/g, " ").slice(0, 300));
    await page.screenshot({ path: `${EVIDENCE}/24-roles-edit-superadmin.png` }).catch(() => {});
    await page.keyboard.press("Escape").catch(() => {});
  }

  // 5. DICOMweb STOW invalid upload
  await page.goto(BASE + "/dicomweb/store", { waitUntil: "domcontentloaded" });
  await sleep(1500);
  const fileInput = page.locator('input[type="file"]').first();
  if (await fileInput.count()) {
    // upload a non-DICOM file
    fs.writeFileSync("/tmp/notdicom.txt", "this is not a dicom file");
    await fileInput.setInputFiles("/tmp/notdicom.txt").catch((e) => log("STOW setInputFiles: " + e.message.slice(0, 120)));
    await sleep(800);
    await page.getByRole("button", { name: /Store to PACS/i }).click().catch(() => {});
    await sleep(2000);
    await msg("STOW invalid file upload");
    await page.screenshot({ path: `${EVIDENCE}/25-stow-invalid.png` }).catch(() => {});
  } else {
    log("STOW: no file input found");
  }

  // 6. Account -> change password: wrong current password
  await page.goto(BASE + "/account", { waitUntil: "domcontentloaded" });
  await sleep(1500);
  await page.getByRole("button", { name: /Change Password/i }).first().click().catch(() => log("ACCOUNT: no change-password button"));
  await sleep(800);
  const pwModal = await page.locator(".ant-modal").last().isVisible().catch(() => false);
  log("ACCOUNT pw modal visible: " + pwModal);
  if (pwModal) {
    const fields = await page.locator(".ant-modal").last().locator('input[type="password"]').all();
    if (fields.length >= 3) {
      await fields[0].fill("WrongPass123!");
      await fields[1].fill("NewPass123!");
      await fields[2].fill("NewPass123!");
      await page.locator(".ant-modal").last().getByRole("button", { name: /Change|Submit|OK/i }).first().click().catch(() => {});
      await msg("ACCOUNT wrong current password");
      await page.screenshot({ path: `${EVIDENCE}/26-account-pw-error.png` }).catch(() => {});
    }
    await page.keyboard.press("Escape").catch(() => {});
  }

  // 7. FHIR config -> Test Connection
  await page.goto(BASE + "/fhir/config", { waitUntil: "domcontentloaded" });
  await sleep(1500);
  await page.getByRole("button", { name: /Test Connection/i }).click().catch(() => log("FHIR: no test button"));
  await sleep(2000);
  await msg("FHIR test connection");
  await page.screenshot({ path: `${EVIDENCE}/27-fhir-test.png` }).catch(() => {});

  log("\nHTTP 4xx/5xx + pageerrors during interactions: " + (feedback.length ? feedback.join("\n") : "(none)"));
  await browser.close();
  log("INTERACTIONS DONE");
})();
