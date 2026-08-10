import { test, expect } from "@playwright/test";
import { loginAsAdmin, menuName, BASE } from "./helpers";

test.describe("Study Viewer", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test("search page loads with search input", async ({ page }) => {
    // Admin now lands on /admin (role-scoped dashboard) after login, so the
    // files search surface is reached via an explicit navigation.
    await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("files-search-input")).toBeVisible({
      timeout: 10000,
    });
  });

  test("sidebar navigation links are visible", async ({ page }) => {
    await expect(
      page.getByRole("menuitem", { name: menuName("Files") }),
    ).toBeVisible({
      timeout: 10000,
    });
    await expect(
      page.getByRole("menuitem", { name: menuName("Account") }),
    ).toBeVisible();
  });
});
