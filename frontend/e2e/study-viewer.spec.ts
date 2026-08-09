import { test, expect } from "@playwright/test";
import { loginAsAdmin, menuName } from "./helpers";

test.describe("Study Viewer", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test("search page loads with search input", async ({ page }) => {
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
