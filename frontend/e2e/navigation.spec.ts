import { test, expect } from "@playwright/test";
import { loginAsAdmin, openAdminItem, openSubmenu, menuName } from "./helpers";

test.describe("Admin Navigation", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test("sidebar visible with Files link", async ({ page }) => {
    await expect(
      page.getByRole("menuitem", { name: menuName("Files") }),
    ).toBeVisible({
      timeout: 10000,
    });
  });

  test("admin submenu expands with all items", async ({ page }) => {
    // The Admin section usually starts open on the Files page; openSubmenu
    // makes the expansion idempotent (clicking an open title would close it).
    await openSubmenu(page, "Admin", "Users");
    for (const item of [
      "Dashboard",
      "Replicas",
      "Users",
      "Tenants",
      "Roles",
      "Logs",
      "Worklist",
      "Service Keys",
      "Routing",
      "FHIR",
      "Integrations",
      "HL7",
      "DICOMweb",
    ]) {
      await expect(
        page.getByRole("menuitem", { name: menuName(item) }),
      ).toBeVisible({ timeout: 5000 });
    }
  });

  test("navigates to Users page", async ({ page }) => {
    await openAdminItem(page, "Users");
    await expect(page).toHaveURL(/\/users/, { timeout: 10000 });
    await expect(page.getByText("Username").first()).toBeVisible({
      timeout: 10000,
    });
  });

  test("navigates to Roles page", async ({ page }) => {
    await openAdminItem(page, "Roles");
    await expect(page).toHaveURL(/\/roles/, { timeout: 10000 });
    await expect(page.getByText("Create Role").first()).toBeVisible({
      timeout: 10000,
    });
  });

  test("navigates to Worklist page", async ({ page }) => {
    await openAdminItem(page, "Worklist");
    await expect(page).toHaveURL(/\/worklist/, { timeout: 10000 });
    await expect(
      page.getByRole("button", { name: "Create worklist entry" }),
    ).toBeVisible({ timeout: 10000 });
  });

  test("navigates to Dashboard page", async ({ page }) => {
    await openAdminItem(page, "Dashboard");
    await expect(page).toHaveURL(/\/admin/, { timeout: 10000 });
    await expect(page.getByText("Operations Dashboard").first()).toBeVisible({
      timeout: 10000,
    });
  });

  test("navigates to Replicas page", async ({ page }) => {
    await openAdminItem(page, "Replicas");
    await expect(page).toHaveURL(/\/replicas/, { timeout: 10000 });
  });

  test("navigates to Logs page", async ({ page }) => {
    await openAdminItem(page, "Logs");
    await expect(page).toHaveURL(/\/logs/, { timeout: 10000 });
    await expect(page.getByText("Audit Log").first()).toBeVisible({
      timeout: 10000,
    });
  });

  test("navigates to Service Keys page", async ({ page }) => {
    await openAdminItem(page, "Service Keys");
    await expect(page).toHaveURL(/\/service-keys/, { timeout: 10000 });
    await expect(page.getByText("Generate Key").first()).toBeVisible({
      timeout: 10000,
    });
  });

  test("navigates to Routing page", async ({ page }) => {
    await openAdminItem(page, "Routing");
    await expect(page).toHaveURL(/\/routing/, { timeout: 10000 });
    await expect(page.getByText("Create Rule").first()).toBeVisible({
      timeout: 10000,
    });
  });

  test("navigates to DICOMweb page", async ({ page }) => {
    // DICOMweb is a submenu: expand it (idempotent), then its first child
    // (Server) targets the /dicomweb route.
    await openSubmenu(page, "DICOMweb", "Server");
    await page.getByRole("menuitem", { name: menuName("Server") }).click();
    await expect(page).toHaveURL(/\/dicomweb/, { timeout: 10000 });
  });

  test("navigates to Integrations page", async ({ page }) => {
    await openAdminItem(page, "Integrations");
    await expect(page).toHaveURL(/\/integrations/, { timeout: 10000 });
    await expect(page.getByText("Webhooks").first()).toBeVisible({
      timeout: 10000,
    });
  });

  test("navigates to Account page", async ({ page }) => {
    await page.getByRole("menuitem", { name: menuName("Account") }).click();
    await expect(page).toHaveURL(/\/account/, { timeout: 10000 });
  });

  test("navigates to Metrics page", async ({ page }) => {
    // "Metrics" names both the submenu and its single child — expand, then use
    // the child's link (antd mounts submenu children lazily on first open).
    await page
      .getByRole("menuitem", { name: menuName("Metrics") })
      .first()
      .click();
    await page.getByRole("link", { name: "Metrics" }).click();
    await expect(page).toHaveURL(/\/metrics/, { timeout: 10000 });
  });

  test("logout navigates to login page", async ({ page }) => {
    await page.getByRole("menuitem", { name: menuName("Logout") }).click();
    await expect(page).toHaveURL(/\/login/, { timeout: 15000 });
    await expect(page.getByText("Sign in to your account")).toBeVisible({
      timeout: 10000,
    });
  });

  test("full session flow: login, browse, logout", async ({ page }) => {
    await openAdminItem(page, "Users");
    await expect(page).toHaveURL(/\/users/, { timeout: 10000 });

    await page.getByRole("menuitem", { name: menuName("Files") }).click();
    await expect(page).toHaveURL(/\/$/, { timeout: 10000 });

    await page.getByRole("menuitem", { name: menuName("Account") }).click();
    await expect(page).toHaveURL(/\/account/, { timeout: 10000 });

    await page.getByRole("menuitem", { name: menuName("Logout") }).click();
    await expect(page).toHaveURL(/\/login/, { timeout: 15000 });
  });
});
