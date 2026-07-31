import React from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import Account from "../account/Account";

const mockRequest = vi.hoisted(() => vi.fn());
vi.mock("../helpers", () => ({
  request: mockRequest,
  isAdmin: () => true,
  setTokens: () => {},
  clearTokens: () => {},
  startRefreshTimer: () => {},
  stopRefreshTimer: () => {},
}));

const mockProfile = {
  id: "u1",
  username: "alice",
  email: "alice@example.com",
  role: "admin",
  admin: true,
};

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <ThemeProvider>
      <AuthProvider>
        <MemoryRouter>{ui}</MemoryRouter>
      </AuthProvider>
    </ThemeProvider>,
  );
}

describe("Account", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRequest.mockResolvedValue({ data: mockProfile });
    localStorage.setItem("token", "test-token");
    localStorage.setItem("userId", "u1");
    localStorage.setItem("username", "alice");
    localStorage.setItem("admin", "true");
    localStorage.setItem("role", "admin");
    localStorage.setItem("tempKey", "test-key");
  });

  it("renders within MemoryRouter", () => {
    renderWithProviders(<Account />);
  });

  it("renders current password field", async () => {
    renderWithProviders(<Account />);
    expect(
      await screen.findByPlaceholderText("Current password"),
    ).toBeInTheDocument();
  });

  it("renders new password field", async () => {
    renderWithProviders(<Account />);
    expect(
      await screen.findByPlaceholderText("New password"),
    ).toBeInTheDocument();
  });

  it("renders confirm password field", async () => {
    renderWithProviders(<Account />);
    expect(
      await screen.findByPlaceholderText("Confirm new password"),
    ).toBeInTheDocument();
  });

  it("renders Change Password button", async () => {
    renderWithProviders(<Account />);
    expect(
      await screen.findByRole("button", { name: "Change Password" }),
    ).toBeInTheDocument();
  });
});
