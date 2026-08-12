import { test, expect } from "@playwright/test";
import {
  loginAsAdmin,
  seedTechnologist,
  seedAuditOnlyUser,
  seedFrontDesk,
  seedPatient,
  stubApiRoutes,
  BASE,
  menuName,
  openSubmenu,
} from "./helpers";

// Admin-console and platform routes gated by PermissionRoute in index.tsx.
// Shared by the denial suite (technologist must be bounced to "/") and the
// positive-control suite (admin must NOT be bounced) so the matrix stays in sync.
const ADMIN_ROUTES = [
  "/admin",
  "/replicas",
  "/users",
  "/roles",
  "/tenants",
  "/logs",
  "/service-keys",
  "/routing",
  "/fhir/config",
  "/fhir/monitoring",
  "/fhir/docs",
  "/hl7",
  "/dicomweb",
  "/integrations",
];

// Clinical surfaces (Reading / Acquisition / QA) are closed to admin-scoped
// roles: ClinicalRoute excludes them regardless of grants and the bounce lands
// on the dashboard. The positive control is therefore inverted for these paths.
const CLINICAL_ROUTES = [
  "/worklist",
  "/schedule-board",
  "/exams",
  "/reading",
  "/peer-review",
  "/qa/queue",
  "/qa/protocols",
  "/qa/incidents",
  "/qa/actions",
];

// Operational (front-office / patient) surfaces: R08 registration, visits and
// the privacy queue, plus the R19 patient portal. Technologists hold none of
// these grants, so the denial loop below covers them too.
const FRONT_OFFICE_ROUTES = [
  "/frontdesk/registration",
  "/frontdesk/visits",
  "/frontdesk/queue",
  "/portal",
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
    // The Admin section is already open for admin (dashboard landing auto-opens
    // it), so expand conditionally: clicking an open submenu title toggles it
    // closed and hides the Users child.
    await openSubmenu(page, "Admin", "Users");
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
  for (const path of [
    ...ADMIN_ROUTES,
    ...CLINICAL_ROUTES,
    ...FRONT_OFFICE_ROUTES,
  ]) {
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
    // emr_admin is admin-scoped with AUDIT_READ (a dashboard permission),
    // so the PermissionRoute bounce lands on the dashboard.
    await seedAuditOnlyUser(page);
    await page.goto(BASE + "/users", { waitUntil: "domcontentloaded" });
    await expect(page).toHaveURL(/\/admin$/, { timeout: 5000 });
    await page.goto(BASE + "/routing", { waitUntil: "domcontentloaded" });
    await expect(page).toHaveURL(/\/admin$/, { timeout: 5000 });
  });
});

test.describe("Front-office deep-link access (R08 / R19 positive control)", () => {
  // A receptionist holding the R08 grants must render the front-desk surfaces
  // in place (URL stays on the path), and the schedule board must open under
  // its SCHEDULE_READ gate (not just WORKLIST_READ).
  for (const path of [
    "/frontdesk/registration",
    "/frontdesk/visits",
    "/frontdesk/queue",
    "/schedule-board",
  ]) {
    test(`receptionist is allowed deep-link ${path}`, async ({ page }) => {
      await seedFrontDesk(page, "receptionist");
      await page.goto(BASE + path, { waitUntil: "domcontentloaded" });
      await expect(page).toHaveURL(new RegExp(path + "$"), {
        timeout: 10000,
      });
    });
  }

  test("patient is allowed deep-link /portal", async ({ page }) => {
    await seedPatient(page);
    await page.goto(BASE + "/portal", { waitUntil: "domcontentloaded" });
    await expect(page).toHaveURL(/\/portal$/, { timeout: 10000 });
  });
});

test.describe("Front-office deep-link denial (no-grant roles)", () => {
  // A technologist holds no R08/R19 grants: the PermissionRoute/ClinicalRoute
  // bounce lands on "/" (Files), mirroring the existing denial suite.
  for (const path of FRONT_OFFICE_ROUTES) {
    test(`technologist is denied deep-link ${path}`, async ({ page }) => {
      await seedTechnologist(page);
      await page.goto(BASE + path, { waitUntil: "domcontentloaded" });
      await expect(page).toHaveURL(/\/$/, { timeout: 5000 });
    });
  }
});

test.describe("Front-office roles denied clinical surfaces", () => {
  // R4-05 inverse: receptionist holds no clinical grants, so deep-linking the
  // reading worklist or the exam console must bounce back to the front-office
  // landing (not render a clinical surface). /worklist is deliberately
  // absent: Matrix A grants the receptionist WORKLIST_READ (the MWL list is
  // part of scheduling), so the gate lets them in — covered by the positive
  // control below.
  for (const path of ["/reading", "/exams"]) {
    test(`receptionist is denied deep-link ${path}`, async ({ page }) => {
      await seedFrontDesk(page, "receptionist");
      await page.goto(BASE + path, { waitUntil: "domcontentloaded" });
      await expect(page).toHaveURL(/\/frontdesk\/registration$/, {
        timeout: 10000,
      });
    });
  }

  test("receptionist is allowed deep-link /worklist (WORKLIST_READ)", async ({
    page,
  }) => {
    await seedFrontDesk(page, "receptionist");
    await page.goto(BASE + "/worklist", { waitUntil: "domcontentloaded" });
    await expect(page).toHaveURL(/\/worklist$/, { timeout: 10000 });
  });

  test("receptionist with a clinical grant follows the permission-based gate", async ({
    page,
  }) => {
    // Drift shape: a front-office role that gained REPORT_READ. ClinicalRoute
    // closes clinical surfaces only to admin-scoped roles (the pacs_admin +
    // REPORT_READ bounce is covered by the admin denial loop); a non-admin
    // front-office role holding the grant opens /reading like any other
    // cross-scope grant (cf. radiologist + LOG_READ reaching /logs). The
    // workspace mapping is unaffected: landing stays frontdesk.
    await stubApiRoutes(page);
    await page.goto(BASE, { waitUntil: "domcontentloaded" });
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
      localStorage.setItem("userId", "fd-2");
      localStorage.setItem("username", "receptionist");
      localStorage.setItem("admin", "false");
      localStorage.setItem("role", "receptionist");
      localStorage.setItem(
        "permissions",
        JSON.stringify(["REGISTRATION_READ", "QUEUE_READ", "REPORT_READ"]),
      );
    });
    await page.goto(BASE, { waitUntil: "domcontentloaded" });
    await page.goto(BASE + "/reading", { waitUntil: "domcontentloaded" });
    await expect(page).toHaveURL(/\/reading$/, { timeout: 10000 });
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

test.describe("Admin deep-link denial (role-scoped clinical routes)", () => {
  // ClinicalRoute excludes admin-scoped roles from Reading / Acquisition / QA
  // even when their grants pass; the redirect lands on the dashboard. The
  // front-desk routes are ClinicalRoutes too, and /portal is a PermissionRoute
  // the admin holds no grant for — both bounce to the dashboard as well.
  for (const path of [...CLINICAL_ROUTES, ...FRONT_OFFICE_ROUTES]) {
    test(`admin is denied deep-link ${path}`, async ({ page }) => {
      await loginAsAdmin(page);
      await page.goto(BASE + path, { waitUntil: "domcontentloaded" });
      await expect(page).toHaveURL(/\/admin$/, { timeout: 10000 });
    });
  }
});
