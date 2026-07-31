import React from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../common/ThemeProvider";
import LoginForm from "../login/Login";

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

function renderWithAuth(ui: React.ReactElement) {
  return render(
    <ThemeProvider>
      <AuthProvider>
        <MemoryRouter>{ui}</MemoryRouter>
      </AuthProvider>
    </ThemeProvider>,
  );
}

describe("LoginForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRequest.mockResolvedValue({ data: mockProviders });
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
