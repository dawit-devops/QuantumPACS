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
    // Dev-DB roles are Administrator/Biller/etc. — "admin" only appears in
    // the seeded username, not the roles list, so assert real role names.
    expect(bodyText).toContain("Administrator");
    expect(bodyText).toContain("Biller");
  });
});
