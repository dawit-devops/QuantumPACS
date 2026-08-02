import React from "react";
import { render, screen } from "@testing-library/react";
import { renderWithApp } from "./renderWithApp";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import Sidebar from "../common/Sidebar";

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useFetch: () => ({ exec: vi.fn() }),
}));

const { requestMock } = vi.hoisted(() => ({
  requestMock: vi.fn().mockResolvedValue({}),
}));

const { mockLogout } = vi.hoisted(() => ({
  mockLogout: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("../api/auth", () => ({
  logout: mockLogout,
}));

vi.mock("../helpers", () => ({
  isAdmin: () => true,
  request: requestMock,
  clearTokens: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  },
  setTokens: () => {},
  startRefreshTimer: () => {},
  stopRefreshTimer: () => {},
}));

function renderWithAuth(ui: React.ReactElement) {
  return renderWithApp(
    <ThemeProvider>
      <AuthProvider>
        <MemoryRouter initialEntries={["/"]}>{ui}</MemoryRouter>
      </AuthProvider>
    </ThemeProvider>,
  );
}

describe("Sidebar", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("renders Files nav item", () => {
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    renderWithAuth(<Sidebar />);
    expect(screen.getByText("Files")).toBeInTheDocument();
  });

  it("renders Account nav item", () => {
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    renderWithAuth(<Sidebar />);
    expect(screen.getByText("Account")).toBeInTheDocument();
  });

  it("renders Logout nav item", () => {
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    renderWithAuth(<Sidebar />);
    expect(screen.getByText("Logout")).toBeInTheDocument();
  });

  it("shows Admin submenu and items for user with admin-level permission", async () => {
    const user = userEvent.setup();
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "false");
    localStorage.setItem("role", "tenant_admin");
    localStorage.setItem(
      "permissions",
      JSON.stringify(["TENANT_READ", "USER_READ"]),
    );
    renderWithAuth(<Sidebar />);
    expect(screen.getByText("Admin")).toBeInTheDocument();
    await user.click(screen.getByText("Admin"));
    expect(screen.getByText("Tenants")).toBeInTheDocument();
    expect(screen.getByText("Users")).toBeInTheDocument();
    expect(screen.queryByText("Replicas")).not.toBeInTheDocument();
  });

  it("hides Admin submenu for user without any admin permission", () => {
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "false");
    localStorage.setItem("role", "cashier");
    localStorage.setItem(
      "permissions",
      JSON.stringify(["PATIENT_READ", "PATIENT_WRITE"]),
    );
    renderWithAuth(<Sidebar />);
    expect(screen.queryByText("Admin")).not.toBeInTheDocument();
  });

  it("shows Admin submenu for admin user", () => {
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("admin", "true");
    renderWithAuth(<Sidebar />);
    expect(screen.getByText("Admin")).toBeInTheDocument();
  });

  it("renders QuantumLogo", () => {
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    renderWithAuth(<Sidebar />);
    const svg = document.querySelector("svg");
    expect(svg?.textContent).toContain("Quantum");
  });

  it("logout calls the logout endpoint and clears session via signOut", async () => {
    const user = userEvent.setup();
    localStorage.setItem("token", "t");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("access_token", "a");
    localStorage.setItem("refresh_token", "r");
    sessionStorage.setItem("tempKey", "share-temp");
    renderWithAuth(<Sidebar />);

    await user.click(screen.getByText("Logout"));

    expect(mockLogout).toHaveBeenCalled();
    expect(localStorage.getItem("userId")).toBeNull();
    expect(localStorage.getItem("access_token")).toBeNull();
    expect(localStorage.getItem("refresh_token")).toBeNull();
    expect(sessionStorage.getItem("tempKey")).toBeNull();
  });
});
