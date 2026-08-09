import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { loginAsAdmin, openAdminItem } from "./helpers";

test.describe("Accessibility (axe)", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test("files page has no serious or critical violations", async ({ page }) => {
    await expect(page.getByTestId("files-search-input")).toBeVisible({
      timeout: 10000,
    });
    const results = await new AxeBuilder({ page }).analyze();
    const blocking = results.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious",
    );
    expect(blocking).toEqual([]);
  });

  test("users page has no serious or critical violations", async ({ page }) => {
    await openAdminItem(page, "Users");
    await expect(page).toHaveURL(/\/users/, { timeout: 10000 });
    // The table is the deterministic "page finished hydrating" signal.
    await expect(page.locator(".ant-table")).toBeVisible({ timeout: 15000 });
    const results = await new AxeBuilder({ page }).analyze();
    const blocking = results.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious",
    );
    expect(blocking).toEqual([]);
  });
});
