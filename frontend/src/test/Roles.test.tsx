import React from "react";
import { render, screen, within, waitFor } from "@testing-library/react";
import { renderWithAuth } from "./renderWithApp";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import Roles from "../roles/Roles";

const mockListRoles = vi.hoisted(() => vi.fn());
const mockListPermissions = vi.hoisted(() => vi.fn());
const mockCreateRole = vi.hoisted(() => vi.fn());
const mockUpdateRole = vi.hoisted(() => vi.fn());
const mockDeleteRole = vi.hoisted(() => vi.fn());
const mockListRoleUsers = vi.hoisted(() => vi.fn());

vi.mock("../api/roles", () => ({
  listRoles: mockListRoles,
  listPermissions: mockListPermissions,
  createRole: mockCreateRole,
  updateRole: mockUpdateRole,
  deleteRole: mockDeleteRole,
  listRoleUsers: mockListRoleUsers,
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useFetch: () => ({ exec: vi.fn() }),
}));

const mockRoles = [
  {
    id: 1,
    name: "Administrator",
    slug: "admin",
    permissions: ["FILE_READ", "FILE_WRITE"],
    built_in: true,
  },
  {
    id: 2,
    name: "Technologist",
    slug: "technologist",
    permissions: ["FILE_READ"],
    built_in: true,
  },
  {
    id: 3,
    name: "Custom Role",
    slug: "custom",
    permissions: ["PATIENT_READ"],
    built_in: false,
  },
];

async function waitForTable() {
  await screen.findByText("Administrator");
}

describe("Roles", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListRoles.mockResolvedValue(mockRoles);
    mockListPermissions.mockResolvedValue({
      Files: ["FILE_READ", "FILE_WRITE", "FILE_DELETE"],
      Patients: ["PATIENT_READ", "PATIENT_WRITE"],
    });
    mockCreateRole.mockResolvedValue(undefined);
    mockUpdateRole.mockResolvedValue(undefined);
    mockDeleteRole.mockResolvedValue(undefined);
    mockListRoleUsers.mockResolvedValue([]);
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "true");
  });

  it("renders Role column header", async () => {
    renderWithAuth(<Roles />);
    const headers = await screen.findAllByText("Role");
    expect(headers.length).toBeGreaterThanOrEqual(1);
  });

  it("displays role names from API", async () => {
    renderWithAuth(<Roles />);
    const admins = await screen.findAllByText("Administrator");
    expect(admins.length).toBeGreaterThanOrEqual(1);
    const techs = await screen.findAllByText("Technologist");
    expect(techs.length).toBeGreaterThanOrEqual(1);
    const customs = await screen.findAllByText("Custom Role");
    expect(customs.length).toBeGreaterThanOrEqual(1);
  });

  it("create modal includes permission checkboxes", async () => {
    const user = userEvent.setup();
    renderWithAuth(<Roles />);
    await waitForTable();

    await user.click(screen.getByText("Create Role"));
    const modal = screen.getByRole("dialog");
    expect(within(modal).getByText("FILE_READ")).toBeInTheDocument();
    expect(within(modal).getByText("PATIENT_READ")).toBeInTheDocument();
  });

  it("create role sends name, slug, and selected permissions", async () => {
    const user = userEvent.setup();
    renderWithAuth(<Roles />);
    await waitForTable();

    await user.click(screen.getByText("Create Role"));

    const modal = screen.getByRole("dialog");
    await user.type(within(modal).getByLabelText("Role Name"), "Test Role");
    await user.type(within(modal).getByLabelText("Slug"), "test-role");
    await user.click(within(modal).getByText("FILE_READ"));

    await user.click(within(modal).getByText("Create"));

    expect(mockCreateRole).toHaveBeenCalledWith({
      name: "Test Role",
      slug: "test-role",
      permissions: ["FILE_READ"],
    });
  });

  it("edit modal opens with pre-filled values when clicking edit", async () => {
    const user = userEvent.setup();
    renderWithAuth(<Roles />);
    await waitForTable();

    const editBtn = screen.getAllByRole("button", { name: /edit/i })[2];
    await user.click(editBtn);

    const modal = screen.getByRole("dialog");
    expect(within(modal).getByDisplayValue("Custom Role")).toBeInTheDocument();
    expect(within(modal).getByDisplayValue("custom")).toBeInTheDocument();
  });

  it("edit role sends updated permissions", async () => {
    const user = userEvent.setup();
    renderWithAuth(<Roles />);
    await waitForTable();

    await user.click(screen.getAllByRole("button", { name: /edit/i })[2]);

    const modal = screen.getByRole("dialog");
    await user.click(within(modal).getByText("PATIENT_READ"));
    await user.click(within(modal).getByText("FILE_READ"));
    await user.click(within(modal).getByText("Update"));

    await waitFor(() => {
      expect(mockUpdateRole).toHaveBeenCalledWith(3, {
        permissions: ["FILE_READ"],
      });
    });
  });

  it("delete role calls API and refreshes list", async () => {
    const user = userEvent.setup();
    renderWithAuth(<Roles />);
    await waitForTable();

    await user.click(screen.getByRole("button", { name: /delete/i }));

    const confirmBtn = screen.getByRole("button", { name: /yes|confirm|ok/i });
    await user.click(confirmBtn);

    await waitFor(() => {
      expect(mockDeleteRole).toHaveBeenCalledWith(3);
    });
  });

  it("does not show edit/delete for built-in roles", async () => {
    renderWithAuth(<Roles />);
    await waitForTable();

    const editBtns = screen.queryAllByRole("button", { name: /edit/i });
    const deleteBtns = screen.queryAllByRole("button", { name: /delete/i });
    expect(editBtns.length).toBe(3);
    expect(deleteBtns.length).toBe(1);
  });
});
