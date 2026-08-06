import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
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
      { date: "2026-07-01", api_calls: 120 },
      { date: "2026-07-02", api_calls: 98 },
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
    await user.type(
      screen.getByPlaceholderText("e.g., Memorial Hospital West"),
      "West Clinic",
    );
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
    await user.type(
      screen.getByPlaceholderText("e.g., Memorial Hospital West"),
      "West Clinic",
    );
    await user.type(screen.getByPlaceholderText("e.g., memorial-west"), "west");
    await user.click(screen.getByRole("button", { name: /^Provision$/ }));

    await waitFor(() => {
      expect(
        screen.queryByText("Tenant Admin Credentials"),
      ).not.toBeInTheDocument();
    });
  });

  it("opens usage drawer and loads api_calls table", async () => {
    const user = userEvent.setup();
    renderWithAuth(<Tenants />);
    await waitForCards();

    await user.click(screen.getAllByText("Usage")[0]);

    await waitFor(() => {
      expect(screen.getByText("API calls")).toBeInTheDocument();
    });
    expect(mockGetTenantUsage).toHaveBeenCalledWith("1");
    expect(screen.getByText("2026-07-01")).toBeInTheDocument();
  });
});
