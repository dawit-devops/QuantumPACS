import { Page } from "@playwright/test";

// E2E_BASE_URL lets CI point at a served build; local dev reuses the vite dev
// server the playwright webServer block starts (or finds already running).
export const BASE = process.env.E2E_BASE_URL || "http://localhost:5173";
export const API_BASE = process.env.E2E_API_BASE || "http://localhost:8080";

// antd Menu items expose "icon-alt label" as their accessible name (the icon
// renders with an aria-label, e.g. "file-search Files", "user Account"), so
// exact-string role lookups never match. Build a substring regex instead.
export function menuName(label: string) {
  return new RegExp(label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
}

/**
 * End-anchored menu-name match. Sidebar items carry an icon whose aria-label
 * joins the accessible name ("lock Admin"), so exact-name locators never
 * match; the plain menuName() regex would also match same-suffix labels
 * ("Worklist" inside "Reading Worklist"). Anchoring the tail picks the
 * label while staying robust to the icon prefix — safe as long as no two
 * visible items end with the same label.
 */
export function menuNameEnd(label: string) {
  return new RegExp(label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "$");
}

/**
 * Resets storage and loads the app from a clean slate. Two-step goto because
 * the first load lets the SPA boot and hydrate before storage is cleared.
 * Also pre-seeds the onboarding tour's done-flag: the tour mounts a full-screen
 * overlay (zIndex 9999) on every page once per profile, and its fade-out keeps
 * intercepting clicks — disabling it entirely makes the suite deterministic.
 */
export async function clearAndGo(page: Page, path = "") {
  await page.goto(BASE + path, { waitUntil: "domcontentloaded" });
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
    localStorage.setItem("quantumpacs-tour-done", "true");
  });
  // domcontentloaded, not networkidle: the QA pages keep the network busy
  // (polling / websocket), so networkidle hangs under parallel load — and
  // against a built preview there is no HMR websocket to settle at all.
  await page.goto(BASE + path, { waitUntil: "domcontentloaded" });
}

/**
 * Waits for the authenticated shell: the sidebar menu is rendered only after
 * the app decides the session is valid, so a visible nav item is the cheapest
 * deterministic "we are logged in" signal (no fixed sleeps). On mobile the
 * nav lives in a closed drawer, so it is opened first when the desktop menu
 * item does not appear.
 */
export async function waitForShell(page: Page) {
  const filesItem = page.getByRole("menuitem", { name: menuName("Files") });
  try {
    await filesItem.waitFor({ state: "visible", timeout: 5000 });
  } catch {
    // Mobile: the nav lives in a closed drawer. The sidebar drawer opens via
    // "Open navigation menu"; MobileNav's bottom drawer ("Menu") shows only a
    // curated subset (no Files), so click the first — the sidebar's. Under
    // load the opener can be slow to appear, so WAIT for it (a one-shot
    // isVisible probe skipped the click entirely when it raced the boot).
    const opener = page
      .getByRole("button", { name: /Open navigation menu|Menu/ })
      .first();
    try {
      await opener.waitFor({ state: "visible", timeout: 15000 });
      await opener.click();
    } catch {
      // fall through — the shell may already be visible on desktop
    }
    await filesItem.waitFor({ state: "visible", timeout: 10000 });
  }
}

/**
 * antd mounts submenu children only while the submenu is open, and the
 * route-dependent defaultOpenKeys usually leave the target section ALREADY
 * open (e.g. the admin workspace section opens on the Files page). Clicking
 * an already-open submenu title TOGGLES it closed, so expand conditionally:
 * only click the title when the probe child is not yet visible.
 */
export async function openSubmenu(
  page: Page,
  title: string,
  probeChild: string,
) {
  // End-anchored names: sidebar labels carry an icon aria-label prefix
  // ("lock Admin"), and some share suffixes ("Worklist" vs "Reading
  // Worklist") — exact matching never finds the icon-prefixed names, while
  // the tail anchor stays unique per section.
  const child = page.getByRole("menuitem", { name: menuNameEnd(probeChild) });
  const childVisible = await child.isVisible().catch(() => false);
  if (!childVisible) {
    await page.getByRole("menuitem", { name: menuNameEnd(title) }).click();
  }
  await child.waitFor({ state: "visible", timeout: 5000 });
}

/**
 * Opens the Admin section (idempotent) and clicks one of its children.
 * .filter({ visible: true }).first() guards against a same-named item in
 * another section that happens to be expanded (e.g. Worklist also lives in
 * Acquisition).
 */
export async function openAdminItem(page: Page, name: string) {
  await openSubmenu(page, "Admin", "Users");
  await page
    .getByRole("menuitem", { name: menuNameEnd(name) })
    .filter({ visible: true })
    .first()
    .click();
}

/**
 * The MWL worklist moved out of the Admin section into the Acquisition group
 * (d4abc25 workspace restructure). Opens Acquisition and clicks its Worklist
 * child — the tail anchor skips Reading's "Reading Worklist".
 */
export async function openWorklist(page: Page) {
  await openSubmenu(page, "Acquisition", "Worklist");
  await page
    .getByRole("menuitem", { name: menuNameEnd("Worklist") })
    .filter({ visible: true })
    .click();
}

/**
 * Endpoint-keyed /api/** stub (R4-05). Boot-time calls must resolve with the
 * shape their unwrapping expects; a single blanket shape already broke once
 * (Files' fallbackToV2 object-shape vs the QA array-shape, see seedQAUser).
 * Keying by path makes the next drift surface here instead of at runtime:
 * every front-office / patient seed returns `{data, total}` (object shape)
 * for everything, with the specific list endpoints called out.
 *
 * M2: requests without a seeded session shape (userId + permissions missing
 * from localStorage) are fulfilled 401 instead of a blanket 200 — the stub
 * must not mask auth gaps by rendering a fake shell for a spec that forgot
 * to seed a session. The access token lives only in the HttpOnly `token`
 * cookie (IAM audit H-2); identity is the localStorage shape we check here.
 */
export async function stubApiRoutes(page: Page) {
  await page.route(
    (u) => u.pathname.startsWith("/api/"),
    async (route) => {
      const hasSession = await page
        .evaluate(() =>
          Boolean(
            localStorage.getItem("userId") &&
            localStorage.getItem("permissions"),
          ),
        )
        .catch(() => false);
      if (!hasSession) {
        return route.fulfill({
          status: 401,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Unauthorized" }),
        });
      }
      const path = new URL(route.request().url()).pathname;
      const keyed: Record<string, object> = {
        // R19 scope + R08 queue unwrap res.data as arrays — keep them literal.
        "/api/portal/scope": { data: [], total: 0 },
        "/api/queue": { data: [], total: 0 },
        "/api/patients/search": { data: [], total: 0 },
        "/api/visits": { data: [], total: 0 },
      };
      const body = JSON.stringify(keyed[path] ?? { data: [], total: 0 });
      route.fulfill({ status: 200, contentType: "application/json", body });
    },
  );
}

/**
 * Seeds an authenticated front-office session (receptionist) with the R08
 * grants: registration, visits, order intake,
 * consent capture, the privacy queue and schedule read/write. /api/** is
 * stubbed so the deep-link suite runs without a real backend user.
 */
export async function seedFrontDesk(
  page: Page,
  role: "receptionist" = "receptionist",
) {
  await stubApiRoutes(page);
  await page.goto(BASE, { waitUntil: "domcontentloaded" });
  await page.evaluate((r) => {
    localStorage.clear();
    sessionStorage.clear();
    localStorage.setItem("userId", "fd-1");
    localStorage.setItem("username", r);
    localStorage.setItem("admin", "false");
    localStorage.setItem("role", r);
    localStorage.setItem(
      "permissions",
      JSON.stringify([
        "REGISTRATION_READ",
        "REGISTRATION_WRITE",
        "QUEUE_READ",
        "SCHEDULE_READ",
        "SCHEDULE_WRITE",
        "WORKLIST_READ",
      ]),
    );

  }, role);
  await page.goto(BASE, { waitUntil: "domcontentloaded" });
}

/**
 * Seeds an authenticated patient session holding PORTAL_READ — the R19
 * own-data portal grant. /api/** is stubbed so the portal renders its
 * empty scope state without a real backend patient.
 */
export async function seedPatient(page: Page) {
  await stubApiRoutes(page);
  await page.goto(BASE, { waitUntil: "domcontentloaded" });
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
    localStorage.setItem("userId", "pat-1");
    localStorage.setItem("username", "patient");
    localStorage.setItem("admin", "false");
    localStorage.setItem("role", "patient");
    localStorage.setItem("permissions", JSON.stringify(["PORTAL_READ"]));

  });
  await page.goto(BASE, { waitUntil: "domcontentloaded" });
}

export async function loginAsAdmin(page: Page) {
  const { username, password } = adminCredentials();
  await loginAs(page, username, password);
}

/** Admin credentials: CI exports E2E_ADMIN_PASS from the seeded SUPERADMIN_PASS
 * (ci.yml), a direct SUPERADMIN_PASS env covers standalone stacks, and
 * pa55w0rd is the default superadmin pass of dev configs. */
export function adminCredentials() {
  return {
    username: process.env.E2E_ADMIN_USER || "admin",
    password:
      process.env.E2E_ADMIN_PASS || process.env.SUPERADMIN_PASS || "pa55w0rd",
  };
}

/** Real login via the UI (used when the test hits the live backend). */
export async function loginAs(page: Page, username: string, password: string) {
  await clearAndGo(page);
  await page.getByPlaceholder("Username").fill(username);
  await page.getByPlaceholder("Password").fill(password);
  await page.getByRole("button", { name: /sign in/i }).click();
  await waitForShell(page);
}

/**
 * Reads one session cookie (token / refresh_token) for the API host. IAM
 * audit H-2: the access token is HttpOnly-cookie-only — Playwright's CDP can
 * read HttpOnly cookies (page JS cannot), so specs assert the cookie channel
 * instead of localStorage. The refresh cookie is scoped to /api/auth while
 * the access cookie sits at /, so the probe URL must match the narrower
 * scope. Returns undefined when absent.
 */
export async function sessionCookie(
  page: Page,
  name: "token" | "refresh_token",
) {
  const cookies = await page.context().cookies(`${API_BASE}/api/auth`);
  return cookies.find((c) => c.name === name);
}

/**
 * Seeds an authenticated, non-admin technologist session directly in localStorage
 * (the same keys AuthContext reads on boot) and stubs every /api/** request so the
 * fake token can never 401-bounce to /login — which would mask the PermissionRoute
 * redirect we are asserting. Lets the deep-link denial suite run without a real
 * technologist user in the backend. WORKLIST grants are included so the MWL
 * Worklist surface (Acquisition workspace) renders for specs that navigate to it.
 */
export async function seedTechnologist(page: Page) {
  await page.route(
    (u) => u.pathname.startsWith("/api/"),
    (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        // Envelope shape: list pages read res.data / res.total; a bare [] makes
        // Files.tsx crash (data.data is undefined) when the technologist
        // landing renders before any navigation.
        body: JSON.stringify({ data: [], total: 0 }),
      }),
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
      JSON.stringify([
        "FILE_READ",
        "STUDY_READ",
        "PATIENT_READ",
        "WORKLIST_READ",
        "WORKLIST_WRITE",
      ]),
    );

  });
  await page.goto(BASE, { waitUntil: "domcontentloaded" });
}

/**
 * Seeds an authenticated nurse session (clinical role, acquisition surface):
 * study reads + EXAM_READ + WORKLIST_READ, no admin-console grants. Proves
 * clinical roles are bounced from admin surfaces (DICOMweb console) and land
 * on their acquisition workspace instead.
 */
export async function seedAcquisitionTechnologist(page: Page) {
  await page.route(
    (u) => u.pathname.startsWith("/api/"),
    (route) => {
      const body = JSON.stringify({ data: [], total: 0 });
      route.fulfill({ status: 200, contentType: "application/json", body });
    },
  );
  await page.goto(BASE, { waitUntil: "domcontentloaded" });
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
    localStorage.setItem("userId", "tech-acq-1");
    localStorage.setItem("username", "technologist");
    localStorage.setItem("admin", "false");
    localStorage.setItem("role", "technologist");
    localStorage.setItem(
      "permissions",
      JSON.stringify([
        "FILE_READ",
        "PATIENT_READ",
        "STUDY_READ",
        "EXAM_READ",
        "WORKLIST_READ",
      ]),
    );

  });
  await page.goto(BASE, { waitUntil: "domcontentloaded" });
}

/**
 * Seeds a physician holding only the legacy DICOMWEB_READ grant — the exact
 * shape of the pre-scope bug where clinical roles with a leftover grant landed
 * on the admin DICOMweb console. The console must bounce them to /account
 * (no REPORT_READ means no clinical surface either).
 */
export async function seedPhysicianLegacy(page: Page) {
  await page.route(
    (u) => u.pathname.startsWith("/api/"),
    (route) => {
      const body = JSON.stringify({ data: [], total: 0 });
      route.fulfill({ status: 200, contentType: "application/json", body });
    },
  );
  await page.goto(BASE, { waitUntil: "domcontentloaded" });
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
    localStorage.setItem("userId", "phys-1");
    localStorage.setItem("username", "physician");
    localStorage.setItem("admin", "false");
    localStorage.setItem("role", "physician");
    localStorage.setItem("permissions", JSON.stringify(["DICOMWEB_READ"]));

  });
  await page.goto(BASE, { waitUntil: "domcontentloaded" });
}

/**
 * Seeds a pacs_admin holding only clinical grants (REPORT_READ) — the inverse
 * drift: an admin-scoped role that must never open the reading worklist even
 * when its permission set contains the clinical grant.
 */
export async function seedPacsAdminClinical(page: Page) {
  await page.route(
    (u) => u.pathname.startsWith("/api/"),
    (route) => {
      const body = JSON.stringify({ data: [], total: 0 });
      route.fulfill({ status: 200, contentType: "application/json", body });
    },
  );
  await page.goto(BASE, { waitUntil: "domcontentloaded" });
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
    localStorage.setItem("userId", "pacsadm-1");
    localStorage.setItem("username", "pacs_admin");
    localStorage.setItem("admin", "false");
    localStorage.setItem("role", "pacs_admin");
    localStorage.setItem("permissions", JSON.stringify(["REPORT_READ"]));

  });
  await page.goto(BASE, { waitUntil: "domcontentloaded" });
}

/**
 * Seeds an authenticated QA session directly in localStorage with the same
 * permission set the retired `qa_team` built-in carried (read-only clinical
 * access + QA_WRITE + PROTOCOL_MANAGE), and stubs /api/** so the fake token
 * never 401-bounces. Lets the QA workflow suite assert menu visibility, page
 * loading, and route gating without a real QA user in the backend — QA
 * coverage is granted via facility custom roles (R2-16), represented here by
 * the custom `qa_officer` slug.
 */
export async function seedQAUser(page: Page) {
  await page.route(
    (u) => u.pathname.startsWith("/api/"),
    (route) => {
      // Files.tsx's fallbackToV2 reads res.data / res.total (object shape); the
      // QA list endpoints read res.data as an array. A bare '[]' would set
      // res.data to undefined and crash Files on boot, so return an object.
      const body = JSON.stringify({ data: [], total: 0 });
      route.fulfill({ status: 200, contentType: "application/json", body });
    },
  );
  await page.goto(BASE, { waitUntil: "domcontentloaded" });
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
    localStorage.setItem("userId", "qa-1");
    localStorage.setItem("username", "qa_officer");
    localStorage.setItem("admin", "false");
    localStorage.setItem("role", "qa_officer");
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

  });
  await page.goto(BASE, { waitUntil: "domcontentloaded" });
}

/**
 * Seeds an authenticated audit-only session (AUDIT_READ but no LOG_READ) —
 * the shape of emr_admin. Validates the dual-permission /logs gate
 * (LOG_READ | AUDIT_READ) end to end.
 */
export async function seedAuditOnlyUser(page: Page) {
  await page.route(
    (u) => u.pathname.startsWith("/api/"),
    (route) => {
      const body = JSON.stringify({ data: [], total: 0 });
      route.fulfill({ status: 200, contentType: "application/json", body });
    },
  );
  await page.goto(BASE, { waitUntil: "domcontentloaded" });
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
    localStorage.setItem("userId", "audit-1");
    localStorage.setItem("username", "audit_viewer");
    localStorage.setItem("admin", "false");
    localStorage.setItem("role", "emr_admin");
    localStorage.setItem(
      "permissions",
      JSON.stringify([
        "FILE_READ",
        "PATIENT_READ",
        "STUDY_READ",
        "REPORT_READ",
        "AUDIT_READ",
      ]),
    );

  });
  await page.goto(BASE, { waitUntil: "domcontentloaded" });
}
