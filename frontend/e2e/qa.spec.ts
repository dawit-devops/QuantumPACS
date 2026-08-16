import { test, expect } from "@playwright/test";
import {
  seedQAUser,
  loginAsAdmin,
  sessionCookie,
  API_BASE,
  menuName,
} from "./helpers";

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
    // domcontentloaded, not networkidle: the QA pages keep the network busy
    // (polling / websocket), so networkidle hangs under parallel load.
    for (const route of QA_ROUTES) {
      await page.goto(route.path, { waitUntil: "domcontentloaded" });
      await expect(page).toHaveURL(route.path, { timeout: 10000 });
    }
  });

  test("QA user sees QA menu items in the sidebar", async ({ page }) => {
    // qa_officer is an unmapped slug, so workspaceFor() falls back to the
    // first permitted landing step — EXAM_READ (acquisition) precedes
    // QA_READ (qa) in the priority chain, opening the Acquisition section.
    // The QA section is still present, just closed, so expand it first.
    const queueItem = page.getByRole("menuitem", { name: menuName("QA Queue") });
    if (!(await queueItem.isVisible().catch(() => false))) {
      await page
        .getByRole("menuitem", { name: menuName("QA") })
        .first()
        .click();
    }
    // The QA workspace section groups children under the QA title, so the
    // child labels are Protocols / Incidents / Corrective Actions (d4abc25
    // workspace restructure) — not prefixed "QA …".
    for (const label of [
      "QA Queue",
      "Protocols",
      "Incidents",
      "Corrective Actions",
    ]) {
      await expect(
        page.getByRole("menuitem", { name: menuName(label) }),
      ).toBeVisible({
        timeout: 10000,
      });
    }
  });

  test("QA user is not shown admin-only menu items", async ({ page }) => {
    // the QA-officer role holds no admin-console grants, so the whole Admin section is
    // filtered out of the sidebar — the strongest form of the old
    // "admin-only items must not appear" assertion.
    await expect(
      page.getByRole("menuitem", { name: menuName("Admin") }),
    ).not.toBeVisible();
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
});

test.describe("Session Auth (real backend)", () => {
  test("API calls are authenticated for a real session", async ({ page }) => {
    // IAM audit H-2: the access token is HttpOnly-cookie-only — the browser
    // never holds a JS-readable token, and page.request shares the context
    // cookie jar. Prove BOTH sides of the contract: anonymous calls must be
    // rejected (401), and a live admin login must yield a cookie-backed
    // session that is accepted (200). Lives outside the QA describe because
    // seedQAUser's /api/** route stub would intercept the login POST.
    //
    // Negative: no cookie → 401. A bare request succeeding would mean /api/files
    // tolerates anonymous callers, which would defeat the point of auth.
    const anon = await page.request.get(`${API_BASE}/api/files`);
    expect(anon.status()).toBe(401);

    // Positive: real login sets the HttpOnly cookie, then an authenticated
    // page.request call rides the shared cookie jar.
    await loginAsAdmin(page);
    const tokenCookie = await sessionCookie(page, "token");
    expect(tokenCookie).toBeTruthy();
    expect(tokenCookie!.httpOnly).toBe(true);
    const resp = await page.request.get(`${API_BASE}/api/files`, {
      headers: { "X-CSRF-Token": "1" },
    });
    expect(resp.status()).toBe(200);
  });
});
