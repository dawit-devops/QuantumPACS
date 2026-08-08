import { test, expect } from "@playwright/test";
import {
  BASE,
  menuName,
  seedNurse,
  seedPhysicianLegacy,
  seedPacsAdminClinical,
} from "./helpers";

// Workspace scope gates (navigator.ts / PermissionRoute): the landing scan is
// bidirectional — clinical roles never land on admin-console surfaces and
// admin-scoped roles never land on clinical surfaces, even when their legacy
// grants would pass (DICOMWEB_READ on physician, REPORT_READ on pacs_admin).
test.describe("Workspace scope gates (navigator)", () => {
  test("nurse is denied the DICOMweb console and lands on the exams worklist", async ({
    page,
  }) => {
    await seedNurse(page);
    await page.goto(BASE + "/dicomweb", { waitUntil: "domcontentloaded" });
    await expect(page).toHaveURL(/\/exams$/, { timeout: 5000 });
  });

  test("physician with legacy DICOMWEB_READ is denied the DICOMweb console", async ({
    page,
  }) => {
    // The permission passes the gate, but the role scope excludes the console:
    // the redirect must go to /account (no REPORT_READ means no clinical
    // surface either).
    await seedPhysicianLegacy(page);
    await page.goto(BASE + "/dicomweb", { waitUntil: "domcontentloaded" });
    await expect(page).toHaveURL(/\/account$/, { timeout: 5000 });
  });

  test("pacs_admin with clinical grants is denied the reading worklist", async ({
    page,
  }) => {
    await seedPacsAdminClinical(page);
    await page.goto(BASE + "/reading", { waitUntil: "domcontentloaded" });
    await expect(page).toHaveURL(/\/account$/, { timeout: 5000 });
  });

  test("nurse keeps the exams worklist deep-link (positive control)", async ({
    page,
  }) => {
    await seedNurse(page);
    await page.goto(BASE + "/exams", { waitUntil: "domcontentloaded" });
    await expect(page).toHaveURL(/\/exams$/, { timeout: 5000 });
  });
});

test.describe("Sidebar section scope", () => {
  test("nurse sees acquisition sections and no admin console", async ({
    page,
  }) => {
    await seedNurse(page);
    await expect(
      page.getByRole("menuitem", { name: menuName("Acquisition") }),
    ).toBeVisible();
    await expect(
      page.getByRole("menuitem", { name: menuName("Worklist") }),
    ).toBeVisible();
    await expect(
      page.getByRole("menuitem", { name: menuName("Reading") }),
    ).not.toBeVisible();
    await expect(
      page.getByRole("menuitem", { name: menuName("Admin") }),
    ).not.toBeVisible();
    await expect(
      page.getByRole("menuitem", { name: menuName("DICOMweb") }),
    ).not.toBeVisible();
  });

  test("pacs_admin sidebar hides clinical sections", async ({ page }) => {
    await seedPacsAdminClinical(page);
    await expect(
      page.getByRole("menuitem", { name: menuName("Reading") }),
    ).not.toBeVisible();
    await expect(
      page.getByRole("menuitem", { name: menuName("Acquisition") }),
    ).not.toBeVisible();
    await expect(
      page.getByRole("menuitem", { name: menuName("QA") }),
    ).not.toBeVisible();
    await expect(
      page.getByRole("menuitem", { name: menuName("Admin") }),
    ).not.toBeVisible();
  });
});
