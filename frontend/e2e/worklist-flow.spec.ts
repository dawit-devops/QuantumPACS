import { test, expect } from "@playwright/test";
import { loginAs, API_BASE, openWorklist } from "./helpers";

test.describe("Worklist Flow (real backend)", () => {
  test.beforeEach(async ({ page }) => {
    // The create/delete cycle writes real rows, so it runs against the live
    // backend as the seeded technologist (WORKLIST_READ + WORKLIST_WRITE).
    // Admin cannot reach /worklist (Acquisition workspace, clinical-only).
    await loginAs(page, "test.technologist", "Test@123456");
  });

  test("creates a worklist entry via the UI and cancels it via the API", async ({
    page,
  }) => {
    const patientId = `E2E-FLOW-${Date.now()}`;

    await openWorklist(page);
    await expect(
      page.getByRole("button", { name: "Create worklist entry" }),
    ).toBeVisible({ timeout: 10000 });

    await page.getByRole("button", { name: "Create worklist entry" }).click();
    const dialog = page.getByRole("dialog", { name: "Create Worklist Entry" });
    await expect(dialog).toBeVisible({ timeout: 5000 });

    await dialog.getByPlaceholder("e.g., PAT-00123").fill(patientId);
    await dialog.getByPlaceholder("Last^First Middle").fill("E2E^Flow Patient");
    await dialog.getByPlaceholder("e.g., ACC-98765").fill(`ACC-${Date.now()}`);
    // antd v6 Selects are native combobox inputs with no [placeholder]
    // attribute and plain-text dropdown options — drive them by typing and
    // Enter (showSearch filters, tags mode creates the tag directly).
    await dialog
      .locator(".ant-form-item")
      .filter({ hasText: "Modality" })
      .locator(".ant-select-input")
      .click();
    await page.keyboard.type("CT");
    await page.keyboard.press("Enter");
    await dialog
      .locator(".ant-form-item")
      .filter({ hasText: "Station AE Title" })
      .locator(".ant-select-input")
      .click();
    await page.keyboard.type("CT_ROOM_1");
    await page.keyboard.press("Enter");

    await dialog.getByRole("button", { name: "OK" }).click();

    // The table refreshes after create; the new row's patient id proves the
    // entry landed (the POST response carries the id, but the UI only shows
    // the row — look it up via the API afterwards for cleanup).
    await expect(
      page.locator(".ant-table").getByText(patientId).first(),
    ).toBeVisible({ timeout: 15000 });

    // Cleanup: find the created entry and cancel it through the API so the
    // dev database does not accumulate E2E rows.
    const token = await page.evaluate(() =>
      localStorage.getItem("access_token"),
    );
    expect(token).toBeTruthy();
    const listResp = await page.request.get(`${API_BASE}/api/worklist`, {
      headers: { "X-Auth-Pacs": token! },
    });
    expect(listResp.status()).toBe(200);
    const { data } = await listResp.json();
    const entry = data.find(
      (e: { patient_id: string }) => e.patient_id === patientId,
    );
    expect(entry).toBeTruthy();

    const delResp = await page.request.delete(
      `${API_BASE}/api/worklist/${entry.id}`,
      {
        headers: { "X-Auth-Pacs": token!, "X-CSRF-Token": "1" },
      },
    );
    expect(delResp.status()).toBe(200);
  });
});
