import React from "react";
import { render, screen } from "@testing-library/react";
import { renderWithAuth } from "./renderWithApp";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import Users from "../users/Users";

const mockListUsers = vi.hoisted(() => vi.fn());
const mockAssignRole = vi.hoisted(() => vi.fn());
const mockDeactivateUser = vi.hoisted(() => vi.fn());
const mockResetPassword = vi.hoisted(() => vi.fn());
const mockListRoles = vi.hoisted(() => vi.fn());

vi.mock("../api/users", () => ({
  listUsers: mockListUsers,
  assignRole: mockAssignRole,
  deactivateUser: mockDeactivateUser,
  resetPassword: mockResetPassword,
}));

vi.mock("../api/roles", () => ({
  listRoles: mockListRoles,
}));

vi.mock("../api/tenants", () => ({
  listSessionTenants: vi.fn(() => Promise.resolve([])),
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useFetch: () => ({ exec: vi.fn() }),
}));

const mockUsers = [
  {
    id: 1,
    username: "admin",
    admin: true,
    status: "active",
    role_id: 1,
    role_name: "Administrator",
    role_slug: "admin",
  },
  {
    id: 2,
    username: "tech1",
    admin: false,
    status: "active",
    role_id: 2,
    role_name: "Technologist",
    role_slug: "technologist",
  },
  {
    id: 3,
    username: "dr.jane",
    admin: false,
    status: "active",
    role_id: 3,
    role_name: "Radiologist",
    role_slug: "radiologist",
  },
];

const mockRoles = [
  { id: 1, name: "Administrator", slug: "admin" },
  { id: 2, name: "Technologist", slug: "technologist" },
  { id: 3, name: "Radiologist", slug: "radiologist" },
];

describe("Users", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // The page's write controls (role select, reset, deactivate) are gated on
    // USER_WRITE, so the suite signs in as a user manager with the full grant.
    localStorage.setItem("userId", "u1");
    localStorage.setItem("username", "user-admin");
    localStorage.setItem("admin", "false");
    localStorage.setItem("role", "tenant_admin");
    localStorage.setItem("permissions", JSON.stringify(["USER_READ", "USER_WRITE"]));
    mockListUsers.mockResolvedValue({
      data: mockUsers,
      total: mockUsers.length,
      page: 1,
      per_page: 20,
      total_pages: 1,
    });
    mockListRoles.mockResolvedValue(mockRoles);
    mockAssignRole.mockResolvedValue(undefined);
    mockDeactivateUser.mockResolvedValue(undefined);
    mockResetPassword.mockResolvedValue({ password: "newpass" });
  });

  it("renders Role column header", async () => {
    renderWithAuth(<Users />);

    const headers = await screen.findAllByText("Role");
    expect(headers.length).toBeGreaterThanOrEqual(1);
  });

  it("displays role name for each user", async () => {
    renderWithAuth(<Users />);

    const admins = await screen.findAllByText("Administrator");
    expect(admins.length).toBeGreaterThanOrEqual(1);
    const techs = await screen.findAllByText("Technologist");
    expect(techs.length).toBeGreaterThanOrEqual(1);
    const rads = await screen.findAllByText("Radiologist");
    expect(rads.length).toBeGreaterThanOrEqual(1);
  });

  it("changes user role when a new role is selected", async () => {
    const user = userEvent.setup();
    renderWithAuth(<Users />);
    await screen.findByText("Technologist");

    const selects = screen.getAllByRole("combobox");
    await user.click(selects[0]);

    const option = screen
      .getAllByText("Radiologist")
      .find((el) => el.closest(".ant-select-item-option"));
    expect(option).toBeTruthy();
    await user.click(option!);

    expect(mockAssignRole).toHaveBeenCalledWith(1, 3);
  });

  it("renders an error state when listUsers fails (T-M4)", async () => {
    mockListUsers.mockRejectedValue(new Error("backend unreachable"));
    renderWithAuth(<Users />);

    expect(await screen.findByText(/backend unreachable/)).toBeInTheDocument();
  });

  it("renders an empty state when there are no users (T-M4)", async () => {
    mockListUsers.mockResolvedValue({
      data: [],
      total: 0,
      page: 1,
      per_page: 20,
      total_pages: 0,
    });
    renderWithAuth(<Users />);

    expect(await screen.findByText(/No data/)).toBeInTheDocument();
  });

  it("surfaces a message when role assignment fails (T-M4)", async () => {
    const user = userEvent.setup();
    mockAssignRole.mockRejectedValue(new Error("denied"));
    renderWithAuth(<Users />);
    await screen.findByText("Technologist");

    const selects = screen.getAllByRole("combobox");
    await user.click(selects[0]);
    const option = screen
      .getAllByText("Radiologist")
      .find((el) => el.closest(".ant-select-item-option"));
    await user.click(option!);

    expect(await screen.findByText(/denied/)).toBeInTheDocument();
  });
});
