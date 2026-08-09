import { test, expect } from "@playwright/test";
import { seedQAUser, API_BASE, menuName } from "./helpers";

test.describe("QA Role", () => {
  test.beforeEach(async ({ page }) => {
    await seedQAUser(page);
  });

  const QA_ROUTES = [
    { path: "/", label: "Files" },
    { path: "/qa/queue", label: "QA Queue" },
    { path: "/qa/protocols", label: "QA Protocols" },
    { path: "/qa/incidents", label: "QA Incidents" },
    { path: "/qa/corrective-actions", label: "QA Corrective Actions" },
  ];

  test("QA user can access QA routes", async ({ page }) => {
    for (const route of QA_ROUTES) {
      await page.goto(route.path, { waitUntil: "networkidle" });
      await expect(page).toHaveURL(route.path, { timeout: 10000 });
    }
  });

  test("QA user sees QA menu items in the sidebar", async ({ page }) => {
    // The QA workspace section is open by default for qa_team users.
    for (const label of [
      "QA Queue",
      "QA Protocols",
      "QA Incidents",
      "QA Corrective Actions",
    ]) {
      await expect(
        page.getByRole("menuitem", { name: menuName(label) }),
      ).toBeVisible({
        timeout: 10000,
      });
    }
  });

  test("QA user is not shown admin-only menu items", async ({ page }) => {
    // Admin is NOT the QA workspace section, so it starts closed — this click
    // genuinely opens it, and the admin-only items still must not appear.
    await page.getByRole("menuitem", { name: menuName("Admin") }).click();
    for (const label of [
      "Users",
      "Roles",
      "Logs",
      "Service Keys",
      "Routing",
      "HL7",
    ]) {
      await expect(
        page.getByRole("menuitem", { name: menuName(label) }),
      ).not.toBeVisible();
    }
  });

  test("QA user sees dashboard content", async ({ page }) => {
    const bodyText = await page.locator("body").innerText({ timeout: 15000 });
    expect(bodyText.length).toBeGreaterThan(50);
  });

  test("QA user API calls are authenticated", async ({ page }) => {
    const resp = await page.request.get(`${API_BASE}/api/files`);
    expect(resp.status()).toBe(200);
  });
});
