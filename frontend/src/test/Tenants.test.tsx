import React from "react";
import { render, screen, waitFor, within } from "@testing-library/react";
import { renderWithAuth } from "./renderWithApp";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import Tenants from "../tenants/Tenants";

const mockListTenants = vi.hoisted(() => vi.fn());
const mockCreateTenant = vi.hoisted(() => vi.fn());
const mockUpdateTenant = vi.hoisted(() => vi.fn());
const mockDeleteTenant = vi.hoisted(() => vi.fn());
const mockGetTenantHealth = vi.hoisted(() => vi.fn());
const mockGetTenantUsage = vi.hoisted(() => vi.fn());

vi.mock("../api/tenants", () => ({
  listTenants: mockListTenants,
  createTenant: mockCreateTenant,
  updateTenant: mockUpdateTenant,
  deleteTenant: mockDeleteTenant,
  getTenantHealth: mockGetTenantHealth,
  getTenantUsage: mockGetTenantUsage,
  listSessionTenants: vi.fn(() => Promise.resolve([])),
}));

vi.mock("../helpers", () => ({
  request: vi.fn(() => Promise.resolve({})),
  isAdmin: () => true,
  setTokens: () => {},
  clearTokens: () => {},
  startRefreshTimer: () => {},
  stopRefreshTimer: () => {},
  emit: vi.fn(),
  subscribe: vi.fn(() => undefined),
}));

// jsdom has no canvas context, so chart.js cannot mount; stand in a plain
// accessible node that keeps the aria-label contract.
vi.mock("react-chartjs-2", () => ({
  Line: (props: { "aria-label"?: string }) => (
    <div role="img" aria-label={props["aria-label"] ?? "chart"} />
  ),
  Bar: (props: { "aria-label"?: string }) => (
    <div role="img" aria-label={props["aria-label"] ?? "chart"} />
  ),
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useFetch: () => ({ exec: vi.fn() }),
}));

const mockTenants = [
  {
    id: "1",
    name: "Main Hospital",
    slug: "main",
    status: "active",
    plan: "enterprise",
    domain: "main.example.com",
    user_count: 42,
    study_count: 1500,
    storage_used_bytes: 536870912000,
    storage_quota_bytes: 1073741824000,
  },
  {
    id: "2",
    name: "North Clinic",
    slug: "north",
    status: "suspended",
    plan: "free",
    domain: "north.example.com",
    user_count: 10,
    study_count: 500,
    storage_used_bytes: 107374182400,
    storage_quota_bytes: 536870912000,
  },
];

async function waitForCards() {
  await screen.findByText("Main Hospital");
}

describe("Tenants", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListTenants.mockResolvedValue(mockTenants);
    mockCreateTenant.mockResolvedValue({ id: "3" } as any);
    mockUpdateTenant.mockResolvedValue(undefined);
    mockDeleteTenant.mockResolvedValue(undefined);
    mockGetTenantHealth.mockResolvedValue({ main: { status: "ok" } });
    mockGetTenantUsage.mockResolvedValue([
      { date: "2026-07-01", api_calls: 120, mwl_queries: 7, notifications: 3 },
      { date: "2026-07-02", api_calls: 98, mwl_queries: 2, notifications: 5 },
    ]);
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "true");
  });

  it("displays tenant names from API", async () => {
    renderWithAuth(<Tenants />);
    const main = await screen.findAllByText("Main Hospital");
    expect(main.length).toBeGreaterThanOrEqual(1);
    const north = await screen.findAllByText("North Clinic");
    expect(north.length).toBeGreaterThanOrEqual(1);
  });

  it("displays tenant slugs as tags", async () => {
    renderWithAuth(<Tenants />);
    await waitForCards();
    expect(screen.getByText("main")).toBeInTheDocument();
    expect(screen.getByText("north")).toBeInTheDocument();
  });

  it("shows user and study counts", async () => {
    renderWithAuth(<Tenants />);
    await waitForCards();
    expect(screen.getByText(/42 users/)).toBeInTheDocument();
    expect(screen.getByText(/1500 studies/)).toBeInTheDocument();
  });

  it("calls tenants endpoint on mount", async () => {
    renderWithAuth(<Tenants />);
    await waitForCards();
    expect(mockListTenants).toHaveBeenCalled();
  });

  it("fetches tenant health once on mount", async () => {
    renderWithAuth(<Tenants />);
    await waitForCards();
    expect(mockGetTenantHealth).toHaveBeenCalled();
  });

  it("renders Provision Tenant button", async () => {
    renderWithAuth(<Tenants />);
    await waitForCards();
    expect(screen.getByText("Provision Tenant")).toBeInTheDocument();
  });

  it("decommission button is visible", async () => {
    renderWithAuth(<Tenants />);
    await waitForCards();
    const decommissionBtns = screen.getAllByText("Decommission");
    expect(decommissionBtns.length).toBe(2);
  });

  it("shows plan tags on cards", async () => {
    renderWithAuth(<Tenants />);
    await waitForCards();
    expect(screen.getByText("enterprise")).toBeInTheDocument();
    expect(screen.getByText("free")).toBeInTheDocument();
  });

  it("shows lifecycle actions: Suspend on active, Activate on suspended", async () => {
    renderWithAuth(<Tenants />);
    await waitForCards();
    expect(screen.getByText("Suspend")).toBeInTheDocument();
    expect(screen.getByText("Activate")).toBeInTheDocument();
    expect(screen.getByText("Quarantine")).toBeInTheDocument();
  });

  it("shows one-time admin password panel after provisioning with admin_password", async () => {
    mockCreateTenant.mockResolvedValue({
      id: "3",
      admin_password: "pw-12345",
    } as any);
    const user = userEvent.setup();
    renderWithAuth(<Tenants />);
    await waitForCards();

    await user.click(screen.getByText("Provision Tenant"));
    await user.type(screen.getByPlaceholderText("e.g., Memorial Hospital West"), "West Clinic");
    await user.type(screen.getByPlaceholderText("e.g., memorial-west"), "west");

    await user.click(screen.getByRole("button", { name: /^Provision$/ }));

    await waitFor(() => {
      expect(screen.getByText("pw-12345")).toBeInTheDocument();
    });
    expect(screen.getByText("Tenant Admin Credentials")).toBeInTheDocument();

    // "I saved it" dismisses the one-time panel for good.
    await user.click(screen.getByRole("button", { name: /I saved it/i }));
    await waitFor(() => {
      expect(screen.queryByText("pw-12345")).not.toBeInTheDocument();
    });
  });

  it("does not show the password panel when response has no admin_password", async () => {
    mockCreateTenant.mockResolvedValue({ id: "3" } as any);
    const user = userEvent.setup();
    renderWithAuth(<Tenants />);
    await waitForCards();

    await user.click(screen.getByText("Provision Tenant"));
    await user.type(screen.getByPlaceholderText("e.g., Memorial Hospital West"), "West Clinic");
    await user.type(screen.getByPlaceholderText("e.g., memorial-west"), "west");
    await user.click(screen.getByRole("button", { name: /^Provision$/ }));

    await waitFor(() => {
      expect(screen.queryByText("Tenant Admin Credentials")).not.toBeInTheDocument();
    });
  });

  it("opens usage drawer and loads api_calls table", async () => {
    const user = userEvent.setup();
    renderWithAuth(<Tenants />);
    await waitForCards();

    await user.click(screen.getAllByText("Usage")[0]);

    await waitFor(() => {
      // "API calls" now labels both the trend-series toggle and the table
      // column, so assert on the column role.
      expect(screen.getByRole("columnheader", { name: /api calls/i })).toBeInTheDocument();
    });
    expect(mockGetTenantUsage).toHaveBeenCalledWith("1");
    expect(screen.getByText("2026-07-01")).toBeInTheDocument();
  });

  it("shows RIS activity columns in usage drawer", async () => {
    const user = userEvent.setup();
    renderWithAuth(<Tenants />);
    await waitForCards();

    await user.click(screen.getAllByText("Usage")[0]);

    await waitFor(() => {
      expect(screen.getByRole("columnheader", { name: /mwl queries/i })).toBeInTheDocument();
    });
    expect(screen.getByRole("columnheader", { name: /^notifications/i })).toBeInTheDocument();
    // Per-day RIS counters render next to api_calls.
    expect(screen.getByText("7")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("raises a 90%-tier storage alert when utilization crosses it (ADM-17)", async () => {
    mockListTenants.mockResolvedValue([
      {
        id: "1",
        name: "Full Tenant",
        slug: "full",
        status: "active",
        storage_used_bytes: 9 * 1024 ** 3,
        storage_quota_bytes: 10 * 1024 ** 3,
      },
    ]);
    renderWithAuth(<Tenants />);
    await screen.findByText("Full Tenant");

    expect(await screen.findByText(/Storage above 90%/)).toBeInTheDocument();
  });

  it("raises an exhausted-quota error alert at 100% (ADM-17)", async () => {
    mockListTenants.mockResolvedValue([
      {
        id: "1",
        name: "Packed Tenant",
        slug: "packed",
        status: "active",
        storage_used_bytes: 10 * 1024 ** 3,
        storage_quota_bytes: 10 * 1024 ** 3,
      },
    ]);
    renderWithAuth(<Tenants />);
    await screen.findByText("Packed Tenant");

    expect(await screen.findByText(/Storage quota exhausted/)).toBeInTheDocument();
  });

  it("shows no storage alert below 80% (ADM-17)", async () => {
    renderWithAuth(<Tenants />);
    await waitForCards();

    // Fixtures sit at ~50% and ~20% — no threshold copy anywhere.
    expect(screen.queryByText(/Storage above 90%/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Storage quota exhausted/)).not.toBeInTheDocument();
  });

  it("requires and sends a justification when the quota changes", async () => {
    const user = userEvent.setup();
    renderWithAuth(<Tenants />);
    await waitForCards();

    // Main Hospital ships with 1000 GB; open its Edit modal.
    const editButtons = screen.getAllByText("Edit");
    await user.click(editButtons[0]);
    const quotaInput = await screen.findByLabelText("Storage Quota (GB)");
    await user.clear(quotaInput);
    await user.type(quotaInput, "500");

    // Saving without a reason fails fast client-side.
    await user.click(screen.getByRole("button", { name: /^Save$/ }));
    const err = await screen.findByText(
      /justification is required when changing the storage quota/i
    );
    expect(err).toBeInTheDocument();
    expect(mockUpdateTenant).not.toHaveBeenCalled();

    await user.type(
      screen.getByLabelText(/Justification \(required for quota changes\)/),
      "Imaging volume doubled after clinic merge"
    );
    await user.click(screen.getByRole("button", { name: /^Save$/ }));

    await waitFor(() => {
      expect(mockUpdateTenant).toHaveBeenCalledWith(
        "1",
        expect.objectContaining({
          storage_quota_bytes: 500 * 1024 ** 3,
          quota_justification: "Imaging volume doubled after clinic merge",
        })
      );
    });
  });

  it("renders usage history trend series toggles in the drawer (ADM-14)", async () => {
    const user = userEvent.setup();
    renderWithAuth(<Tenants />);
    await waitForCards();

    await user.click(screen.getAllByText("Usage")[0]);

    const group = await screen.findByRole("group", {
      name: "Usage trend series",
    });
    expect(group).toBeInTheDocument();
    // Toggle labels share text with table columns — assert within the group.
    expect(within(group).getByText("API calls")).toBeInTheDocument();
    expect(within(group).getByText("Storage (GB)")).toBeInTheDocument();
    expect(screen.getByText("Active users")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /usage history chart/i })).toBeInTheDocument();
    // The per-day table still renders beneath the chart.
    expect(await screen.findByText("2026-07-01")).toBeInTheDocument();
  });

  it("keeps the trend chart alive when series are toggled (ADM-14)", async () => {
    const user = userEvent.setup();
    renderWithAuth(<Tenants />);
    await waitForCards();

    await user.click(screen.getAllByText("Usage")[0]);
    await screen.findByRole("group", { name: "Usage trend series" });

    await user.click(screen.getByText("Storage (GB)"));
    await user.click(screen.getByText("Active users"));

    expect(screen.getByRole("img", { name: /usage history chart/i })).toBeInTheDocument();
  });
});
