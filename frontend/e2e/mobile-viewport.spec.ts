import { test, expect } from "@playwright/test";
import { clearAndGo, loginAsAdmin, menuName } from "./helpers";

test.describe("Mobile Viewport", () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test("login page renders on mobile", async ({ page }) => {
    await clearAndGo(page);
    await expect(page.getByText("Sign in to your account")).toBeVisible({
      timeout: 15000,
    });
    await page.getByPlaceholder("Username").fill("admin");
    await page.getByPlaceholder("Password").fill("pa55w0rd");
    await page.getByRole("button", { name: /sign in/i }).click();
    // Admin login lands on the role-scoped dashboard (/admin). The sidebar
    // lives in a closed drawer on mobile, so the shell signal is the
    // dashboard heading itself, not a nav item.
    await expect(page.getByText("Operations Dashboard")).toBeVisible({
      timeout: 20000,
    });
  });

  test("mobile nav drawer opens with Files link after login", async ({
    page,
  }) => {
    await loginAsAdmin(page);
    // waitForShell already opened the sidebar drawer on mobile; the Files
    // item is what proved the shell loaded. The drawer holds the full nav
    // (incl. Account) — MobileNav's bottom "Menu" button only shows a
    // curated subset, so assert inside the already-open sidebar drawer.
    await expect(
      page.getByRole("menuitem", { name: menuName("Files") }),
    ).toBeVisible({
      timeout: 10000,
    });
    await expect(
      page.getByRole("menuitem", { name: menuName("Account") }),
    ).toBeVisible({
      timeout: 5000,
    });
  });
});
