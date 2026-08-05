import React from "react";
import { render, screen } from "@testing-library/react";
import { renderWithAuth } from "./renderWithApp";
import { MemoryRouter } from "react-router";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import LoginForm from "../login/Login";

const mockListLoginProviders = vi.hoisted(() => vi.fn());

vi.mock("../api/auth", () => ({
  listLoginProviders: mockListLoginProviders,
}));

vi.mock("../helpers", () => ({
  request: vi.fn(() => Promise.resolve({})),
  isAdmin: () => true,
  setTokens: () => {},
  clearTokens: () => {},
  startRefreshTimer: () => {},
  stopRefreshTimer: () => {},
}));

vi.mock("../hooks", () => ({
  useDocumentTitle: vi.fn(),
  useFetch: () => ({
    exec: vi.fn(),
    showLoading: false,
    loading: false,
    data: null,
    error: null,
  }),
}));

const mockProviders = [
  { id: "1", name: "Google", slug: "google", icon: null },
  { id: "2", name: "Microsoft", slug: "microsoft", icon: null },
];

describe("LoginForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListLoginProviders.mockResolvedValue(mockProviders);
  });

  it("renders login form", () => {
    renderWithAuth(<LoginForm />);
    expect(screen.getByText(/Sign in to your account/)).toBeInTheDocument();
    expect(screen.getByText("Sign In")).toBeInTheDocument();
  });

  it("renders SSO section with provider buttons", async () => {
    renderWithAuth(<LoginForm />);

    const googleBtns = await screen.findAllByText("Sign in with Google");
    expect(googleBtns.length).toBeGreaterThanOrEqual(1);
    const msBtns = await screen.findAllByText("Sign in with Microsoft");
    expect(msBtns.length).toBeGreaterThanOrEqual(1);
  });
});
