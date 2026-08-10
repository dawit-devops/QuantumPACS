import { test, expect } from "@playwright/test";
import { loginAs, API_BASE } from "./helpers";

// Real-backend coverage for a non-admin role: the technologist session is
// established through the REAL UI login (not a forged localStorage stub),
// which exercises the backend login endpoint, JWT minting and the role's
// workspace landing. Runs against the live backend like worklist-flow.spec.ts.
test.describe("Real role login (real backend)", () => {
  test("technologist logs in via the UI and lands on the Acquisition workspace", async ({
    page,
  }) => {
    await loginAs(page, "test.technologist", "Test@123456");

    // Acquisition workspace landing (navigator.ts: technologist -> acquisition)
    // is the strongest "the right workspace opened" signal.
    await expect(page).toHaveURL(/\/exams/, { timeout: 15000 });
    // The MWL Worklist lives in the Acquisition section for clinical roles.
    await expect(
      page.getByRole("menuitem", { name: /Worklist/ }).first(),
    ).toBeVisible({ timeout: 10000 });
  });

  test("technologist session makes authenticated API calls", async ({
    page,
  }) => {
    await loginAs(page, "test.technologist", "Test@123456");

    const token = await page.evaluate(() =>
      localStorage.getItem("access_token"),
    );
    expect(token).toBeTruthy();

    // The token from the real login must be accepted by role-scoped endpoints
    // (WORKLIST_READ + the account profile every session loads).
    const worklist = await page.request.get(`${API_BASE}/api/worklist`, {
      headers: { "X-Auth-Pacs": token! },
    });
    expect(worklist.status()).toBe(200);

    const profile = await page.request.get(
      `${API_BASE}/api/account/profile`,
      { headers: { "X-Auth-Pacs": token! } },
    );
    expect(profile.status()).toBe(200);
  });
});
