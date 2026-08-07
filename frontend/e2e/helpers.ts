import { Page } from "@playwright/test";

export const BASE = "http://localhost:5173";

export async function clearAndGo(page: Page, path = "") {
  await page.goto(BASE + path, { waitUntil: "domcontentloaded" });
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
  await page.goto(BASE + path, { waitUntil: "networkidle" });
}

export async function loginAsAdmin(page: Page) {
  await clearAndGo(page);
  await page.getByPlaceholder("Username").fill("admin");
  await page.getByPlaceholder("Password").fill("pa55w0rd");
  await page.getByRole("button", { name: /sign in/i }).click();
  // super_admin lands on the role-scoped platform workspace (/users) since the
  // navigator change, not the files page — wait for the authenticated shell
  // (sidebar) instead of a files-page string.
  await page.locator(".ant-layout-sider").first().waitFor({ state: "visible", timeout: 30000 });
  // The onboarding tour mounts at App level and covers every route with a
  // full-screen overlay (zIndex 9999) until dismissed once per browser profile
  // — dismiss it so specs can click through the UI on any page.
  const tourDismiss = page.getByRole("button", { name: "Dismiss tour" });
  await tourDismiss.waitFor({ state: "visible", timeout: 3000 }).catch(() => {});
  if (await tourDismiss.isVisible().catch(() => false)) {
    await tourDismiss.click();
  }
  await page.waitForTimeout(2000);
}

/**
 * Seeds an authenticated, non-admin technologist session directly in localStorage
 * (the same keys AuthContext reads on boot) and stubs every /api/** request so the
 * fake token can never 401-bounce to /login — which would mask the PermissionRoute
 * redirect we are asserting. Lets the deep-link denial suite run without a real
 * technologist user in the backend.
 */
export async function seedTechnologist(page: Page) {
  await page.route("**/api/**", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: "[]" }),
  );
  await page.goto(BASE, { waitUntil: "domcontentloaded" });
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
    localStorage.setItem("userId", "tech-1");
    localStorage.setItem("username", "technician");
    localStorage.setItem("admin", "false");
    localStorage.setItem("role", "technologist");
    localStorage.setItem(
      "permissions",
      JSON.stringify(["FILE_READ", "STUDY_READ", "PATIENT_READ"]),
    );
    localStorage.setItem("access_token", "e2e-technologist-token");
    localStorage.setItem("refresh_token", "e2e-technologist-token");
  });
  await page.goto(BASE, { waitUntil: "domcontentloaded" });
}

/**
 * Seeds an authenticated QA Team session directly in localStorage with the same
 * permission set as the backend `qa_team` built-in role (read-only clinical
 * access + QA_WRITE + PROTOCOL_MANAGE), and stubs /api/** so the fake token
 * never 401-bounces. Lets the QA workflow suite assert menu visibility, page
 * loading, and route gating without a real qa_team user in the backend.
 */
export async function seedQAUser(page: Page) {
  await page.route("**/api/**", (route) => {
    // Files.tsx's fallbackToV2 reads res.data / res.total (object shape); the
    // QA list endpoints read res.data as an array. A bare '[]' would set
    // res.data to undefined and crash Files on boot, so return an object.
    const body = JSON.stringify({ data: [], total: 0 });
    route.fulfill({ status: 200, contentType: "application/json", body });
  });
  await page.goto(BASE, { waitUntil: "domcontentloaded" });
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
    localStorage.setItem("userId", "qa-1");
    localStorage.setItem("username", "qa_officer");
    localStorage.setItem("admin", "false");
    localStorage.setItem("role", "qa_team");
    localStorage.setItem(
      "permissions",
      JSON.stringify([
        "FILE_READ",
        "PATIENT_READ",
        "STUDY_READ",
        "EXAM_READ",
        "QA_READ",
        "QA_WRITE",
        "PROTOCOL_MANAGE",
        "PEER_REVIEW_READ",
        "PEER_REVIEW_WRITE",
        "DICOMWEB_READ",
        "METRICS_READ",
      ]),
    );
    localStorage.setItem("access_token", "e2e-qa-token");
    localStorage.setItem("refresh_token", "e2e-qa-token");
  });
  await page.goto(BASE, { waitUntil: "domcontentloaded" });
}
