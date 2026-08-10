import { test, expect } from "@playwright/test";
import { seedTechnologist, API_BASE } from "./helpers";
import { WorklistPage } from "./pages/WorklistPage";

test.describe("Worklist (MWL)", () => {
  test.beforeEach(async ({ page }) => {
    // Worklist is an Acquisition-workspace surface (d4abc25): admin-scoped
    // roles never see the sidebar entry, so specs drive it as a technologist.
    await seedTechnologist(page);
  });

  test("worklist page loads via the Acquisition submenu", async ({ page }) => {
    const worklist = new WorklistPage(page);
    await worklist.openViaAdminSidebar();
    await expect(worklist.createEntryButton).toBeVisible({ timeout: 10000 });
  });

  test("worklist page has content after navigation", async ({ page }) => {
    const worklist = new WorklistPage(page);
    await worklist.openViaAdminSidebar();
    const bodyText = await page.locator("body").innerText({ timeout: 15000 });
    expect(bodyText.length).toBeGreaterThan(50);
  });

  test("worklist API requires auth token", async ({ page }) => {
    const resp = await page.request.post(`${API_BASE}/api/worklist`, {
      headers: { "Content-Type": "application/json" },
      data: {
        patient_name: "E2E^Test",
        patient_id: `E2E-${Date.now()}`,
        accession_number: `ACC-${Date.now()}`,
        modality: "CT",
        scheduled_ae_title: "E2E_TEST",
        status: "scheduled",
      },
    });
    expect(resp.status()).toBe(401);
  });
});
