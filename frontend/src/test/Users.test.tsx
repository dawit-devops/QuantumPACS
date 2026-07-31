import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import Users from "../users/Users";

const mockRequest = vi.hoisted(() => vi.fn());

vi.mock("../helpers", () => ({
  request: mockRequest,
  isAdmin: () => true,
  setTokens: () => {},
  clearTokens: () => {},
  startRefreshTimer: () => {},
  stopRefreshTimer: () => {},
}));

vi.mock("../hooks", () => ({
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
    mockRequest.mockImplementation((url: string) => {
      if (url === "roles") return Promise.resolve({ data: mockRoles });
      return Promise.resolve({ data: mockUsers });
    });
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
    mockRequest.mockImplementation((url: string, opts?: any) => {
      if (url === "roles") return Promise.resolve({ data: mockRoles });
      if (url === "users/role") return Promise.resolve({});
      return Promise.resolve({ data: mockUsers });
    });
    renderWithAuth(<Users />);
    await screen.findByText("Technologist");

    const selects = screen.getAllByRole("combobox");
    await user.click(selects[0]);

    const option = screen
      .getAllByText("Radiologist")
      .find((el) => el.closest(".ant-select-item-option"));
    expect(option).toBeTruthy();
    await user.click(option!);

    expect(mockRequest).toHaveBeenCalledWith("users/role", {
      data: { user_id: 1, role_id: 3 },
    });
  });
});
