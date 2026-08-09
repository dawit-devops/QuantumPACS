import { test, expect } from "@playwright/test";
import { seedQAUser, BASE } from "./helpers";

test.describe("STOW-RS Upload", () => {
  test.beforeEach(async ({ page }) => {
    // QA carries DICOMWEB_READ, which gates the /dicomweb/store route; the
    // seeded session also stubs /api/** so the fake token never 401-bounces.
    await seedQAUser(page);
  });

  test("store page renders with dropzone and submit action", async ({
    page,
  }) => {
    await page.goto(`${BASE}/dicomweb/store`, {
      waitUntil: "domcontentloaded",
    });
    await expect(page.getByText("Store Studies (STOW-RS)")).toBeVisible({
      timeout: 10000,
    });
    await expect(
      page.getByRole("button", { name: "Select DICOM files to store" }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /store to pacs/i }),
    ).toBeVisible();
  });

  test("selecting a DICOM file lists it for upload", async ({ page }) => {
    await page.goto(`${BASE}/dicomweb/store`, {
      waitUntil: "domcontentloaded",
    });
    // StowUpload does not parse DICOM content client-side — it only lists the
    // selected files, so a magic-prefixed dummy buffer is a valid fixture.
    const dummyDcm = Buffer.concat([
      Buffer.alloc(128),
      Buffer.from("DICM", "ascii"),
    ]);
    await page.setInputFiles("#stow-file-input", {
      name: "e2e-sample.dcm",
      mimeType: "application/dicom",
      buffer: dummyDcm,
    });
    await expect(page.getByText("e2e-sample.dcm")).toBeVisible({
      timeout: 5000,
    });
    await expect(
      page.getByRole("button", { name: /store to pacs/i }),
    ).toBeEnabled();
  });
});
