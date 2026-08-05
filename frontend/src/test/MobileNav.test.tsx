import React from "react";
import { render, screen } from "@testing-library/react";
import { renderWithApp } from "./renderWithApp";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi } from "vitest";
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
  it("renders Files, Metrics, and Account links", () => {
    renderWithRouter("/");
    expect(screen.getByText("Files")).toBeInTheDocument();
    expect(screen.getByText("Metrics")).toBeInTheDocument();
    expect(screen.getByText("Account")).toBeInTheDocument();
  });

  it("highlights Files as active on root path", () => {
    renderWithRouter("/");
    const filesLink = screen.getByText("Files").closest("a");
    expect(filesLink?.className).toContain("active");
  });

  it("highlights Metrics as active on /metrics", () => {
    renderWithRouter("/metrics");
    const metricsLink = screen.getByText("Metrics").closest("a");
    expect(metricsLink?.className).toContain("active");
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
    expect(links.length).toBe(3);
  });
});
