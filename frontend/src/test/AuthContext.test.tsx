import React from "react";
import { render, screen } from "@testing-library/react";
import { renderWithApp } from "./renderWithApp";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router";
import { describe, it, expect, beforeEach } from "vitest";
import { AuthProvider, useAuth } from "../auth/AuthContext";
import ProtectedRoute from "../auth/ProtectedRoute";
import RequirePermission from "../auth/RequirePermission";

function TestConsumer() {
  const { isAuthenticated, user } = useAuth();
  return (
    <div>
      <div data-testid="auth-status">
        {isAuthenticated ? "authenticated" : "unauthenticated"}
      </div>
      {user && <div data-testid="auth-user">{user.username}</div>}
    </div>
  );
}

function BrokenComponent() {
  useAuth();
  return <div />;
}

function SignInTestConsumer() {
  const { isAuthenticated, user, signIn } = useAuth();
  return (
    <div>
      <div data-testid="auth-status">
        {isAuthenticated ? "authenticated" : "unauthenticated"}
      </div>
      {user && <div data-testid="auth-user">{user.username}</div>}
      <button
        data-testid="signin-btn"
        onClick={() =>
          signIn("test-token", {
            id: "u1",
            username: "alice",
            admin: false,
            role: "user",
            permissions: [],
          })
        }
      >
        Sign In
      </button>
    </div>
  );
}

function PermissionTestConsumer() {
  const { hasPermission } = useAuth();
  return (
    <div>
      <div data-testid="perm-file-read">
        {hasPermission("FILE_READ") ? "yes" : "no"}
      </div>
      <div data-testid="perm-user-delete">
        {hasPermission("USER_DELETE") ? "yes" : "no"}
      </div>
    </div>
  );
}

function TenantSignInTestConsumer() {
  const { signIn, activeTenant } = useAuth();
  return (
    <div>
      <button
        data-testid="tenant-signin-btn"
        onClick={() =>
          signIn("test-token", {
            id: "u1",
            username: "alice",
            admin: false,
            role: "user",
            permissions: [],
            tenant_id: "memorial-west",
            tenant_name: "Memorial Hospital West",
          })
        }
      >
        Sign In With Tenant
      </button>
      <div data-testid="tenant-status">
        {activeTenant
          ? `${activeTenant.slug}|${activeTenant.name}`
          : "no-tenant"}
      </div>
    </div>
  );
}

function SignOutTestConsumer() {
  const { isAuthenticated, user, signOut } = useAuth();
  return (
    <div>
      <div data-testid="auth-status">
        {isAuthenticated ? "authenticated" : "unauthenticated"}
      </div>
      {user && <div data-testid="auth-user">{user.username}</div>}
      <button data-testid="signout-btn" onClick={() => signOut()}>
        Sign Out
      </button>
    </div>
  );
}

describe("AuthProvider", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("provides isAuthenticated=false when no token exists", () => {
    renderWithApp(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    );
    expect(screen.getByTestId("auth-status")).toHaveTextContent(
      "unauthenticated",
    );
  });

  it("signIn sets localStorage and updates auth state", async () => {
    const user = userEvent.setup();
    renderWithApp(
      <AuthProvider>
        <SignInTestConsumer />
      </AuthProvider>,
    );

    expect(screen.getByTestId("auth-status")).toHaveTextContent(
      "unauthenticated",
    );

    await user.click(screen.getByTestId("signin-btn"));

    expect(screen.getByTestId("auth-status")).toHaveTextContent(
      "authenticated",
    );
    expect(screen.getByTestId("auth-user")).toHaveTextContent("alice");
    expect(localStorage.getItem("userId")).toBe("u1");
    expect(localStorage.getItem("username")).toBe("alice");
    expect(localStorage.getItem("access_token")).toBe("test-token");
    expect(localStorage.getItem("refresh_token")).toBeNull();
  });

  it("signIn activates the tenant from the login response (tenant_id + tenant_name)", async () => {
    const user = userEvent.setup();
    renderWithApp(
      <AuthProvider>
        <TenantSignInTestConsumer />
      </AuthProvider>,
    );

    expect(screen.getByTestId("tenant-status")).toHaveTextContent("no-tenant");

    await user.click(screen.getByTestId("tenant-signin-btn"));

    // The backend returns tenant_id (a slug) + tenant_name after this
    // branch's backend work; signIn must persist and activate both.
    expect(localStorage.getItem("tenant_id")).toBe("memorial-west");
    expect(localStorage.getItem("tenant_name")).toBe("Memorial Hospital West");
    expect(screen.getByTestId("tenant-status")).toHaveTextContent(
      "memorial-west|Memorial Hospital West",
    );
  });

  it("signOut clears localStorage and sets isAuthenticated to false", async () => {
    localStorage.setItem("userId", "u1");
    localStorage.setItem("username", "alice");
    localStorage.setItem("admin", "false");
    localStorage.setItem("access_token", "t");
    localStorage.setItem("refresh_token", "r");
    sessionStorage.setItem("tempKey", "share-temp");
    sessionStorage.setItem("shareKeyError", "expired");

    const user = userEvent.setup();
    renderWithApp(
      <AuthProvider>
        <SignOutTestConsumer />
      </AuthProvider>,
    );

    expect(screen.getByTestId("auth-status")).toHaveTextContent(
      "authenticated",
    );

    await user.click(screen.getByTestId("signout-btn"));

    expect(screen.getByTestId("auth-status")).toHaveTextContent(
      "unauthenticated",
    );
    expect(localStorage.getItem("userId")).toBeNull();
    expect(localStorage.getItem("access_token")).toBeNull();
    expect(localStorage.getItem("refresh_token")).toBeNull();
    expect(sessionStorage.getItem("tempKey")).toBeNull();
    expect(sessionStorage.getItem("shareKeyError")).toBeNull();
    expect(screen.queryByTestId("auth-user")).toBeNull();
  });

  it("RequirePermission renders children when user has the required permission", () => {
    localStorage.setItem("token", "test-token");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("username", "admin-user");
    localStorage.setItem("admin", "true");
    localStorage.setItem("role", "admin");

    renderWithApp(
      <AuthProvider>
        <RequirePermission permission="admin">
          <div data-testid="admin-content">Admin Panel</div>
        </RequirePermission>
      </AuthProvider>,
    );
    expect(screen.getByTestId("admin-content")).toBeInTheDocument();
  });

  it("RequirePermission hides children when user lacks the required permission", () => {
    localStorage.setItem("token", "test-token");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("username", "regular-user");
    localStorage.setItem("admin", "false");
    localStorage.setItem("role", "user");

    renderWithApp(
      <AuthProvider>
        <RequirePermission permission="admin">
          <div data-testid="admin-content">Admin Panel</div>
        </RequirePermission>
      </AuthProvider>,
    );
    expect(screen.queryByTestId("admin-content")).toBeNull();
  });

  it("redirects unauthenticated users to /login", () => {
    renderWithApp(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <AuthProvider>
          <Routes>
            <Route
              path="/login"
              element={<div data-testid="login-page">Login</div>}
            />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <div data-testid="dashboard">Dashboard</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );
    expect(screen.getByTestId("login-page")).toBeInTheDocument();
    expect(screen.queryByTestId("dashboard")).toBeNull();
  });

  it("renders children when authenticated", () => {
    localStorage.setItem("token", "test-token");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("username", "alice");
    localStorage.setItem("admin", "false");
    localStorage.setItem("role", "user");

    renderWithApp(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <AuthProvider>
          <Routes>
            <Route
              path="/login"
              element={<div data-testid="login-page">Login</div>}
            />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <div data-testid="dashboard">Dashboard</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );
    expect(screen.getByTestId("dashboard")).toBeInTheDocument();
    expect(screen.queryByTestId("login-page")).toBeNull();
  });

  it("throws when useAuth is used outside AuthProvider", () => {
    expect(() => renderWithApp(<BrokenComponent />)).toThrow(
      "useAuth must be used within an AuthProvider",
    );
  });

  it("hasPermission returns true when user permissions include the required permission", () => {
    localStorage.setItem("token", "test-token");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("username", "tech-user");
    localStorage.setItem("admin", "false");
    localStorage.setItem("role", "technologist");
    localStorage.setItem(
      "permissions",
      JSON.stringify(["FILE_READ", "STUDY_READ", "WORKLIST_READ"]),
    );

    renderWithApp(
      <AuthProvider>
        <PermissionTestConsumer />
      </AuthProvider>,
    );
    expect(screen.getByTestId("perm-file-read")).toHaveTextContent("yes");
    expect(screen.getByTestId("perm-user-delete")).toHaveTextContent("no");
  });

  it("hasPermission returns true for admin users regardless of permissions list", () => {
    localStorage.setItem("token", "test-token");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("username", "admin-user");
    localStorage.setItem("admin", "true");
    localStorage.setItem("role", "super_admin");
    localStorage.setItem("permissions", JSON.stringify([]));

    renderWithApp(
      <AuthProvider>
        <PermissionTestConsumer />
      </AuthProvider>,
    );
    expect(screen.getByTestId("perm-file-read")).toHaveTextContent("yes");
    expect(screen.getByTestId("perm-user-delete")).toHaveTextContent("yes");
  });

  it("provides isAuthenticated=true when token and userId exist in localStorage", () => {
    localStorage.setItem("token", "test-token");
    localStorage.setItem("userId", "user-1");
    localStorage.setItem("username", "testuser");
    localStorage.setItem("admin", "false");
    localStorage.setItem("role", "user");

    renderWithApp(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    );
    expect(screen.getByTestId("auth-status")).toHaveTextContent(
      "authenticated",
    );
    expect(screen.getByTestId("auth-user")).toHaveTextContent("testuser");
  });
});
