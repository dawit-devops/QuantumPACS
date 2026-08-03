import { test, expect } from "@playwright/test";
import { seedQAUser, seedTechnologist, loginAsAdmin, BASE } from "./helpers";

// Every QA screen is gated on QA_READ via PermissionRoute in index.tsx. This
// suite is the positive control for the R05 QA Team role: a seeded qa_team
// session (same permission set as the backend built-in role) must see the QA
// menu items, reach every /qa/* page, and render its heading.
const QA_ROUTES = [
  { path: "/qa/queue", heading: "QA Review Queue" },
  { path: "/qa/protocols", heading: "Protocol Registry" },
  { path: "/qa/incidents", heading: "Incidents & Retakes" },
  { path: "/qa/actions", heading: "Corrective Actions" },
];

test.describe("QA Team (R05) — role workflow", () => {
  test("QA user sees the QA menu items under Admin", async ({ page }) => {
    await seedQAUser(page);
    await page.getByText("Admin").first().click();
    for (const label of [
      "QA Queue",
      "Protocols",
      "Incidents",
      "Corrective Actions",
    ]) {
      await expect(page.getByText(label).first()).toBeVisible({
        timeout: 5000,
      });
    }
  });

  test("QA user is not shown admin-only items", async ({ page }) => {
    await seedQAUser(page);
    await page.getByText("Admin").first().click();
    // QA lacks USER_READ / ROLE_READ / LOG_READ — those menu items must stay hidden.
    await expect(page.getByText("Users").first()).not.toBeVisible({
      timeout: 5000,
    });
    await expect(page.getByText("Roles").first()).not.toBeVisible({
      timeout: 5000,
    });
    await expect(page.getByText("Logs").first()).not.toBeVisible({
      timeout: 5000,
    });
  });

  for (const { path, heading } of QA_ROUTES) {
    test(`QA user can open ${path}`, async ({ page }) => {
      await seedQAUser(page);
      await page.goto(BASE + path, { waitUntil: "domcontentloaded" });
      await expect(page).toHaveURL(new RegExp(path + "$"), { timeout: 10000 });
      await expect(page.getByText(heading).first()).toBeVisible({
        timeout: 10000,
      });
    });
  }

  test("QA user can open the review form from the queue", async ({ page }) => {
    await seedQAUser(page);
    await page.goto(BASE + "/qa/queue", { waitUntil: "domcontentloaded" });
    await expect(page.getByText("QA Review Queue").first()).toBeVisible({
      timeout: 10000,
    });
    // The review route is registered under the same QA_READ gate — deep-link it.
    await page.goto(BASE + "/qa/review/e2e-exam", {
      waitUntil: "domcontentloaded",
    });
    await expect(page).toHaveURL(/\/qa\/review\/e2e-exam/, { timeout: 10000 });
  });
});

test.describe("QA Team (R05) — route gating matrix", () => {
  for (const { path } of QA_ROUTES) {
    test(`technologist is denied deep-link ${path}`, async ({ page }) => {
      await seedTechnologist(page);
      await page.goto(BASE + path, { waitUntil: "domcontentloaded" });
      await expect(page).toHaveURL(/\/$/, { timeout: 5000 });
    });
  }

  for (const { path } of QA_ROUTES) {
    test(`admin is allowed deep-link ${path}`, async ({ page }) => {
      await loginAsAdmin(page);
      await page.goto(BASE + path, { waitUntil: "domcontentloaded" });
      await expect(page).toHaveURL(new RegExp(path + "$"), { timeout: 10000 });
    });
  }
});

test.describe("QA Team (R05) — API auth", () => {
  test("QA endpoints require an auth token", async ({ page }) => {
    const resp = await page.request.get("http://localhost:8080/api/qa/queue");
    expect(resp.status()).toBe(401);
  });

  test("QA endpoints deny unauthenticated mutation", async ({ page }) => {
    const resp = await page.request.post(
      "http://localhost:8080/api/qa/reviews",
      {
        headers: { "Content-Type": "application/json" },
        data: { exam_id: "x" },
      },
    );
    expect(resp.status()).toBe(401);
  });
});
