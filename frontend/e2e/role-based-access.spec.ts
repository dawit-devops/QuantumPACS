import { test, expect } from "@playwright/test";
import {
  loginAsAdmin,
  seedTechnologist,
  seedAuditOnlyUser,
  BASE,
  menuName,
} from "./helpers";

// Every admin route gated by PermissionRoute in index.tsx. Shared by the denial
// suite (technologist must be bounced to "/") and the positive-control suite
// (admin must NOT be bounced) so the matrix stays in sync.
const ADMIN_ROUTES = [
  "/admin",
  "/replicas",
  "/users",
  "/roles",
  "/tenants",
  "/logs",
  "/worklist",
  "/schedule-board",
  "/exams",
  "/reading",
  "/peer-review",
  "/service-keys",
  "/routing",
  "/fhir/config",
  "/fhir/monitoring",
  "/fhir/docs",
  "/hl7",
  "/dicomweb",
  "/integrations",
  "/qa/queue",
  "/qa/protocols",
  "/qa/incidents",
  "/qa/actions",
];

test.describe("Role-Based Access", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test("admin sees admin menu item", async ({ page }) => {
    await expect(
      page.getByRole("menuitem", { name: menuName("Admin") }),
    ).toBeVisible({
      timeout: 5000,
    });
  });

  test("admin can navigate to Users page", async ({ page }) => {
    await page.getByRole("menuitem", { name: menuName("Admin") }).click();
    await page.getByRole("menuitem", { name: menuName("Users") }).click();
    await expect(page).toHaveURL(/\/users/, { timeout: 10000 });
  });

  test("account page loads", async ({ page }) => {
    await page.getByRole("menuitem", { name: menuName("Account") }).click();
    await expect(page).toHaveURL(/\/account/, { timeout: 10000 });
  });

  test("metrics page loads", async ({ page }) => {
    // "Metrics" names both the submenu and its single child — expand the
    // submenu, then follow the child's link (mounted lazily on first open).
    await page
      .getByRole("menuitem", { name: menuName("Metrics") })
      .first()
      .click();
    await page.getByRole("link", { name: "Metrics" }).click();
    await expect(page).toHaveURL(/\/metrics/, { timeout: 10000 });
  });
});

test.describe("Non-admin deep-link denial (PermissionRoute)", () => {
  // A technologist without those permissions must be redirected to "/" (Files)
  // rather than reaching the route.
  for (const path of ADMIN_ROUTES) {
    test(`technologist is denied deep-link ${path}`, async ({ page }) => {
      await seedTechnologist(page);
      await page.goto(BASE + path, { waitUntil: "domcontentloaded" });
      await expect(page).toHaveURL(/\/$/, { timeout: 5000 });
    });
  }

  test("technologist can still reach always-visible Files", async ({
    page,
  }) => {
    await seedTechnologist(page);
    await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
    await expect(page).toHaveURL(/\/$/, { timeout: 5000 });
  });
});

test.describe("Audit-only deep-link access (LOG_READ | AUDIT_READ gate)", () => {
  // AUDIT_READ without LOG_READ must satisfy the /logs route (the imaging
  // informatics / department manager shape), while still being bounced
  // elsewhere. Also proves the gate is a union, not an AND.
  test("audit-only user can reach /logs", async ({ page }) => {
    await seedAuditOnlyUser(page);
    await page.goto(BASE + "/logs", { waitUntil: "domcontentloaded" });
    await expect(page).toHaveURL(/\/logs$/, { timeout: 10000 });
  });

  test("audit-only user is still denied /users and /routing", async ({
    page,
  }) => {
    await seedAuditOnlyUser(page);
    await page.goto(BASE + "/users", { waitUntil: "domcontentloaded" });
    await expect(page).toHaveURL(/\/$/, { timeout: 5000 });
    await page.goto(BASE + "/routing", { waitUntil: "domcontentloaded" });
    await expect(page).toHaveURL(/\/$/, { timeout: 5000 });
  });
});

test.describe("Admin deep-link access (PermissionRoute positive control)", () => {
  // An admin user must NOT be bounced back to "/" — the route renders in place
  // (URL stays on the path). Admin pages hydrate slower than a redirect, so the
  // longer timeout covers the full page load.
  for (const path of ADMIN_ROUTES) {
    test(`admin is allowed deep-link ${path}`, async ({ page }) => {
      await loginAsAdmin(page);
      await page.goto(BASE + path, { waitUntil: "domcontentloaded" });
      // Trailing-anchor match on the literal path, so /users matches /users and
      // not /users/x. Paths contain only letters and slashes (not regex specials).
      await expect(page).toHaveURL(new RegExp(path + "$"), {
        timeout: 10000,
      });
    });
  }
});
