import { test, expect } from "@playwright/test";
import { clearAndGo, BASE } from "./helpers";
import { LoginPage } from "./pages/LoginPage";

test.describe("Login Flow", () => {
  test("renders login page with branding", async ({ page }) => {
    await clearAndGo(page);
    await expect(page.getByText("Sign in to your account")).toBeVisible({
      timeout: 15000,
    });
    await expect(page).toHaveTitle(/QuantumPACS/);
    await expect(page.getByRole("button", { name: /sign in/i })).toBeVisible();
  });

  test("logs in with admin credentials and lands on the admin dashboard", async ({
    page,
  }) => {
    const login = new LoginPage(page);
    await login.loginAsAdmin();
    await expect(page).toHaveURL(/\/admin/, { timeout: 15000 });
    // The dashboard header is the real "landed on Operations Dashboard" signal.
    await expect(page.getByText("Operations Dashboard")).toBeVisible({
      timeout: 15000,
    });
  });

  test("stays on login page with wrong password", async ({ page }) => {
    const login = new LoginPage(page);
    await login.open();
    await login.login("admin", "wrongpass");
    // No fixed sleep: the URL assertion retries until the failed request settles.
    await expect(page).toHaveURL(/\/login/, { timeout: 15000 });
    await expect(page.getByText("Sign in to your account")).toBeVisible();
  });

  test("redirects unauthenticated user to login", async ({ page }) => {
    await page.goto(BASE + "/users", { waitUntil: "networkidle" });
    await expect(page).toHaveURL(/\/login/, { timeout: 15000 });
  });
});
