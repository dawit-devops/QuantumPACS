import React from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router";
import { describe, it, expect, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import PermissionRoute from "../auth/PermissionRoute";

describe("PermissionRoute", () => {
  beforeEach(() => {
    localStorage.clear();
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

  it("redirects authenticated users lacking the permission to / (Files)", () => {
    localStorage.setItem("userId", "u1");
    localStorage.setItem("username", "tech-user");
    localStorage.setItem("admin", "false");
    localStorage.setItem("role", "technologist");
    localStorage.setItem(
      "permissions",
      JSON.stringify(["FILE_READ", "WORKLIST_READ"]),
    );

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
    expect(screen.getByTestId("files-page")).toBeInTheDocument();
    expect(screen.queryByTestId("users-page")).toBeNull();
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
});
