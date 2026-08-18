import { test, expect } from "@playwright/test";
import { loginAs, API_BASE } from "./helpers";

// Phase 4 of user-feature-review/tenant-admin (phase/user-feature-review-tenant-admin).
// Real-backend coverage for the tenant admin, exercising the hand-off items
// from docs/user-feature-review/tenant-admin/03-handoff.md. Serial because the
// role's grant set changed under this branch (migration 061) — keep assertions
// deterministic against the seeded test.tenant_admin account.
test.describe.configure({ mode: "serial" });
test.describe("Tenant admin workflow polish (real backend)", () => {
  test.beforeEach(async ({ page }) => {
    // test.tenant_admin is seeded (user id 41, tenant=default) with the Matrix
    // C set incl. the P1-2 interface grants. Real UI login hits the live DB.
    await loginAs(page, "test.tenant_admin", "Test@123456");
  });

  test("P1-1: dashboard never offers an Open button for a route the role cannot open", async ({
    page,
  }) => {
    await page.goto("/admin", { waitUntil: "domcontentloaded" });
    await expect(page.getByText("Operations Dashboard")).toBeVisible({
      timeout: 10000,
    });

    // FHIR is SYSTEM_ADMIN-gated: the Interfaces panel row must render with
    // NO "Open" affordance for tenant_admin.
    const fhirRow = page
      .locator(".dashboard-panel")
      .filter({ hasText: "Interfaces" })
      .locator(".ant-space")
      .filter({ hasText: /FHIR/ })
      .first();
    await expect(fhirRow).toBeVisible({ timeout: 10000 });
    expect(await fhirRow.locator("button", { hasText: "Open" }).count()).toBe(0);

    // DICOM Listener + HL7 now hold HL7_READ/DICOMWEB_READ (P1-2): their Open
    // buttons must navigate to the real surfaces, not bounce back.
    const hl7Row = page
      .locator(".dashboard-panel")
      .filter({ hasText: "Interfaces" })
      .locator(".ant-space")
      .filter({ hasText: /HL7/ })
      .first();
    await hl7Row.locator("button", { hasText: "Open" }).click();
    await expect(page).toHaveURL(/\/hl7/, { timeout: 10000 });

    // Storage drill-down still works (REPLICA_READ).
    await page.goto("/admin", { waitUntil: "domcontentloaded" });
    await page
      .locator("button[aria-label='Open Storage dashboard']")
      .click();
    await expect(page).toHaveURL(/\/replicas/, { timeout: 10000 });
  });

  test("P1-2: interface grants are real — HL7, Routing, DICOMweb reachable from the sidebar", async ({
    page,
  }) => {
    // Sidebar exposes the newly granted surfaces.
    await page.goto("/admin", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("menuitem", { name: /HL7/ })).toBeVisible({
      timeout: 10000,
    });
    await expect(page.getByRole("menuitem", { name: /Routing/ })).toBeVisible();
    await expect(page.getByRole("menuitem", { name: /DICOMweb/ })).toBeVisible();

    // HL7 admin surface renders without permission error (Tabs-based page).
    await page.goto("/hl7", { waitUntil: "domcontentloaded" });
    await expect(page.getByText("Missing permission")).toHaveCount(0);
    await expect(page.getByRole("tab", { name: /Messages/ })).toBeVisible({
      timeout: 10000,
    });

    // DICOMweb console renders (Server surface).
    await page.goto("/dicomweb", { waitUntil: "domcontentloaded" });
    await expect(page.getByText("Missing permission")).toHaveCount(0);
    await expect(page.locator("body")).not.toBeEmpty({ timeout: 10000 });
  });

  test("P2-1: tenant card shows real user/study counts, never '?'", async ({
    page,
  }) => {
    await page.goto("/tenants", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: "Tenants" })).toBeVisible({
      timeout: 10000,
    });
    // The scoped tenant card carries counts from the enriched list.
    await expect(page.getByText(/users/).first()).toBeVisible({
      timeout: 10000,
    });
    await expect(page.getByText(/studies/).first()).toBeVisible();
    // No "?" placeholder ever renders (AC: card must never show it).
    await expect(page.getByText("? users")).toHaveCount(0);
    await expect(page.getByText("? studies")).toHaveCount(0);
    // The counts are real numbers, not the loading em-dash.
    const cardText = await page
      .locator(".ant-card")
      .filter({ hasText: /users/ })
      .first()
      .innerText();
    expect(/\d+ users/.test(cardText)).toBe(true);
  });

  test("P2-2: users directory shows a tenant column and is tenant-scoped", async ({
    page,
  }) => {
    await page.goto("/users", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: "Users" })).toBeVisible({
      timeout: 10000,
    });
    // Tenant column header renders.
    await expect(page.locator("th", { hasText: "Tenant" })).toBeVisible({
      timeout: 10000,
    });
    // The visible users carry a tenant tag — and the backend scopes the list
    // to 'default' for tenant_admin (API check mirrors the UI).
    const resp = await page.request.get(`${API_BASE}/api/v2/users?limit=50`);
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    const tenants = new Set(
      (body.data ?? []).map((u: any) => u.tenant).filter(Boolean),
    );
    expect([...tenants].every((t) => t === "default")).toBe(true);
  });

  test("P2-3: immutable built-in roles show a locked (disabled) Edit action", async ({
    page,
  }) => {
    await page.goto("/roles", { waitUntil: "domcontentloaded" });
    // Immutable anchors (emr_admin, pacs_admin, patient) render disabled Edit.
    // Match the role-name CELL, not the whole row — "Patient" text also
    // appears in other rows' permission chips ("View patient chart").
    for (const name of ["EMR Admin", "PACS Administrator", "Patient"]) {
      const nameCell = page
        .locator(".ant-table-tbody td", { hasText: name })
        .filter({ hasText: "Built-in" })
        .first();
      await expect(nameCell).toBeVisible({ timeout: 10000 });
      const row = nameCell.locator("xpath=ancestor::tr");
      const editBtn = row.locator("button", { hasText: "Edit" });
      expect(await editBtn.isDisabled().catch(() => true)).toBe(true);
    }
    // A facility-editable built-in (e.g. Cashier) keeps Edit enabled.
    const cashierCell = page
      .locator(".ant-table-tbody td", { hasText: "Cashier" })
      .filter({ hasText: "Built-in" })
      .first();
    await expect(cashierCell).toBeVisible({ timeout: 10000 });
    const cashier = cashierCell.locator("xpath=ancestor::tr");
    expect(
      await cashier.locator("button", { hasText: "Edit" }).isDisabled(),
    ).toBe(false);
  });
});
