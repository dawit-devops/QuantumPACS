import React from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import PermissionRoute from "../auth/PermissionRoute";
import { landingRouteFor } from "../navigator";

// navigator's landingRouteFor is implementer-1's module; tests stub it so the
// gate's redirect wiring is asserted without depending on its priority logic.
const { landingRouteForMock } = vi.hoisted(() => ({
  landingRouteForMock: vi.fn(() => "/"),
}));

vi.mock("../navigator", () => ({
  landingRouteFor: landingRouteForMock,
  navigate: vi.fn(),
  setNavigator: vi.fn(),
}));

describe("PermissionRoute", () => {
  beforeEach(() => {
    localStorage.clear();
    landingRouteForMock.mockImplementation(() => "/");
  });

  it("redirects unauthenticated users to /login", () => {
    render(
      <MemoryRouter initialEntries={["/users"]}>
        <AuthProvider>
          <Routes>
            <Route
              path="/login"
              element={<div data-testid="login-page">Login</div>}
            />
            <Route
              path="/users"
              element={
                <PermissionRoute permission="USER_READ">
                  <div data-testid="users-page">Users</div>
                </PermissionRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );
    expect(screen.getByTestId("login-page")).toBeInTheDocument();
    expect(screen.queryByTestId("users-page")).toBeNull();
  });

  it("redirects authenticated users lacking the permission to landingRouteFor", () => {
    localStorage.setItem("userId", "u1");
    localStorage.setItem("username", "tech-user");
    localStorage.setItem("admin", "false");
    localStorage.setItem("role", "technologist");
    localStorage.setItem(
      "permissions",
      JSON.stringify(["FILE_READ", "WORKLIST_READ"]),
    );
    landingRouteForMock.mockImplementation(() => "/worklist");

    render(
      <MemoryRouter initialEntries={["/users"]}>
        <AuthProvider>
          <Routes>
            <Route
              path="/"
              element={<div data-testid="files-page">Files</div>}
            />
            <Route
              path="/worklist"
              element={<div data-testid="worklist-page">Worklist</div>}
            />
            <Route
              path="/users"
              element={
                <PermissionRoute permission="USER_READ">
                  <div data-testid="users-page">Users</div>
                </PermissionRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );
    expect(screen.getByTestId("worklist-page")).toBeInTheDocument();
    expect(screen.queryByTestId("users-page")).toBeNull();
    // The current user must be passed so the landing choice fits their grants.
    expect(landingRouteForMock).toHaveBeenCalledWith(
      expect.objectContaining({ role: "technologist" }),
    );
  });

  it("renders children when the user has the required permission", () => {
    localStorage.setItem("userId", "u1");
    localStorage.setItem("username", "admin-user");
    localStorage.setItem("admin", "false");
    localStorage.setItem("role", "admin");
    localStorage.setItem("permissions", JSON.stringify(["USER_READ"]));

    render(
      <MemoryRouter initialEntries={["/users"]}>
        <AuthProvider>
          <Routes>
            <Route
              path="/"
              element={<div data-testid="files-page">Files</div>}
            />
            <Route
              path="/users"
              element={
                <PermissionRoute permission="USER_READ">
                  <div data-testid="users-page">Users</div>
                </PermissionRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );
    expect(screen.getByTestId("users-page")).toBeInTheDocument();
    expect(screen.queryByTestId("files-page")).toBeNull();
  });

  it("renders children for admin users regardless of the permission list", () => {
    localStorage.setItem("userId", "u1");
    localStorage.setItem("username", "super-admin");
    localStorage.setItem("admin", "true");
    localStorage.setItem("role", "super_admin");
    localStorage.setItem("permissions", JSON.stringify([]));

    render(
      <MemoryRouter initialEntries={["/replicas"]}>
        <AuthProvider>
          <Routes>
            <Route
              path="/replicas"
              element={
                <PermissionRoute permission="REPLICA_READ">
                  <div data-testid="replicas-page">Replicas</div>
                </PermissionRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );
    expect(screen.getByTestId("replicas-page")).toBeInTheDocument();
  });

  it("renders children when any of the listed permissions matches", () => {
    localStorage.setItem("userId", "u1");
    localStorage.setItem("username", "ops-user");
    localStorage.setItem("admin", "false");
    localStorage.setItem("role", "ops_engineer");
    localStorage.setItem("permissions", JSON.stringify(["REPLICA_READ"]));

    render(
      <MemoryRouter initialEntries={["/admin-panel"]}>
        <AuthProvider>
          <Routes>
            <Route
              path="/admin-panel"
              element={
                <PermissionRoute permission={["USER_READ", "REPLICA_READ"]}>
                  <div data-testid="panel-page">Panel</div>
                </PermissionRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );
    expect(screen.getByTestId("panel-page")).toBeInTheDocument();
  });

  it("redirects when none of the listed permissions matches", () => {
    localStorage.setItem("userId", "u1");
    localStorage.setItem("username", "billing-clerk");
    localStorage.setItem("admin", "false");
    localStorage.setItem("role", "billing_clerk");
    localStorage.setItem(
      "permissions",
      JSON.stringify(["BILLING_READ", "METERING_READ"]),
    );
    landingRouteForMock.mockImplementation(() => "/account");

    render(
      <MemoryRouter initialEntries={["/admin-panel"]}>
        <AuthProvider>
          <Routes>
            <Route
              path="/account"
              element={<div data-testid="account-page">Account</div>}
            />
            <Route
              path="/admin-panel"
              element={
                <PermissionRoute permission={["USER_READ", "REPLICA_READ"]}>
                  <div data-testid="panel-page">Panel</div>
                </PermissionRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );
    expect(screen.getByTestId("account-page")).toBeInTheDocument();
    expect(screen.queryByTestId("panel-page")).toBeNull();
  });
});
