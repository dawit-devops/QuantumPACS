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
    await expect(page.getByTestId("files-search-input")).toBeVisible({
      timeout: 20000,
    });
  });

  test("mobile nav drawer opens with Files link after login", async ({
    page,
  }) => {
    await loginAsAdmin(page);
    // waitForShell already opened the drawer on mobile; the Files item is what
    // proved the shell loaded.
    await expect(
      page.getByRole("menuitem", { name: menuName("Files") }),
    ).toBeVisible({
      timeout: 10000,
    });
    await page.getByRole("button", { name: "Menu" }).click();
    await expect(
      page.getByRole("menuitem", { name: menuName("Account") }),
    ).toBeVisible({
      timeout: 5000,
    });
  });
});
