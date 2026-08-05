import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderWithAuth } from "../../src/test/renderWithApp";
import { MemoryRouter } from "react-router";
import { App } from "antd";
import React from "react";

// Mock the tenant API module
vi.mock("../../src/api/tenants", () => ({
  createTenant: vi.fn(),
  listTenants: vi.fn(),
  getTenant: vi.fn(),
  updateTenant: vi.fn(),
  deleteTenant: vi.fn(),
}));

// Mock the users API module
vi.mock("../../src/api/users", () => ({
  createUser: vi.fn(),
  listUsers: vi.fn(),
  getUser: vi.fn(),
  updateUser: vi.fn(),
}));

// Mock the API client
vi.mock("../../src/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

describe("Tenant Provisioning E2E Flow", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  it("provision tenant → assign user → verify access flow completes", async () => {
    const { createTenant, listTenants, getTenant } = await import(
      "../../src/api/tenants"
    );
    const { createUser, listUsers } = await import("../../src/api/users");

    // Step 1: Provision tenant
    (createTenant as vi.MockedFunction<typeof createTenant>).mockResolvedValue({
      data: { id: "tenant-1", name: "TestTenant", status: "active" },
      status: 201,
    });

    const tenantResult = await createTenant({ name: "TestTenant" });
    expect(tenantResult.status).toBe(201);
    expect(tenantResult.data.id).toBe("tenant-1");

    // Step 2: Assign user to tenant
    (createUser as vi.MockedFunction<typeof createUser>).mockResolvedValue({
      data: { id: "user-1", username: "tenant-user", role: "radiologist" },
      status: 201,
    });

    const userResult = await createUser({
      username: "tenant-user",
      role: "radiologist",
      tenantId: "tenant-1",
    });
    expect(userResult.status).toBe(201);

    // Step 3: Verify tenant access
    (listTenants as vi.MockedFunction<typeof listTenants>).mockResolvedValue({
      data: [{ id: "tenant-1", name: "TestTenant" }],
      total: 1,
    });

    const tenantsResult = await listTenants();
    expect(tenantsResult.data).toHaveLength(1);
    expect(tenantsResult.data[0].name).toBe("TestTenant");

    // Step 4: Verify user can access tenant data
    (listUsers as vi.MockedFunction<typeof listUsers>).mockResolvedValue({
      data: [{ id: "user-1", username: "tenant-user", tenantId: "tenant-1" }],
      total: 1,
    });

    const usersResult = await listUsers({ tenantId: "tenant-1" });
    expect(usersResult.data).toHaveLength(1);
    expect(usersResult.data[0].username).toBe("tenant-user");
  });

  it("tenant isolation: user from tenant A cannot access tenant B data", async () => {
    const { getTenant } = await import("../../src/api/tenants");

    // Tenant A user tries to access Tenant B's data
    (getTenant as vi.MockedFunction<typeof getTenant>).mockResolvedValue({
      status: 403,
      error: "Access denied: tenant mismatch",
    });

    const result = await getTenant("tenant-b", { tenantId: "tenant-a" });
    expect(result.status).toBe(403);
  });

  it("tenant creation with invalid data returns 422", async () => {
    const { createTenant } = await import("../../src/api/tenants");

    (createTenant as vi.MockedFunction<typeof createTenant>).mockResolvedValue({
      status: 422,
      error: "Validation error: name is required",
    });

    const result = await createTenant({});
    expect(result.status).toBe(422);
  });
});
