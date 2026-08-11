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
  roleDisplayName: (slug?: string, fallback?: string) => fallback ?? slug,
  permissionLabel: (code: string) => code,
  builtinRoleEditable: (slug?: string, isAdmin = false) =>
    ![
      "super_admin",
      "tenant_admin",
      "pacs_admin",
      "emr_admin",
      "patient",
    ].includes(slug ?? "") &&
    (slug !== "teleradiologist" || isAdmin),
  builtinRoleEditTooltip: (slug?: string, isAdmin = false) =>
    [
      "super_admin",
      "tenant_admin",
      "pacs_admin",
      "emr_admin",
      "patient",
    ].includes(slug ?? "")
      ? "Cannot modify immutable built-in role"
      : slug === "teleradiologist" && !isAdmin
        ? "Only the platform admin can modify this role"
        : "",
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useFetch: () => ({ exec: vi.fn() }),
}));

const mockRoles = [
  {
    id: 1,
    name: "Administrator",
    slug: "super_admin",
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
  {
    id: 4,
    name: "Teleradiologist",
    slug: "teleradiologist",
    permissions: ["STUDY_READ"],
    built_in: true,
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

  it("renders headers and role names from API", async () => {
    renderWithAuth(<Roles />);
    const headers = await screen.findAllByText("Role");
    expect(headers.length).toBeGreaterThanOrEqual(1);
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
    await user.type(within(modal).getByLabelText("Slug"), "test_role");
    await user.click(within(modal).getByText("FILE_READ"));

    await user.click(within(modal).getByText("Create"));

    expect(mockCreateRole).toHaveBeenCalledWith({
      name: "Test Role",
      slug: "test_role",
      permissions: ["FILE_READ"],
    });
  });

  it("edit modal pre-fills values and sends updated permissions", async () => {
    const user = userEvent.setup();
    renderWithAuth(<Roles />);
    await waitForTable();

    await user.click(screen.getAllByText("Edit")[2]);

    const modal = screen.getByRole("dialog");
    expect(within(modal).getByDisplayValue("Custom Role")).toBeInTheDocument();
    expect(within(modal).getByDisplayValue("custom")).toBeInTheDocument();

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

    await user.click(screen.getByText("Delete"));

    const confirmBtn = screen.getByText(/yes|confirm|ok/i);
    await user.click(confirmBtn);

    await waitFor(() => {
      expect(mockDeleteRole).toHaveBeenCalledWith(3);
    });
  });

  it("tiers built-in edit access (immutable locked, others open)", async () => {
    renderWithAuth(<Roles />);
    await waitForTable();

    const editBtns = screen.getAllByText("Edit");
    expect(editBtns.length).toBe(4);
    // super_admin (immutable) — locked
    expect(editBtns[0].closest("button")).toBeDisabled();
    // technologist (facility-editable) — open
    expect(editBtns[1].closest("button")).toBeEnabled();
    // custom role — editable, deletable
    expect(editBtns[2].closest("button")).toBeEnabled();
    // teleradiologist — open for the platform admin (admin=true here)
    expect(editBtns[3].closest("button")).toBeEnabled();
    expect(screen.queryAllByText("Delete").length).toBe(1);
  });

  it("keeps teleradiologist locked for non-platform admins", async () => {
    localStorage.setItem("admin", "false");
    localStorage.setItem(
      "permissions",
      JSON.stringify(["ROLE_WRITE", "ROLE_DELETE"]),
    );
    renderWithAuth(<Roles />);
    await waitForTable();

    const editBtns = screen.getAllByText("Edit");
    expect(editBtns[0].closest("button")).toBeDisabled();
    expect(editBtns[1].closest("button")).toBeEnabled();
    expect(editBtns[3].closest("button")).toBeDisabled();
  });
});
