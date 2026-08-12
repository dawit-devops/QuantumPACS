import { test, expect, type Page } from "@playwright/test";
import { loginAs, sessionCookie, API_BASE, BASE, menuName } from "./helpers";

// End-to-end verification of the IAM audit (docs/iam-audit.md) fixes:
//   H-2  the access token is HttpOnly-cookie-only in the browser — nothing
//        token-shaped may ever land in localStorage/sessionStorage, API calls
//        attach no JS-readable auth header, and the refresh endpoint rotates
//        the access cookie.
//   M-5  the refresh response body still carries the token (API clients), but
//        the frontend must never persist it.
//   WS   the websocket handshake authenticates via the cookie (ws_token
//        minting) and connects.
//   WADO the detail viewer fetches pixel payloads through the cookie (the
//        token cookie is set at path "/" so /dicomweb and /files/{id}/data —
//        outside /api — stay authenticated).
// Logout must clear both session cookies.
test.describe("IAM cookie channel (real backend)", () => {
  const USER = "test.radiologist";
  const PASS = "Test@123456";

  test.beforeEach(async ({ page }) => {
    // No session may leak into a test that asserts anonymous rejection.
    await page.context().clearCookies();
  });

  test("login stores tokens in HttpOnly cookies, never in JS storage", async ({
    page,
  }) => {
    await loginAs(page, USER, PASS);

    const token = await sessionCookie(page, "token");
    const refresh = await sessionCookie(page, "refresh_token");

    // The session is cookie-bound: HttpOnly (xss-immune), path / (covers
    // /dicomweb outside /api), Strict same-site (CSRF-hardened).
    expect(token).toBeTruthy();
    expect(token!.httpOnly).toBe(true);
    expect(token!.path).toBe("/");
    expect(token!.sameSite).toBe("Strict");
    expect(refresh).toBeTruthy();
    expect(refresh!.httpOnly).toBe(true);

    // No token-shaped value anywhere JS can read.
    const storage = await page.evaluate(() => ({
      lsKeys: Object.keys(localStorage),
      ssKeys: Object.keys(sessionStorage),
      access: localStorage.getItem("access_token"),
      refresh: localStorage.getItem("refresh_token"),
      sessionAccess: sessionStorage.getItem("access_token"),
    }));
    expect(storage.access).toBeNull();
    expect(storage.refresh).toBeNull();
    expect(storage.sessionAccess).toBeNull();
    expect(storage.lsKeys).not.toContain("access_token");
    expect(storage.lsKeys).not.toContain("refresh_token");
    expect(storage.ssKeys).not.toContain("access_token");
    // Identity metadata only — the app gates the shell on userId.
    expect(storage.lsKeys).toContain("userId");
  });

  test("anonymous API calls are rejected 401", async ({ page }) => {
    const anon = await page.request.get(`${API_BASE}/api/files`);
    expect(anon.status()).toBe(401);
  });

  test("failed login leaves no session cookies and stays on /login", async ({
    page,
  }) => {
    await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" });
    await page.getByPlaceholder("Username").fill(USER);
    await page.getByPlaceholder("Password").fill("wrong-password");
    await page.getByRole("button", { name: /sign in/i }).click();

    await expect(page).toHaveURL(/\/login/, { timeout: 15000 });
    await expect(
      page.getByText(/invalid credentials|incorrect|failed/i),
    ).toBeVisible({
      timeout: 10000,
    });
    expect(await sessionCookie(page, "token")).toBeUndefined();
    expect(await sessionCookie(page, "refresh_token")).toBeUndefined();
    expect(
      await page.evaluate(() => localStorage.getItem("access_token")),
    ).toBeNull();
  });

  test("page API calls authenticate via cookie — no JS-readable auth header", async ({
    page,
  }) => {
    // Watch a real app request (the boot-time notifications poll) after login.
    let bootRequest: string | null = null;
    let hadAuthHeader = false;
    let hadCookie = false;
    await page
      .context()
      .route("**/api/notifications/unread-count", async (route) => {
        const req = route.request();
        bootRequest = req.url();
        const headers = req.headers();
        hadAuthHeader = headers["x-auth-pacs"] !== undefined;
        hadCookie = (headers["cookie"] || "").includes("token=");
        await route.continue();
      });

    await loginAs(page, USER, PASS);

    expect(bootRequest).toBeTruthy();
    expect(hadCookie).toBe(true);
    expect(hadAuthHeader).toBe(false);
  });

  test("refresh rotates the access cookie and never touches JS storage", async ({
    page,
  }) => {
    await loginAs(page, USER, PASS);
    const before = await sessionCookie(page, "token");
    const refreshBefore = await sessionCookie(page, "refresh_token");
    expect(before).toBeTruthy();

    // Same-site cross-origin fetch — exactly what the SPA does on the timer.
    const resp = await page.evaluate(
      async (apiBase) => {
        const r = await fetch(`${apiBase}/api/auth/refresh`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
        });
        return { status: r.status, body: await r.json() };
      },
      API_BASE,
    );
    expect(resp.status).toBe(200);
    // M-5: the refresh body still carries the access token for API clients —
    // the browser must not persist it.
    expect(resp.body.access_token).toBeTruthy();

    // Both session cookies rotate on refresh (create_token_pair mints a new
    // access AND refresh JWT; the frontend picks the new access cookie up
    // transparently).
    const after = await sessionCookie(page, "token");
    const refreshAfter = await sessionCookie(page, "refresh_token");
    expect(after!.value).not.toBe(before!.value);
    expect(refreshAfter!.value).not.toBe(refreshBefore!.value);

    // Still nothing token-shaped in JS storage after the rotation.
    const storage = await page.evaluate(() => ({
      access: localStorage.getItem("access_token"),
      refresh: localStorage.getItem("refresh_token"),
    }));
    expect(storage.access).toBeNull();
    expect(storage.refresh).toBeNull();

    // The rotated cookie keeps the session valid.
    const files = await page.request.get(`${API_BASE}/api/files`);
    expect(files.status()).toBe(200);
  });

  test("websocket handshake authenticates via the cookie and connects", async ({
    page,
  }) => {
    const wsUrls: string[] = [];
    let wsTokenStatus = 0;
    page.on("websocket", (ws) => wsUrls.push(ws.url()));
    page.on("response", (resp) => {
      if (resp.url().includes("/api/ws_token")) wsTokenStatus = resp.status();
    });

    await loginAs(page, USER, PASS);

    // ws_token minting requires the cookie-authenticated session.
    await expect.poll(() => wsTokenStatus, { timeout: 15000 }).toBe(200);
    // The handshake rides the short-lived one-shot ws_token in the query.
    await expect
      .poll(() => wsUrls.length, { timeout: 15000 })
      .toBeGreaterThan(0);
    expect(wsUrls[0]).toContain("token=");
  });

  test("viewer fetches pixels through the cookie (path /) — no 401s", async ({
    page,
  }) => {
    await loginAs(page, USER, PASS);

    // Pick the seeded DICOM known to carry pixel data (smoke set), fall back
    // to the first file row otherwise.
    const list = await page.request.get(`${API_BASE}/api/files`);
    expect(list.status()).toBe(200);
    const files = ((await list.json())?.data ?? []) as Array<{ id: number }>;
    test.skip(
      files.length === 0,
      "no file records — seed the smoke set (E2E-FIXTURE-CT-001.dcm) for this spec",
    );
    const target = files.find((f) => f.id === 14) ?? files[0];

    const pixelStatuses: number[] = [];
    page.on("response", (resp) => {
      const url = resp.url();
      if (
        (url.includes(`/files/${target.id}/data`) ||
          url.includes("/dicomweb/")) &&
        resp.request().method() === "GET"
      ) {
        pixelStatuses.push(resp.status());
      }
    });

    await page.goto(`${BASE}/files/${target.id}`, {
      waitUntil: "domcontentloaded",
    });

    // The viewer surface mounts and attempts the pixel fetch.
    const viewport = page.locator(".viewportElement");
    await expect(viewport).toBeVisible({ timeout: 15000 });
    await expect
      .poll(() => pixelStatuses.length, { timeout: 20000 })
      .toBeGreaterThan(0);
    // The cookie channel must never 401 — an unauthenticated pixel fetch is
    // the exact regression H-2 guards against.
    expect(pixelStatuses.every((s) => s !== 401)).toBe(true);
    // File 14 (CT_small.dcm) has pixels: the readout must go live.
    if (target.id === 14) {
      await expect(viewport).toContainText(/WW\/WC: [1-9]\d* \/ \d+/, {
        timeout: 20000,
      });
    }
  });

  test("logout clears the session cookies", async ({ page }) => {
    await loginAs(page, USER, PASS);
    expect(await sessionCookie(page, "token")).toBeTruthy();

    await page.getByRole("menuitem", { name: menuName("Logout") }).click();
    await expect(page).toHaveURL(/\/login/, { timeout: 15000 });

    expect(await sessionCookie(page, "token")).toBeUndefined();
    expect(await sessionCookie(page, "refresh_token")).toBeUndefined();
    // Boot-time state cleared too — no half-session on the login page.
    const storage = await page.evaluate(() => localStorage.getItem("userId"));
    expect(storage).toBeNull();
  });
});
