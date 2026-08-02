import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
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

vi.mock("../api/tenants", () => ({
  listTenants: mockListTenants,
  createTenant: mockCreateTenant,
  updateTenant: mockUpdateTenant,
  deleteTenant: mockDeleteTenant,
  listSessionTenants: vi.fn(() => Promise.resolve([])),
}));

vi.mock("../helpers", () => ({
  request: vi.fn(() => Promise.resolve({})),
  isAdmin: () => true,
  setTokens: () => {},
  clearTokens: () => {},
  startRefreshTimer: () => {},
  stopRefreshTimer: () => {},
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
    status: "active",
    domain: "north.example.com",
    user_count: 10,
    study_count: 500,
    storage_used_bytes: 107374182400,
    storage_quota_bytes: 536870912000,
  },
];

const mockStats = {
  user_count: 42,
  study_count: 1500,
  file_count: 12000,
  storage_used_bytes: 536870912000,
  last_activity: "2026-07-28T12:00:00Z",
};

async function waitForCards() {
  await screen.findByText("Main Hospital");
}

describe("Tenants", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListTenants.mockResolvedValue(mockTenants);
    mockCreateTenant.mockResolvedValue({} as any);
    mockUpdateTenant.mockResolvedValue(undefined);
    mockDeleteTenant.mockResolvedValue(undefined);
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "true");
  });

  function renderWithAuth(ui: React.ReactElement) {
    return render(
      <ThemeProvider>
        <AuthProvider>
          <MemoryRouter>{ui}</MemoryRouter>
        </AuthProvider>
      </ThemeProvider>,
    );
  }

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
});
