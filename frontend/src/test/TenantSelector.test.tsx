import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithApp } from "./renderWithApp";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, afterEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import TenantSelector from "../auth/TenantSelector";

const mockListSessionTenants = vi.hoisted(() => vi.fn());
const mockEmit = vi.hoisted(() => vi.fn());
vi.mock("../api/tenants", () => ({
  listSessionTenants: mockListSessionTenants,
}));
vi.mock("../helpers", () => ({
  request: vi.fn(() => Promise.resolve({})),
  isAdmin: () => true,
  emit: mockEmit,
  subscribe: vi.fn(() => undefined),
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useFetch: () => ({ exec: vi.fn() }),
}));

afterEach(() => {
  localStorage.clear();
  mockEmit.mockClear();
});

const mockTenants = [
  { id: "1", name: "Main Hospital", slug: "main" },
  { id: "2", name: "North Clinic", slug: "north" },
];

function initAuth(tenantId = "main", tenantName = "Main Hospital") {
  localStorage.setItem("token", "test-token");
  localStorage.setItem("userId", "u1");
  localStorage.setItem("username", "admin");
  localStorage.setItem("admin", "true");
  localStorage.setItem("role", "admin");
  localStorage.setItem("tenant_id", tenantId);
  localStorage.setItem("tenant_name", tenantName);
  localStorage.setItem(
    "permissions",
    JSON.stringify(["USER_READ", "TENANT_READ", "ROLE_READ"]),
  );
}

describe("TenantSelector", () => {
  it("renders tenant name when active tenant is set in localStorage", async () => {
    initAuth();
    mockListSessionTenants.mockResolvedValue(mockTenants);

    renderWithApp(
      <MemoryRouter>
        <AuthProvider>
          <TenantSelector />
        </AuthProvider>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Main Hospital")).toBeInTheDocument();
    });
  });

  it("renders nothing when not authenticated", async () => {
    mockListSessionTenants.mockResolvedValue(mockTenants);

    renderWithApp(
      <MemoryRouter>
        <AuthProvider>
          <TenantSelector />
        </AuthProvider>
      </MemoryRouter>,
    );

    expect(screen.queryByText("Main Hospital")).not.toBeInTheDocument();
  });

  it("renders nothing (no dead Tenant label) when authenticated without a tenant", async () => {
    initAuth();
    localStorage.removeItem("tenant_id");
    localStorage.removeItem("tenant_name");
    mockListSessionTenants.mockResolvedValue(mockTenants);

    renderWithApp(
      <MemoryRouter>
        <AuthProvider>
          <TenantSelector />
        </AuthProvider>
      </MemoryRouter>,
    );

    expect(screen.queryByText("Tenant")).not.toBeInTheDocument();
  });

  it("displays tenant list in Select dropdown", async () => {
    initAuth();
    mockListSessionTenants.mockResolvedValue(mockTenants);

    renderWithApp(
      <MemoryRouter>
        <AuthProvider>
          <TenantSelector />
        </AuthProvider>
      </MemoryRouter>,
    );

    const selector = await screen.findByRole("combobox");
    expect(selector).toBeInTheDocument();

    fireEvent.mouseDown(selector);

    await waitFor(() => {
      expect(screen.getByText("North Clinic")).toBeInTheDocument();
    });
  });

  it("switches active tenant via dropdown and emits tenant:changed", async () => {
    initAuth();
    mockListSessionTenants.mockResolvedValue(mockTenants);

    renderWithApp(
      <MemoryRouter>
        <AuthProvider>
          <TenantSelector />
        </AuthProvider>
      </MemoryRouter>,
    );

    const selector = await screen.findByRole("combobox");
    fireEvent.mouseDown(selector);

    const option = await screen.findByText("North Clinic");
    expect(option).toBeInTheDocument();

    fireEvent.click(option);

    await waitFor(() => {
      expect(localStorage.getItem("tenant_id")).toBe("north");
    });

    expect(localStorage.getItem("tenant_name")).toBe("North Clinic");
    // Screens subscribed via useTenantRefetch() depend on this event.
    expect(mockEmit).toHaveBeenCalledWith("tenant:changed", "north");
    const northElements = screen.getAllByText("North Clinic");
    expect(northElements.length).toBeGreaterThanOrEqual(1);
  });
});
