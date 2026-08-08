import { test, expect } from "@playwright/test";
import { loginAsAdmin, openSubmenu, openAdminItem, menuName } from "./helpers";

test.describe("Admin Sections", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test("admin can navigate to DICOMweb Server page", async ({ page }) => {
    await openSubmenu(page, "Admin", "Users");
    await openSubmenu(page, "DICOMweb", "Server");
    await page.getByRole("menuitem", { name: menuName("Server") }).click();
    await expect(page).toHaveURL(/\/dicomweb/, { timeout: 10000 });
  });

  test("admin can navigate to HL7 dashboard page", async ({ page }) => {
    await openAdminItem(page, "HL7");
    await expect(page).toHaveURL(/\/hl7/, { timeout: 10000 });
  });

  test("admin can navigate to Integrations page", async ({ page }) => {
    await openAdminItem(page, "Integrations");
    await expect(page).toHaveURL(/\/integrations/, { timeout: 10000 });
  });
});
