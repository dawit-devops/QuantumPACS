import { test, expect } from "@playwright/test";
import {
  loginAsAdmin,
  adminCredentials,
  sessionCookie,
  API_BASE,
  BASE,
} from "./helpers";

// Patient-portal coverage against the REAL backend (Portal.test.tsx is mocked
// and share-link.spec.ts never opens a real share). The share lifecycle — the
// data path the portal viewer depends on — is exercised end-to-end: admin
// creates a share for a seeded record, the key roundtrips, the link boots
// the share session, and logging in afterwards renders the shared record in
// the share view (M9). Requires at least one file record: the CI e2e job
// seeds E2E-FIXTURE-CT-001.dcm; local runs skip with an explicit message.
test.describe("Patient portal share flow (real backend)", () => {
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

  function escapeRe(s: string) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  test("shares a file record via the API and revokes it again", async ({
    page,
  }) => {
    await loginAsAdmin(page);
    expect(await sessionCookie(page, "token")).toBeTruthy();

    const file = await pickFile(page);
    expect(file.id).toBeTruthy();

    // Create the share (POST /api/files/{id}/share, duration in seconds).
    const share = await page.request.post(
      `${API_BASE}/api/files/${file.id}/share`,
      {
        headers: { "X-CSRF-Token": "1" },
        data: { duration: 60 },
      },
    );
    expect(share.status()).toBe(200);
    const { key } = await share.json();
    expect(key).toBeTruthy();

    // The record's share list now exposes the active link (the endpoint
    // returns the bare array, not a {data} envelope).
    const listResp = await page.request.get(
      `${API_BASE}/api/files/${file.id}/shares`,
    );
    expect(listResp.status()).toBe(200);
    const shares = await listResp.json();
    expect(shares.some((s: { active: boolean }) => s.active)).toBe(true);

    // Revoke the share so the dev database does not accumulate links.
    const shareId = shares[0].id;
    const delResp = await page.request.delete(
      `${API_BASE}/api/files/${file.id}/shares/${shareId}`,
      { headers: { "X-CSRF-Token": "1" } },
    );
    expect(delResp.status()).toBe(200);
  });

  test("share link boots the session and the record renders post-login", async ({
    page,
  }) => {
    await loginAsAdmin(page);
    expect(await sessionCookie(page, "token")).toBeTruthy();

    const file = await pickFile(page);
    const share = await page.request.post(
      `${API_BASE}/api/files/${file.id}/share`,
      {
        headers: { "X-CSRF-Token": "1" },
        data: { duration: 60 },
      },
    );
    expect(share.status()).toBe(200);
    const { key } = await share.json();

    // Open the share link in a fresh context (no admin session): ShareView
    // stashes the key in sessionStorage and hands off to the app shell. The
    // session must boot without the "expired or invalid" share error.
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await page.goto(`${BASE}/view/${key}`, { waitUntil: "domcontentloaded" });
    await expect(page).toHaveURL(/\/login/, { timeout: 15000 });
    expect(await page.evaluate(() => sessionStorage.getItem("tempKey"))).toBe(
      key,
    );
    await expect(page.getByText(/expired or is invalid/)).not.toBeVisible();

    // M9 patient-side loop: log in WITHOUT clearing storage so the share key
    // survives, then open the shared record — it must render in the share
    // view (Detail with tempKey set suppresses the admin sidebar).
    const creds = adminCredentials();
    await page.getByPlaceholder("Username").fill(creds.username);
    await page.getByPlaceholder("Password").fill(creds.password);
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page).not.toHaveURL(/\/login/, { timeout: 15000 });
    expect(await page.evaluate(() => sessionStorage.getItem("tempKey"))).toBe(
      key,
    );
    await page.goto(`${BASE}/files/${file.id}`, {
      waitUntil: "domcontentloaded",
    });
    await expect(
      page.getByText(new RegExp(`File ${escapeRe(file.name)}`)).first(),
    ).toBeVisible({ timeout: 15000 });
    // Share view: the admin sidebar stays hidden while tempKey is present.
    await expect(
      page.getByRole("menuitem", { name: /Files/ }).first(),
    ).not.toBeVisible({ timeout: 10000 });
  });
});
