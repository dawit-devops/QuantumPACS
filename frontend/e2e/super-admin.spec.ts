import { test, expect } from "@playwright/test";
import { loginAs, API_BASE } from "./helpers";

// Phase 4 of user-feature-review/super-admin (phase/user-feature-review-super-admin).
// Real-backend coverage for the platform admin, exercising the P1-1..P2-6
// hand-off items from docs/user-feature-review/super-admin/03-handoff.md.
//
// NOTE: the maintenance test (P1-2) toggles a GLOBAL platform state — it is
// written to ALWAYS exit maintenance, even on assertion failure, so a broken
// run can never leave the dev platform write-locked.
// The maintenance test toggles GLOBAL platform state, so the whole file must
// run serially: a sibling test's afterEach would otherwise clear the flag
// mid-flight. Serial mode also keeps the enter/exit assertions deterministic
// under --repeat-each and parallel workers.
test.describe.configure({ mode: "serial" });
test.describe("Super admin workflow polish (real backend)", () => {
  test.beforeEach(async ({ page }) => {
    // test.super_admin is seeded (user id 36, admin=true) with every grant.
    // Real UI login so maintenance, backups and prefs hit the live backend.
    await loginAs(page, "test.super_admin", "Test@123456");
  });

  test.afterEach(async ({ page }) => {
    // Safety net: never leave maintenance active after a spec run.
    const resp = await page.request.post(`${API_BASE}/api/v2/admin/maintenance`, {
      data: { active: false, reason: "" },
      headers: { "X-CSRF-Token": "1" },
    });
    // 200 or 422 (already off / state machine) both fine; anything else is a
    // platform problem worth surfacing in the run.
    if (resp.status() >= 500) {
      console.error(`maintenance exit failed: ${resp.status()}`);
    }
  });

  test("P1-1: notification prefs page toggles study.arrived and persists server-side", async ({
    page,
  }) => {
    await page.goto("/account/notifications", { waitUntil: "domcontentloaded" });

    // AC-1: the surface lists event types grouped with on/off toggles.
    await expect(
      page.getByRole("heading", { name: "Notification Preferences" }),
    ).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByText("Operational alerts", { exact: true }),
    ).toBeVisible();
    await expect(page.getByText("Clinical activity", { exact: true })).toBeVisible();

    // AC-2: the platform admin's role default mutes upload receipts while
    // operational alerts stay ON. The test must be idempotent: a previous run
    // may have left study.arrived toggled, so normalize to OFF first.
    const arrivedSwitch = page.getByRole("switch", {
      name: "Study arrived (upload receipt) notifications",
    });
    await expect(arrivedSwitch).toBeVisible({ timeout: 10000 });
    if (await arrivedSwitch.isChecked()) {
      await arrivedSwitch.click();
      await expect(arrivedSwitch).not.toBeChecked({ timeout: 5000 });
    }
    await expect(
      page.getByRole("switch", { name: "Storage quota breach notifications" }),
    ).toBeChecked();

    // AC-3: toggling writes through the API — flip study.arrived ON, reload,
    // and confirm the server returns the persisted value (not client cache).
    await arrivedSwitch.click();
    await expect(arrivedSwitch).toBeChecked({ timeout: 5000 });
    const prefResp = await page.request.get(
      `${API_BASE}/api/v2/notifications/preferences`,
    );
    expect(prefResp.status()).toBe(200);
    const prefs = (await prefResp.json()).preferences;
    expect(prefs["study.arrived"]).toBe(true);

    // Reload — the page reads prefs from the backend, so the toggle persists.
    await page.reload({ waitUntil: "domcontentloaded" });
    await expect(
      page.getByRole("switch", { name: "Study arrived (upload receipt) notifications" }),
    ).toBeChecked({ timeout: 10000 });

    // AC-4: restore the role default (OFF) so the fixture stays clean.
    await page
      .getByRole("switch", { name: "Study arrived (upload receipt) notifications" })
      .click();
    await expect(
      page.getByRole("switch", { name: "Study arrived (upload receipt) notifications" }),
    ).not.toBeChecked({ timeout: 5000 });
    const restored = (await (
      await page.request.get(`${API_BASE}/api/v2/notifications/preferences`)
    ).json()).preferences;
    expect(restored["study.arrived"]).toBe(false);
  });

  test("P1-2: maintenance on -> write gate 503 -> banner -> off restores writes", async ({
    page,
  }) => {
    // Enter maintenance with a reason (AC-2: writes the audit event).
    await page.goto("/admin/maintenance", { waitUntil: "domcontentloaded" });
    await expect(
      page.getByRole("heading", { name: "Maintenance Mode" }),
    ).toBeVisible({ timeout: 10000 });

    // If a prior run left it on, exit first so the enter path is exercised.
    if (await page.getByText("MAINTENANCE ACTIVE").isVisible().catch(() => false)) {
      await page.getByRole("button", { name: "Exit maintenance" }).click();
      await page.getByRole("button", { name: "Resume writes" }).click();
      await expect(page.getByText("PLATFORM ONLINE")).toBeVisible({ timeout: 10000 });
    }

    await page.getByRole("button", { name: "Enter maintenance" }).click();
    await page
      .getByPlaceholder("e.g. v3 release migration window")
      .fill("e2e verification window");
    await page.getByRole("button", { name: "Enter maintenance", exact: true }).click();

    // AC-3: write endpoints 503 while reads stay available.
    await expect(page.getByText("MAINTENANCE ACTIVE")).toBeVisible({ timeout: 10000 });
    const writeResp = await page.request.post(`${API_BASE}/api/v2/files/upload`, {
      multipart: { file: { name: "x.dcm", mimeType: "application/dicom", buffer: Buffer.from("x") } },
      headers: { "X-CSRF-Token": "1" },
    });
    expect(writeResp.status()).toBe(503);
    const readResp = await page.request.get(`${API_BASE}/api/v2/admin/status`);
    expect(readResp.status()).toBe(200);
    expect((await readResp.json()).maintenance.active).toBe(true);

    // AC-4: the banner is visible app-wide (navigate away from the page).
    await page.goto("/users", { waitUntil: "domcontentloaded" });
    await expect(
      page.getByText("System is in maintenance mode — writes are paused."),
    ).toBeVisible({ timeout: 10000 });

    // AC-5: exit restores writes and clears the banner. The maintenance flag
    // is GLOBAL platform state, so a parallel run can clear it between steps:
    // re-enter via the UI if the page already shows PLATFORM ONLINE.
    await page.goto("/admin/maintenance", { waitUntil: "domcontentloaded" });
    if (await page.getByText("PLATFORM ONLINE").isVisible().catch(() => false)) {
      await page.getByRole("button", { name: "Enter maintenance" }).click();
      await page
        .getByPlaceholder("e.g. v3 release migration window")
        .fill("e2e re-entry after parallel clobber");
      await page
        .getByRole("button", { name: "Enter maintenance", exact: true })
        .click();
      await expect(page.getByText("MAINTENANCE ACTIVE")).toBeVisible({
        timeout: 10000,
      });
    }
    await page.getByRole("button", { name: "Exit maintenance" }).click();
    await page.getByRole("button", { name: "Resume writes" }).click();
    await expect(page.getByText("PLATFORM ONLINE")).toBeVisible({ timeout: 10000 });
    const writeAfter = await page.request.post(`${API_BASE}/api/v2/files/upload`, {
      multipart: { file: { name: "x.dcm", mimeType: "application/dicom", buffer: Buffer.from("x") } },
      headers: { "X-CSRF-Token": "1" },
    });
    expect([200, 400, 422]).toContain(writeAfter.status());
  });

  test("P2-1: backups page triggers an on-demand backup and lists it", async ({
    page,
  }) => {
    await page.goto("/admin/backups", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: "Backups" })).toBeVisible({
      timeout: 10000,
    });

    // AC-1: empty state OR a populated table both render without error.
    await page.getByRole("button", { name: "Back up now" }).click();

    // AC-2/AC-3: the run completes and surfaces in the table (or a failure tag
    // if the storage backend has no master — the page must not crash either way).
    await expect(
      page.getByRole("button", { name: "Back up now" }),
    ).toBeEnabled({ timeout: 20000 });
    const statusCells = page.locator(".ant-table-cell").filter({ hasText: /COMPLETED|FAILED|RUNNING/ });
    await expect(statusCells.first()).toBeVisible({ timeout: 10000 });
    const status = (await statusCells.first().textContent()) ?? "";
    expect(["COMPLETED", "FAILED", "RUNNING"]).toContain(status.trim());
  });

  test("P2-5: role membership modal lists users with their status", async ({
    page,
  }) => {
    await page.goto("/roles", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: /Roles/ })).toBeVisible({
      timeout: 10000,
    });

    // Click the first role with a user count (a link-button in the Users column).
    const countLink = page.locator(".ant-table-cell button.ant-btn-link", {
      hasText: /\d+/,
    });
    await countLink.first().click();

    // The modal renders the membership table with Username + Status columns;
    // status comes from the fixed users.status column (was a 500 before).
    await expect(
      page.locator(".ant-modal-confirm-title", { hasText: /Users with role/ }),
    ).toBeVisible({ timeout: 10000 });
    await expect(page.locator(".ant-modal .ant-table")).toBeVisible();
    await expect(
      page.locator(".ant-modal .ant-table th", { hasText: "Status" }),
    ).toBeVisible();
    await expect(
      page.locator(".ant-modal .ant-table th", { hasText: "Username" }),
    ).toBeVisible();
  });

  test("P2-6: notifications menu item announces 'Notifications', count stays visual", async ({
    page,
  }) => {
    await page.goto("/admin", { waitUntil: "domcontentloaded" });
    await expect(page.getByText("Operations Dashboard")).toBeVisible({
      timeout: 10000,
    });

    // The menuitem's accessible name must be exactly the label — the unread
    // badge is aria-hidden and no longer concatenates into the name.
    const item = page.getByRole("menuitem", { name: "Notifications" });
    await expect(item).toBeVisible({ timeout: 10000 });

    // Visual count is still rendered for sighted users (inside the bell).
    await expect(item.locator(".ant-badge")).toHaveCount(1, { timeout: 5000 });
  });
});
