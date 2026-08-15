import { test, expect } from "@playwright/test";
import { loginAs, API_BASE } from "./helpers";

// Phase 4 of user-feature-review/care-coordinator
// (phase/user-feature-review-care-coordinator). Real-backend coverage for the
// canonical care_coordinator (15 grants post migration 063):
//   P1-2  landing is the role's own Orders page, not the radiologist worklist
//   P0-1  the Schedule Board loads day data (WORKLIST_READ unlock) — for
//         care_coordinator AND physician
//   P1-1  the Files page list loads (FILE_READ unlock, no dead end)
//   P0-2  a seeded visit order renders on the Orders page (status lifecycle)
//   P2-1  the patient page shows the Reports & Results card
// Serial: the orders-seeding test mutates shared state; the others are
// read-only but keep ordering deterministic.
test.describe.configure({ mode: "serial" });
test.describe("Care coordinator workflow (real backend)", () => {
  const csrf = { "Content-Type": "application/json", "X-CSRF-Token": "1" };

  // Dismiss the onboarding tour overlay (fixed tooltip that intercepts
  // clicks near the top of the page).
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      try {
        localStorage.setItem("quantumpacs-tour-done", "1");
      } catch {}
    });
  });

  test("P1-2: lands on /orders, not the radiologist worklist", async ({ page }) => {
    await loginAs(page, "test.care_coordinator", "Test@123456");
    await expect(page).toHaveURL(/\/orders/, { timeout: 15000 });
    await expect(page.getByRole("heading", { name: /Orders/ })).toBeVisible({
      timeout: 10000,
    });
    // The coordination sidebar item is visible and the reading item is not.
    await expect(page.getByRole("menuitem", { name: /Orders/ })).toBeVisible();
    await expect(page.getByRole("menuitem", { name: /Reading Worklist/ })).toHaveCount(0);
  });

  test("P0-1: Schedule Board loads day data for care_coordinator", async ({
    page,
  }) => {
    await loginAs(page, "test.care_coordinator", "Test@123456");
    await page.goto("/schedule-board", { waitUntil: "domcontentloaded" });
    // The board renders the day header and does NOT show the permission dead
    // end (pre-fix: "Failed to load schedule · Missing permission: WORKLIST_READ").
    await expect(page.getByRole("heading", { name: /Schedule Board/ })).toBeVisible({
      timeout: 10000,
    });
    await expect(page.getByText(/Failed to load schedule/)).toHaveCount(0, {
      timeout: 10000,
    });
    // Day data renders — either scheduled/performed totals or the board grid.
    await expect(
      page.getByText(/Scheduled|Performed|Cancelled|Today/).first(),
    ).toBeVisible({ timeout: 10000 });
  });

  test("P0-1: physician also loads the Schedule Board (cross-role fix)", async ({
    page,
  }) => {
    await loginAs(page, "test.physician", "Test@123456");
    await page.goto("/schedule-board", { waitUntil: "domcontentloaded" });
    await expect(page.getByText(/Failed to load schedule/)).toHaveCount(0, {
      timeout: 10000,
    });
    await expect(page.getByRole("heading", { name: /Schedule Board/ })).toBeVisible();
  });

  test("P1-1: Files page list loads (no permission dead end)", async ({
    page,
  }) => {
    await loginAs(page, "test.care_coordinator", "Test@123456");
    await page.goto("/", { waitUntil: "domcontentloaded" });
    // Pre-fix the page rendered "Missing permission: FILE_READ" with a
    // non-functional Retry. Now the search surface + list render (the
    // "Search uploaded studies and images" PageHeader description).
    await expect(page.getByText(/Missing permission: FILE_READ/)).toHaveCount(0, {
      timeout: 10000,
    });
    await expect(
      page.getByText(/Search uploaded studies and images/),
    ).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/No files uploaded/)).toHaveCount(0, { timeout: 10000 });
  });

  test("P0-2: a seeded visit order renders on the Orders page", async ({
    page,
  }) => {
    // Seed a visit + order via the receptionist (REGISTRATION_WRITE create
    // path — care_coordinator holds no write grants), then assert the
    // coordinator's Orders page shows the row with a derived status.
    const stamp = Date.now();
    const login = await page.request.post(`${API_BASE}/api/v2/login`, {
      data: { username: "test.receptionist", password: "Test@123456" },
    });
    expect(login.status()).toBe(200);
    const recTok = (await login.json()).token;
    const recH = { ...csrf, Authorization: `Bearer ${recTok}` };

    const visit = await page.request.post(`${API_BASE}/api/v2/visits`, {
      headers: recH,
      data: { patient_id: `E2E-CC-${stamp}` },
    });
    expect(visit.status()).toBe(201);
    const visitId = (await visit.json()).data.id;

    const order = await page.request.post(
      `${API_BASE}/api/v2/visits/${visitId}/orders`,
      {
        headers: recH,
        data: {
          requested_procedure: "MRI Brain",
          indication: "E2E coordination probe",
          urgency: "routine",
          referring_physician: "Dr E2E",
        },
      },
    );
    expect(order.status()).toBe(201);

    // Care coordinator sees the order on the Orders page.
    await loginAs(page, "test.care_coordinator", "Test@123456");
    await expect(page.getByRole("heading", { name: /Orders/ })).toBeVisible();
    await expect(page.getByText("MRI Brain").first()).toBeVisible({
      timeout: 10000,
    });
    // Summary headline renders (1 open · ... reported today).
    await expect(page.getByText(/open ·/)).toBeVisible({ timeout: 10000 });
  });

  test("P2-1: patient page shows the Reports & Results card", async ({
    page,
  }) => {
    await loginAs(page, "test.care_coordinator", "Test@123456");
    await page.goto("/patients/13", { waitUntil: "domcontentloaded" });
    await expect(page.getByText(/Reports & Results/)).toBeVisible({
      timeout: 10000,
    });
  });
});
