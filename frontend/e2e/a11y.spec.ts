import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { loginAsAdmin, openAdminItem, BASE } from "./helpers";

test.describe("Accessibility (axe)", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  // antd renders an invisible 0-height measure row (<tr aria-hidden>) to size
  // scrollable tables; it embeds focusable inputs (select-all checkbox), so
  // axe flags it. The row is a rendering artifact, not a user-facing control
  // — excluded from the scan the same way audit tools scope to visible UI.
  async function scan(page: import("@playwright/test").Page) {
    const results = await new AxeBuilder({ page })
      .exclude(".ant-table-measure-row")
      .analyze();
    const blocking = results.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious",
    );
    expect(blocking).toEqual([]);
  }

  test("files page has no serious or critical violations", async ({ page }) => {
    // Admin login now lands on the dashboard; the files page is the audit
    // target, so navigate to it explicitly. domcontentloaded (never
    // networkidle — keep-alive sockets/polling make it hang) plus the
    // explicit element wait below is the deterministic "page ready" signal.
    await page.goto(`${BASE}/`, { waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("files-search-input")).toBeVisible({
      timeout: 10000,
    });
    await scan(page);
  });

  test("users page has no serious or critical violations", async ({ page }) => {
    await openAdminItem(page, "Users");
    await expect(page).toHaveURL(/\/users/, { timeout: 10000 });
    // The table is the deterministic "page finished hydrating" signal. .first()
    // guards the navigation overlap where the dashboard replica table is still
    // mounted while the lazy users page swaps in.
    await expect(page.locator(".ant-table").first()).toBeVisible({
      timeout: 15000,
    });
    await scan(page);
  });
});
