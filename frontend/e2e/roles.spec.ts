import { test, expect } from "@playwright/test";
import { loginAsAdmin, openAdminItem } from "./helpers";

test.describe("Role Management", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  async function openRoles(page: Parameters<typeof loginAsAdmin>[0]) {
    await openAdminItem(page, "Roles");
    await expect(page).toHaveURL(/\/roles/, { timeout: 10000 });
  }

  test("roles page loads via admin menu", async ({ page }) => {
    await openRoles(page);
    await expect(page.locator("body")).not.toBeEmpty({ timeout: 15000 });
  });

  test("roles page exposes the Create Role action", async ({ page }) => {
    await openRoles(page);
    await expect(
      page.getByRole("button", { name: /add role|create role|new role/i }),
    ).toBeVisible({
      timeout: 10000,
    });
  });

  test("roles page lists existing roles", async ({ page }) => {
    await openRoles(page);
    // The list loads over the real API; wait for a row before asserting the
    // body — capturing innerText during the fetch race produced flakes.
    await expect(page.getByText("Administrator").first()).toBeVisible({
      timeout: 15000,
    });
    const bodyText = await page.locator("body").innerText({ timeout: 15000 });
    // The RBAC overhaul (d4abc25) replaced the legacy Administrator/Biller
    // roles with the matrix built-ins seeded by seed_rbac (backend
    // permissions.py BUILT_IN_ROLES); assert the current canonical names.
    expect(bodyText).toContain("Radiologist");
    expect(bodyText).toContain("Cashier");
  });
});
