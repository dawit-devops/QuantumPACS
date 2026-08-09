import { test, expect } from "@playwright/test";
import { loginAsAdmin, API_BASE, openSubmenu, menuName } from "./helpers";

test.describe("Admin UI", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test("sidebar contains navigation items after login", async ({ page }) => {
    await expect(
      page.getByRole("menuitem", { name: menuName("Files") }),
    ).toBeVisible({
      timeout: 10000,
    });
    await expect(
      page.getByRole("menuitem", { name: menuName("Logout") }),
    ).toBeVisible({
      timeout: 5000,
    });
  });

  test("full session flow: login, browse files, logout", async ({ page }) => {
    await expect(
      page.getByRole("menuitem", { name: menuName("Files") }),
    ).toBeVisible({
      timeout: 10000,
    });
    await expect(
      page.getByRole("menuitem", { name: menuName("Account") }),
    ).toBeVisible();

    await page.getByRole("menuitem", { name: menuName("Account") }).click();
    await expect(page).toHaveURL(/\/account/, { timeout: 10000 });

    await page.getByRole("menuitem", { name: menuName("Files") }).click();
    await expect(page).toHaveURL(/\/$/, { timeout: 10000 });

    await page.getByRole("menuitem", { name: menuName("Logout") }).click();
    await expect(page).toHaveURL(/\/login/, { timeout: 15000 });
    await expect(page.getByText("Sign in to your account")).toBeVisible({
      timeout: 10000,
    });
  });

  test("admin submenu navigation", async ({ page }) => {
    await openSubmenu(page, "Admin", "Users");
    for (const item of ["Replicas", "Users", "Logs", "Roles"]) {
      await expect(
        page.getByRole("menuitem", { name: menuName(item) }),
      ).toBeVisible({ timeout: 5000 });
    }

    await page.getByRole("menuitem", { name: menuName("Users") }).click();
    await expect(page).toHaveURL(/\/users/, { timeout: 10000 });
  });
});

test.describe("API Integration", () => {
  test("health endpoint returns 200", async ({ page }) => {
    const resp = await page.request.get(`${API_BASE}/api/health`);
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(["ok", "degraded"]).toContain(body.status);
  });

  test("CORS headers present on API response", async ({ page }) => {
    // CORS response headers are only emitted for cross-origin requests (with
    // an Origin header) — a plain request context has no origin.
    const resp = await page.request.get(`${API_BASE}/api/health`, {
      headers: { Origin: "http://localhost:5173" },
    });
    expect(resp.headers()["access-control-allow-origin"]).toBeTruthy();
  });

  test("API rejects unauthenticated requests with 401", async ({ page }) => {
    const resp = await page.request.get(`${API_BASE}/api/files`);
    expect(resp.status()).toBe(401);
  });

  test("API accepts X-Auth-Pacs header with valid token", async ({ page }) => {
    const resp = await page.request.post(`${API_BASE}/api/login`, {
      data: { username: "admin", password: "pa55w0rd" },
    });
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body).toHaveProperty("token");

    const filesResp = await page.request.get(`${API_BASE}/api/files`, {
      headers: { "X-Auth-Pacs": body.token },
    });
    expect(filesResp.status()).toBe(200);
  });
});
