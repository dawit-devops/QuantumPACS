import { test, expect } from "@playwright/test";
import {
  loginAsAdmin,
  sessionCookie,
  menuName,
  API_BASE,
  BASE,
} from "./helpers";

// E2E-6: viewer state survives in-page navigation. The Study Viewer keeps
// CornerstoneElement mounted when the user switches to the Data/Share tabs
// (the `visible` prop only toggles display), so zoom/window-level state is
// preserved — the viewer must never re-fetch the pixel payload on tab
// roundtrips. Runs against the REAL backend and seeded file record like
// portal-share.spec.ts; the pixel data may be absent in CI (the fixture is a
// DB row only, `indexed: false`), so assertions must not require the image
// to render — the /data fetch attempt is the observable contract.
test.describe("Study Viewer state", () => {
  // IAM H-2: page.request shares the login cookie — no token plumbing.
  async function pickFile(page: { request: any }) {
    const list = await page.request.get(`${API_BASE}/api/files`);
    expect(list.status()).toBe(200);
    const body = await list.json();
    const files = body?.data ?? [];
    test.skip(
      files.length === 0,
      "no seeded file record — the CI e2e job seeds E2E-FIXTURE-CT-001.dcm; " +
        "local dev needs at least one row in the files table for this spec to run",
    );
    return files[0];
  }

  test("viewer stays mounted across tab switches — pixel payload fetched once", async ({
    page,
  }) => {
    await loginAsAdmin(page);
    expect(await sessionCookie(page, "token")).toBeTruthy();
    const file = await pickFile(page);
    expect(file.id).toBeTruthy();

    let dataRequests = 0;
    page.on("request", (req) => {
      if (req.url().includes(`/files/${file.id}/data`)) dataRequests += 1;
    });

    await page.goto(`${BASE}/files/${file.id}`, {
      waitUntil: "domcontentloaded",
    });
    await expect(
      page.getByText(new RegExp(`File ${file.name}`)).first(),
    ).toBeVisible({ timeout: 15000 });

    // Viewer surface (image tab): the cornerstone element is mounted.
    const viewport = page.locator(".viewportElement");
    await expect(viewport).toBeVisible({ timeout: 15000 });
    await expect(viewport).toHaveCount(1);
    const afterLoad = dataRequests;

    // Switch to the Data tab: the viewer must stay in the DOM (mounted,
    // hidden via display:none) — unmounting would reset zoom/WL state.
    await page.getByRole("menuitem", { name: menuName("Data") }).click();
    await expect(viewport).toHaveCount(1);
    await expect(viewport).not.toBeVisible();
    // Data tab content: KeyValueTable with its tag-filter search input is the
    // stable marker (works for records with any DICOM metadata, or none).
    await expect(page.getByPlaceholder("Search...")).toBeVisible();

    // Back to the Image tab: same mounted element reappears without any
    // re-fetch of the pixel payload (state preserved, no remount).
    await page.getByRole("menuitem", { name: menuName("Image") }).click();
    await expect(viewport).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(800);
    expect(dataRequests).toBe(afterLoad);
  });
});
