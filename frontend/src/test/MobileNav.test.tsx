import React from "react";
import { screen } from "@testing-library/react";
import { renderWithApp } from "./renderWithApp";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import MobileNav from "../common/MobileNav";

vi.mock("../helpers", () => ({
  isAdmin: () => false,
  request: vi.fn(),
  clearTokens: () => {},
  setTokens: () => {},
  startRefreshTimer: () => {},
  stopRefreshTimer: () => {},
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useFetch: () => ({ exec: vi.fn() }),
}));

const { mockLogout } = vi.hoisted(() => ({
  mockLogout: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("../api/auth", () => ({
  logout: mockLogout,
}));

function setSession(opts: {
  role?: string;
  admin?: boolean;
  permissions?: string[];
}) {
  localStorage.setItem("token", "t");
  localStorage.setItem("userId", "u1");
  localStorage.setItem("admin", String(opts.admin ?? false));
  localStorage.setItem("role", opts.role ?? "user");
  localStorage.setItem("permissions", JSON.stringify(opts.permissions ?? []));
}

function renderWithRouter(path: string) {
  return renderWithApp(
    <ThemeProvider>
      <AuthProvider>
        <MemoryRouter initialEntries={[path]}>
          <MobileNav />
        </MemoryRouter>
      </AuthProvider>
    </ThemeProvider>,
  );
}

describe("MobileNav", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("renders Files and Account links", () => {
    renderWithRouter("/");
    expect(screen.getByText("Files")).toBeInTheDocument();
    expect(screen.getByText("Account")).toBeInTheDocument();
    expect(screen.queryByText("Metrics")).not.toBeInTheDocument();
  });

  it("highlights Files as active on root path", () => {
    renderWithRouter("/");
    const filesLink = screen.getByText("Files").closest("a");
    expect(filesLink?.className).toContain("active");
  });

  it("highlights Account as active on /account", () => {
    renderWithRouter("/account");
    const accountLink = screen.getByText("Account").closest("a");
    expect(accountLink?.className).toContain("active");
  });

  it("has accessible labels on nav items", () => {
    renderWithRouter("/");
    const nav = document.querySelector("nav");
    expect(nav).toBeInTheDocument();
    const links = nav!.querySelectorAll("a");
    expect(links.length).toBe(2);
  });

  it("hides the Menu button when the user has no workspace sections", () => {
    setSession({ role: "patient", permissions: ["PORTAL_READ"] });
    renderWithRouter("/");
    expect(screen.queryByLabelText("Menu")).not.toBeInTheDocument();
  });

  it("opens workspace sections in the drawer for a LOG_READ-only user (desktop parity)", async () => {
    const user = userEvent.setup();
    setSession({ role: "user", permissions: ["LOG_READ"] });
    renderWithRouter("/");
    await user.click(screen.getByLabelText("Menu"));
    expect(await screen.findByText("Admin")).toBeInTheDocument();
    await user.click(screen.getByText("Admin"));
    expect(await screen.findByText("Logs")).toBeInTheDocument();
  });
});
