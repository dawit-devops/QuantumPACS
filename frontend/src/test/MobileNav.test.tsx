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

function setSession(opts: { role?: string; admin?: boolean; permissions?: string[] }) {
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
    </ThemeProvider>
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
    // A patient without PORTAL_READ has no permitted section: the portal
    // (My Records) section and all clinical/admin sections stay hidden, so
    // the drawer trigger must not render. With PORTAL_READ the patient does
    // have a workspace section and the Menu button legitimately appears.
    setSession({ role: "patient", permissions: [] });
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

  it("hides clinical sections in the drawer for a tenant_admin even with clinical grants", async () => {
    const user = userEvent.setup();
    setSession({
      role: "tenant_admin",
      permissions: ["REPORT_READ", "EXAM_READ", "QA_READ", "USER_READ"],
    });
    renderWithRouter("/");
    await user.click(screen.getByLabelText("Menu"));
    expect(await screen.findByText("Admin")).toBeInTheDocument();
    expect(screen.queryByText("Reading")).not.toBeInTheDocument();
    expect(screen.queryByText("Acquisition")).not.toBeInTheDocument();
    expect(screen.queryByText("QA")).not.toBeInTheDocument();
  });

  it("hides Front Desk and My Records from a tenant_admin even with the grants", async () => {
    // NON_ADMIN_WORKSPACES drift guard (mobile parity with the sidebar):
    // an admin-scoped role holding the R08/R19 grants must not see the
    // front-office or patient surfaces in the drawer.
    const user = userEvent.setup();
    setSession({
      role: "tenant_admin",
      permissions: [
        "REGISTRATION_READ",
        "REGISTRATION_WRITE",
        "QUEUE_READ",
        "PORTAL_READ",
        "USER_READ",
      ],
    });
    renderWithRouter("/");
    await user.click(screen.getByLabelText("Menu"));
    expect(await screen.findByText("Admin")).toBeInTheDocument();
    expect(screen.queryByText("Front Desk")).not.toBeInTheDocument();
    expect(screen.queryByText("My Records")).not.toBeInTheDocument();
  });

  it("shows the Front Desk section in the drawer for a receptionist with R08 grants", async () => {
    const user = userEvent.setup();
    setSession({
      role: "receptionist",
      permissions: ["REGISTRATION_READ", "REGISTRATION_WRITE", "QUEUE_READ", "SCHEDULE_READ"],
    });
    renderWithRouter("/");
    await user.click(screen.getByLabelText("Menu"));
    expect(await screen.findByText("Front Desk")).toBeInTheDocument();
    await user.click(screen.getByText("Front Desk"));
    expect(await screen.findByText("Registration")).toBeInTheDocument();
    // S4 renamed the visits surface to Today's Schedule (/frontdesk/schedule);
    // the assertion tracks the shipped label.
    expect(screen.getByText("Today's Schedule")).toBeInTheDocument();
    expect(screen.getByText("Waiting Queue")).toBeInTheDocument();
    expect(screen.queryByText("My Records")).not.toBeInTheDocument();
  });
});
